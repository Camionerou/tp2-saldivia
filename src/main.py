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
from modelos import TRAMOS
from pipeline import ErrorSalida, guardar_salidas, procesar

RAIZ = Path(__file__).resolve().parents[1]


def fecha_de_corte(texto):
    """R33: argparse convierte un ValueError/ArgumentTypeError en error de uso (código 2)."""
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"'{texto}' no es una fecha válida con formato AAAA-MM-DD")


def leer_argumentos(argv):
    parser = argparse.ArgumentParser(
        description="Ranking de proveedores con devoluciones abiertas.")
    parser.add_argument("archivo", help="extracto de devoluciones (.csv o .json)")
    parser.add_argument("--corte", type=fecha_de_corte, default=None,
                        help="fecha de corte AAAA-MM-DD (por defecto, la más reciente del extracto)")
    parser.add_argument("--salida", default=str(RAIZ / "outputs"),
                        help="carpeta donde se guardan los resultados (por defecto, outputs/)")
    parser.add_argument("--grafico", action="store_true",
                        help="guarda además ranking.png (requiere matplotlib)")
    return parser.parse_args(argv)


def mostrar(resultado, carpeta, graficados):
    """`graficados`: proveedores en ranking.png, o None si no se pidió --grafico."""
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
        tramos = "".join(f"{nombre:>8}" for _, nombre in TRAMOS)
        print(f"{'':>67}{'Renglones por antigüedad (días)':>32}")
        print(f"{'#':>3}  {'Proveedor':<22}{'Renglones':>10}{'Unidades':>10}"
              f"{'Más vieja':>13}{'Días':>7}{tramos}{'Resuelto':>11}")
        for posicion, r in enumerate(resultado.ranking, start=1):
            por_tramo = "".join(f"{cantidad or '·':>8}" for cantidad in r.por_tramo)
            print(f"{posicion:>3}  {r.proveedor:<22}{r.renglones:>10}{r.unidades:>10}"
                  f"{r.fecha_mas_vieja.isoformat():>13}{r.dias_mas_vieja:>7}{por_tramo}"
                  f"{r.porcentaje_resuelto():>9} %")
    if carpeta.is_relative_to(Path.cwd()):
        carpeta = carpeta.relative_to(Path.cwd())
    archivos = [f"{carpeta}/ranking.csv", f"{carpeta}/registro_limpieza.csv"]
    if graficados:
        archivos.append(f"{carpeta}/ranking.png")
        if graficados < len(resultado.ranking):  # R44
            print(f"\nEl gráfico muestra los {graficados} primeros de {len(resultado.ranking)} "
                  "proveedores; el ranking completo está en ranking.csv.")
    elif graficados == 0:  # R43
        print("No se generó el gráfico porque no hay devoluciones abiertas.")
    print(f"\nResultados guardados en {', '.join(archivos[:-1])} y {archivos[-1]}")


def main(argv=None):
    argumentos = leer_argumentos(argv)
    carpeta = Path(argumentos.salida)
    graficados = None
    try:
        if argumentos.grafico:
            # R42: se importa antes de procesar, para que sin matplotlib la corrida
            # falle sin dejar salidas a medias.
            from grafico import graficar_ranking
        resultado = procesar(argumentos.archivo, argumentos.corte)
        guardar_salidas(resultado, carpeta)
        if argumentos.grafico:
            graficados = graficar_ranking(resultado, carpeta / "ranking.png")
    except (ErrorEntrada, ErrorSalida) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    mostrar(resultado, carpeta, graficados)
    return 0


if __name__ == "__main__":
    sys.exit(main())
