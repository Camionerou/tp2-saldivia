"""Contrato de la línea de comandos: códigos de salida, mensajes y R33."""
import subprocess
import sys
import unittest

from ayuda import DATOS, RAIZ, TestConArchivos, renglon

MAIN = RAIZ / "src" / "main.py"


def ejecutar(*argumentos):
    """Corre la aplicación como lo haría el usuario y devuelve el proceso terminado."""
    return subprocess.run([sys.executable, str(MAIN), *map(str, argumentos)],
                          capture_output=True, text=True, encoding="utf-8")


class TestLineaDeComandos(TestConArchivos):

    def test_caso_normal_termina_con_codigo_0(self):
        proceso = ejecutar(DATOS / "devoluciones.csv", "--salida", self.carpeta)
        self.assertEqual(proceso.returncode, 0, proceso.stderr)
        self.assertIn("Filas leídas: 83 | válidas: 75 | rechazadas: 7", proceso.stdout)
        self.assertIn("Proveedor 01", proceso.stdout)
        self.assertTrue((self.carpeta / "ranking.csv").is_file())

    def test_error_de_entrada_termina_con_codigo_1_sin_traceback(self):
        proceso = ejecutar(self.carpeta / "no_existe.csv", "--salida", self.carpeta)
        self.assertEqual(proceso.returncode, 1)
        self.assertIn("Error: No se encontró el archivo", proceso.stderr)
        self.assertNotIn("Traceback", proceso.stderr)
        self.assertFalse((self.carpeta / "ranking.csv").exists())

    def test_R33_fecha_de_corte_invalida_es_error_de_uso(self):
        for corte in ("2026-13-01", "15/09/2026", "mañana"):
            with self.subTest(corte=corte):
                proceso = ejecutar(DATOS / "devoluciones.csv", "--corte", corte,
                                   "--salida", self.carpeta)
                self.assertEqual(proceso.returncode, 2)
                self.assertIn("no es una fecha válida", proceso.stderr)

    def test_R33_corte_explicito(self):
        proceso = ejecutar(DATOS / "devoluciones.json", "--corte", "2026-06-30",
                           "--salida", self.carpeta)
        self.assertEqual(proceso.returncode, 0, proceso.stderr)
        self.assertIn("Fecha de corte: 2026-06-30", proceso.stdout)

    def test_R34_umbral_guarda_el_registro_para_diagnosticar(self):
        ruta = self.json([renglon(cantidad=0), renglon(cantidad=0), renglon()])
        proceso = ejecutar(ruta, "--salida", self.carpeta)
        self.assertEqual(proceso.returncode, 1)
        self.assertIn("Se rechazaron 2 de 3 filas", proceso.stderr)
        self.assertTrue((self.carpeta / "registro_limpieza.csv").is_file())
        self.assertFalse((self.carpeta / "ranking.csv").exists())

    def test_R35_sin_abiertas_termina_bien_con_mensaje(self):
        proceso = ejecutar(self.json([renglon(estado="cerrada")]), "--salida", self.carpeta)
        self.assertEqual(proceso.returncode, 0)
        self.assertIn("No hay devoluciones abiertas al 2026-03-10", proceso.stdout)


if __name__ == "__main__":
    unittest.main()
