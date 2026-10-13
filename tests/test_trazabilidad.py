"""T01: cada punto de docs/puntos_de_ruptura.md tiene al menos un test, y al revés."""
import re
import unittest

from ayuda import RAIZ

DOCUMENTO = RAIZ / "docs" / "puntos_de_ruptura.md"
# Primera columna de las tablas: "| R14 |", "| R10b |", "| P03 |", "| T01 |".
PATRON_ID_DOC = re.compile(r"^\| ([RPT]\d{2}[a-z]?) \|", re.MULTILINE)
# En los tests: el nombre "def test_R14_..." o la primera columna de una tabla ("R14", ...).
PATRON_ID_TEST = re.compile(r'def test_([RPT]\d{2}[a-z]?)_|^\s*\("([RPT]\d{2}[a-z]?)",', re.MULTILINE)


class TestTrazabilidad(unittest.TestCase):

    def test_T01_todo_punto_documentado_tiene_test(self):
        documentados = set(PATRON_ID_DOC.findall(DOCUMENTO.read_text(encoding="utf-8")))
        probados = set()
        for archivo in (RAIZ / "tests").glob("test_*.py"):
            for en_nombre, en_tabla in PATRON_ID_TEST.findall(archivo.read_text(encoding="utf-8")):
                probados.add(en_nombre or en_tabla)

        self.assertGreater(len(documentados), 40, "no se encontraron las tablas del documento")
        self.assertEqual(sorted(documentados - probados), [], "puntos documentados sin test")
        self.assertEqual(sorted(probados - documentados), [], "tests de puntos que no están documentados")


if __name__ == "__main__":
    unittest.main()
