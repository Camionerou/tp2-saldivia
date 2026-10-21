"""Gráfico del ranking: una barra por proveedor, partida en tramos de antigüedad.

Es lo único de la aplicación que usa una biblioteca externa (matplotlib) y solo se
importa con la opción --grafico, así el resto funciona con la biblioteca estándar.
"""
from pipeline import ErrorSalida

try:
    import matplotlib
except ImportError:  # R42
    raise ErrorSalida("Para usar --grafico hace falta matplotlib. "
                      "Instalalo con: pip install -r requirements.txt")
matplotlib.use("Agg")  # sin ventana: solo se guarda el archivo
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from modelos import TRAMOS

# Un solo tono de claro a oscuro: cuanto más vieja la devolución, más oscuro el tramo.
COLORES_TRAMOS = ("#86b6ef", "#3987e5", "#1c5cab", "#0d366b")
TINTA = "#555555"
# R44: con más proveedores las barras de abajo no se leen; el ranking completo está en el CSV.
MAXIMO_PROVEEDORES = 20


def graficar_ranking(resultado, ruta):
    """Grafica los primeros proveedores del ranking y devuelve cuántos graficó."""
    if not resultado.ranking:  # R43
        return 0
    ranking = resultado.ranking[:MAXIMO_PROVEEDORES][::-1]  # barh dibuja de abajo hacia arriba
    proveedores = [r.proveedor for r in ranking]
    figura, eje = plt.subplots(figsize=(9, 1.5 + 0.4 * len(ranking)))

    acumulado = [0] * len(ranking)
    for posicion, ((_, nombre), color) in enumerate(zip(TRAMOS, COLORES_TRAMOS)):
        cantidades = [r.por_tramo[posicion] for r in ranking]
        # El borde blanco separa los tramos de una misma barra.
        eje.barh(proveedores, cantidades, left=acumulado, height=0.7, color=color,
                 edgecolor="white", linewidth=0.8, label=f"{nombre} días")
        acumulado = [a + c for a, c in zip(acumulado, cantidades)]

    for fila, r in enumerate(ranking):
        # El desplazamiento va en puntos, así la distancia a la barra no depende de la escala.
        eje.annotate(str(r.renglones), (r.renglones, fila), xytext=(4, 0),
                     textcoords="offset points", va="center", fontsize=9, color=TINTA)

    titulo = f"Devoluciones abiertas por proveedor al {resultado.corte}"
    if len(resultado.ranking) > MAXIMO_PROVEEDORES:
        titulo += f"\nLos {MAXIMO_PROVEEDORES} primeros de {len(resultado.ranking)} proveedores"
    eje.set_title(titulo, loc="left")
    eje.set_ylim(-0.6, len(ranking) - 0.4)
    eje.set_xlabel("Renglones abiertos", color=TINTA)
    eje.xaxis.set_major_locator(MaxNLocator(integer=True))
    eje.grid(axis="x", color="#e5e5e5")
    eje.set_axisbelow(True)
    eje.tick_params(colors=TINTA, length=0)
    for borde in ("top", "right", "left"):
        eje.spines[borde].set_visible(False)
    eje.spines["bottom"].set_color("#cccccc")
    eje.legend(title="Antigüedad", frameon=False, loc="lower right")

    try:
        figura.savefig(ruta, dpi=150, bbox_inches="tight")
    except OSError as error:  # R38
        raise ErrorSalida(f"No se pudo escribir '{ruta}' ({error.strerror}).")
    finally:
        plt.close(figura)
    return len(ranking)
