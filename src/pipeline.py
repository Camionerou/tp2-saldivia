"""Flujo completo: leer -> validar -> limpiar -> analizar -> guardar.

Cada etapa es una función con una sola responsabilidad; `procesar` las encadena.
Los comentarios `# Rxx` remiten a docs/puntos_de_ruptura.md.
"""
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from fuentes import ErrorEntrada, fuente_para
from modelos import RegistroLimpieza, ResumenProveedor
from validacion import validar_fila

UMBRAL_RECHAZO = 0.5
COLUMNAS_RANKING = ("posicion", "proveedor", "renglones_abiertos", "unidades",
                    "devolucion_mas_vieja", "dias_abierta")


class ErrorUmbral(ErrorEntrada):
    """Se rechazaron demasiadas filas. Lleva el registro para poder guardarlo igual."""

    def __init__(self, mensaje, registro):
        super().__init__(mensaje)
        self.registro = registro


class ErrorSalida(Exception):
    """No se pudieron escribir las salidas. El mensaje es para el usuario."""


@dataclass
class Resultado:
    filas_leidas: int
    validas: list
    ranking: list
    registro: RegistroLimpieza
    corte: object
    avisos: list


def validar_filas(filas, registro):
    """Valida cada fila cruda; las que no sirven quedan en el registro."""
    return [d for d in (validar_fila(f, registro) for f in filas) if d is not None]


def quitar_duplicados(devoluciones, registro):
    """R29: conserva la primera aparición de cada renglón idéntico.

    La clave es el renglón completo y no el número de remito: un remito puede
    tener varios renglones (R30) y la numeración se reutiliza (R31).
    """
    vistas = {}
    unicas = []
    for d in devoluciones:
        if d.clave() in vistas:
            registro.anotar(d.numero_fila, d.remito, "duplicada", "fila", "",
                            f"renglón idéntico al de la fila {vistas[d.clave()]}")
        else:
            vistas[d.clave()] = d.numero_fila
            unicas.append(d)
    return unicas


def avisar_remitos_reutilizados(devoluciones, registro):
    """R31: el mismo número de remito con otra fecha u otro proveedor."""
    primera = {}
    for d in devoluciones:
        if d.remito not in primera:
            primera[d.remito] = d
            continue
        original = primera[d.remito]
        if (d.fecha, d.proveedor) != (original.fecha, original.proveedor):
            registro.anotar(d.numero_fila, d.remito, "aviso", "remito", d.remito,
                            f"remito reutilizado: ya se usó en la fila {original.numero_fila} "
                            f"({original.fecha}, {original.proveedor})")


def avisar_proveedores_parecidos(devoluciones, registro):
    """R25: nombres que solo difieren en mayúsculas. Se avisa pero no se unifican."""
    variantes = defaultdict(set)
    for d in devoluciones:
        variantes[d.proveedor.casefold()].add(d.proveedor)
    for nombres in variantes.values():
        if len(nombres) > 1:
            registro.anotar(None, "", "aviso", "proveedor", " / ".join(sorted(nombres)),
                            "mismo nombre con distintas mayúsculas; no se unificaron")


def filtrar_por_corte(devoluciones, corte, registro):
    """R15: una devolución posterior a la fecha de corte todavía no existía."""
    dentro = []
    for d in devoluciones:
        if d.fecha > corte:
            registro.anotar(d.numero_fila, d.remito, "rechazada", "fecha", d.fecha.isoformat(),
                            f"posterior a la fecha de corte {corte}")
        else:
            dentro.append(d)
    return dentro


def verificar_umbral(filas_leidas, registro, umbral=UMBRAL_RECHAZO):
    """R34: si se rechaza más de la mitad, el problema es el archivo."""
    rechazadas = registro.contar("rechazada")
    if rechazadas > filas_leidas * umbral:
        raise ErrorUmbral(
            f"Se rechazaron {rechazadas} de {filas_leidas} filas (más del {umbral:.0%}). "
            f"Motivo más frecuente: {registro.motivo_mas_frecuente('rechazada')}. "
            "Probablemente el archivo no es un extracto de devoluciones, cambió su "
            "formato o la fecha de corte es incorrecta.", registro)


def armar_ranking(devoluciones, corte):
    """Agrupa las devoluciones abiertas por proveedor y las ordena (R36)."""
    resumenes = {}
    for d in devoluciones:
        if d.esta_abierta():
            resumen = resumenes.setdefault(d.proveedor, ResumenProveedor(d.proveedor))
            resumen.agregar(d, corte)
    return sorted(resumenes.values(), key=ResumenProveedor.orden)


def procesar(ruta, corte=None, umbral=UMBRAL_RECHAZO):
    """Ejecuta el flujo completo sobre un archivo y devuelve el `Resultado`."""
    fuente = fuente_para(ruta)
    filas = fuente.cargar()
    registro = RegistroLimpieza()

    validas = validar_filas(filas, registro)
    validas = quitar_duplicados(validas, registro)
    avisar_remitos_reutilizados(validas, registro)
    avisar_proveedores_parecidos(validas, registro)

    if validas:
        # R32: sin corte explícito se usa la fecha más reciente del extracto, no la
        # de hoy, para que el resultado dependa solo de la entrada.
        corte = corte or max(d.fecha for d in validas)
        validas = filtrar_por_corte(validas, corte, registro)
    verificar_umbral(len(filas), registro, umbral)

    return Resultado(len(filas), validas, armar_ranking(validas, corte),
                     registro, corte, fuente.avisos)


def guardar_ranking(ranking, ruta):
    # R39: utf-8-sig para que Excel muestre bien los acentos.
    with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(COLUMNAS_RANKING)
        for posicion, r in enumerate(ranking, start=1):
            escritor.writerow([posicion, r.proveedor, r.renglones, r.unidades,
                               r.fecha_mas_vieja.isoformat(), r.dias_mas_vieja])


def guardar_salidas(resultado, carpeta):
    """Escribe ranking.csv y registro_limpieza.csv en `carpeta`."""
    carpeta = Path(carpeta)
    ruta = carpeta / "ranking.csv"
    try:
        carpeta.mkdir(parents=True, exist_ok=True)  # R37
        guardar_ranking(resultado.ranking, ruta)
        ruta = carpeta / "registro_limpieza.csv"
        resultado.registro.guardar(ruta)
    except OSError as error:  # R38
        raise ErrorSalida(f"No se pudo escribir '{ruta}' ({error.strerror}). "
                           "¿Está abierto en Excel o la carpeta no tiene permisos?") from None
