"""Genera el extracto simulado de devoluciones a proveedores (CSV y JSON).

El extracto imita la forma de uno real: remitos de devolución con uno o varios
renglones, la mayoría todavía abiertos, y los errores de carga típicos. Cada error
se inyecta a propósito y está anotado con el punto de ruptura que lo cubre
(ver docs/puntos_de_ruptura.md).

La semilla es fija: ejecutar el script otra vez produce exactamente los mismos
archivos.

Uso, desde la raíz del proyecto:
    python3 src/generar_datos.py
"""
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

SEMILLA = 20261013
RAIZ = Path(__file__).resolve().parents[1]
COLUMNAS = ["remito", "fecha", "proveedor", "articulo", "cantidad", "motivo",
            "estado", "descuenta_stock"]

# Artículo devuelto y el motivo que suele anotar Calidad.
ARTICULOS = [
    ("Sensor de temperatura", "lectura errática"),
    ("Motor de limpiaparabrisas", "no arranca"),
    ("Bisagra de tapa", "medida fuera de tolerancia"),
    ("Burlete de ventanilla", "material quebradizo"),
    ("Fusible térmico", "no corresponde al pedido"),
    ("Llave de luces", "falso contacto"),
    ("Amortiguador de puerta", "pierde aceite"),
    ("Espejo retrovisor", "llegó roto"),
    ("Panel de aluminio", "golpeado en el transporte"),
    ("Cable de batería", "sección incorrecta"),
    ("Ventilador de habitáculo", "ruido excesivo"),
    ("Cerradura de compartimiento", "no traba"),
]

# 18 proveedores ficticios; pocos concentran la mayoría de las devoluciones.
PROVEEDORES = [f"Proveedor {n:02d}" for n in range(1, 19)]
PESOS = [12, 9, 5, 4] + [1] * 14


def generar_filas():
    """Devuelve la lista de renglones, ya con los errores inyectados."""
    azar = random.Random(SEMILLA)
    filas = []
    fecha = date(2026, 1, 5)
    numero = 1101

    while fecha <= date(2026, 9, 30):
        proveedor = azar.choices(PROVEEDORES, weights=PESOS)[0]
        # Cerca del 10 % de los remitos tiene más de un renglón.
        renglones = azar.choice([2, 3]) if azar.random() < 0.10 else 1
        # Las devoluciones viejas tienen algo más de chance de estar cerradas.
        prob_cerrada = 0.25 if fecha.month <= 4 else 0.08
        estado = "cerrada" if azar.random() < prob_cerrada else "abierta"
        for articulo, motivo in azar.sample(ARTICULOS, renglones):
            filas.append({
                "remito": f"0002-{numero:08d}",
                "fecha": fecha.isoformat(),
                "proveedor": proveedor,
                "articulo": articulo,
                "cantidad": azar.randint(1, 20),
                "motivo": motivo,
                "estado": estado,
                "descuenta_stock": azar.random() < 0.15,
            })
        numero += 1
        fecha += timedelta(days=azar.randint(2, 5))

    # R31: la numeración se reutiliza. Dos números viejos vuelven a usarse a fin
    # de septiembre para otras devoluciones.
    for viejo, proveedor, (articulo, motivo) in [
        (1103, "Proveedor 07", ARTICULOS[4]),
        (1115, "Proveedor 01", ARTICULOS[7]),
    ]:
        filas.append({
            "remito": f"0002-{viejo:08d}", "fecha": "2026-09-30",
            "proveedor": proveedor, "articulo": articulo,
            "cantidad": azar.randint(1, 20), "motivo": motivo,
            "estado": "abierta", "descuenta_stock": False,
        })

    inyectar_errores(filas)
    return filas


def inyectar_errores(filas):
    """Modifica filas puntuales para reproducir errores de carga reales."""
    # Correcciones: la aplicación las arregla y lo anota.
    filas[4]["estado"] = " Abierta "                     # R21
    filas[9]["estado"] = "CERRADA"                       # R21
    filas[14]["fecha"] = a_fecha_argentina(filas[14]["fecha"])  # R13b
    filas[50]["fecha"] = a_fecha_argentina(filas[50]["fecha"])  # R13b
    filas[22]["proveedor"] = filas[22]["proveedor"] + " "        # R24

    # Faltantes que no impiden responder la pregunta: la fila se conserva.
    for i in (6, 27, 41, 63):
        filas[i]["motivo"] = ""                          # R26
    for i in (18, 58):
        filas[i]["descuenta_stock"] = None               # R27b

    # Errores que obligan a rechazar la fila.
    filas[11]["fecha"] = "2026-02-30"                    # R14
    filas[25]["remito"] = "0002-1127"                    # R11
    filas[31]["cantidad"] = "dos"                        # R16
    filas[36]["cantidad"] = 0                            # R17
    filas[44]["cantidad"] = "1.000"                      # R18
    filas[47]["estado"] = "anulada"                      # R22
    filas[55]["proveedor"] = ""                          # R23

    # R29: un renglón cargado dos veces, uno detrás del otro.
    filas.insert(34, dict(filas[33]))


def a_fecha_argentina(iso):
    """Convierte '2026-03-07' en '07/03/2026'."""
    anio, mes, dia = iso.split("-")
    return f"{dia}/{mes}/{anio}"


def a_texto_csv(valor):
    """Representa un valor como lo escribiría una exportación a CSV."""
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "si" if valor else "no"
    return str(valor)


def guardar_csv(filas, ruta):
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS)
        escritor.writeheader()
        for fila in filas:
            escritor.writerow({c: a_texto_csv(fila[c]) for c in COLUMNAS})


def guardar_json(filas, ruta):
    with ruta.open("w", encoding="utf-8") as archivo:
        json.dump(filas, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")


if __name__ == "__main__":
    filas = generar_filas()
    carpeta = RAIZ / "data"
    carpeta.mkdir(exist_ok=True)
    guardar_csv(filas, carpeta / "devoluciones.csv")
    guardar_json(filas, carpeta / "devoluciones.json")
    print(f"Se generaron {len(filas)} renglones en data/devoluciones.csv y data/devoluciones.json")
