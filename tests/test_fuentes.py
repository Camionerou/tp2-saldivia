"""Lectura del archivo y del esquema: puntos R01 a R10e."""
import unittest

from ayuda import DATOS, ENCABEZADO, TestConArchivos, renglon

from fuentes import ErrorEntrada, FuenteCSV, FuenteDatos, FuenteJSON, fuente_para

FILA_OK = "0002-00000001,2026-03-10,Proveedor 01,Llave de luces,5,falso contacto,abierta,no"


class TestContrato(TestConArchivos):

    def test_caso_normal_lee_los_dos_formatos(self):
        filas_csv = fuente_para(DATOS / "devoluciones.csv").cargar()
        filas_json = fuente_para(DATOS / "devoluciones.json").cargar()
        self.assertEqual(len(filas_csv), 83)
        self.assertEqual(len(filas_json), 83)
        self.assertEqual(filas_csv[0].numero_fila, 1)
        self.assertEqual(filas_csv[0].valores["remito"], "0002-00001101")

    def test_las_dos_fuentes_cumplen_el_contrato(self):
        self.assertIsInstance(FuenteCSV("x.csv"), FuenteDatos)
        self.assertIsInstance(FuenteJSON("x.json"), FuenteDatos)
        with self.assertRaises(TypeError):
            FuenteDatos("x")  # la clase base es abstracta


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

    def test_R03_la_extension_no_distingue_mayusculas(self):
        self.assertIsInstance(fuente_para("DEVOLUCIONES.CSV"), FuenteCSV)

    def test_R04_archivo_sin_devoluciones(self):
        casos = {
            "vacio.csv": "",
            "espacios.csv": "  \n\n",
            "solo_encabezado.csv": "remito,fecha,proveedor,articulo,cantidad,motivo,estado,descuenta_stock\n",
            "vacio.json": "",
            "lista_vacia.json": "[]",
        }
        for nombre, contenido in casos.items():
            with self.subTest(nombre=nombre):
                ruta = self.escribir(nombre, contenido)
                with self.assertRaisesRegex(ErrorEntrada, "vacío|no tiene devoluciones"):
                    fuente_para(ruta).cargar()

    def test_R05_codificacion_windows_1252(self):
        ruta = self.csv(FILA_OK.replace("Llave de luces", "Fusible térmico"),
                        codificacion="cp1252")
        fuente = fuente_para(ruta)
        filas = fuente.cargar()
        self.assertEqual(filas[0].valores["articulo"], "Fusible térmico")
        self.assertEqual(fuente.codificacion, "cp1252")
        self.assertTrue(any("Windows-1252" in a for a in fuente.avisos))

    def test_R05_codificacion_ilegible(self):
        # 0x81 no es UTF-8 válido y tampoco está definido en cp1252.
        ruta = self.escribir("raro.csv", b"remito\x81\n")
        with self.assertRaisesRegex(ErrorEntrada, "ni en Windows-1252"):
            fuente_para(ruta).cargar()

    def test_R06_bom_de_excel(self):
        ruta = self.csv(FILA_OK, codificacion="utf-8-sig")
        filas = fuente_para(ruta).cargar()
        self.assertIn("remito", filas[0].valores)
        self.assertEqual(filas[0].valores["remito"], "0002-00000001")

    def test_R07_separador_punto_y_coma(self):
        ruta = self.csv(FILA_OK.replace(",", ";"),
                        encabezado="remito;fecha;proveedor;articulo;cantidad;motivo;estado;descuenta_stock")
        fuente = fuente_para(ruta)
        filas = fuente.cargar()
        self.assertEqual(filas[0].valores["cantidad"], "5")
        self.assertTrue(any("';'" in a for a in fuente.avisos))

    def test_R07_coma_dentro_de_comillas_no_confunde_el_separador(self):
        ruta = self.csv(FILA_OK.replace("falso contacto", '"golpeado, con marcas"'))
        filas = fuente_para(ruta).cargar()
        self.assertEqual(filas[0].valores["motivo"], "golpeado, con marcas")
        self.assertIsNone(filas[0].problema)

    def test_R08_json_mal_formado(self):
        ruta = self.escribir("roto.json", '[{"remito": "0002-00000001",}]')
        with self.assertRaisesRegex(ErrorEntrada, r"mal formado \(línea 1, columna \d+\)"):
            fuente_para(ruta).cargar()

    def test_R09_raiz_del_json_no_es_lista(self):
        ruta = self.json({"devoluciones": [renglon()]})
        with self.assertRaisesRegex(ErrorEntrada, "debe ser una lista"):
            fuente_para(ruta).cargar()

    def test_R09_elemento_que_no_es_objeto(self):
        ruta = self.json([renglon(), ["0002-00000002", "2026-03-10"], renglon(remito="0002-00000003")])
        filas = fuente_para(ruta).cargar()
        self.assertEqual(len(filas), 3)
        self.assertEqual(filas[1].problema, "no es un objeto JSON")
        self.assertIsNone(filas[2].problema)


class TestEsquema(TestConArchivos):

    def test_R10_faltan_columnas_obligatorias(self):
        ruta = self.csv("0002-00000001,2026-03-10,5",
                        encabezado="remito,fecha,cantidad")
        with self.assertRaises(ErrorEntrada) as contexto:
            fuente_para(ruta).cargar()
        mensaje = str(contexto.exception)
        # Lista todas las faltantes juntas, no solo la primera.
        for columna in ("proveedor", "articulo", "motivo", "estado", "descuenta_stock"):
            self.assertIn(columna, mensaje)

    def test_R10_json_sin_un_campo_en_ningun_objeto(self):
        sin_proveedor = {k: v for k, v in renglon().items() if k != "proveedor"}
        ruta = self.json([sin_proveedor, sin_proveedor])
        with self.assertRaisesRegex(ErrorEntrada, "faltan columnas obligatorias: proveedor"):
            fuente_para(ruta).cargar()

    def test_R10b_encabezados_con_mayusculas_y_espacios(self):
        ruta = self.csv(FILA_OK, encabezado=" Remito ,FECHA,Proveedor,articulo,Cantidad,motivo,estado,descuenta_stock")
        filas = fuente_para(ruta).cargar()
        self.assertEqual(filas[0].valores["proveedor"], "Proveedor 01")

    def test_R10c_columnas_de_mas(self):
        ruta = self.csv(FILA_OK + ",nota interna",
                        encabezado="remito,fecha,proveedor,articulo,cantidad,motivo,estado,descuenta_stock,observaciones")
        fuente = fuente_para(ruta)
        fuente.cargar()
        self.assertTrue(any("observaciones" in a for a in fuente.avisos))

    def test_R10d_fila_con_campos_de_mas_o_de_menos(self):
        ruta = self.csv(FILA_OK, FILA_OK + ",sobra", "0002-00000003,2026-03-10,Proveedor 01")
        filas = fuente_para(ruta).cargar()
        self.assertIsNone(filas[0].problema)
        self.assertIn("tiene 9 campos", filas[1].problema)
        self.assertIn("tiene 3 campos", filas[2].problema)

    def test_R10d_objeto_json_al_que_le_falta_un_campo(self):
        incompleto = {k: v for k, v in renglon().items() if k != "cantidad"}
        filas = fuente_para(self.json([renglon(), incompleto])).cargar()
        self.assertIn("cantidad", filas[1].problema)

    def test_R10e_lineas_vacias_y_de_solo_separadores(self):
        ruta = self.csv(FILA_OK, "", ",,,,,,,", FILA_OK.replace("0001", "0002"))
        fuente = fuente_para(ruta)
        filas = fuente.cargar()
        self.assertEqual([f.numero_fila for f in filas], [1, 2])
        self.assertTrue(any("2 líneas vacías" in a for a in fuente.avisos))

    def test_R10f_lineas_vacias_antes_del_encabezado(self):
        ruta = self.escribir("arriba.csv", "\n;;;;;;;\n" + ENCABEZADO.replace(",", ";") + "\n"
                             + FILA_OK.replace(",", ";") + "\n")
        fuente = fuente_para(ruta)
        filas = fuente.cargar()
        self.assertEqual(filas[0].valores["proveedor"], "Proveedor 01")
        self.assertTrue(any("';'" in a for a in fuente.avisos))


if __name__ == "__main__":
    unittest.main()
