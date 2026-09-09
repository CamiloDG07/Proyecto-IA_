from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"

TIPOS_TRANSFERENCIA = {
    "intercambio": "#1565c0",
    "cruce_troncal": "#e53935",
    "continuidad_troncal": "#6a1b9a",
    "continuidad_troncal_auto": "#6a1b9a",
    "residual_geografico": "#2e7d32",
}


def _posiciones(G: nx.Graph) -> dict:
    return {n: (G.nodes[n]["lon"], G.nodes[n]["lat"]) for n in G.nodes}


def _dibujar_base(G: nx.Graph, pos: dict, ax, con_colores_por_troncal: bool = True) -> None:
    if con_colores_por_troncal:
        troncales = sorted({d["nom_tronc"] for _, d in G.nodes(data=True)})
        cmap = plt.get_cmap("tab20")
        color_map = {t: cmap(i / len(troncales)) for i, t in enumerate(troncales)}
        colores = [color_map[G.nodes[n]["nom_tronc"]] for n in G.nodes]
    else:
        colores = "#546e7a"

    sizes = [140 if G.nodes[n]["tipo_esta"] in (1, 3) else 40 for n in G.nodes]
    nx.draw_networkx_edges(G, pos, width=1.0, edge_color="#b0bec5", alpha=0.7, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_size=sizes, node_color=colores, alpha=0.9, ax=ax)
    if con_colores_por_troncal:
        handles = [
            plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color_map[t], markersize=8, label=t)
            for t in troncales
        ]
        ax.legend(handles=handles, loc="lower left", fontsize=8, ncol=2, framealpha=0.9)


def graficar_red_completa(G: nx.Graph, ruta_salida: Path) -> None:
    """Vista general sin etiquetas (topologia + troncales, para el informe)."""
    pos = _posiciones(G)
    fig, ax = plt.subplots(figsize=(13, 13))
    _dibujar_base(G, pos, ax)
    ax.set_title("Red troncal de Transmilenio - grafo corregido (1 sola componente conexa)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(ruta_salida, dpi=200)
    plt.close(fig)


def graficar_red_con_pesos(G: nx.Graph, ruta_salida: Path, mostrar_tiempo: bool = True) -> None:
    """Vista general con distancia_km (y tiempo_min) sobre cada arista, fuente
    pequena para intra_trazado y grande/coloreada para las 22 de transferencia."""
    pos = _posiciones(G)
    fig, ax = plt.subplots(figsize=(26, 26))
    _dibujar_base(G, pos, ax)

    for u, v, data in G.edges(data=True):
        x = (pos[u][0] + pos[v][0]) / 2
        y = (pos[u][1] + pos[v][1]) / 2
        etiqueta = f"{data['weight']:.2f}"
        if mostrar_tiempo:
            etiqueta += f" ({data['tiempo_min']:.1f}')"
        tipo = data["tipo"]
        if tipo == "intra_trazado":
            ax.text(x, y, etiqueta, fontsize=3.3, color="#78909c", ha="center", va="center", zorder=3)
        else:
            color = TIPOS_TRANSFERENCIA.get(tipo, "#000000")
            ax.text(
                x, y, etiqueta, fontsize=7, color=color, fontweight="bold", ha="center", va="center", zorder=4,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec=color, lw=0.8, alpha=0.85),
            )

    handles_tipo = [
        plt.Line2D([0], [0], marker="s", color="w", markerfacecolor=c, markersize=9, label=t)
        for t, c in TIPOS_TRANSFERENCIA.items()
    ]
    leg2 = ax.legend(handles=handles_tipo, loc="lower right", fontsize=7, title="Aristas de transferencia (etiqueta grande)", framealpha=0.9)
    ax.add_artist(leg2)

    ax.set_title(
        "Red troncal de Transmilenio con pesos de arista (distancia_km" + (" y tiempo_min entre parentesis" if mostrar_tiempo else "") + ")",
        fontsize=14, fontweight="bold",
    )
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.grid(True, linestyle="--", alpha=0.3)
    plt.tight_layout()
    plt.savefig(ruta_salida, dpi=220)
    plt.close(fig)


def graficar_zoom(G: nx.Graph, bbox: tuple, ruta_salida: Path, titulo: str, mostrar_tiempo: bool = True) -> None:
    """Zoom a una zona (bbox = (lon_min, lon_max, lat_min, lat_max)) con todas
    las etiquetas de peso legibles - pensado para una zona con varios cruces."""
    lon_min, lon_max, lat_min, lat_max = bbox
    pos = _posiciones(G)
    nodos_en_zona = [n for n, (x, y) in pos.items() if lon_min <= x <= lon_max and lat_min <= y <= lat_max]
    sub = G.subgraph(nodos_en_zona)

    fig, ax = plt.subplots(figsize=(13, 13))
    _dibujar_base(sub, pos, ax, con_colores_por_troncal=True)

    for u, v, data in sub.edges(data=True):
        x = (pos[u][0] + pos[v][0]) / 2
        y = (pos[u][1] + pos[v][1]) / 2
        etiqueta = f"{data['weight']:.2f} km"
        if mostrar_tiempo:
            etiqueta += f" / {data['tiempo_min']:.1f} min"
        tipo = data["tipo"]
        color = TIPOS_TRANSFERENCIA.get(tipo, "#455a64")
        peso_fuente = "bold" if tipo in TIPOS_TRANSFERENCIA else "normal"
        ax.text(
            x, y, etiqueta, fontsize=9, color=color, fontweight=peso_fuente, ha="center", va="center", zorder=4,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=color, lw=0.8, alpha=0.9),
        )

    for n in sub.nodes:
        x, y = pos[n]
        ax.annotate(sub.nodes[n]["nom_est"], (x, y), textcoords="offset points", xytext=(6, 6), fontsize=8)

    ax.set_xlim(lon_min, lon_max)
    ax.set_ylim(lat_min, lat_max)
    ax.set_title(titulo, fontsize=13, fontweight="bold")
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(ruta_salida, dpi=200)
    plt.close(fig)


def main():
    import pickle

    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(OUTPUT_DIR / "grafo_transmilenio.gpickle", "rb") as f:
        G = pickle.load(f)

    graficar_red_completa(G, OUTPUT_DIR / "red_transmilenio_corregida.png")
    print(f"Guardado: {OUTPUT_DIR / 'red_transmilenio_corregida.png'} (vista general, sin etiquetas)")

    graficar_red_con_pesos(G, OUTPUT_DIR / "grafo_con_pesos.png")
    print(f"Guardado: {OUTPUT_DIR / 'grafo_con_pesos.png'} (vista general, con distancia_km y tiempo_min)")

    zona_comuneros = (-74.108, -74.078, 4.588, 4.620)
    graficar_zoom(
        G, zona_comuneros, OUTPUT_DIR / "grafo_con_pesos_zoom_comuneros.png",
        "Zoom: cruce de troncales alrededor de Comuneros / Ricaurte (Av. Calle 6 - NQS)",
    )
    print(f"Guardado: {OUTPUT_DIR / 'grafo_con_pesos_zoom_comuneros.png'} (zoom, detalle legible)")


if __name__ == "__main__":
    main()
