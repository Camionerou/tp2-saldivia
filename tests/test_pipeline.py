"""Duplicados, análisis y salidas: puntos R29 a R39, y el caso normal completo."""
import csv
import os
import unittest
from datetime import date

from ayuda import DATOS, TestConArchivos, renglon

from fuentes import ErrorEntrada
from pipeline import ErrorSalida, guardar_salidas, procesar, verificar_umbral


class TestCasoNormal(unittest.TestCase):
    """El extracto de data/ tiene errores conocidos: el resultado es exacto."""

    def setUp(self):
        self.resultado = procesar(DATOS / "devoluciones.csv")

    def test_conteos_de_la_limpieza(self):
        r = self.resultado
        self.assertEqual(r.filas_leidas, 83)
        self.assertEqual(len(r.validas), 75)
        self.assertEqual(r.registro.contar("rechazada"), 7)
        self.assertEqual(r.registro.contar("duplicada"), 1)
        self.assertEqual(r.registro.contar("corregida"), 5)

    def test_filas_rechazadas_y_motivos(self):
        rechazos = {e.numero_fila: e.campo for e in self.resultado.registro.eventos
                    if e.accion == "rechazada"}
        self.assertEqual(rechazos, {12: "fecha", 26: "remito", 32: "cantidad", 38: "cantidad",
                                    46: "cantidad", 49: "estado", 57: "proveedor"})

    def test_primer_puesto_del_ranking(self):
        primero = self.resultado.ranking[0]
        self.assertEqual((primero.proveedor, primero.renglones, primero.unidades),
                         ("Proveedor 01", 17, 179))
        self.assertEqual(len(self.resultado.ranking), 15)


class TestDuplicados(TestConArchivos):

    def test_R29_renglon_cargado_dos_veces(self):
        resultado = procesar(self.json([renglon(), renglon(), renglon(remito="0002-00000002")]))
        self.assertEqual(len(resultado.validas), 2)
        duplicadas = [e for e in resultado.registro.eventos if e.accion == "duplicada"]
        self.assertEqual(len(duplicadas), 1)
        self.assertEqual(duplicadas[0].numero_fila, 2)
        self.assertIn("fila 1", duplicadas[0].motivo)
        self.assertEqual(resultado.ranking[0].unidades, 10)  # no 15

    def test_R29_duplicado_detectado_despues_de_normalizar(self):
        resultado = procesar(self.json([renglon(), renglon(estado=" ABIERTA ", cantidad="5")]))
        self.assertEqual(resultado.registro.contar("duplicada"), 1)

    def test_R30_remito_con_varios_renglones_no_es_duplicado(self):
        resultado = procesar(self.json([renglon(articulo="Llave de luces"),
                                        renglon(articulo="Fusible térmico")]))
        self.assertEqual(len(resultado.validas), 2)
        self.assertEqual(resultado.registro.eventos, [])

    def test_R31_remito_reutilizado_se_conserva_y_avisa(self):
        resultado = procesar(self.json([
            renglon(fecha="2026-01-10", proveedor="Proveedor 01"),
            renglon(fecha="2026-09-01", proveedor="Proveedor 07"),
        ]))
        self.assertEqual(len(resultado.validas), 2)
        avisos = [e for e in resultado.registro.eventos if e.accion == "aviso"]
        self.assertEqual(len(avisos), 1)
        self.assertIn("remito reutilizado", avisos[0].motivo)


class TestAnalisis(TestConArchivos):

    def test_R15_fecha_posterior_al_corte(self):
        resultado = procesar(self.json([renglon(fecha="2026-03-01"), renglon(remito="0002-00000002"),
                                        renglon(remito="0002-00000003", fecha="2026-03-20")]),
                             corte=date(2026, 3, 10))
        self.assertEqual(len(resultado.validas), 2)
        rechazo = [e for e in resultado.registro.eventos if e.accion == "rechazada"]
        self.assertEqual(rechazo[0].numero_fila, 3)
        self.assertIn("posterior a la fecha de corte", rechazo[0].motivo)

    def test_R32_sin_corte_se_usa_la_fecha_mas_reciente(self):
        resultado = procesar(self.json([renglon(fecha="2026-03-01"),
                                        renglon(remito="0002-00000002", fecha="2026-05-20")]))
        self.assertEqual(resultado.corte, date(2026, 5, 20))
        self.assertEqual(resultado.ranking[0].dias_mas_vieja, 80)

    def test_R34_demasiadas_filas_rechazadas(self):
        resultado = procesar(self.json([renglon(), renglon(cantidad=0), renglon(cantidad="dos")]))
        with self.assertRaisesRegex(ErrorEntrada, "Se rechazaron 2 de 3 filas"):
            verificar_umbral(resultado)

    def test_R34_justo_en_el_umbral_no_aborta(self):
        verificar_umbral(procesar(self.json([renglon(), renglon(cantidad=0)])))

    def test_R34_corte_anterior_a_todo_el_extracto(self):
        resultado = procesar(self.json([renglon()]), corte=date(2025, 1, 1))
        with self.assertRaisesRegex(ErrorEntrada, "fecha de corte"):
            verificar_umbral(resultado)

    def test_R34_guarda_el_registro_y_borra_el_ranking_viejo(self):
        guardar_salidas(procesar(self.json([renglon()])), self.carpeta)
        self.assertTrue((self.carpeta / "ranking.csv").exists())
        malo = procesar(self.json([renglon(cantidad=0), renglon(cantidad=0), renglon()]))
        with self.assertRaises(ErrorEntrada):
            guardar_salidas(malo, self.carpeta)
        self.assertFalse((self.carpeta / "ranking.csv").exists())
        registro = (self.carpeta / "registro_limpieza.csv").read_text(encoding="utf-8-sig")
        self.assertEqual(registro.count("rechazada"), 2)

    def test_R35_sin_devoluciones_abiertas(self):
        resultado = procesar(self.json([renglon(estado="cerrada")]))
        self.assertEqual(resultado.ranking, [])
        guardar_salidas(resultado, self.carpeta / "salida")
        with open(self.carpeta / "salida" / "ranking.csv", encoding="utf-8-sig") as archivo:
            self.assertEqual(len(archivo.readlines()), 1)  # solo el encabezado

    def test_R36_desempate_total_del_ranking(self):
        datos = [
            renglon(remito="0002-00000001", proveedor="Proveedor C", fecha="2026-03-01"),
            renglon(remito="0002-00000002", proveedor="Proveedor B", fecha="2026-02-01"),
            renglon(remito="0002-00000003", proveedor="Proveedor A", fecha="2026-03-01"),
            renglon(remito="0002-00000004", proveedor="Proveedor D", fecha="2026-03-01", cantidad=9),
            renglon(remito="0002-00000005", proveedor="Proveedor E", fecha="2026-03-05"),
            renglon(remito="0002-00000006", proveedor="Proveedor E", fecha="2026-03-06"),
        ]
        resultado = procesar(self.json(datos), corte=date(2026, 3, 10))
        orden = [r.proveedor for r in resultado.ranking]
        # E: más renglones. B: más antigua. D: más unidades. A antes que C por nombre.
        self.assertEqual(orden, ["Proveedor E", "Proveedor B", "Proveedor D",
                                 "Proveedor A", "Proveedor C"])


class TestSalidas(TestConArchivos):

    def setUp(self):
        super().setUp()
        self.resultado = procesar(self.json([renglon(articulo="Válvula de freno")]))

    def test_R37_crea_la_carpeta_de_salida(self):
        destino = self.carpeta / "no" / "existe"
        guardar_salidas(self.resultado, destino)
        self.assertTrue((destino / "ranking.csv").is_file())
        self.assertTrue((destino / "registro_limpieza.csv").is_file())

    @unittest.skipIf(os.name == "nt" or os.geteuid() == 0, "los permisos POSIX no aplican")
    def test_R38_no_se_puede_escribir(self):
        destino = self.carpeta / "solo_lectura"
        destino.mkdir()
        destino.chmod(0o500)
        try:
            with self.assertRaisesRegex(ErrorSalida, "No se pudo escribir .*registro_limpieza.csv"):
                guardar_salidas(self.resultado, destino)
        finally:
            destino.chmod(0o700)

    def test_R39_salidas_con_bom_para_excel(self):
        guardar_salidas(self.resultado, self.carpeta)
        crudo = (self.carpeta / "ranking.csv").read_bytes()
        self.assertTrue(crudo.startswith(b"\xef\xbb\xbf"))
        with open(self.carpeta / "ranking.csv", encoding="utf-8-sig", newline="") as archivo:
            filas = list(csv.DictReader(archivo))
        self.assertEqual(filas[0]["proveedor"], "Proveedor 01")
        self.assertEqual(filas[0]["dias_abierta"], "0")


if __name__ == "__main__":
    unittest.main()
