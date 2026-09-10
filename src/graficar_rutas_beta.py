"""
graficar_rutas_beta.py

Genera, para cada caso de prueba en outputs/pruebas_agente.json, una imagen del
grafo real (outputs/grafo_transmilenio.gpickle) con la ruta calculada resaltada
por tramos de troncal y etiquetas estilo "letrero de bus" (numero de ruta facil +
estacion donde termina el tramo), usando directamente los campos "ruta" y
"rutas_tomadas" que ya devuelve AgenteRutas.calcular_ruta() (ver src/agente.py).

Uso:
    python src/graficar_rutas_beta.py

Salida:
    outputs/ruta_beta_<origen>_<destino>.png  (una imagen por caso de prueba exitoso)

Nota: cada estacion en "ruta" ya trae su cod_nodo (identificador unico); el
grafo se indexa por cod_nodo en vez de por nombre porque el dataset tiene un
nombre duplicado ("Temporal AV. Jimenez - Inter Electricas" son dos estaciones
fisicas distintas, cod_nodo 9110 en Caracas y 14003 en Eje Ambiental, ~150m
aparte -las 3 rutas de prueba pasan por ahi-). Resolver por nombre en vez de
cod_nodo dibujaria el tramo equivocado justo en ese punto.
"""
import json
import pickle
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.lines import Line2D

BASE_DIR = Path(__file__).resolve().parent.parent
GRAFO_PICKLE = BASE_DIR / "outputs" / "grafo_transmilenio.gpickle"
PRUEBAS_JSON = BASE_DIR / "outputs" / "pruebas_agente.json"

COLOR_POR_TRONCAL = {
    "Americas": "#1f77b4", "Autopista Norte": "#ff7f0e", "Avenida Ciudad de Cali": "#2ca02c",
    "Calle 26": "#d62728", "Calle 80": "#9467bd", "Caracas": "#8c564b", "Caracas Sur": "#e377c2",
    "Carrera 10": "#7f7f7f", "Carrera 7": "#bcbd22", "Eje Ambiental": "#17becf",
    "NQS Central": "#aa1f99", "NQS Sur": "#3355ff", "Suba": "#228833",
}

OFFSETS = [
    (14, 14), (14, -26), (-95, 14), (-95, -26),
    (14, 46), (-95, 46), (14, -58), (-95, -58),
]


def slug(texto: str) -> str:
    texto = texto.lower()
    for a, b in [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")]:
        texto = texto.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "_", texto).strip("_")


def agrupar_por_tramo(ruta):
    """Reagrupa la lista de estaciones (campo 'ruta', cada una con cod_nodo,
    nom_est, nom_tronc) en bloques consecutivos del mismo troncal, en el mismo
    orden en que calcular_ruta() arma 'rutas_tomadas'. Devuelve una lista de
    listas de cod_nodo (no de nombres: el dataset tiene un nombre duplicado
    entre dos estaciones fisicas distintas, ver docstring del modulo)."""
    bloques = []
    actual = None
    for est in ruta:
        tronc = est["nom_tronc"]
        if actual is None or actual["troncal"] != tronc:
            if actual is not None:
                bloques.append(actual["cods"])
            actual = {"troncal": tronc, "cods": [est["cod_nodo"]]}
        else:
            actual["cods"].append(est["cod_nodo"])
    if actual is not None:
        bloques.append(actual["cods"])
    return bloques


def main():
    with open(GRAFO_PICKLE, "rb") as f:
        G = pickle.load(f)
    with open(PRUEBAS_JSON, encoding="utf-8") as f:
        casos = json.load(f)

    pos = {n: (d["lon"], d["lat"]) for n, d in G.nodes(data=True)}

    for caso in casos:
        if not caso.get("exito"):
            continue

        ruta = caso["ruta"]
        rutas_tomadas = caso["rutas_tomadas"]
        bloques = agrupar_por_tramo(ruta)

        if len(bloques) != len(rutas_tomadas):
            print(f"[!] Aviso: {caso['caso']} - bloques ({len(bloques)}) y "
                  f"rutas_tomadas ({len(rutas_tomadas)}) no coinciden, se omite.")
            continue

        ruta_nodos = [e["cod_nodo"] for e in ruta]

        fig, ax = plt.subplots(figsize=(11, 9))
        nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#d9d9d9", width=1.0)
        nx.draw_networkx_nodes(G, pos, ax=ax, node_size=15, node_color="#d9d9d9")

        legend_elements = []
        for i, (nodos_seg, tramo) in enumerate(zip(bloques, rutas_tomadas)):
            color = COLOR_POR_TRONCAL.get(tramo["troncal"], "black")
            edges_seg = list(zip(nodos_seg[:-1], nodos_seg[1:]))
            if edges_seg:
                nx.draw_networkx_edges(G, pos, ax=ax, edgelist=edges_seg, edge_color=color, width=4.5)
            nx.draw_networkx_nodes(G, pos, ax=ax, nodelist=nodos_seg, node_size=45, node_color=color)

            nodo_destino = nodos_seg[-1]
            destino_nombre = G.nodes[nodo_destino]["nom_est"]
            x, y = pos[nodo_destino]
            etiqueta = f"{tramo['ruta_facil']}  {destino_nombre}"
            dx, dy = OFFSETS[i % len(OFFSETS)]
            ax.annotate(
                etiqueta, xy=(x, y), xytext=(dx, dy), textcoords="offset points",
                fontsize=8.5, fontweight="bold", color="white",
                bbox=dict(boxstyle="round,pad=0.3", fc=color, ec="none", alpha=0.95),
                arrowprops=dict(arrowstyle="-", color=color, lw=1.2, shrinkA=0, shrinkB=6, alpha=0.9),
                zorder=6,
            )
            legend_elements.append(Line2D([0], [0], color=color, lw=4.5,
                                           label=f"Ruta {tramo['ruta_facil']} ({tramo['troncal']})"))

        nx.draw_networkx_nodes(G, pos, ax=ax, nodelist=[ruta_nodos[0]], node_size=180,
                                node_color="white", edgecolors="black", linewidths=2)
        nx.draw_networkx_nodes(G, pos, ax=ax, nodelist=[ruta_nodos[-1]], node_size=180,
                                node_color="white", edgecolors="black", linewidths=2)

        ax.legend(handles=legend_elements, loc="lower left", fontsize=9, framealpha=0.9,
                  title="Rutas fáciles (beta)")
        ax.set_title(f"{caso['caso']}\n{caso['num_estaciones']} estaciones · "
                     f"{caso['num_transferencias']} transferencias · "
                     f"{caso['distancia_total_km']} km · {caso['tiempo_viaje_min']} min", fontsize=11)
        ax.set_xlabel("Longitud")
        ax.set_ylabel("Latitud")
        ax.set_aspect("equal")
        ax.margins(0.12)
        fig.tight_layout()

        nombre_archivo = f"ruta_beta_{slug(caso['origen'])}_{slug(caso['destino'])}.png"
        salida = BASE_DIR / "outputs" / nombre_archivo
        fig.savefig(salida, dpi=200)
        plt.close(fig)
        print(f"Guardado: {salida}")


if __name__ == "__main__":
    main()
