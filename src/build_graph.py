"""Construcción del grafo de la red de carga interurbana.

Lee outputs/aristas_red.json y outputs/nodos_red.json (generados por
construir_red.py), calcula el costo compuesto por arista y guarda el grafo en
outputs/grafo_carga.gpickle.

Costo compuesto, normalizado por el máximo de cada criterio:

    c(e) = w1 * d_e / d_max + w2 * p_e / p_max + w3 * r_e / r_max

con r_e el puntaje GiZScore promedio de la arista. La normalización por el
máximo conserva la proporcionalidad con la distancia (la de mín-máx no).

Riesgo faltante: 21 de 33 aristas no tienen dato. No se imputa. Se guardan
dos variantes y un indicador booleano riesgo_disponible:
  - peso_multicriterio: riesgo faltante tratado como 0 (variante limitada,
    sesga hacia corredores sin medición);
  - peso_sin_riesgo: sin término de riesgo, con w1 y w2 renormalizados.
"""
import json
import pickle
from pathlib import Path

import networkx as nx

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "outputs"

# Sin criterio objetivo para ponderar los tres criterios: pesos iguales.
PESOS = {"distancia": 1 / 3, "peaje": 1 / 3, "riesgo": 1 / 3}


def cargar_datos():
    """Devuelve (nodos, aristas) leídos de los JSON de construir_red.py."""
    with open(SALIDA / "nodos_red.json", encoding="utf-8") as f:
        nodos = json.load(f)
    with open(SALIDA / "aristas_red.json", encoding="utf-8") as f:
        aristas = json.load(f)
    return nodos, aristas


def maximos(aristas):
    """Máximo de cada criterio (el de riesgo solo sobre datos disponibles)."""
    return {
        "distancia": max(a["distancia_km"] for a in aristas),
        "peaje": max(a["peaje_cop_camion"] for a in aristas),
        "riesgo": max(a["riesgo_gizscore_prom"] for a in aristas),
    }


def construir_grafo(pesos=None):
    """Construye el grafo no dirigido con los atributos de cada arista."""
    pesos = pesos or PESOS
    nodos, aristas = cargar_datos()
    tope = maximos(aristas)
    w1, w2, w3 = pesos["distancia"], pesos["peaje"], pesos["riesgo"]
    suma_sin_riesgo = w1 + w2

    grafo = nx.Graph()
    grafo.add_nodes_from(nodos)
    for a in aristas:
        disponible = a["riesgo_puntos_criticos"] > 0
        d = a["distancia_km"] / tope["distancia"]
        p = a["peaje_cop_camion"] / tope["peaje"]
        r = a["riesgo_gizscore_prom"] / tope["riesgo"] if disponible else 0.0
        grafo.add_edge(
            a["origen"], a["destino"],
            distancia_km=a["distancia_km"],
            peaje_nombre=a["peaje_nombre"],
            peaje_cop_camion=a["peaje_cop_camion"],
            riesgo_gizscore_prom=a["riesgo_gizscore_prom"],
            riesgo_fallecidos_hist=a["riesgo_fallecidos_hist"],
            riesgo_puntos_criticos=a["riesgo_puntos_criticos"],
            riesgo_disponible=disponible,
            peso_multicriterio=w1 * d + w2 * p + w3 * r,
            peso_sin_riesgo=(w1 * d + w2 * p) / suma_sin_riesgo,
        )
    grafo.graph["pesos"] = dict(pesos)
    grafo.graph["maximos"] = tope
    return grafo


def estadisticas(grafo):
    """Resumen verificable del grafo."""
    n, m = grafo.number_of_nodes(), grafo.number_of_edges()
    datos = [d for _, _, d in grafo.edges(data=True)]
    return {
        "nodos": n,
        "aristas": m,
        "conexo": nx.is_connected(grafo),
        "ciclos_independientes": m - n + 1,
        "aristas_con_peaje": sum(d["peaje_cop_camion"] > 0 for d in datos),
        "aristas_con_riesgo": sum(d["riesgo_disponible"] for d in datos),
        "distancia_total_km": round(sum(d["distancia_km"] for d in datos), 2),
        "maximos": grafo.graph["maximos"],
        "pesos": grafo.graph["pesos"],
    }


def guardar_grafo(grafo, ruta=None):
    ruta = ruta or SALIDA / "grafo_carga.gpickle"
    with open(ruta, "wb") as f:
        pickle.dump(grafo, f, protocol=pickle.HIGHEST_PROTOCOL)
    return ruta


def cargar_grafo(ruta=None):
    ruta = ruta or SALIDA / "grafo_carga.gpickle"
    with open(ruta, "rb") as f:
        return pickle.load(f)


def main():
    grafo = construir_grafo()
    ruta = guardar_grafo(grafo)
    stats = estadisticas(grafo)
    with open(SALIDA / "estadisticas_grafo.json", "w",
              encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    for clave, valor in stats.items():
        print(f"{clave}: {valor}")
    print(f"Grafo guardado en {ruta}")


if __name__ == "__main__":
    main()
