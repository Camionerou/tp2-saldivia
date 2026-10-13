"""Lectura del archivo y del esquema: puntos R01 a R10f."""
import json
import unittest

from ayuda import DATOS, ENCABEZADO, TestConArchivos, renglon

from fuentes import ErrorEntrada, FuenteCSV, FuenteDatos, FuenteJSON, fuente_para

FILA_OK = "0002-00000001,2026-03-10,Proveedor 01,Llave de luces,5,falso contacto,abierta,no"
SIN_PROVEEDOR = {k: v for k, v in renglon().items() if k != "proveedor"}

# Archivos que no se pueden usar: (punto, nombre, contenido, parte del mensaje).
ABORTOS = [
    ("R04", "vacio.csv", "", "vacío"),
    ("R04", "espacios.csv", "  \n\n", "vacío"),
    ("R04", "solo_encabezado.csv", ENCABEZADO + "\n", "no tiene devoluciones"),
    ("R04", "vacio.json", "", "vacío"),
    ("R04", "lista_vacia.json", "[]", "no tiene devoluciones"),
    ("R05", "ilegible.csv", b"remito\x81\n", "ni en Windows-1252"),  # 0x81 no existe en cp1252
    ("R08", "roto.json", '[{"remito": "0002-00000001",}]', r"mal formado \(línea 1, columna \d+\)"),
    ("R09", "raiz_objeto.json", json.dumps({"devoluciones": [renglon()]}), "debe ser una lista"),
    ("R10", "faltan.csv", "remito,fecha,cantidad\n0002-00000001,2026-03-10,5\n",
     "faltan columnas obligatorias: proveedor, articulo, motivo, estado, descuenta_stock"),
    ("R10", "faltan.json", json.dumps([SIN_PROVEEDOR, SIN_PROVEEDOR]),
     "faltan columnas obligatorias: proveedor"),
]


class TestContrato(TestConArchivos):

    def test_caso_normal_lee_los_dos_formatos(self):
        filas_csv = fuente_para(DATOS / "devoluciones.csv").cargar()
        filas_json = fuente_para(DATOS / "devoluciones.json").cargar()
        self.assertEqual((len(filas_csv), len(filas_json)), (83, 83))
        self.assertEqual(filas_csv[0].numero_fila, 1)
        self.assertEqual(filas_csv[0].valores["remito"], "0002-00001101")

    def test_las_dos_fuentes_cumplen_el_contrato(self):
        self.assertIsInstance(FuenteCSV("x.csv"), FuenteDatos)
        self.assertIsInstance(FuenteJSON("x.json"), FuenteDatos)
        with self.assertRaises(TypeError):
            FuenteDatos("x")  # la clase base es abstracta

    def test_archivos_que_no_se_pueden_usar(self):
        for punto, nombre, contenido, mensaje in ABORTOS:
            with self.subTest(punto=punto, archivo=nombre):
                with self.assertRaisesRegex(ErrorEntrada, mensaje):
                    fuente_para(self.escribir(nombre, contenido)).cargar()


class TestArchivo(TestConArchivos):

    def test_R01_archivo_inexistente(self):
        with self.assertRaisesRegex(ErrorEntrada, "No se encontró el archivo"):
            fuente_para(self.carpeta / "no_existe.csv").cargar()

    def test_R02_la_ruta_es_una_carpeta(self):
        (self.carpeta / "carpeta.csv").mkdir()
        with self.assertRaisesRegex(ErrorEntrada, "es una carpeta"):
            fuente_para(self.carpeta / "carpeta.csv").cargar()

    def test_R03_extension_no_soportada(self):
        for nombre in ("devoluciones.xlsx", "devoluciones"):
            with self.subTest(nombre=nombre):
                with self.assertRaisesRegex(ErrorEntrada, r"no está soportado.*\.csv o \.json"):
                    fuente_para(nombre)
        self.assertIsInstance(fuente_para("DEVOLUCIONES.CSV"), FuenteCSV)

    def test_R05_codificacion_windows_1252(self):
        ruta = self.csv(FILA_OK.replace("Llave de luces", "Fusible térmico"), codificacion="cp1252")
        fuente = fuente_para(ruta)
        self.assertEqual(fuente.cargar()[0].valores["articulo"], "Fusible térmico")
        self.assertTrue(any("Windows-1252" in a for a in fuente.avisos))

    def test_R06_bom_de_excel(self):
        filas = fuente_para(self.csv(FILA_OK, codificacion="utf-8-sig")).cargar()
        self.assertEqual(filas[0].valores["remito"], "0002-00000001")

    def test_R07_separador_punto_y_coma(self):
        ruta = self.csv(FILA_OK.replace(",", ";"), encabezado=ENCABEZADO.replace(",", ";"))
        fuente = fuente_para(ruta)
        self.assertEqual(fuente.cargar()[0].valores["cantidad"], "5")
        self.assertTrue(any("';'" in a for a in fuente.avisos))

    def test_R07_coma_dentro_de_comillas_no_confunde_el_separador(self):
        filas = fuente_para(self.csv(FILA_OK.replace("falso contacto", '"golpeado, con marcas"'))).cargar()
        self.assertEqual(filas[0].valores["motivo"], "golpeado, con marcas")
        self.assertIsNone(filas[0].problema)

    def test_R09_elemento_que_no_es_objeto(self):
        filas = fuente_para(self.json([renglon(), ["0002-00000002"], renglon()])).cargar()
        self.assertEqual([f.problema for f in filas], [None, "no es un objeto JSON", None])


class TestEsquema(TestConArchivos):

    def test_R10b_encabezados_con_mayusculas_y_espacios(self):
        ruta = self.csv(FILA_OK, encabezado=" Remito ,FECHA" + ENCABEZADO[len("remito,fecha"):])
        self.assertEqual(fuente_para(ruta).cargar()[0].valores["remito"], "0002-00000001")

    def test_R10c_columnas_de_mas(self):
        fuente = fuente_para(self.csv(FILA_OK + ",nota", encabezado=ENCABEZADO + ",observaciones"))
        fuente.cargar()
        self.assertTrue(any("observaciones" in a for a in fuente.avisos))

    def test_R10d_fila_con_campos_de_mas_o_de_menos(self):
        filas = fuente_para(self.csv(FILA_OK, FILA_OK + ",sobra", "0002-00000003,2026-03-10")).cargar()
        self.assertIsNone(filas[0].problema)
        self.assertIn("tiene 9 campos", filas[1].problema)
        self.assertIn("tiene 2 campos", filas[2].problema)

    def test_R10d_objeto_json_al_que_le_falta_un_campo(self):
        incompleto = {k: v for k, v in renglon().items() if k != "cantidad"}
        filas = fuente_para(self.json([renglon(), incompleto])).cargar()
        self.assertIn("cantidad", filas[1].problema)

    def test_R10e_lineas_vacias_y_de_solo_separadores(self):
        fuente = fuente_para(self.csv(FILA_OK, "", ",,,,,,,", FILA_OK))
        self.assertEqual([f.numero_fila for f in fuente.cargar()], [1, 2])
        self.assertTrue(any("2 líneas vacías" in a for a in fuente.avisos))

    def test_R10f_lineas_vacias_antes_del_encabezado(self):
        ruta = self.escribir("arriba.csv", "\n;;;;;;;\n" + ENCABEZADO.replace(",", ";") + "\n"
                             + FILA_OK.replace(",", ";") + "\n")
        fuente = fuente_para(ruta)
        self.assertEqual(fuente.cargar()[0].valores["proveedor"], "Proveedor 01")
        self.assertTrue(any("';'" in a for a in fuente.avisos))


if __name__ == "__main__":
    unittest.main()
