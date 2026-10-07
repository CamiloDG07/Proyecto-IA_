"""Demostración en vivo: los cinco algoritmos y el despachador.

Uso:
    python src/demostracion.py ORIGEN DESTINO [CRITERIO]
    python src/demostracion.py despachador TIPO ORIGEN [--destino D]
        [--paradas A,B] [--obligatorias A,B] [--bloqueados U/V;X/Y]
        [--criterio C]

CRITERIO es distancia (por defecto), compuesto_sin_riesgo, compuesto, peaje o
riesgo. La primera forma imprime, por algoritmo, la ruta, el costo, los nodos
expandidos y generados, la frontera máxima y el tiempo medio de 200
repeticiones. La segunda llama al despachador y muestra la ruta, el costo, el
método elegido, el motivo y las métricas. TIPO es a (origen a destino), b
(paradas en orden fijo), c (obligatorias o tramos bloqueados), d (orden libre
con regreso) o e (orden libre sin regreso).
"""
import argparse
import sys

from agente import CRITERIOS
from build_graph import cargar_grafo
from busquedas import a_estrella, bfs, dfs, medir, ucs, voraz
from despachador import Despachador, Solicitud
from heuristica import Heuristica, alfa_minimo, cargar_coordenadas

REPETICIONES = 200


def main(argumentos):
    if argumentos and argumentos[0] == "despachador":
        lector = argparse.ArgumentParser(prog="demostracion.py despachador")
        lector.add_argument("tipo", choices=list("abcde"))
        lector.add_argument("origen")
        lector.add_argument("--destino")
        lector.add_argument("--paradas", default="")
        lector.add_argument("--obligatorias", default="")
        lector.add_argument("--bloqueados", default="")
        lector.add_argument("--criterio", default="distancia",
                            choices=list(CRITERIOS))
        a = lector.parse_args(argumentos[1:])
        lista = [x for x in a.paradas.split(",") if x]
        restricciones = {
            "obligatorias": [x for x in a.obligatorias.split(",") if x],
            "bloqueados": [tuple(x.split("/"))
                           for x in a.bloqueados.split(";") if x]}
        grafo = cargar_grafo()
        salida = Despachador(grafo, cargar_coordenadas()).resolver(
            Solicitud(a.tipo, a.origen, a.destino, tuple(lista),
                      a.criterio, restricciones))
        print(f"Tipo {a.tipo} ({salida['tipo']}), criterio {a.criterio}")
        print(f"Ruta: {' > '.join(salida['ruta'])}")
        print(f"Orden de paradas: {' > '.join(salida['orden_paradas'])}")
        print(f"Costo: {salida['costo']:.3f}")
        print(f"Método: {salida['metodo']}")
        print(f"Motivo: {salida['motivo']}")
        for clave, valor in salida["metricas"].items():
            print(f"  {clave}: {valor}")
        return 0
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
