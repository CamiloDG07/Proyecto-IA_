"""Demostración en vivo: los cinco algoritmos sobre un par de ciudades.

Uso:
    python src/demostracion.py ORIGEN DESTINO [CRITERIO]

CRITERIO es distancia (por defecto), compuesto_sin_riesgo, compuesto, peaje o
riesgo. Imprime, por algoritmo, la ruta, el costo, los nodos expandidos y
generados, la frontera máxima y el tiempo medio de 200 repeticiones.
"""
import sys

from agente import CRITERIOS
from build_graph import cargar_grafo
from busquedas import a_estrella, bfs, dfs, medir, ucs, voraz
from heuristica import Heuristica, alfa_minimo, cargar_coordenadas

REPETICIONES = 200


def main(argumentos):
    if len(argumentos) not in (2, 3):
        print(__doc__)
        return 1
    origen, destino = argumentos[0], argumentos[1]
    criterio = argumentos[2] if len(argumentos) == 3 else "distancia"
    if criterio not in CRITERIOS:
        print(f"Criterio desconocido: {criterio}")
        return 1
    grafo = cargar_grafo()
    coordenadas = cargar_coordenadas()
    h = Heuristica(grafo, coordenadas, criterio,
                   alfa_minimo(grafo, coordenadas))
    atributo = CRITERIOS[criterio]
    casos = [
        ("BFS", bfs, (grafo, origen, destino, atributo)),
        ("DFS", dfs, (grafo, origen, destino, atributo)),
        ("UCS", ucs, (grafo, origen, destino, atributo)),
        ("Voraz", voraz, (grafo, origen, destino, atributo, h)),
        ("A*", a_estrella, (grafo, origen, destino, atributo, h)),
    ]
    nota = " (heurística limitada)" if h.limitada else ""
    print(f"{origen} a {destino}, criterio {criterio}{nota}")
    for nombre, funcion, args in casos:
        m = medir(funcion, REPETICIONES, *args)
        r = m["resultado"]
        via = "Santander" if "Bucaramanga" in r["ruta"] else "Bogotá"
        print(f"{nombre:6s} costo {r['costo']:9.3f}  expandidos "
              f"{r['nodos_expandidos']:3d}  generados "
              f"{r['nodos_generados']:3d}  frontera {r['frontera_max']:2d}  "
              f"{m['tiempo_media_s'] * 1e6:7.1f} us  {r['saltos']} saltos")
        print(f"       {' > '.join(r['ruta'])}"
              + (f"  [{via}]" if "Bogotá" in r["ruta"]
                 or "Bucaramanga" in r["ruta"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
