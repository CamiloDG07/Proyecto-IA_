"""Pruebas del núcleo de trazas (src/trazas.py).

1. Equivalencia con busquedas.py: para los 992 pares ordenados de la red, los
   9 criterios y los 5 algoritmos (44 640 casos), la ruta, el costo, los
   saltos, los expandidos, los generados, la frontera máxima y las
   reexpansiones de la versión con traza son idénticos a los de busquedas.py.
2. Invariantes de la traza en los mismos casos: cada entrada se extrae a lo
   sumo una vez; el último paso es la meta; los contadores del último paso
   coinciden con los finales; toda entrada tiene un padre creado antes y
   expandido en el paso en que nació; la frontera de cada paso es el
   conjunto de entradas creadas y aún no extraídas; la rama de la meta
   reproduce la ruta.
"""
import sys
from pathlib import Path
if True:  # carpetas de código en el path
    sys.path[:0] = [str(Path(__file__).resolve().parents[1] / c)
                    for c in ("src", "experimentos", "informe", "pruebas")]
from build_graph import cargar_grafo
from busquedas import a_estrella, bfs, dfs, ucs, voraz
from heuristica import (ATRIBUTOS, Heuristica, alfa_minimo,
                        cargar_coordenadas)
from trazas import (a_estrella_traza, bfs_traza, dfs_traza, ucs_traza,
                    voraz_traza)

CAMPOS = ("ruta", "costo", "saltos", "nodos_expandidos", "nodos_generados",
          "frontera_max", "reexpansiones")


def verificar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)


def pares(algoritmo, h):
    """Funciones (sin traza, con traza) y sus argumentos de heurística."""
    sin_h = {"bfs": (bfs, bfs_traza), "dfs": (dfs, dfs_traza),
             "ucs": (ucs, ucs_traza)}
    if algoritmo in sin_h:
        return sin_h[algoritmo], ()
    funciones = {"voraz": (voraz, voraz_traza),
                 "astar": (a_estrella, a_estrella_traza)}
    return funciones[algoritmo], (h,)


def invariantes(r, destino, caso):
    entradas, pasos = r["entradas"], r["pasos"]
    extraidas = [p["extraida"] for p in pasos[1:]]
    verificar(len(extraidas) == len(set(extraidas)),
              f"{caso}: una entrada se extrajo más de una vez")
    verificar(all(e["extraido"] is None or pasos[e["extraido"]]["extraida"]
                  == e["id"] for e in entradas),
              f"{caso}: el paso de extracción no coincide")
    ultimo = pasos[-1]
    meta = entradas[ultimo["extraida"]]
    verificar(ultimo["resultado"] == "meta" and meta["ciudad"] == destino
              and meta["resultado"] == "meta",
              f"{caso}: el último paso no es la meta")
    verificar((ultimo["expandidos"], ultimo["generados"],
               ultimo["frontera_max"], ultimo["reexpansiones"])
              == (r["nodos_expandidos"], r["nodos_generados"],
                  r["frontera_max"], r["reexpansiones"]),
              f"{caso}: contadores finales distintos")
    verificar(len(pasos) == len(extraidas) + 1
              and pasos[0]["resultado"] == "inicio",
              f"{caso}: pasos mal formados")
    for e in entradas:
        if e["padre"] is None:
            verificar(e["id"] == 0 and e["creado"] == 0,
                      f"{caso}: solo el origen carece de padre")
            continue
        padre = entradas[e["padre"]]
        verificar(padre["id"] < e["id"] and padre["creado"] < e["creado"]
                  and padre["extraido"] == e["creado"]
                  and padre["resultado"] == "expandido",
                  f"{caso}: padre de la entrada {e['id']} inválido")
    for numero, paso in enumerate(pasos):
        esperado = {e["id"] for e in entradas if e["creado"] <= numero
                    and (e["extraido"] is None or e["extraido"] > numero)}
        verificar(set(paso["frontera"]) == esperado
                  and len(paso["frontera"]) == len(esperado),
                  f"{caso}: frontera del paso {numero} inconsistente")
    rama, ident = [], meta["id"]
    while ident is not None:
        rama.append(entradas[ident]["ciudad"])
        ident = entradas[ident]["padre"]
    verificar(rama[::-1] == r["ruta"], f"{caso}: la rama no es la ruta")


def main():
    grafo = cargar_grafo()
    coordenadas = cargar_coordenadas()
    alfa = alfa_minimo(grafo, coordenadas)
    nodos = sorted(grafo)
    casos = 0
    for criterio, atributo in ATRIBUTOS.items():
        h = Heuristica(grafo, coordenadas, criterio, alfa)
        for algoritmo in ("bfs", "dfs", "ucs", "voraz", "astar"):
            (base, traza), extra = pares(algoritmo, h)
            for origen in nodos:
                for destino in nodos:
                    if origen == destino:
                        continue
                    esperado = base(grafo, origen, destino, atributo,
                                    *extra)
                    r = traza(grafo, origen, destino, atributo, *extra)
                    caso = f"{algoritmo} {criterio} {origen}->{destino}"
                    for campo in CAMPOS:
                        verificar(r[campo] == esperado[campo],
                                  f"{caso}: {campo} difiere")
                    invariantes(r, destino, caso)
                    casos += 1
        print(f"Criterio {criterio}: equivalente en los 5 algoritmos")
    verificar(casos == 44640, f"se esperaban 44640 casos, hubo {casos}")
    print(f"{casos} casos idénticos a busquedas.py con invariantes válidos")
    r = a_estrella_traza(grafo, "Duitama", "Puente Nacional", "distancia_km",
                         Heuristica(grafo, coordenadas, "distancia", alfa))
    verificar(r["nodos_expandidos"] == 14 and len(r["h"]) == 32,
              "A* distancia del caso central expande 14 nodos")
    print("Caso central: A* con distancia expande 14 nodos; tabla h de 32")


if __name__ == "__main__":
    main()
