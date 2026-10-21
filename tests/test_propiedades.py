"""Propiedades que el resultado tiene que cumplir siempre: P01 a P07.

Se comprueban sobre el extracto de data/ en los dos formatos y sobre extractos
generados al azar (con semilla fija), para no depender de un único ejemplo.
"""
import random
import unittest

from ayuda import DATOS, TestConArchivos, renglon

from modelos import tramo
from pipeline import guardar_salidas, procesar


def extracto_al_azar(semilla, cantidad=60):
    """Renglones válidos e inválidos mezclados, siempre los mismos para una semilla."""
    azar = random.Random(semilla)
    filas = []
    for i in range(cantidad):
        fila = renglon(
            remito=f"0002-{azar.randint(1, 40):08d}",
            fecha=f"2026-{azar.randint(1, 9):02d}-{azar.randint(1, 28):02d}",
            proveedor=f"Proveedor {azar.randint(1, 8):02d}",
            cantidad=azar.randint(1, 20),
            estado=azar.choice(["abierta", "abierta", "cerrada"]),
        )
        sorteo = azar.random()
        if sorteo < 0.10:
            fila["cantidad"] = azar.choice([0, "dos", -1, True, "1.000"])
        elif sorteo < 0.15:
            fila["fecha"] = "2026-02-30"
        elif sorteo < 0.20 and filas:
            fila = dict(azar.choice(filas))  # duplicado
        filas.append(fila)
    return filas


class TestPropiedades(TestConArchivos):

    def resultados(self):
        """Resultados sobre los que se verifican las propiedades."""
        yield "data CSV", procesar(DATOS / "devoluciones.csv")
        yield "data JSON", procesar(DATOS / "devoluciones.json")
        for semilla in range(5):
            ruta = self.json(extracto_al_azar(semilla), nombre=f"azar_{semilla}.json")
            yield f"azar {semilla}", procesar(ruta)

    def test_P01_conservacion_de_filas(self):
        for nombre, r in self.resultados():
            with self.subTest(nombre):
                self.assertEqual(r.filas_leidas, len(r.validas) + r.registro.contar("rechazada")
                                 + r.registro.contar("duplicada"))
                # Ninguna fila está a la vez entre las válidas y las rechazadas.
                validas = {d.numero_fila for d in r.validas}
                self.assertFalse(validas & set(r.registro.filas_con("rechazada")))

    def test_P02_conservacion_de_unidades(self):
        for nombre, r in self.resultados():
            with self.subTest(nombre):
                abiertas = sum(d.cantidad for d in r.validas if d.esta_abierta())
                self.assertEqual(sum(p.unidades for p in r.ranking), abiertas)
                renglones = sum(1 for d in r.validas if d.esta_abierta())
                self.assertEqual(sum(p.renglones for p in r.ranking), renglones)

    def test_P03_equivalencia_csv_json(self):
        csv_, json_ = self.carpeta / "csv", self.carpeta / "json"
        guardar_salidas(procesar(DATOS / "devoluciones.csv"), csv_)
        guardar_salidas(procesar(DATOS / "devoluciones.json"), json_)
        for archivo in ("ranking.csv", "registro_limpieza.csv"):
            with self.subTest(archivo):
                self.assertEqual((csv_ / archivo).read_bytes(), (json_ / archivo).read_bytes())

    def test_P04_reproducibilidad(self):
        primera, segunda = self.carpeta / "1", self.carpeta / "2"
        guardar_salidas(procesar(DATOS / "devoluciones.csv"), primera)
        guardar_salidas(procesar(DATOS / "devoluciones.csv"), segunda)
        for archivo in ("ranking.csv", "registro_limpieza.csv"):
            with self.subTest(archivo):
                self.assertEqual((primera / archivo).read_bytes(), (segunda / archivo).read_bytes())

    def test_P05_rangos_validos(self):
        for nombre, r in self.resultados():
            with self.subTest(nombre):
                for d in r.validas:
                    self.assertGreaterEqual(d.cantidad, 1)
                    self.assertLessEqual(d.fecha, r.corte)
                for p in r.ranking:
                    self.assertGreaterEqual(p.dias_mas_vieja, 0)
                    self.assertGreaterEqual(p.renglones, 1)
                    self.assertTrue(0 <= p.porcentaje_resuelto() < 100)

    def test_P06_ranking_ordenado(self):
        for nombre, r in self.resultados():
            with self.subTest(nombre):
                claves = [p.orden() for p in r.ranking]
                self.assertEqual(claves, sorted(claves))
                self.assertEqual(len({p.proveedor for p in r.ranking}), len(r.ranking))

    def test_P07_los_tramos_suman_los_renglones(self):
        for nombre, r in self.resultados():
            with self.subTest(nombre):
                for p in r.ranking:
                    self.assertEqual(sum(p.por_tramo), p.renglones)
                    # La devolución más vieja define el último tramo con renglones.
                    ultimo = max(i for i, cantidad in enumerate(p.por_tramo) if cantidad)
                    self.assertEqual(ultimo, tramo(p.dias_mas_vieja))


if __name__ == "__main__":
    unittest.main()
