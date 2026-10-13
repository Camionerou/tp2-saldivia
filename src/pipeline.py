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


def verificar_umbral(resultado, umbral=UMBRAL_RECHAZO):
    """R34: si se rechaza más de la mitad, el problema es el archivo."""
    rechazadas = resultado.registro.contar("rechazada")
    if rechazadas > resultado.filas_leidas * umbral:
        raise ErrorEntrada(
            f"Se rechazaron {rechazadas} de {resultado.filas_leidas} filas (más del {umbral:.0%}). "
            f"Motivo más frecuente: {resultado.registro.motivo_mas_frecuente('rechazada')}. "
            "Probablemente el archivo no es un extracto de devoluciones, cambió su "
            "formato o la fecha de corte es incorrecta. Revisá registro_limpieza.csv.")


def armar_ranking(devoluciones, corte):
    """Agrupa las devoluciones abiertas por proveedor y las ordena (R36)."""
    resumenes = {}
    for d in devoluciones:
        if d.esta_abierta():
            resumen = resumenes.setdefault(d.proveedor, ResumenProveedor(d.proveedor))
            resumen.agregar(d, corte)
    return sorted(resumenes.values(), key=ResumenProveedor.orden)


def procesar(ruta, corte=None):
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

    return Resultado(len(filas), validas, armar_ranking(validas, corte),
                     registro, corte, fuente.avisos)


def escribir_csv(ruta, encabezado, filas):
    """Escribe un CSV pensado para abrir en Excel."""
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)  # R37
        # R39: utf-8-sig para que Excel muestre bien los acentos.
        with open(ruta, "w", encoding="utf-8-sig", newline="") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(encabezado)
            escritor.writerows(filas)
    except OSError as error:  # R38
        raise ErrorSalida(f"No se pudo escribir '{ruta}' ({error.strerror}). "
                          "¿Está abierto en Excel o la carpeta no tiene permisos?")


def guardar_salidas(resultado, carpeta):
    """Guarda el registro siempre y el ranking solo si el resultado es confiable.

    El registro va primero: si se rechazaron demasiadas filas (R34), es lo que
    sirve para diagnosticar. En ese caso se borra el ranking de una corrida
    anterior, para que no quede uno viejo al lado de un registro nuevo.
    """
    carpeta = Path(carpeta)
    escribir_csv(carpeta / "registro_limpieza.csv", RegistroLimpieza.COLUMNAS,
                 resultado.registro.como_filas())
    ruta_ranking = carpeta / "ranking.csv"
    try:
        verificar_umbral(resultado)
    except ErrorEntrada as error:
        try:
            ruta_ranking.unlink(missing_ok=True)
        except OSError:  # R38
            raise ErrorSalida(f"{error} Además, no se pudo borrar el ranking anterior "
                              f"'{ruta_ranking}': ¿está abierto en Excel?")
        raise error
    filas = []
    for posicion, r in enumerate(resultado.ranking, start=1):
        filas.append([posicion, r.proveedor, r.renglones, r.unidades,
                      r.fecha_mas_vieja.isoformat(), r.dias_mas_vieja])
    escribir_csv(ruta_ranking, COLUMNAS_RANKING, filas)
