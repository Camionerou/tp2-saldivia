"""Ranking de proveedores con devoluciones abiertas.

Uso, desde la raíz del proyecto:
    python3 src/main.py data/devoluciones.csv
    python3 src/main.py data/devoluciones.json --corte 2026-09-15 --salida outputs

Códigos de salida: 0 si terminó bien, 1 si la entrada o la salida tienen un
problema, 2 si los argumentos son incorrectos.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

from fuentes import ErrorEntrada
from pipeline import ErrorSalida, guardar_salidas, procesar

RAIZ = Path(__file__).resolve().parents[1]


def fecha_de_corte(texto):
    """R33: argparse convierte un ValueError/ArgumentTypeError en error de uso (código 2)."""
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"'{texto}' no es una fecha válida con formato AAAA-MM-DD") from None


def leer_argumentos(argv):
    parser = argparse.ArgumentParser(
        description="Ranking de proveedores con devoluciones abiertas.")
    parser.add_argument("archivo", help="extracto de devoluciones (.csv o .json)")
    parser.add_argument("--corte", type=fecha_de_corte, default=None,
                        help="fecha de corte AAAA-MM-DD (por defecto, la más reciente del extracto)")
    parser.add_argument("--salida", default=str(RAIZ / "outputs"),
                        help="carpeta donde se guardan los resultados (por defecto, outputs/)")
    return parser.parse_args(argv)


def mostrar(resultado, carpeta):
    registro = resultado.registro
    for aviso in resultado.avisos:
        print(f"Aviso: {aviso}")
    print(f"Filas leídas: {resultado.filas_leidas} | válidas: {len(resultado.validas)} | "
          f"rechazadas: {registro.contar('rechazada')} | duplicadas: {registro.contar('duplicada')} | "
          f"corregidas: {registro.contar('corregida')}")
    print(f"Fecha de corte: {resultado.corte}\n")

    if not resultado.ranking:  # R35
        print(f"No hay devoluciones abiertas al {resultado.corte}.")
    else:
        print(f"{'#':>3}  {'Proveedor':<22}{'Renglones':>10}{'Unidades':>10}"
              f"{'Más vieja':>13}{'Días':>7}")
        for posicion, r in enumerate(resultado.ranking, start=1):
            print(f"{posicion:>3}  {r.proveedor:<22}{r.renglones:>10}{r.unidades:>10}"
                  f"{r.fecha_mas_vieja.isoformat():>13}{r.dias_mas_vieja:>7}")
    if carpeta.is_relative_to(Path.cwd()):
        carpeta = carpeta.relative_to(Path.cwd())
    print(f"\nResultados guardados en {carpeta}/ranking.csv y {carpeta}/registro_limpieza.csv")


def main(argv=None):
    argumentos = leer_argumentos(argv)
    carpeta = Path(argumentos.salida)
    try:
        resultado = procesar(argumentos.archivo, argumentos.corte)
        guardar_salidas(resultado, carpeta)
    except (ErrorEntrada, ErrorSalida) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    mostrar(resultado, carpeta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
