"""Validación de cada campo: puntos R11 a R28.

Los casos están en tablas: cada fila es un caso, con el punto de ruptura que
cubre. Para agregar un caso basta con agregar una fila.
"""
import unittest
from datetime import date

from ayuda import renglon

from fuentes import FilaCruda
from modelos import Devolucion, RegistroLimpieza
from validacion import (ValorInvalido, limpiar_cantidad, limpiar_descuenta_stock,
                        limpiar_estado, limpiar_fecha, limpiar_proveedor,
                        limpiar_remito, validar_fila)

# Valores que hacen rechazar la fila: (punto, función, valor, parte del mensaje).
RECHAZOS = [
    ("R11", limpiar_remito, "0002-1127", "formato 0000-00000000"),
    ("R11", limpiar_remito, "A002-00001127", "formato 0000-00000000"),
    ("R11", limpiar_remito, "0002-000011270", "formato 0000-00000000"),
    ("R11", limpiar_remito, "0002-00001127\n0002", "formato 0000-00000000"),
    ("R12", limpiar_remito, "   ", "vacío"),
    ("R13", limpiar_fecha, "15-09-2026", "formato"),
    ("R13", limpiar_fecha, "2026/09/15", "formato"),
    ("R13", limpiar_fecha, "2026-9-15", "formato"),
    ("R13", limpiar_fecha, 20260915, "formato"),
    ("R14", limpiar_fecha, "2026-02-30", "no existe en el calendario"),
    ("R14", limpiar_fecha, "31/04/2026", "no existe en el calendario"),
    ("R14", limpiar_fecha, "2026-13-01", "no existe en el calendario"),
    ("R14", limpiar_fecha, "2025-02-29", "no existe en el calendario"),  # no bisiesto
    ("R16", limpiar_cantidad, "dos", "no es un número"),
    ("R16", limpiar_cantidad, "", "no es un número"),
    ("R16", limpiar_cantidad, "1e3", "no es un número"),
    ("R17", limpiar_cantidad, 0, "al menos 1"),
    ("R17", limpiar_cantidad, "-3", "al menos 1"),
    ("R18", limpiar_cantidad, 2.5, "decimales"),
    ("R18", limpiar_cantidad, "2,5", "decimales"),
    ("R18", limpiar_cantidad, "1.000", "separador de miles"),  # ¿mil o uno? no se adivina
    ("R20", limpiar_cantidad, True, "verdadero/falso"),  # isinstance(True, int) es True
    ("R20", limpiar_cantidad, False, "verdadero/falso"),
    ("R22", limpiar_estado, "anulada", "no es 'abierta' ni 'cerrada'"),
    ("R22", limpiar_estado, "", "no es 'abierta' ni 'cerrada'"),
    ("R23", limpiar_proveedor, "   ", "proveedor está vacío"),
    ("R28", limpiar_remito, None, "vacío"),
    ("R28", limpiar_cantidad, None, "no es un número"),
    ("R28", limpiar_proveedor, None, "proveedor está vacío"),
]

# Valores que se aceptan: (punto, función, valor, valor limpio, ¿se anota corrección?).
ACEPTADOS = [
    ("R11", limpiar_remito, "0002-00001127", "0002-00001127", False),
    ("R13b", limpiar_fecha, "07/03/2026", date(2026, 3, 7), True),  # día/mes, nunca mes/día
    ("R14", limpiar_fecha, "2028-02-29", date(2028, 2, 29), False),  # bisiesto
    ("R18", limpiar_cantidad, 3.0, 3, True),
    ("R21", limpiar_estado, " Abierta ", "abierta", True),
    ("R21", limpiar_estado, "CERRADA", "cerrada", True),
    ("R24", limpiar_proveedor, "  Proveedor   01 ", "Proveedor 01", True),
    ("R27", limpiar_descuenta_stock, "SI", True, False),
    ("R27", limpiar_descuenta_stock, "sí", True, False),
    ("R27", limpiar_descuenta_stock, "1", True, False),
    ("R27", limpiar_descuenta_stock, "false", False, False),
    ("R27", limpiar_descuenta_stock, " no ", False, False),
    ("R27b", limpiar_descuenta_stock, "tal vez", None, False),
    (None, limpiar_cantidad, " 12 ", 12, False),
    (None, limpiar_cantidad, "+3", 3, False),
]

# Faltantes que no intervienen en la pregunta: la fila se conserva con un aviso.
# (punto, campo, valor, aviso esperado)
CONSERVADOS = [
    ("R23b", "articulo", "", "sin artículo"),
    ("R26", "motivo", "", "sin motivo"),
    ("R26", "motivo", None, "sin motivo"),
    ("R27b", "descuenta_stock", "", "sin dato de stock"),
    ("R27b", "descuenta_stock", None, "sin dato de stock"),
]


def validar(**cambios):
    """Valida un renglón con los cambios pedidos; devuelve (devolución, registro)."""
    registro = RegistroLimpieza()
    devolucion = validar_fila(FilaCruda(7, renglon(**cambios)), registro)
    return devolucion, registro


class TestCampos(unittest.TestCase):

    def test_rechazos(self):
        for punto, limpiar, valor, mensaje in RECHAZOS:
            with self.subTest(punto=punto, valor=valor):
                with self.assertRaisesRegex(ValorInvalido, mensaje):
                    limpiar(valor)

    def test_aceptados(self):
        for punto, limpiar, valor, esperado, corrige in ACEPTADOS:
            with self.subTest(punto=punto, valor=valor):
                limpio, correccion = limpiar(valor)
                self.assertEqual(limpio, esperado)
                self.assertIs(type(limpio), type(esperado))  # 3 y no 3.0; True y no 1
                self.assertEqual(correccion is not None, corrige)

    def test_conservados_con_aviso(self):
        for punto, campo, valor, aviso in CONSERVADOS:
            with self.subTest(punto=punto, campo=campo, valor=valor):
                devolucion, registro = validar(**{campo: valor})
                self.assertIsNotNone(devolucion)
                self.assertEqual([(e.accion, e.motivo) for e in registro.eventos], [("aviso", aviso)])


class TestFilaCompleta(unittest.TestCase):

    def test_caso_normal(self):
        devolucion, registro = validar()
        self.assertEqual(devolucion, Devolucion("0002-00000001", date(2026, 3, 10), "Proveedor 01",
                                                "Llave de luces", 5, "falso contacto", "abierta", False,
                                                numero_fila=7))
        self.assertEqual(registro.eventos, [])

    def test_una_fila_con_varios_errores_los_registra_todos(self):
        devolucion, registro = validar(fecha="2026-02-30", cantidad="dos")
        self.assertIsNone(devolucion)
        self.assertEqual({e.campo for e in registro.eventos}, {"fecha", "cantidad"})
        self.assertEqual(registro.contar("rechazada"), 1)  # una fila, dos motivos

    def test_fila_rechazada_no_anota_correcciones(self):
        _, registro = validar(estado=" Abierta ", cantidad=0)
        self.assertEqual([e.accion for e in registro.eventos], ["rechazada"])

    def test_R24_la_correccion_queda_en_el_registro(self):
        devolucion, registro = validar(proveedor="Proveedor 01 ")
        self.assertEqual(devolucion.proveedor, "Proveedor 01")
        self.assertEqual((registro.eventos[0].accion, registro.eventos[0].valor_original),
                         ("corregida", "Proveedor 01 "))


if __name__ == "__main__":
    unittest.main()
