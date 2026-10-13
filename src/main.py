import csv
from pathlib import Path

ruta = Path(__file__).resolve().parents[1] / "data" / "ventas.csv"

with ruta.open(encoding="utf-8", newline="") as archivo:
    ventas = list(csv.DictReader(archivo))

total = sum(
    int(venta["cantidad"]) * int(venta["precio"])
    for venta in ventas
)
print(f"Total de ventas: {total}")
