"""Pruebas de corrección de busquedas.py y heuristica.py.

1. Grafo de juguete con resultado conocido a mano.
2. Grafos geométricos aleatorios (semilla fija), contra networkx.
3. La red de carga: todos los pares de nodos y todos los criterios.

Las referencias de costo salen de nx.shortest_path_length; los algoritmos
de busquedas.py no usan networkx para buscar.
"""
import random
from itertools import permutations
from math import hypot

import networkx as nx

from busquedas import a_estrella, bfs, dfs, ucs, voraz
from build_graph import cargar_grafo
from heuristica import (ATRIBUTOS, Heuristica, alfa_minimo,
                        cargar_coordenadas)

EPS = 1e-9
SEMILLA = 20261020


def ruta_valida(grafo, ruta, origen, destino):
    return (ruta[0] == origen and ruta[-1] == destino
            and len(set(ruta)) == len(ruta)
            and all(grafo.has_edge(u, v) for u, v in zip(ruta, ruta[1:])))


def verificar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)


def prueba_juguete():
    """Grafo con dos rutas: A-B-D (2 saltos, costo 10) y A-C-E-D (3, 6)."""
    g = nx.Graph()
    for u, v, w in [("A", "B", 4), ("B", "D", 6), ("A", "C", 1),
                    ("C", "E", 2), ("E", "D", 3)]:
        g.add_edge(u, v, costo=w)
    r = ucs(g, "A", "D", "costo")
    verificar(r["ruta"] == ["A", "C", "E", "D"] and r["costo"] == 6,
              "UCS: ruta óptima de costo 6")
    r = bfs(g, "A", "D", "costo")
    verificar(r["ruta"] == ["A", "B", "D"] and r["costo"] == 10,
              "BFS: ruta de menos saltos (2) aunque cueste 10")
    r = dfs(g, "A", "D", "costo")
    verificar(ruta_valida(g, r["ruta"], "A", "D"), "DFS: ruta válida")

    def h_cero(nodo, meta):
        return 0.0

    r = a_estrella(g, "A", "D", "costo", h_cero)
    verificar(r["costo"] == 6, "A* con h = 0 es óptimo (costo 6)")
    r = voraz(g, "A", "D", "costo", h_cero)
    verificar(ruta_valida(g, r["ruta"], "A", "D"), "Voraz: ruta válida")
    r = ucs(g, "A", "A", "costo")
    verificar(r["ruta"] == ["A"] and r["costo"] == 0, "origen = destino")
    g.add_node("Z")
    for algoritmo in (lambda: bfs(g, "A", "Z"), lambda: dfs(g, "A", "Z"),
                      lambda: ucs(g, "A", "Z", "costo")):
        try:
            algoritmo()
        except ValueError:
            continue
        raise AssertionError("Debía fallar sin ruta")
    print("  ok: grafo de juguete (UCS, BFS, DFS, A*, voraz, sin ruta)")


def grafo_aleatorio(n, semilla):
    """Grafo geométrico conexo; costo = distancia euclidiana * factor >= 1."""
    azar = random.Random(semilla)
    puntos = {i: (azar.uniform(0, 100), azar.uniform(0, 100))
              for i in range(n)}
    g = nx.Graph()
    g.add_nodes_from(puntos)
    orden = list(puntos)
    azar.shuffle(orden)
    pares = list(zip(orden, orden[1:]))
    pares += [tuple(azar.sample(orden, 2)) for _ in range(n)]
    for u, v in pares:
        d = hypot(puntos[u][0] - puntos[v][0], puntos[u][1] - puntos[v][1])
        g.add_edge(u, v, costo=d * azar.uniform(1.0, 1.8))
    return g, puntos


def prueba_aleatorios():
    total = 0
    for semilla in range(SEMILLA, SEMILLA + 25):
        g, p = grafo_aleatorio(30, semilla)

        def h(n, m, p=p):
            return hypot(p[n][0] - p[m][0], p[n][1] - p[m][1])

        for o, d in list(permutations(g, 2))[::37]:
            optimo = nx.shortest_path_length(g, o, d, weight="costo")
            saltos = nx.shortest_path_length(g, o, d)
            r = ucs(g, o, d, "costo")
            verificar(abs(r["costo"] - optimo) < EPS, "UCS óptimo")
            r = a_estrella(g, o, d, "costo", h)
            verificar(abs(r["costo"] - optimo) < EPS, "A* óptimo")
            verificar(r["reexpansiones"] == 0, "A* con h consistente")
            r = bfs(g, o, d, "costo")
            verificar(r["saltos"] == saltos, "BFS mínimo de saltos")
            for r in (dfs(g, o, d, "costo"), voraz(g, o, d, "costo", h)):
                verificar(ruta_valida(g, r["ruta"], o, d), "ruta válida")
            total += 1
    print(f"  ok: {total} pares en 25 grafos aleatorios (semilla fija)")


def prueba_red():
    grafo = cargar_grafo()
    coordenadas = cargar_coordenadas()
    alfa = alfa_minimo(grafo, coordenadas)
    pares = list(permutations(grafo, 2))
    for criterio, atributo in ATRIBUTOS.items():
        h = Heuristica(grafo, coordenadas, criterio, alfa)
        for o, d in pares:
            optimo = nx.shortest_path_length(grafo, o, d, weight=atributo)
            r = ucs(grafo, o, d, atributo)
            verificar(abs(r["costo"] - optimo) < EPS,
                      f"UCS óptimo {o}-{d} ({criterio})")
            r = a_estrella(grafo, o, d, atributo, h)
            verificar(abs(r["costo"] - optimo) < EPS,
                      f"A* óptimo {o}-{d} ({criterio})")
            verificar(r["reexpansiones"] == 0,
                      f"A* sin reexpansiones {o}-{d} ({criterio})")
            r = bfs(grafo, o, d, atributo)
            verificar(r["saltos"] == nx.shortest_path_length(grafo, o, d),
                      f"BFS mínimo de saltos {o}-{d}")
            for r in (dfs(grafo, o, d, atributo),
                      voraz(grafo, o, d, atributo, h)):
                verificar(ruta_valida(grafo, r["ruta"], o, d),
                          f"ruta válida {o}-{d} ({criterio})")
        print(f"  ok: {len(pares)} pares, criterio {criterio}")


def main():
    print("Pruebas de busquedas.py y heuristica.py")
    prueba_juguete()
    prueba_aleatorios()
    prueba_red()
    print("Todas las pruebas pasaron.")


if __name__ == "__main__":
    main()
