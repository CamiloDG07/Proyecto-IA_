"""
Visualizacion de una ruta especifica resaltada sobre la red completa.

Dibuja toda la red corregida (grafo_transmilenio.gpickle) en gris claro de
fondo -mismo estilo que outputs/red_transmilenio_corregida.png- y resalta
encima, con una linea de color y grosor mayor, la ruta que calcula
AgenteRutas para un par origen-destino. Las estaciones donde ocurre una
transferencia de troncal se marcan con un punto de otro color.

Genera las 3 imagenes para los casos de prueba de src/pruebas_agente.py:
  outputs/ruta_portal_suba_portal_tunal.png
  outputs/ruta_portal_norte_portal_usme.png
  outputs/ruta_museo_nacional_portal_americas.png
"""

from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

from agente import AgenteRutas

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"

COLOR_FONDO_NODO = "#cfd8dc"
COLOR_FONDO_ARISTA = "#e0e0e0"
COLOR_RUTA = "#e53935"
COLOR_TRANSFERENCIA = "#1565c0"

CASOS = [
    {"origen": 3000, "destino": 8000, "archivo": "ruta_portal_suba_portal_tunal.png"},
    {"origen": 2000, "destino": 9000, "archivo": "ruta_portal_norte_portal_usme.png"},
    {"origen": 10009, "destino": 5000, "archivo": "ruta_museo_nacional_portal_americas.png"},
]


def dibujar_ruta(agente: AgenteRutas, origen, destino, archivo_salida: Path) -> dict:
    """Calcula la ruta origen->destino y guarda la imagen resaltada. Retorna
    el resultado de AgenteRutas.calcular_ruta() (incluye tiempo y memoria)."""
    resultado = agente.calcular_ruta(origen, destino)
    if not resultado["exito"]:
        raise ValueError(resultado["mensaje"])

    G = agente.G
    pos = {n: (G.nodes[n]["lon"], G.nodes[n]["lat"]) for n in G.nodes}
    cods_ruta = [est["cod_nodo"] for est in resultado["ruta"]]
    cods_transferencia = {
        cods_ruta[i]
        for i in range(1, len(cods_ruta))
        if G.nodes[cods_ruta[i]]["nom_tronc"] != G.nodes[cods_ruta[i - 1]]["nom_tronc"]
    }

    fig, ax = plt.subplots(figsize=(13, 13))

    # Red completa de fondo, en gris claro (mismo estilo que red_transmilenio_corregida.png)
    nx.draw_networkx_edges(G, pos, width=1.0, edge_color=COLOR_FONDO_ARISTA, alpha=0.7, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_size=25, node_color=COLOR_FONDO_NODO, ax=ax)

    # Ruta resaltada
    aristas_ruta = list(zip(cods_ruta, cods_ruta[1:]))
    nx.draw_networkx_edges(G, pos, edgelist=aristas_ruta, width=4.0, edge_color=COLOR_RUTA, ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=cods_ruta, node_size=70, node_color=COLOR_RUTA, ax=ax)

    # Estaciones de origen/destino y de transferencia, resaltadas aparte
    nx.draw_networkx_nodes(
        G, pos, nodelist=list(cods_transferencia), node_size=160,
        node_color=COLOR_TRANSFERENCIA, edgecolors="white", linewidths=1.2, ax=ax,
    )
    nx.draw_networkx_nodes(
        G, pos, nodelist=[cods_ruta[0], cods_ruta[-1]], node_size=180,
        node_color="#2e7d32", edgecolors="white", linewidths=1.2, ax=ax,
    )

    handles = [
        plt.Line2D([0], [0], color=COLOR_RUTA, lw=4, label="Ruta calculada"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor="#2e7d32", markersize=10, label="Origen / destino"),
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=COLOR_TRANSFERENCIA, markersize=10, label="Transferencia de troncal"),
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=9, framealpha=0.9)

    titulo = (
        f"{resultado['origen']} -> {resultado['destino']}\n"
        f"Estaciones: {resultado['num_estaciones']} | Transferencias: {resultado['num_transferencias']} "
        f"| Tiempo de calculo: {resultado['tiempo_calculo_ms']:.3f} ms"
    )
    ax.set_title(titulo, fontsize=13, fontweight="bold")
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(archivo_salida, dpi=200)
    plt.close(fig)

    return resultado


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    agente = AgenteRutas.desde_pickle()

    for caso in CASOS:
        archivo_salida = OUTPUT_DIR / caso["archivo"]
        resultado = dibujar_ruta(agente, caso["origen"], caso["destino"], archivo_salida)
        print(
            f"{resultado['origen']} -> {resultado['destino']}: "
            f"{resultado['num_estaciones']} estaciones, {resultado['num_transferencias']} transferencias, "
            f"{resultado['tiempo_calculo_ms']:.3f} ms -> {archivo_salida}"
        )


if __name__ == "__main__":
    main()
