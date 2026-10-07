"""Verifica la fórmula del óptimo por estructura contra Held-Karp.

Para un grafo conexo con un solo ciclo, el recorrido cerrado de costo mínimo
que visita todos los nodos cuesta

    2 (W - C) + min(C, 2 (C - w_max)),

con W la suma de todas las aristas, C la longitud del ciclo y w_max su arista
mayor. Argumento: en un recorrido cerrado todo puente se recorre dos veces
(hay nodos al otro lado); en el ciclo, el grado par en cada nodo obliga a que
todas las aristas se usen una vez (el ciclo completo) o a que se usen dos
veces todas menos una (la omitida), y la mayor es la mejor omisión.

Aquí se comprueba numéricamente: N_GRAFOS grafos aleatorios de un solo ciclo
(n entre 5 y 12 nodos, ciclo de longitud 3 a n, pesos aleatorios con semilla
fija), con el costo de Held-Karp (modo ciclo) sobre la matriz de caminos
mínimos entre todos los nodos. Escribe outputs/verificacion_estructura.json.
"""
import json
import random
from collections import Counter

import networkx as nx
import numpy as np

from build_graph import SALIDA
from held_karp import held_karp
from validacion_agente import optimo_unicicilo

N_GRAFOS = 300
SEMILLA = 20261020
TOLERANCIA = 1e-9


def grafo_unicicilo(azar):
    """Grafo conexo de un solo ciclo con n nodos y pesos aleatorios."""
    n = azar.randint(5, 12)
    largo = azar.randint(3, n)
    g = nx.Graph()
    for i in range(largo):
        g.add_edge(i, (i + 1) % largo, peso=azar.uniform(1, 10))
    for nodo in range(largo, n):
        g.add_edge(nodo, azar.randrange(nodo), peso=azar.uniform(1, 10))
    return g, n, largo


def main():
    azar = random.Random(SEMILLA)
    discrepancias, largos = [], Counter()
    peor = 0.0
    for i in range(N_GRAFOS):
        g, n, largo = grafo_unicicilo(azar)
        largos[largo] += 1
        distancias = dict(nx.all_pairs_dijkstra_path_length(g,
                                                            weight="peso"))
        matriz = np.array([[distancias[a][b] for b in range(n)]
                           for a in range(n)])
        exacto, _ = held_karp(matriz, 0, "ciclo")
        formula = optimo_unicicilo(g, "peso")
        peor = max(peor, abs(exacto - formula))
        if abs(exacto - formula) > TOLERANCIA:
            discrepancias.append({"grafo": i, "n": n, "ciclo": largo,
                                  "held_karp": exacto, "formula": formula})
    resultado = {
        "grafos": N_GRAFOS, "semilla": SEMILLA,
        "coincidencias": N_GRAFOS - len(discrepancias),
        "discrepancias": discrepancias,
        "mayor_diferencia_absoluta": peor,
        "tolerancia": TOLERANCIA,
        "longitudes_de_ciclo": dict(sorted(largos.items())),
        "nodos": "5 a 12",
    }
    with open(SALIDA / "verificacion_estructura.json", "w",
              encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=1)
    print(f"{N_GRAFOS} grafos: {resultado['coincidencias']} coincidencias, "
          f"{len(discrepancias)} discrepancias, mayor diferencia {peor:.2e}")
    print("longitudes de ciclo:", resultado["longitudes_de_ciclo"])


if __name__ == "__main__":
    main()
