"""Visualización de las rutas de los cinco algoritmos y del barrido de pesos.

Dibuja la red con las coordenadas oficiales (longitud en x, latitud en y),
el ciclo señalado y la ruta de cada algoritmo para Duitama a Puente Nacional,
con los criterios distancia y compuesto sin riesgo; y la ruta ganadora en la
malla de pesos. Guarda PNG y PDF vectorial en outputs/.

Color: azul (ruta por Bogotá) y naranja (ruta por Santander); la identidad
se refuerza con el estilo de línea y el rótulo, no solo con el color.
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402

from agente import CRITERIOS  # noqa: E402
from build_graph import SALIDA, cargar_grafo  # noqa: E402
from busquedas import a_estrella, bfs, dfs, ucs, voraz  # noqa: E402
from diagrama_red import aristas_del_ciclo  # noqa: E402
from heuristica import (Heuristica, alfa_minimo,  # noqa: E402
                        cargar_coordenadas)

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
AZUL = "#2a78d6"
NARANJA = "#eb6834"
GRIS_CICLO = "#d9c9c0"
GRIS_RED = "#b9b8b3"
ORIGEN, DESTINO = "Duitama", "Puente Nacional"


def estilo_ruta(ruta):
    """(color, estilo de línea, nombre de la vía) según pase por Bogotá."""
    if "Bogotá" in ruta:
        return AZUL, "-", "por Bogotá"
    return NARANJA, "--", "por Santander"


def dibujar_red(ax, grafo, pos, aristas_ciclo):
    for u, v in grafo.edges:
        en_ciclo = frozenset((u, v)) in aristas_ciclo
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color=GRIS_CICLO if en_ciclo else GRIS_RED,
                lw=5.5 if en_ciclo else 1.0, solid_capstyle="round",
                zorder=1)
    xs = [pos[n][0] for n in grafo]
    ys = [pos[n][1] for n in grafo]
    ax.scatter(xs, ys, s=10, color=TINTA_2, zorder=3)


def dibujar_ruta(ax, grafo, pos, ruta):
    color, trazo, _ = estilo_ruta(ruta)
    ax.plot([pos[n][0] for n in ruta], [pos[n][1] for n in ruta],
            color=color, lw=2.4, ls=trazo, zorder=4, solid_capstyle="round")
    for nodo, marca in ((ruta[0], "o"), (ruta[-1], "s")):
        ax.scatter([pos[nodo][0]], [pos[nodo][1]], s=46, marker=marca,
                   color=color, edgecolors=SUPERFICIE, linewidths=1.5,
                   zorder=5)
        ax.annotate(nodo, pos[nodo], xytext=(5, 5), textcoords="offset points",
                    fontsize=7, color=TINTA, zorder=6)


def algoritmos_ruta(grafo, coordenadas, alfa, criterio):
    atributo = CRITERIOS[criterio]
    h = Heuristica(grafo, coordenadas, criterio, alfa)
    return {
        "BFS": bfs(grafo, ORIGEN, DESTINO, atributo),
        "DFS": dfs(grafo, ORIGEN, DESTINO, atributo),
        "UCS": ucs(grafo, ORIGEN, DESTINO, atributo),
        "Voraz": voraz(grafo, ORIGEN, DESTINO, atributo, h),
        "A*": a_estrella(grafo, ORIGEN, DESTINO, atributo, h),
    }


def figura_rutas(grafo, coordenadas, alfa, criterio, nombre):
    pos = {n: (lon, lat) for n, (lat, lon) in coordenadas.items()}
    _, aristas_ciclo = aristas_del_ciclo(grafo)
    resultados = algoritmos_ruta(grafo, coordenadas, alfa, criterio)
    fig, ejes = plt.subplots(2, 3, figsize=(13, 9.5), facecolor=SUPERFICIE)
    for ax, (algoritmo, r) in zip(ejes.flat, resultados.items()):
        ax.set_facecolor(SUPERFICIE)
        dibujar_red(ax, grafo, pos, aristas_ciclo)
        dibujar_ruta(ax, grafo, pos, r["ruta"])
        _, _, via = estilo_ruta(r["ruta"])
        km = sum(grafo[u][v]["distancia_km"]
                 for u, v in zip(r["ruta"], r["ruta"][1:]))
        ax.set_title(f"{algoritmo}: {via}, {km:.2f} km, {r['saltos']} saltos,"
                     f"\n{r['nodos_expandidos']} nodos expandidos",
                     fontsize=9, color=TINTA)
        ax.set_aspect("equal")
        ax.axis("off")
    leyenda = ejes.flat[5]
    leyenda.axis("off")
    leyenda.plot([], [], color=GRIS_CICLO, lw=5.5, label="Ciclo")
    leyenda.plot([], [], color=GRIS_RED, lw=1.0, label="Resto de la red")
    leyenda.plot([], [], color=AZUL, lw=2.4, ls="-",
                 label="Ruta por Bogotá")
    leyenda.plot([], [], color=NARANJA, lw=2.4, ls="--",
                 label="Ruta por Santander")
    leyenda.scatter([], [], marker="o", color=TINTA_2, label="Origen")
    leyenda.scatter([], [], marker="s", color=TINTA_2, label="Destino")
    leyenda.legend(loc="center", fontsize=10, frameon=False)
    fig.suptitle(f"{ORIGEN} a {DESTINO}, criterio {criterio.replace('_', ' ')}"
                 " (coordenadas oficiales DANE e INVÍAS)", fontsize=11,
                 color=TINTA)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(SALIDA / f"{nombre}.{ext}", dpi=200,
                    facecolor=SUPERFICIE)
    plt.close(fig)


def figura_barrido():
    with open(SALIDA / "barrido_pesos.json", encoding="utf-8") as f:
        barridos = json.load(f)
    paneles = ((barridos[0], "Base: Chocontá a Tunja 17.69 km"),
               (barridos[1], "Cota inferior: 56.96 km"),
               (barridos[3], "Progresivas: 61.0 km"))
    fig, ejes = plt.subplots(1, 3, figsize=(9.0, 3.7), facecolor=SUPERFICIE,
                             sharey=True)
    for ax, (b, titulo) in zip(ejes, paneles):
        ax.set_facecolor(SUPERFICIE)
        cuentas = {}
        for via, color, marca in (("Bogotá", AZUL, "o"),
                                  ("Santander", NARANJA, "^")):
            pts = [p for p in b["puntos"] if p["compuesto"] == via]
            cuentas[via] = len(pts)
            ax.scatter([p["w1"] for p in pts], [p["w2"] for p in pts],
                       s=24, color=color, marker=marca,
                       edgecolors=SUPERFICIE, linewidths=0.6, zorder=3,
                       label=f"Gana la ruta por {via}")
        dd, dp, dr = b["delta_corta_menos_desvio"]
        w1 = [i / 100 for i in range(101)]
        frontera = [(-(x * (dd - dr) + dr) / (dp - dr)) for x in w1]
        pares = [(x, y) for x, y in zip(w1, frontera) if 0 <= y <= 1 - x]
        ax.plot([p[0] for p in pares], [p[1] for p in pares], color=TINTA_2,
                lw=1.4, zorder=2, label="Frontera exacta")
        ax.plot([0, 1], [1, 0], color=GRIS_RED, lw=0.8, zorder=1)
        ax.set_xlabel("$w_1$ (distancia)", color=TINTA, fontsize=10)
        ax.set_title(f"{titulo}\nBogotá {cuentas['Bogotá']}, Santander "
                     f"{cuentas['Santander']}", fontsize=10, color=TINTA)
        ax.set_xlim(-0.04, 1.04)
        ax.set_ylim(-0.04, 1.04)
        ax.tick_params(labelsize=9)
        ax.grid(color="#e6e5e1", lw=0.6)
        ax.set_axisbelow(True)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
    ejes[0].set_ylabel("$w_2$ (peaje); $w_3 = 1 - w_1 - w_2$ (riesgo)",
                       color=TINTA, fontsize=10)
    manijas, rotulos = ejes[0].get_legend_handles_labels()
    fig.legend(manijas, rotulos, loc="lower center", ncol=3, fontsize=10,
               frameon=False)
    fig.suptitle("Duitama a Puente Nacional: ruta de menor costo compuesto "
                 "en la malla de pesos (paso 0.1)", fontsize=11, color=TINTA)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    for ext in ("png", "pdf"):
        fig.savefig(SALIDA / f"barrido_pesos.{ext}", dpi=200,
                    facecolor=SUPERFICIE)
    plt.close(fig)


def main():
    grafo = cargar_grafo()
    coordenadas = cargar_coordenadas()
    alfa = alfa_minimo(grafo, coordenadas)
    figura_rutas(grafo, coordenadas, alfa, "distancia",
                 "rutas_central_distancia")
    figura_rutas(grafo, coordenadas, alfa, "compuesto_sin_riesgo",
                 "rutas_central_compuesto_sin_riesgo")
    figura_barrido()
    print("Figuras escritas en", SALIDA)


if __name__ == "__main__":
    main()
