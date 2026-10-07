"""Pruebas del perfil topológico contra una enumeración independiente.

La enumeración de esta prueba no usa networkx: recorre el grafo con su propia
búsqueda en profundidad sobre listas de adyacencia, cuenta los caminos
simples de cada par, y calcula los puntos de articulación quitando cada nodo
y comprobando la conectividad con una búsqueda en anchura propia. Debe
coincidir con outputs/perfil_topologico.json y con los valores del estudio
previo de la red (111 y 385 pares con uno y dos caminos; 374 con paso
obligatorio; 105 con atajo; 17 de camino único; 10 puntos de articulación).
"""
import itertools
import json
import subprocess
import sys
from collections import deque
from pathlib import Path

from build_graph import SALIDA, cargar_grafo
from perfil_topologico import perfil

RAIZ = Path(__file__).resolve().parent.parent
ESPERADO = {"1": 111, "2": 385, "paso_obligatorio": 374, "atajo": 105,
            "camino_unico": 17, "articulacion": 10}


def ok(condicion, mensaje):
    if not condicion:
        print(f"  FALLA: {mensaje}")
        sys.exit(1)
    print(f"  ok: {mensaje}")


def adyacencia(grafo):
    return {n: sorted(grafo[n]) for n in grafo}


def caminos(ady, a, b):
    """Todos los caminos simples de a a b (DFS con pila propia)."""
    salida = []
    pila = [(a, [a])]
    while pila:
        nodo, camino = pila.pop()
        if nodo == b:
            salida.append(camino)
            continue
        for v in ady[nodo]:
            if v not in camino:
                pila.append((v, camino + [v]))
    return salida


def conexo_sin(ady, quitado):
    nodos = [n for n in ady if n != quitado]
    visto = {nodos[0]}
    cola = deque([nodos[0]])
    while cola:
        n = cola.popleft()
        for v in ady[n]:
            if v != quitado and v not in visto:
                visto.add(v)
                cola.append(v)
    return len(visto) == len(nodos)


def independiente(grafo):
    ady = adyacencia(grafo)
    conteo_caminos, conteo_clase = {}, {}
    detalle = {}
    for a, b in itertools.combinations(sorted(ady), 2):
        cs = caminos(ady, a, b)
        interiores = [frozenset(c[1:-1]) for c in cs]
        comun = frozenset.intersection(*interiores)
        disjuntos = any(not (x & y) for i, x in enumerate(interiores)
                        for y in interiores[i + 1:])
        clase = ("paso_obligatorio" if comun else
                 "atajo" if disjuntos else "camino_unico")
        clave = str(len(cs))
        conteo_caminos[clave] = conteo_caminos.get(clave, 0) + 1
        conteo_clase[clase] = conteo_clase.get(clase, 0) + 1
        detalle[f"{a}|{b}"] = (len(cs), clase, sorted(comun))
    articulacion = sorted(n for n in ady if not conexo_sin(ady, n))
    return conteo_caminos, conteo_clase, articulacion, detalle


def main():
    grafo = cargar_grafo()
    ok(grafo.number_of_nodes() == 32 and grafo.number_of_edges() == 32,
       "la red tiene 32 nodos y 32 aristas")
    p = perfil(grafo)
    caminos_i, clases_i, art_i, detalle_i = independiente(grafo)
    ok(sum(caminos_i.values()) == 496, "la enumeración independiente "
       "cubre los 496 pares")
    ok(p["pares_por_numero_de_caminos"] == caminos_i,
       f"caminos simples por par coinciden con la enumeración "
       f"independiente: {caminos_i}")
    ok(p["pares_por_clase"] == clases_i,
       f"clases (obligatorio, atajo, único) coinciden: {clases_i}")
    ok(p["puntos_de_articulacion"] == art_i,
       f"puntos de articulación coinciden: {len(art_i)}")
    ok(all((v["caminos"], v["clase"], v["obligatorios"]) == detalle_i[k]
           for k, v in p["detalle"].items()),
       "el detalle de cada uno de los 496 pares coincide")
    ok(caminos_i["1"] == ESPERADO["1"] and caminos_i["2"] == ESPERADO["2"],
       "111 pares con un camino y 385 con dos (estudio previo)")
    ok(clases_i["paso_obligatorio"] == ESPERADO["paso_obligatorio"]
       and clases_i["atajo"] == ESPERADO["atajo"]
       and clases_i["camino_unico"] == ESPERADO["camino_unico"],
       "374 con paso obligatorio, 105 con atajo y 17 de camino único")
    ok(len(art_i) == ESPERADO["articulacion"],
       "10 puntos de articulación (estudio previo)")
    ok(sum(clases_i.values()) == 496, "las tres clases suman 496")
    with open(SALIDA / "perfil_topologico.json", encoding="utf-8") as f:
        guardado = json.load(f)
    ok(guardado["pares_por_clase"] == clases_i
       and guardado["puntos_de_articulacion"] == art_i,
       "outputs/perfil_topologico.json coincide con la enumeración")
    r = subprocess.run([sys.executable, "-m", "pycodestyle",
                        "--max-line-length=79",
                        str(RAIZ / "src" / "perfil_topologico.py"),
                        str(RAIZ / "src" / "pruebas_perfil_topologico.py")],
                       capture_output=True, text=True)
    ok(r.returncode == 0, "pycodestyle limpio" + r.stdout)
    print("Todas las pruebas del perfil topológico pasaron.")


if __name__ == "__main__":
    main()
