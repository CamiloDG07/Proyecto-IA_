"""Heurística geodésica para A* y búsqueda voraz, y su verificación.

Para los criterios basados en distancia,

    h(n) = alfa * d_geo(n, meta)            (criterio distancia, en km)
    h(n) = w1 / (w1 + w2) * alfa * d_geo(n, meta) / d_max
                                            (criterio compuesto_sin_riesgo)

con d_geo la distancia de Haversine entre las coordenadas oficiales de
data/carga/coordenadas_nodos.csv y alfa el mínimo de la razón
carretera/geodésica entre las aristas, redondeado hacia abajo a 6 decimales.
Con ese alfa, alfa * d_geo(u, v) <= c(u, v) en toda arista, lo que garantiza
admisibilidad y consistencia por la desigualdad triangular. Los términos de
peaje y de riesgo (no negativos) no se incluyen en h y no la rompen.

Para el criterio compuesto (riesgo faltante igual a 0) se usa solo el término
de distancia, w1 * alfa * d_geo / d_max, y se marca como limitada. Para
peaje y riesgo no hay información geométrica: la heurística admisible es
h = 0 (A* se reduce a costo uniforme).

El script escribe outputs/analisis_heuristica.json con alfa, las aristas que
lo determinan y la verificación numérica de admisibilidad y consistencia.
"""
import csv
import json
from math import asin, cos, floor, radians, sin, sqrt

import networkx as nx

from build_graph import RAIZ, SALIDA, cargar_grafo

COORDENADAS_CSV = RAIZ / "data" / "carga" / "coordenadas_nodos.csv"
ATRIBUTOS = {
    "distancia": "distancia_km",
    "peaje": "peaje_cop_camion",
    "riesgo": "riesgo_gizscore_prom",
    "compuesto": "peso_multicriterio",
    "compuesto_sin_riesgo": "peso_sin_riesgo",
}
CRITERIOS_LIMITADOS = ("compuesto", "riesgo")


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia geodésica en km (esfera de radio 6371.0088 km)."""
    f1, f2 = radians(lat1), radians(lat2)
    a = (sin((f2 - f1) / 2) ** 2
         + cos(f1) * cos(f2) * sin(radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6371.0088 * asin(sqrt(a))


def cargar_coordenadas(ruta=COORDENADAS_CSV):
    """Diccionario nodo -> (latitud, longitud)."""
    with open(ruta, encoding="utf-8") as f:
        return {r["nodo"]: (float(r["latitud"]), float(r["longitud"]))
                for r in csv.DictReader(f)}


def razones_carretera_geodesica(grafo, coordenadas):
    """Aristas ordenadas por razón carretera/geodésica, de menor a mayor."""
    filas = []
    for u, v, d in grafo.edges(data=True):
        geo = haversine_km(*coordenadas[u], *coordenadas[v])
        filas.append((d["distancia_km"] / geo, u, v,
                      d["distancia_km"], geo))
    return sorted(filas)


def alfa_minimo(grafo, coordenadas, decimales=6, excluir=()):
    """Mínimo de la razón, redondeado hacia abajo a `decimales`.

    excluir: pares de nodos cuya arista no se considera (solo para análisis
    de sensibilidad; el alfa de referencia usa todas las aristas).
    """
    excluidas = {frozenset(par) for par in excluir}
    razones = [r[0] for r in razones_carretera_geodesica(grafo, coordenadas)
               if frozenset((r[1], r[2])) not in excluidas]
    escala = 10 ** decimales
    return floor(min(razones) * escala) / escala


class Heuristica:
    """h(nodo, meta) para un criterio, con su indicador de limitación."""

    def __init__(self, grafo, coordenadas, criterio, alfa):
        if criterio not in ATRIBUTOS:
            raise ValueError(f"Criterio desconocido: {criterio}")
        self.criterio = criterio
        self.alfa = alfa
        self.coordenadas = coordenadas
        self.limitada = criterio in CRITERIOS_LIMITADOS
        pesos = grafo.graph["pesos"]
        tope = grafo.graph["maximos"]["distancia"]
        if criterio == "distancia":
            self.factor = alfa
        elif criterio == "compuesto_sin_riesgo":
            w1, w2 = pesos["distancia"], pesos["peaje"]
            self.factor = alfa * w1 / (w1 + w2) / tope
        elif criterio == "compuesto":
            self.factor = alfa * pesos["distancia"] / tope
        else:
            self.factor = 0.0

    def __call__(self, nodo, meta):
        if self.factor == 0.0:
            return 0.0
        return self.factor * haversine_km(*self.coordenadas[nodo],
                                          *self.coordenadas[meta])

    def precalcular(self, grafo, meta):
        """Tabla de h hacia `meta` para todos los nodos (mismos valores)."""
        return HeuristicaPrecalculada(self, grafo, meta)


class HeuristicaPrecalculada:
    """h hacia una meta fija, precalculada: devuelve los mismos valores.

    La tabla se construye una vez por destino; la búsqueda solo consulta.
    """

    def __init__(self, heuristica, grafo, meta):
        self.meta = meta
        self.criterio = heuristica.criterio
        self.alfa = heuristica.alfa
        self.limitada = heuristica.limitada
        self.factor = heuristica.factor
        self.tabla = {nodo: heuristica(nodo, meta) for nodo in grafo}

    def __call__(self, nodo, meta):
        if meta != self.meta:
            raise ValueError(f"Tabla precalculada hacia {self.meta}, "
                             f"no hacia {meta}")
        return self.tabla[nodo]


def verificar_admisibilidad(grafo, h, criterio):
    """h(n, m) <= costo óptimo de n a m, para todo par con n distinto de m."""
    atributo = ATRIBUTOS[criterio]
    optimo = dict(nx.all_pairs_dijkstra_path_length(grafo, weight=atributo))
    margenes = [(optimo[n][m] - h(n, m), n, m)
                for n in grafo for m in grafo if n != m]
    minimo, maximo = min(margenes), max(margenes)
    return {
        "pares": len(margenes),
        "violaciones": sum(1 for x in margenes if x[0] < -1e-12),
        "margen_minimo": minimo[0], "par_margen_minimo": [minimo[1],
                                                          minimo[2]],
        "margen_maximo": maximo[0],
    }


def verificar_consistencia(grafo, h, criterio):
    """h(u, m) <= c(u, v) + h(v, m) en cada arista (ambos sentidos)."""
    atributo = ATRIBUTOS[criterio]
    margenes = []
    for u, v, d in grafo.edges(data=True):
        c = d[atributo]
        for a, b in ((u, v), (v, u)):
            for m in grafo:
                margenes.append((c + h(b, m) - h(a, m), a, b, m))
    minimo = min(margenes)
    return {
        "casos": len(margenes),
        "violaciones": sum(1 for x in margenes if x[0] < -1e-12),
        "margen_minimo": minimo[0],
        "caso_margen_minimo": [minimo[1], minimo[2], minimo[3]],
    }


def main():
    grafo = cargar_grafo()
    coordenadas = cargar_coordenadas()
    razones = razones_carretera_geodesica(grafo, coordenadas)
    alfa = alfa_minimo(grafo, coordenadas)
    resultado = {
        "alfa": alfa,
        "razon_minima_exacta": razones[0][0],
        "aristas_que_determinan_alfa": [
            {"arista": [r[1], r[2]], "razon": r[0]} for r in razones[:3]],
        "aristas_con_razon_menor_que_1": [
            {"arista": [r[1], r[2]], "carretera_km": r[3],
             "geodesica_km": r[4], "razon": r[0]}
            for r in razones if r[0] < 1],
        "criterios": {},
    }
    for criterio in ("distancia", "compuesto_sin_riesgo", "compuesto"):
        h = Heuristica(grafo, coordenadas, criterio, alfa)
        resultado["criterios"][criterio] = {
            "limitada": h.limitada,
            "admisibilidad": verificar_admisibilidad(grafo, h, criterio),
            "consistencia": verificar_consistencia(grafo, h, criterio),
        }
    pura = Heuristica(grafo, coordenadas, "distancia", 1.0)
    resultado["geodesica_pura_distancia"] = {
        "alfa": 1.0,
        "admisibilidad": verificar_admisibilidad(grafo, pura, "distancia"),
        "consistencia": verificar_consistencia(grafo, pura, "distancia"),
    }
    with open(SALIDA / "analisis_heuristica.json", "w",
              encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(f"alfa = {alfa:.6f} (razón mínima {razones[0][0]:.10f})")
    for r in razones[:3]:
        print(f"  {r[1]} - {r[2]}: {r[0]:.6f}")
    for criterio, datos in resultado["criterios"].items():
        a, c = datos["admisibilidad"], datos["consistencia"]
        print(f"{criterio}: admisibilidad violaciones={a['violaciones']} "
              f"margen mín={a['margen_minimo']:.6f}; "
              f"consistencia violaciones={c['violaciones']} "
              f"margen mín={c['margen_minimo']:.6f}")


if __name__ == "__main__":
    main()
