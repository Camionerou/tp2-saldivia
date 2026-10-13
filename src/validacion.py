"""Validación y limpieza de cada campo de una fila.

Cada función `limpiar_<campo>` recibe el valor crudo (texto si viene del CSV,
cualquier tipo si viene del JSON) y:

- devuelve `(valor_limpio, correccion)`, donde `correccion` es None o un texto que
  explica qué se cambió;
- o lanza `ValorInvalido` con un motivo en castellano si la fila no se puede usar.

Los comentarios `# Rxx` remiten a docs/puntos_de_ruptura.md.
"""
import re
from datetime import date

from modelos import ESTADOS, Devolucion

# Remito: 4 dígitos de punto de venta, guion y 8 dígitos de número (0002-00001103).
PATRON_REMITO = re.compile(r"\d{4}-\d{8}")
# Fecha ISO (2026-03-07) y fecha argentina día/mes/año (07/03/2026).
PATRON_FECHA_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
PATRON_FECHA_AR = re.compile(r"(\d{2})/(\d{2})/(\d{4})")
# Cantidad entera, con signo opcional para poder dar un mensaje claro si es negativa.
PATRON_ENTERO = re.compile(r"[+-]?\d+")
# 1.000 / 12.500: separador de miles argentino (ambiguo, ver R19).
PATRON_MILES = re.compile(r"\d{1,3}(\.\d{3})+")
# 2.5 / 2,5: número con decimales.
PATRON_DECIMAL = re.compile(r"[+-]?\d+[.,]\d+")

VERDADEROS = {"si", "sí", "s", "true", "verdadero", "1"}
FALSOS = {"no", "n", "false", "falso", "0"}


class ValorInvalido(Exception):
    """El valor no se puede usar y la fila se rechaza. El mensaje explica por qué."""


def como_texto(valor):
    """R28: None (null en JSON) se trata como texto vacío."""
    return "" if valor is None else str(valor)


def limpiar_texto(valor):
    """R24: quita espacios al inicio y al final y colapsa los repetidos."""
    original = como_texto(valor)
    limpio = " ".join(original.split())
    correccion = "se quitaron espacios de más" if limpio != original else None
    return limpio, correccion


def limpiar_remito(valor):
    remito, correccion = limpiar_texto(valor)
    if not remito:
        raise ValorInvalido("el remito está vacío")  # R12
    if not PATRON_REMITO.fullmatch(remito):  # R11
        raise ValorInvalido("el remito no tiene el formato 0000-00000000 "
                            "(4 dígitos, guion, 8 dígitos)")
    return remito, correccion


def limpiar_fecha(valor):
    texto, _ = limpiar_texto(valor)
    iso = PATRON_FECHA_ISO.fullmatch(texto)
    argentina = PATRON_FECHA_AR.fullmatch(texto)
    if iso:
        anio, mes, dia = iso.groups()
        correccion = None
    elif argentina:  # R13b
        dia, mes, anio = argentina.groups()
        correccion = "fecha en formato dd/mm/aaaa convertida a aaaa-mm-dd"
    else:  # R13
        raise ValorInvalido("la fecha no tiene formato aaaa-mm-dd ni dd/mm/aaaa")
    # R14: la regex solo mira la forma; date() comprueba que el día exista.
    try:
        return date(int(anio), int(mes), int(dia)), correccion
    except ValueError:
        raise ValorInvalido(f"la fecha {texto} no existe en el calendario")


def limpiar_cantidad(valor):
    # R20: en Python True es un int (True + 1 == 2); hay que descartarlo antes.
    if isinstance(valor, bool):
        raise ValorInvalido("la cantidad es un valor verdadero/falso, no un número")
    if isinstance(valor, float):
        if not valor.is_integer():  # R18
            raise ValorInvalido("la cantidad tiene decimales y se devuelven piezas enteras")
        cantidad, correccion = int(valor), "cantidad escrita como real convertida a entero"
    elif isinstance(valor, int):
        cantidad, correccion = valor, None
    else:
        texto = como_texto(valor).strip()
        if PATRON_ENTERO.fullmatch(texto):
            cantidad, correccion = int(texto), None
        elif PATRON_MILES.fullmatch(texto):  # R19
            raise ValorInvalido(f"la cantidad '{texto}' es ambigua: puede ser "
                                "un número con separador de miles o con decimales")
        elif PATRON_DECIMAL.fullmatch(texto):  # R18
            raise ValorInvalido("la cantidad tiene decimales y se devuelven piezas enteras")
        else:  # R16
            raise ValorInvalido("la cantidad está vacía o no es un número")
    if cantidad < 1:  # R17
        raise ValorInvalido(f"la cantidad debe ser al menos 1 y es {cantidad}")
    return cantidad, correccion


def limpiar_estado(valor):
    original = como_texto(valor)
    estado = original.strip().lower()
    if estado not in ESTADOS:  # R22
        raise ValorInvalido(f"el estado '{original}' no es 'abierta' ni 'cerrada'")
    correccion = f"estado '{original}' normalizado a '{estado}'" if estado != original else None  # R21
    return estado, correccion


def limpiar_proveedor(valor):
    proveedor, correccion = limpiar_texto(valor)  # R24
    if not proveedor:  # R23
        raise ValorInvalido("el proveedor está vacío")
    return proveedor, correccion


def limpiar_descuenta_stock(valor):
    """R27: interpreta las distintas formas de escribir sí/no. R27b: vacío -> None."""
    if isinstance(valor, bool):
        return valor, None
    texto = como_texto(valor).strip().lower()
    if texto in VERDADEROS:
        return True, None
    if texto in FALSOS:
        return False, None
    return None, None


def validar_fila(fila, registro):
    """Convierte una `FilaCruda` en `Devolucion` o devuelve None si se rechaza.

    Junta todos los problemas de la fila antes de decidir, para que el registro
    muestre todo lo que hay que arreglar y no solo el primer error.
    """
    valores = fila.valores
    remito_original = como_texto(valores.get("remito")).strip()
    if fila.problema:  # R09, R10d
        registro.anotar(fila.numero_fila, remito_original, "rechazada", "fila", "", fila.problema)
        return None

    limpiadores = {
        "remito": limpiar_remito,
        "fecha": limpiar_fecha,
        "proveedor": limpiar_proveedor,
        "articulo": limpiar_texto,
        "cantidad": limpiar_cantidad,
        "motivo": limpiar_texto,
        "estado": limpiar_estado,
        "descuenta_stock": limpiar_descuenta_stock,
    }
    limpios, errores, correcciones = {}, [], []
    for campo, limpiar in limpiadores.items():
        try:
            limpios[campo], correccion = limpiar(valores[campo])
            if correccion:
                correcciones.append((campo, correccion))
        except ValorInvalido as error:
            errores.append((campo, str(error)))

    if errores:
        for campo, motivo in errores:
            registro.anotar(fila.numero_fila, remito_original, "rechazada", campo, valores[campo], motivo)
        return None

    for campo, motivo in correcciones:
        registro.anotar(fila.numero_fila, remito_original, "corregida", campo, valores[campo], motivo)
    if not limpios["articulo"]:  # R23b
        registro.anotar(fila.numero_fila, remito_original, "aviso", "articulo", "", "sin artículo")
    if not limpios["motivo"]:  # R26
        registro.anotar(fila.numero_fila, remito_original, "aviso", "motivo", "", "sin motivo")
    if limpios["descuenta_stock"] is None:  # R27b
        registro.anotar(fila.numero_fila, remito_original, "aviso", "descuenta_stock",
                        valores["descuenta_stock"], "sin dato de stock")

    return Devolucion(numero_fila=fila.numero_fila, **limpios)
