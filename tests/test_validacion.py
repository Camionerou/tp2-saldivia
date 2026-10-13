"""Validación de cada campo: puntos R11 a R28."""
import unittest
from datetime import date

from ayuda import renglon

from fuentes import FilaCruda
from modelos import Devolucion, RegistroLimpieza
from validacion import (ValorInvalido, limpiar_cantidad, limpiar_descuenta_stock,
                        limpiar_estado, limpiar_fecha, limpiar_proveedor,
                        limpiar_remito, limpiar_texto, validar_fila)


def validar(**cambios):
    """Valida un renglón con los cambios pedidos; devuelve (devolución, registro)."""
    registro = RegistroLimpieza()
    devolucion = validar_fila(FilaCruda(7, renglon(**cambios)), registro)
    return devolucion, registro


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

    def test_la_clase_devolucion_no_admite_valores_imposibles(self):
        base = dict(remito="0002-00000001", fecha=date(2026, 3, 10), proveedor="P",
                    articulo="", cantidad=1, motivo="", estado="abierta", descuenta_stock=None)
        for cambio in ({"cantidad": 0}, {"cantidad": True}, {"estado": "anulada"}, {"proveedor": ""}):
            with self.subTest(cambio=cambio):
                with self.assertRaises(ValueError):
                    Devolucion(**{**base, **cambio})


class TestRemito(unittest.TestCase):

    def test_R11_remito_mal_formado(self):
        for valor in ("0002-1127", "2-00001127", "A002-00001127", "0002_00001127",
                      "0002-000011270", "00020-0001127", "0002-00001127\n0002"):
            with self.subTest(valor=valor):
                with self.assertRaisesRegex(ValorInvalido, "formato 0000-00000000"):
                    limpiar_remito(valor)

    def test_R11_remito_valido(self):
        self.assertEqual(limpiar_remito("0002-00001127"), ("0002-00001127", None))

    def test_R12_remito_vacio(self):
        for valor in ("", "   ", None):
            with self.subTest(valor=valor):
                with self.assertRaisesRegex(ValorInvalido, "vacío"):
                    limpiar_remito(valor)


class TestFecha(unittest.TestCase):

    def test_R13_formato_no_reconocido(self):
        for valor in ("15-09-2026", "2026/09/15", "ayer", "2026-9-15", "", None, 20260915):
            with self.subTest(valor=valor):
                with self.assertRaisesRegex(ValorInvalido, "formato"):
                    limpiar_fecha(valor)

    def test_R13b_formato_argentino_se_convierte(self):
        fecha, correccion = limpiar_fecha("07/03/2026")
        self.assertEqual(fecha, date(2026, 3, 7))  # día/mes, nunca mes/día
        self.assertIn("dd/mm/aaaa", correccion)

    def test_R14_fecha_que_no_existe(self):
        for valor in ("2026-02-30", "31/04/2026", "2026-13-01", "2026-00-10", "2025-02-29"):
            with self.subTest(valor=valor):
                with self.assertRaisesRegex(ValorInvalido, "no existe en el calendario"):
                    limpiar_fecha(valor)

    def test_R14_bisiesto_valido(self):
        self.assertEqual(limpiar_fecha("2028-02-29"), (date(2028, 2, 29), None))


class TestCantidad(unittest.TestCase):

    def test_R16_cantidad_no_numerica(self):
        for valor in ("dos", "", None, "5 u.", "1e3"):
            with self.subTest(valor=valor):
                with self.assertRaisesRegex(ValorInvalido, "no es un número"):
                    limpiar_cantidad(valor)

    def test_R17_cantidad_cero_o_negativa(self):
        for valor in (0, -3, "0", "-3"):
            with self.subTest(valor=valor):
                with self.assertRaisesRegex(ValorInvalido, "al menos 1"):
                    limpiar_cantidad(valor)

    def test_R18_cantidad_con_decimales(self):
        for valor in (2.5, "2.5", "2,5"):
            with self.subTest(valor=valor):
                with self.assertRaisesRegex(ValorInvalido, "decimales"):
                    limpiar_cantidad(valor)

    def test_R18_real_entero_de_json_se_corrige(self):
        cantidad, correccion = limpiar_cantidad(3.0)
        self.assertEqual(cantidad, 3)
        self.assertIs(type(cantidad), int)
        self.assertIsNotNone(correccion)

    def test_R19_separador_de_miles_es_ambiguo(self):
        for valor in ("1.000", "12.500"):
            with self.subTest(valor=valor):
                with self.assertRaisesRegex(ValorInvalido, "ambigua"):
                    limpiar_cantidad(valor)

    def test_R20_booleano_no_es_cantidad(self):
        # isinstance(True, int) es True en Python: sin el chequeo, pasaría como 1.
        for valor in (True, False):
            with self.subTest(valor=valor):
                with self.assertRaisesRegex(ValorInvalido, "verdadero/falso"):
                    limpiar_cantidad(valor)

    def test_cantidades_validas(self):
        for valor, esperado in ((5, 5), ("5", 5), (" 12 ", 12), ("+3", 3)):
            with self.subTest(valor=valor):
                self.assertEqual(limpiar_cantidad(valor), (esperado, None))


class TestEstado(unittest.TestCase):

    def test_R21_estado_con_espacios_o_mayusculas(self):
        for valor, esperado in ((" Abierta ", "abierta"), ("CERRADA", "cerrada")):
            with self.subTest(valor=valor):
                estado, correccion = limpiar_estado(valor)
                self.assertEqual(estado, esperado)
                self.assertIn("normalizado", correccion)

    def test_R22_estado_desconocido(self):
        for valor in ("anulada", "", None, "abiert"):
            with self.subTest(valor=valor):
                with self.assertRaisesRegex(ValorInvalido, "no es 'abierta' ni 'cerrada'"):
                    limpiar_estado(valor)


class TestTextos(unittest.TestCase):

    def test_R23_proveedor_vacio(self):
        for valor in ("", "   ", None):
            with self.subTest(valor=valor):
                with self.assertRaisesRegex(ValorInvalido, "proveedor está vacío"):
                    limpiar_proveedor(valor)

    def test_R23b_articulo_vacio_se_conserva_con_aviso(self):
        devolucion, registro = validar(articulo="")
        self.assertIsNotNone(devolucion)
        self.assertEqual([(e.accion, e.motivo) for e in registro.eventos], [("aviso", "sin artículo")])

    def test_R24_espacios_de_mas(self):
        self.assertEqual(limpiar_proveedor("  Proveedor   01 "),
                         ("Proveedor 01", "se quitaron espacios de más"))
        self.assertEqual(limpiar_texto("Proveedor 01"), ("Proveedor 01", None))

    def test_R24_queda_anotado_en_el_registro(self):
        devolucion, registro = validar(proveedor="Proveedor 01 ")
        self.assertEqual(devolucion.proveedor, "Proveedor 01")
        self.assertEqual(registro.eventos[0].accion, "corregida")
        self.assertEqual(registro.eventos[0].valor_original, "Proveedor 01 ")

    def test_R26_motivo_vacio_se_conserva_con_aviso(self):
        devolucion, registro = validar(motivo="")
        self.assertIsNotNone(devolucion)
        self.assertEqual(devolucion.motivo, "")
        self.assertEqual([(e.accion, e.motivo) for e in registro.eventos], [("aviso", "sin motivo")])

    def test_R28_null_se_trata_como_vacio(self):
        devolucion, registro = validar(motivo=None)
        self.assertEqual(devolucion.motivo, "")
        _, registro = validar(proveedor=None)
        self.assertEqual(registro.eventos[0].motivo, "el proveedor está vacío")


class TestDescuentaStock(unittest.TestCase):

    def test_R27_variantes_de_si_y_no(self):
        for valor in (True, "si", "SI", "Sí", "true", "1", " s "):
            with self.subTest(valor=valor):
                self.assertEqual(limpiar_descuenta_stock(valor), (True, None))
        for valor in (False, "no", "NO", "false", "0"):
            with self.subTest(valor=valor):
                self.assertEqual(limpiar_descuenta_stock(valor), (False, None))

    def test_R27b_vacio_o_desconocido_se_conserva_sin_dato(self):
        for valor in ("", None, "tal vez"):
            with self.subTest(valor=valor):
                devolucion, registro = validar(descuenta_stock=valor)
                self.assertIsNone(devolucion.descuenta_stock)
                self.assertEqual(registro.eventos[0].motivo, "sin dato de stock")


if __name__ == "__main__":
    unittest.main()
