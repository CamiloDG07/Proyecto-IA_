"""Búsquedas con traza: la misma lógica de busquedas.py, registrando cada paso.

Cada función repite, línea por línea, el algoritmo de su homónimo en
busquedas.py (mismas convenciones: prueba de meta al extraer, vecinos en
orden alfabético, desempate de la cola por orden de inserción, expandidos
sin contar la meta) y, además de los mismos campos del resultado, devuelve:

  entradas  una entrada de frontera por cada inserción:
            {id, ciudad, padre, g, h, f, creado, extraido, resultado}.
            `padre` es el id de la entrada que se expandió para crearla;
            `creado` y `extraido` son índices de paso; `resultado` es
            "expandido", "meta", "descartado" (entrada vieja o ya visitada)
            o None si nunca salió de la frontera. Una ciudad puede tener
            varias entradas (UCS, A*, DFS).
  pasos     el paso 0 (inicio) y un paso por extracción:
            {extraida, resultado, nuevas, frontera, expandidos, generados,
            frontera_max, reexpansiones}, con `frontera` como lista de ids
            en el orden en que saldrían.
  h         tabla h(n) hacia la meta para todos los nodos.

g es el costo acumulado de la rama con el atributo del criterio (también en
BFS y DFS, que no lo usan para decidir). h y f solo se llenan donde el
algoritmo las usa: f = g en UCS, f = h en la búsqueda voraz y f = g + h en
A*; en BFS y DFS son None.

El módulo no mide tiempo ni memoria: eso lo hace busquedas.medir.
"""
import heapq
from collections import deque
from itertools import count

from busquedas import _reconstruir, _resultado, _sin_ruta, _validar, _vecinos


class _Registro:
    """Acumula las entradas y los pasos de una búsqueda."""

    def __init__(self):
        self.entradas = []
        self.pasos = []

    def nueva(self, ciudad, padre, g, h=None, f=None):
        entrada = {"id": len(self.entradas), "ciudad": ciudad,
                   "padre": padre, "g": g, "h": h, "f": f,
                   "creado": len(self.pasos), "extraido": None,
                   "resultado": None}
        self.entradas.append(entrada)
        return entrada["id"]

    def extraer(self, ident, resultado):
        entrada = self.entradas[ident]
        entrada["extraido"] = len(self.pasos)
        entrada["resultado"] = resultado

    def paso(self, extraida, resultado, nuevas, frontera, contadores):
        expandidos, generados, maximo, reexpansiones = contadores
        self.pasos.append({
            "extraida": extraida, "resultado": resultado,
            "nuevas": list(nuevas), "frontera": list(frontera),
            "expandidos": expandidos, "generados": generados,
            "frontera_max": maximo, "reexpansiones": reexpansiones})


def _tabla_h(grafo, h, destino):
    return {nodo: (h(nodo, destino) if h is not None else None)
            for nodo in grafo}


def _final(registro, resultado, grafo, h, destino):
    resultado.update({"entradas": registro.entradas,
                      "pasos": registro.pasos,
                      "h": _tabla_h(grafo, h, destino)})
    return resultado


def bfs_traza(grafo, origen, destino, atributo="distancia_km", h=None):
    """BFS con traza; `h` solo llena la tabla informativa de h(n)."""
    _validar(grafo, origen, destino)
    reg = _Registro()
    frontera = deque([(origen, reg.nueva(origen, None, 0.0))])
    padre = {origen: None}
    expandidos, generados, maximo = 0, 1, 1
    reg.paso(None, "inicio", [0], [i for _, i in frontera],
             (0, 1, 1, 0))
    while frontera:
        nodo, ident = frontera.popleft()
        if nodo == destino:
            reg.extraer(ident, "meta")
            reg.paso(ident, "meta", [], [i for _, i in frontera],
                     (expandidos, generados, maximo, 0))
            resultado = _resultado(grafo, atributo,
                                   _reconstruir(padre, nodo), expandidos,
                                   generados, maximo)
            return _final(reg, resultado, grafo, h, destino)
        reg.extraer(ident, "expandido")
        expandidos += 1
        nuevas = []
        for vecino in _vecinos(grafo, nodo):
            if vecino not in padre:
                padre[vecino] = nodo
                g = reg.entradas[ident]["g"] + grafo[nodo][vecino][atributo]
                nuevas.append(reg.nueva(vecino, ident, g))
                frontera.append((vecino, nuevas[-1]))
                generados += 1
        maximo = max(maximo, len(frontera))
        reg.paso(ident, "expandido", nuevas, [i for _, i in frontera],
                 (expandidos, generados, maximo, 0))
    raise _sin_ruta(origen, destino)


def dfs_traza(grafo, origen, destino, atributo="distancia_km", h=None):
    """DFS con traza; la frontera se lista con la cima de la pila primero."""
    _validar(grafo, origen, destino)
    reg = _Registro()
    frontera = [(origen, None, reg.nueva(origen, None, 0.0))]
    padre = {}
    expandidos, generados, maximo = 0, 1, 1
    reg.paso(None, "inicio", [0], [e[2] for e in reversed(frontera)],
             (0, 1, 1, 0))
    while frontera:
        nodo, anterior, ident = frontera.pop()
        if nodo in padre:
            reg.extraer(ident, "descartado")
            reg.paso(ident, "descartado", [],
                     [e[2] for e in reversed(frontera)],
                     (expandidos, generados, maximo, 0))
            continue
        padre[nodo] = anterior
        if nodo == destino:
            reg.extraer(ident, "meta")
            reg.paso(ident, "meta", [], [e[2] for e in reversed(frontera)],
                     (expandidos, generados, maximo, 0))
            resultado = _resultado(grafo, atributo,
                                   _reconstruir(padre, nodo), expandidos,
                                   generados, maximo)
            return _final(reg, resultado, grafo, h, destino)
        reg.extraer(ident, "expandido")
        expandidos += 1
        nuevas = []
        # se crean en orden alfabético y se apilan al revés, como busquedas
        for vecino in reversed(_vecinos(grafo, nodo)):
            if vecino not in padre:
                g = reg.entradas[ident]["g"] + grafo[nodo][vecino][atributo]
                frontera.append((vecino, nodo,
                                 reg.nueva(vecino, ident, g)))
                nuevas.append(frontera[-1][2])
                generados += 1
        maximo = max(maximo, len(frontera))
        reg.paso(ident, "expandido", nuevas,
                 [e[2] for e in reversed(frontera)],
                 (expandidos, generados, maximo, 0))
    raise _sin_ruta(origen, destino)


def _orden_cola(frontera):
    """Ids de la cola de prioridad en el orden en que saldrían."""
    return [e[-1] for e in sorted(frontera)]


def _mejor_primero_traza(grafo, origen, destino, atributo, prioridad, h):
    """Núcleo de UCS y A* con traza (misma lógica que _mejor_primero)."""
    _validar(grafo, origen, destino)
    reg = _Registro()
    orden = count()
    mejor_g = {origen: 0.0}
    padre = {origen: None}
    expandido = set()
    f0 = prioridad(0.0, origen)
    h0 = h(origen, destino) if h is not None else None
    frontera = [(f0, next(orden), 0.0, origen,
                 reg.nueva(origen, None, 0.0, h0, f0))]
    expandidos, generados, maximo, reexpansiones = 0, 1, 1, 0
    reg.paso(None, "inicio", [0], _orden_cola(frontera), (0, 1, 1, 0))
    while frontera:
        _, _, g, nodo, ident = heapq.heappop(frontera)
        if g > mejor_g[nodo]:
            reg.extraer(ident, "descartado")
            reg.paso(ident, "descartado", [], _orden_cola(frontera),
                     (expandidos, generados, maximo, reexpansiones))
            continue
        if nodo == destino:
            reg.extraer(ident, "meta")
            reg.paso(ident, "meta", [], _orden_cola(frontera),
                     (expandidos, generados, maximo, reexpansiones))
            resultado = _resultado(grafo, atributo,
                                   _reconstruir(padre, nodo), expandidos,
                                   generados, maximo, reexpansiones)
            return _final(reg, resultado, grafo, h, destino)
        if nodo in expandido:
            reexpansiones += 1
        expandido.add(nodo)
        expandidos += 1
        reg.extraer(ident, "expandido")
        nuevas = []
        for vecino in _vecinos(grafo, nodo):
            nuevo = g + grafo[nodo][vecino][atributo]
            if nuevo < mejor_g.get(vecino, float("inf")):
                mejor_g[vecino] = nuevo
                padre[vecino] = nodo
                f = prioridad(nuevo, vecino)
                hv = h(vecino, destino) if h is not None else None
                entrada = reg.nueva(vecino, ident, nuevo, hv, f)
                heapq.heappush(frontera, (f, next(orden), nuevo, vecino,
                                          entrada))
                nuevas.append(entrada)
                generados += 1
        maximo = max(maximo, len(frontera))
        reg.paso(ident, "expandido", nuevas, _orden_cola(frontera),
                 (expandidos, generados, maximo, reexpansiones))
    raise _sin_ruta(origen, destino)


def ucs_traza(grafo, origen, destino, atributo="distancia_km", h=None):
    """Costo uniforme con traza; `h` solo llena la tabla informativa."""
    resultado = _mejor_primero_traza(grafo, origen, destino, atributo,
                                     lambda g, nodo: g, None)
    resultado["h"] = _tabla_h(grafo, h, destino)
    return resultado


def a_estrella_traza(grafo, origen, destino, atributo, h):
    """A* con traza: f = g + h(n, destino)."""
    return _mejor_primero_traza(
        grafo, origen, destino, atributo,
        lambda g, nodo: g + h(nodo, destino), h)


def voraz_traza(grafo, origen, destino, atributo, h):
    """Búsqueda voraz con traza (misma lógica que busquedas.voraz)."""
    _validar(grafo, origen, destino)
    reg = _Registro()
    orden = count()
    padre = {origen: None}
    expandido = set()
    h0 = h(origen, destino)
    frontera = [(h0, next(orden), origen,
                 reg.nueva(origen, None, 0.0, h0, h0))]
    expandidos, generados, maximo = 0, 1, 1
    reg.paso(None, "inicio", [0], _orden_cola(frontera), (0, 1, 1, 0))
    while frontera:
        _, _, nodo, ident = heapq.heappop(frontera)
        if nodo in expandido:
            reg.extraer(ident, "descartado")
            reg.paso(ident, "descartado", [], _orden_cola(frontera),
                     (expandidos, generados, maximo, 0))
            continue
        if nodo == destino:
            reg.extraer(ident, "meta")
            reg.paso(ident, "meta", [], _orden_cola(frontera),
                     (expandidos, generados, maximo, 0))
            resultado = _resultado(grafo, atributo,
                                   _reconstruir(padre, nodo), expandidos,
                                   generados, maximo)
            return _final(reg, resultado, grafo, h, destino)
        expandido.add(nodo)
        expandidos += 1
        reg.extraer(ident, "expandido")
        nuevas = []
        for vecino in _vecinos(grafo, nodo):
            if vecino not in expandido and vecino not in padre:
                padre[vecino] = nodo
                hv = h(vecino, destino)
                g = reg.entradas[ident]["g"] + grafo[nodo][vecino][atributo]
                entrada = reg.nueva(vecino, ident, g, hv, hv)
                heapq.heappush(frontera, (hv, next(orden), vecino, entrada))
                nuevas.append(entrada)
                generados += 1
        maximo = max(maximo, len(frontera))
        reg.paso(ident, "expandido", nuevas, _orden_cola(frontera),
                 (expandidos, generados, maximo, 0))
    raise _sin_ruta(origen, destino)


ALGORITMOS = {
    "bfs": bfs_traza, "dfs": dfs_traza, "ucs": ucs_traza,
    "voraz": voraz_traza, "astar": a_estrella_traza,
}
