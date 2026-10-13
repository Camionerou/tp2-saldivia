"""Utilidades compartidas por los tests.

Agrega `src/` al camino de importación y ofrece una clase base que crea una
carpeta temporal por test, para escribir archivos de entrada mínimos a medida.
Cada test arma exactamente el caso que prueba: así se ve en el mismo test qué
entrada produce qué resultado.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

DATOS = RAIZ / "data"
ENCABEZADO = "remito,fecha,proveedor,articulo,cantidad,motivo,estado,descuenta_stock"


def renglon(**cambios):
    """Un renglón válido como diccionario (tipos de JSON), con los cambios pedidos."""
    base = {
        "remito": "0002-00000001",
        "fecha": "2026-03-10",
        "proveedor": "Proveedor 01",
        "articulo": "Llave de luces",
        "cantidad": 5,
        "motivo": "falso contacto",
        "estado": "abierta",
        "descuenta_stock": False,
    }
    base.update(cambios)
    return base


class TestConArchivos(unittest.TestCase):
    """Base para tests que necesitan escribir archivos de entrada."""

    def setUp(self):
        self._temporal = tempfile.TemporaryDirectory()
        self.carpeta = Path(self._temporal.name)

    def tearDown(self):
        self._temporal.cleanup()

    def escribir(self, nombre, contenido, codificacion="utf-8"):
        """Escribe texto (o bytes) en la carpeta temporal y devuelve la ruta."""
        ruta = self.carpeta / nombre
        if isinstance(contenido, bytes):
            ruta.write_bytes(contenido)
        else:
            ruta.write_text(contenido, encoding=codificacion, newline="")
        return ruta

    def csv(self, *lineas, nombre="entrada.csv", encabezado=ENCABEZADO, codificacion="utf-8"):
        """CSV con el encabezado estándar y las líneas dadas."""
        return self.escribir(nombre, "\n".join([encabezado, *lineas]) + "\n", codificacion)

    def json(self, datos, nombre="entrada.json"):
        return self.escribir(nombre, json.dumps(datos, ensure_ascii=False))
