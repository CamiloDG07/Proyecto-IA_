"""Algoritmos de búsqueda implementados desde cero: BFS, DFS, costo uniforme
(UCS), voraz (greedy best-first) y A*.

No se usan las búsquedas de networkx; el grafo solo aporta vecinos y costos
de arista. Todos los algoritmos devuelven un diccionario con la ruta, su
costo y los contadores de la búsqueda.

Convenciones (las mismas para los cinco, para que los contadores sean
comparables):
  - nodos_generados: nodos insertados en la frontera (incluye el origen y
    las entradas repetidas que se reinsertan por mejor costo);
  - nodos_expandidos: nodos extraídos de la frontera cuyos sucesores se
    generan. El nodo meta se extrae pero no se expande, y no se cuenta;
  - frontera_max: tamaño máximo de la frontera;
  - reexpansiones: expansiones de un nodo ya expandido antes (solo ocurre
    en UCS y A* si el costo mejora; con h consistente es 0).
  - La prueba de meta se hace al extraer el nodo de la frontera.
  - Los vecinos se recorren en orden alfabético, de modo que BFS y DFS son
    deterministas.

BFS minimiza el número de saltos, no el costo. DFS devuelve la primera ruta
que encuentra en su orden de exploración. UCS y A* con h admisible son
óptimos. La búsqueda voraz no garantiza optimalidad.

El tiempo se mide sin tracemalloc y la memoria en una corrida aparte, porque
tracemalloc distorsiona el tiempo (ver medir).
"""
import heapq
import time
import tracemalloc
from collections import deque
from itertools import count
from statistics import mean, pstdev


def _vecinos(grafo, nodo):
    return sorted(grafo[nodo])


def _validar(grafo, origen, destino):
    for nodo in (origen, destino):
        if nodo not in grafo:
            raise ValueError(f"Nodo fuera del grafo: {nodo}")


def _reconstruir(padre, destino):
    ruta = [destino]
    while padre[ruta[-1]] is not None:
        ruta.append(padre[ruta[-1]])
    return ruta[::-1]


def _resultado(grafo, atributo, ruta, expandidos, generados, frontera_max,
               reexpansiones=0):
    costo = sum(grafo[u][v][atributo] for u, v in zip(ruta, ruta[1:]))
    return {
        "ruta": ruta,
        "saltos": len(ruta) - 1,
        "costo": costo,
        "nodos_expandidos": expandidos,
        "nodos_generados": generados,
        "frontera_max": frontera_max,
        "reexpansiones": reexpansiones,
    }


def _sin_ruta(origen, destino):
    return ValueError(f"Sin ruta de {origen} a {destino}")


def bfs(grafo, origen, destino, atributo="distancia_km"):
    """Búsqueda en anchura: ruta con el menor número de saltos."""
    _validar(grafo, origen, destino)
    frontera = deque([origen])
    padre = {origen: None}
    expandidos, generados, maximo = 0, 1, 1
    while frontera:
        nodo = frontera.popleft()
        if nodo == destino:
            return _resultado(grafo, atributo, _reconstruir(padre, nodo),
                              expandidos, generados, maximo)
        expandidos += 1
        for vecino in _vecinos(grafo, nodo):
            if vecino not in padre:
                padre[vecino] = nodo
                frontera.append(vecino)
                generados += 1
        maximo = max(maximo, len(frontera))
    raise _sin_ruta(origen, destino)


def dfs(grafo, origen, destino, atributo="distancia_km"):
    """Búsqueda en profundidad (grafo, con conjunto de explorados)."""
    _validar(grafo, origen, destino)
    frontera = [(origen, None)]
    padre = {}
    expandidos, generados, maximo = 0, 1, 1
    while frontera:
        nodo, anterior = frontera.pop()
        if nodo in padre:
            continue
        padre[nodo] = anterior
        if nodo == destino:
            return _resultado(grafo, atributo, _reconstruir(padre, nodo),
                              expandidos, generados, maximo)
        expandidos += 1
        for vecino in reversed(_vecinos(grafo, nodo)):
            if vecino not in padre:
                frontera.append((vecino, nodo))
                generados += 1
        maximo = max(maximo, len(frontera))
    raise _sin_ruta(origen, destino)


def _mejor_primero(grafo, origen, destino, atributo, prioridad):
    """Núcleo de UCS y A*: prioridad(g, nodo) -> f. Con reexpansión."""
    _validar(grafo, origen, destino)
    orden = count()
    mejor_g = {origen: 0.0}
    padre = {origen: None}
    expandido = set()
    frontera = [(prioridad(0.0, origen), next(orden), 0.0, origen)]
    expandidos, generados, maximo, reexpansiones = 0, 1, 1, 0
    while frontera:
        _, _, g, nodo = heapq.heappop(frontera)
        if g > mejor_g[nodo]:
            continue
        if nodo == destino:
            return _resultado(grafo, atributo, _reconstruir(padre, nodo),
                              expandidos, generados, maximo, reexpansiones)
        if nodo in expandido:
            reexpansiones += 1
        expandido.add(nodo)
        expandidos += 1
        for vecino in _vecinos(grafo, nodo):
            nuevo = g + grafo[nodo][vecino][atributo]
            if nuevo < mejor_g.get(vecino, float("inf")):
                mejor_g[vecino] = nuevo
                padre[vecino] = nodo
                heapq.heappush(frontera, (prioridad(nuevo, vecino),
                                          next(orden), nuevo, vecino))
                generados += 1
        maximo = max(maximo, len(frontera))
    raise _sin_ruta(origen, destino)


def ucs(grafo, origen, destino, atributo="distancia_km"):
    """Costo uniforme: óptimo para costos no negativos."""
    return _mejor_primero(grafo, origen, destino, atributo,
                          lambda g, nodo: g)


def a_estrella(grafo, origen, destino, atributo, h):
    """A*: f = g + h(n, destino). Óptimo si h es admisible."""
    return _mejor_primero(grafo, origen, destino, atributo,
                          lambda g, nodo: g + h(nodo, destino))


def voraz(grafo, origen, destino, atributo, h):
    """Búsqueda voraz: expande el nodo con menor h(n, destino)."""
    _validar(grafo, origen, destino)
    orden = count()
    padre = {origen: None}
    expandido = set()
    frontera = [(h(origen, destino), next(orden), origen)]
    expandidos, generados, maximo = 0, 1, 1
    while frontera:
        _, _, nodo = heapq.heappop(frontera)
        if nodo in expandido:
            continue
        if nodo == destino:
            return _resultado(grafo, atributo, _reconstruir(padre, nodo),
                              expandidos, generados, maximo)
        expandido.add(nodo)
        expandidos += 1
        for vecino in _vecinos(grafo, nodo):
            if vecino not in expandido and vecino not in padre:
                padre[vecino] = nodo
                heapq.heappush(frontera, (h(vecino, destino), next(orden),
                                          vecino))
                generados += 1
        maximo = max(maximo, len(frontera))
    raise _sin_ruta(origen, destino)


def medir(algoritmo, repeticiones, *args, **kwargs):
    """Tiempo (media y desviación estándar) y memoria pico de un algoritmo.

    El tiempo se mide en `repeticiones` corridas sin tracemalloc; la memoria
    pico se mide en una corrida adicional con tracemalloc. Devuelve también
    el resultado de la búsqueda (determinista) y el número de repeticiones.
    """
    resultado = algoritmo(*args, **kwargs)
    tiempos = []
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        algoritmo(*args, **kwargs)
        tiempos.append(time.perf_counter() - inicio)
    tracemalloc.start()
    algoritmo(*args, **kwargs)
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "resultado": resultado,
        "repeticiones": repeticiones,
        "tiempo_media_s": mean(tiempos),
        "tiempo_desv_s": pstdev(tiempos),
        "memoria_pico_kib": pico / 1024,
    }
