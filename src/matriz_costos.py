"""Matriz de costos entre paradas con las búsquedas propias del proyecto.

Para un conjunto de paradas calcula el costo y la ruta expandida de cada par
con UCS o A* (de busquedas.py; no se reimplementa ninguna búsqueda). Es
genérica: sirve para cualquier grafo de networkx con un atributo de costo
no negativo por arista, y admite tramos bloqueados.

Si el grafo no es dirigido solo se busca un sentido de cada par y el otro se
obtiene invirtiendo la ruta; si es dirigido se buscan los dos sentidos.
"""
import time

import networkx as nx
import numpy as np

from busquedas import a_estrella, ucs


class MatrizCostos:
    """Costos y rutas entre las paradas, con el atributo de costo dado."""

    def __init__(self, grafo, paradas, atributo, bloqueados=(),
                 heuristica=None):
        """heuristica: objeto con precalcular(grafo, meta) y limitada; si
        se da, los tramos se resuelven con A* (debe ser admisible); si no,
        con UCS."""
        paradas = list(paradas)
        if len(set(paradas)) != len(paradas):
            raise ValueError("Paradas repetidas")
        for nodo in paradas:
            if nodo not in grafo:
                raise ValueError(f"Parada fuera del grafo: {nodo}")
        self.nodos = paradas
        self.indice = {nodo: i for i, nodo in enumerate(paradas)}
        self.atributo = atributo
        self.buscador = "A*" if heuristica is not None else "UCS"
        self.vista = (nx.restricted_view(grafo, [], list(bloqueados))
                      if bloqueados else grafo)
        n = len(paradas)
        self.costo = np.zeros((n, n))
        self.rutas = {}
        self.nodos_expandidos = 0
        simetrico = not grafo.is_directed()
        tablas = {}
        inicio = time.perf_counter()
        for i, a in enumerate(paradas):
            for j, b in enumerate(paradas):
                if i == j or (simetrico and j < i):
                    continue
                resultado = self._buscar(a, b, heuristica, tablas)
                self.costo[i, j] = resultado["costo"]
                self.rutas[(i, j)] = resultado["ruta"]
                self.nodos_expandidos += resultado["nodos_expandidos"]
                if simetrico:
                    self.costo[j, i] = resultado["costo"]
                    self.rutas[(j, i)] = resultado["ruta"][::-1]
        self.tiempo_s = time.perf_counter() - inicio

    def _buscar(self, a, b, heuristica, tablas):
        try:
            if heuristica is None:
                return ucs(self.vista, a, b, self.atributo)
            if b not in tablas:
                tablas[b] = heuristica.precalcular(self.vista, b)
            return a_estrella(self.vista, a, b, self.atributo, tablas[b])
        except ValueError as error:
            raise ValueError(f"Sin ruta entre las paradas {a} y {b} "
                             f"(bloqueos o grafo desconexo)") from error

    def costo_entre(self, a, b):
        return float(self.costo[self.indice[a], self.indice[b]])

    def ruta_entre(self, a, b):
        if a == b:
            return [a]
        return list(self.rutas[(self.indice[a], self.indice[b])])

    def ruta_expandida(self, orden):
        """Ruta completa (sin repetir el nodo de unión) y costo de un orden.

        orden: lista de paradas visitadas en ese orden.
        """
        ruta = [orden[0]]
        total = 0.0
        tramos = []
        for a, b in zip(orden, orden[1:]):
            tramo = self.ruta_entre(a, b)
            costo = self.costo_entre(a, b)
            tramos.append({"desde": a, "hasta": b, "ruta": tramo,
                           "costo": costo})
            ruta += tramo[1:]
            total += costo
        return ruta, total, tramos
