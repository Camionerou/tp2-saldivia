"""Flujo completo: leer -> validar -> limpiar -> analizar -> guardar.

Cada etapa es una función con una sola responsabilidad; `procesar` las encadena.
Los comentarios `# Rxx` remiten a docs/puntos_de_ruptura.md.
"""
import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from fuentes import ErrorEntrada, fuente_para
from modelos import RegistroLimpieza, ResumenProveedor
from validacion import validar_fila

UMBRAL_RECHAZO = 0.5
COLUMNAS_RANKING = ("posicion", "proveedor", "renglones_abiertos", "unidades",
                    "devolucion_mas_vieja", "dias_abierta",
                    "hasta_30_dias", "31_a_90_dias", "91_a_180_dias", "mas_de_180_dias",
                    "cerradas", "porcentaje_resuelto")


class ErrorSalida(Exception):
    """No se pudieron escribir las salidas. El mensaje es para el usuario."""


@dataclass
class Resultado:
    filas_leidas: int
    validas: list
    ranking: list
    registro: RegistroLimpieza
    corte: date | None
    avisos: list


def validar_filas(filas, registro):
    validas = []
    for fila in filas:
        devolucion = validar_fila(fila, registro)
        if devolucion is not None:
            validas.append(devolucion)
    return validas


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
    """Agrupa las devoluciones por proveedor y ordena los que tienen abiertas (R36).

    Las cerradas también se agrupan para calcular el porcentaje resuelto (R41), pero
    un proveedor sin abiertas no tiene nada que reclamarle y queda afuera.
    """
    resumenes = {}
    for d in devoluciones:
        resumen = resumenes.setdefault(d.proveedor, ResumenProveedor(d.proveedor))
        resumen.agregar(d, corte)
    con_abiertas = [r for r in resumenes.values() if r.renglones]
    return sorted(con_abiertas, key=ResumenProveedor.orden)


def procesar(ruta, corte=None):
    fuente = fuente_para(ruta)
    filas = fuente.cargar()
    registro = RegistroLimpieza()

    validas = validar_filas(filas, registro)
    validas = quitar_duplicados(validas, registro)
    avisar_remitos_reutilizados(validas, registro)

    if validas:
        # R32: sin corte explícito se usa la fecha más reciente del extracto, no la
        # de hoy, para que el resultado dependa solo de la entrada.
        corte = corte or max(d.fecha for d in validas)
        validas = filtrar_por_corte(validas, corte, registro)

    # P01: toda fila leída termina válida o anotada en el registro. Si no, es un bug.
    descartadas = registro.contar("rechazada") + registro.contar("duplicada")
    if len(validas) + descartadas != len(filas):
        raise RuntimeError(f"La limpieza perdió filas: {len(validas)} válidas + {descartadas} "
                           f"descartadas no suman las {len(filas)} leídas.")

    return Resultado(len(filas), validas, armar_ranking(validas, corte),
                     registro, corte, fuente.avisos)


def escribir_csv(ruta, encabezado, filas):
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
    sirve para diagnosticar. El ranking y su gráfico de una corrida anterior se borran
    antes de verificar el umbral, para que no queden viejos al lado de un registro nuevo.
    """
    carpeta = Path(carpeta)
    escribir_csv(carpeta / "registro_limpieza.csv", RegistroLimpieza.COLUMNAS,
                 resultado.registro.como_filas())
    ruta_ranking = carpeta / "ranking.csv"
    for anterior in (ruta_ranking, carpeta / "ranking.png"):
        try:
            anterior.unlink(missing_ok=True)
        except OSError:  # R38
            raise ErrorSalida(f"No se pudo reemplazar '{anterior}': ¿está abierto en otro programa?")
    verificar_umbral(resultado)
    filas = []
    for posicion, r in enumerate(resultado.ranking, start=1):
        filas.append([posicion, r.proveedor, r.renglones, r.unidades,
                      r.fecha_mas_vieja.isoformat(), r.dias_mas_vieja, *r.por_tramo,
                      r.cerradas, r.porcentaje_resuelto()])
    escribir_csv(ruta_ranking, COLUMNAS_RANKING, filas)
