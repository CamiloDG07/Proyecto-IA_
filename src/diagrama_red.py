"""Diagrama esquemático de la red de carga, con el ciclo señalado.

La posición de los nodos es esquemática (disposición automática), no
geográfica. Guarda outputs/diagrama_red.png y outputs/diagrama_red.pdf.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402

from build_graph import SALIDA, cargar_grafo  # noqa: E402

COLOR_CICLO = "#c0392b"
COLOR_RED = "#7f8c8d"
COLOR_NODO = "#d6eaf8"


def aristas_del_ciclo(grafo):
    """Aristas del único ciclo independiente de la red."""
    ciclos = nx.cycle_basis(grafo)
    if len(ciclos) != 1:
        raise ValueError(f"Se esperaba 1 ciclo y hay {len(ciclos)}")
    ciclo = ciclos[0]
    return ciclo, {frozenset(par) for par in zip(ciclo, ciclo[1:] + ciclo[:1])}


def dibujar(grafo, ruta_png, ruta_pdf):
    ciclo, aristas_ciclo = aristas_del_ciclo(grafo)
    pos = nx.kamada_kawai_layout(grafo, weight=None)
    fig, ax = plt.subplots(figsize=(11, 8.5))
    en_ciclo = [e for e in grafo.edges if frozenset(e) in aristas_ciclo]
    fuera = [e for e in grafo.edges if frozenset(e) not in aristas_ciclo]
    nx.draw_networkx_edges(grafo, pos, edgelist=fuera, ax=ax,
                           edge_color=COLOR_RED, width=1.4)
    nx.draw_networkx_edges(grafo, pos, edgelist=en_ciclo, ax=ax,
                           edge_color=COLOR_CICLO, width=2.6)
    nx.draw_networkx_nodes(grafo, pos, ax=ax, node_color=COLOR_NODO,
                           edgecolors="#34495e", node_size=330)
    nx.draw_networkx_labels(grafo, pos, ax=ax, font_size=6.5)
    etiquetas = {(u, v): f"{d['distancia_km']:.1f}"
                 for u, v, d in grafo.edges(data=True)}
    nx.draw_networkx_edge_labels(grafo, pos, edge_labels=etiquetas, ax=ax,
                                 font_size=5.5, rotate=False,
                                 bbox={"alpha": 0.0, "pad": 0.1})
    ax.plot([], [], color=COLOR_CICLO, lw=2.6, label="Ciclo (vía Santander)")
    ax.plot([], [], color=COLOR_RED, lw=1.4, label="Resto de la red")
    ax.legend(loc="lower left", fontsize=8)
    ax.set_title("Red de carga interurbana: 33 ciudades y 33 tramos "
                 "(distancia en km)", fontsize=10)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(ruta_png, dpi=200)
    fig.savefig(ruta_pdf)
    plt.close(fig)
    return ciclo


def main():
    grafo = cargar_grafo()
    ciclo = dibujar(grafo, SALIDA / "diagrama_red.png",
                    SALIDA / "diagrama_red.pdf")
    print("Ciclo:", " - ".join(ciclo))


if __name__ == "__main__":
    main()
