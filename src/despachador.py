"""Despachador del agente multifuncional.

Recibe una solicitud (tipo de problema, origen, destino, paradas, criterio y
restricciones) y elige el método. Regla fija:

  1. Se usa siempre un método EXACTO cuando es viable:
     - un solo par de ciudades (tipo a) o paradas en orden fijo (tipo b):
       A* con heurística admisible si el criterio la tiene y hay
       coordenadas (distancia y compuesto sin riesgo); UCS en los demás
       casos (peaje, riesgo, compuesto). Cada tramo se resuelve de forma
       exacta;
     - orden libre de paradas (tipos c con varias obligatorias, d y e):
       programación dinámica de Held-Karp mientras el número de paradas
       libres k sea menor o igual que UMBRAL_K.
  2. La metaheurística (ACO con 2-opt) se usa solo cuando el exacto no es
     viable: k mayor que UMBRAL_K.

UMBRAL_K no se supone: lo fija la medición real de Held-Karp en esta máquina
(src/medir_umbral.py escribe outputs/umbral_held_karp.json) con un
presupuesto de tiempo por solicitud declarado en ese archivo.

Tipos de solicitud:
  a  origen_destino              origen a destino
  b  paradas_orden_fijo          origen, paradas en el orden dado, destino
  c  obligatorias_o_bloqueados   paradas obligatorias intermedias en orden
                                 libre entre origen y destino y/o tramos
                                 bloqueados
  d  orden_libre_regreso         recorrer todas las paradas y volver al
                                 origen
  e  orden_libre_sin_regreso     recorrer todas las paradas desde el origen,
                                 sin volver

Los tramos bloqueados (restricciones["bloqueados"]) valen para los cinco
tipos. El agente es genérico: funciona con cualquier grafo de networkx con
costos no negativos por arista (se le pasa el diccionario criterios que
traduce el nombre del criterio al atributo de arista).
"""
import json
import time
import tracemalloc
from dataclasses import dataclass, field

from aco_multiparada import aco_semillas, es_simetrica
from agente import CRITERIOS
from build_graph import SALIDA
from held_karp import held_karp
from heuristica import Heuristica, alfa_minimo
from matriz_costos import MatrizCostos

TIPOS = {
    "a": "origen_destino",
    "b": "paradas_orden_fijo",
    "c": "obligatorias_o_bloqueados",
    "d": "orden_libre_regreso",
    "e": "orden_libre_sin_regreso",
}
CRITERIOS_CON_HEURISTICA = ("distancia", "compuesto_sin_riesgo")
ARCHIVO_UMBRAL = SALIDA / "umbral_held_karp.json"
SEMILLAS_ACO = tuple(range(1, 11))


def cargar_medicion_umbral():
    """Medición de Held-Karp en esta máquina (outputs/umbral_held_karp)."""
    if not ARCHIVO_UMBRAL.exists():
        raise FileNotFoundError(
            "Falta outputs/umbral_held_karp.json: ejecute "
            "python src/medir_umbral.py")
    with open(ARCHIVO_UMBRAL, encoding="utf-8") as f:
        return json.load(f)


def cargar_umbral():
    """k máximo exacto medido en esta máquina."""
    return cargar_medicion_umbral()["k_exacto"]


@dataclass
class Solicitud:
    """Solicitud al despachador."""

    tipo: str
    origen: object
    destino: object = None
    paradas: tuple = ()
    criterio: str = "distancia"
    restricciones: dict = field(default_factory=dict)

    def clave_tipo(self):
        if self.tipo in TIPOS:
            return self.tipo
        for letra, nombre in TIPOS.items():
            if self.tipo == nombre:
                return letra
        raise ValueError(f"Tipo de problema desconocido: {self.tipo}")


class Despachador:
    """Elige y ejecuta el método según el tipo de solicitud."""

    def __init__(self, grafo, coordenadas=None, criterios=None,
                 umbral_k=None):
        self.grafo = grafo
        self.coordenadas = coordenadas
        self.criterios = criterios or CRITERIOS
        self.umbral_k = umbral_k
        self.alfa = None
        if coordenadas is not None:
            self.alfa = alfa_minimo(grafo, coordenadas)

    # ---- selección ------------------------------------------------------
    def _umbral(self):
        if self.umbral_k is None:
            self.umbral_k = cargar_umbral()
        return self.umbral_k

    def _presupuesto(self):
        """Presupuesto de tiempo (s) con el que se midió el umbral."""
        return cargar_medicion_umbral()["presupuesto_s"]

    def _heuristica(self, criterio):
        """Heurística admisible para el criterio, o None (se usa UCS)."""
        if (self.coordenadas is None
                or criterio not in CRITERIOS_CON_HEURISTICA):
            return None
        return Heuristica(self.grafo, self.coordenadas, criterio, self.alfa)

    def _matriz(self, solicitud, nodos):
        if solicitud.criterio not in self.criterios:
            raise ValueError(f"Criterio desconocido: {solicitud.criterio}")
        return MatrizCostos(
            self.grafo, nodos, self.criterios[solicitud.criterio],
            solicitud.restricciones.get("bloqueados", ()),
            self._heuristica(solicitud.criterio))

    # ---- resolución -----------------------------------------------------
    def resolver(self, solicitud):
        """Ruta, costo, método usado, motivo de la elección y métricas."""
        inicio = time.perf_counter()
        letra = solicitud.clave_tipo()
        if letra == "a":
            salida = self._tipo_a(solicitud)
        elif letra == "b":
            salida = self._tipo_b(solicitud)
        elif letra == "c":
            salida = self._tipo_c(solicitud)
        elif letra == "d":
            salida = self._orden_libre(solicitud, "ciclo")
        else:
            salida = self._orden_libre(solicitud, "libre")
        salida["tipo"] = TIPOS[letra]
        salida["criterio"] = solicitud.criterio
        salida["metricas"]["tiempo_s"] = time.perf_counter() - inicio
        return salida

    def medir_memoria(self, solicitud):
        """Memoria pico (KiB) en una corrida aparte, con tracemalloc."""
        tracemalloc.start()
        try:
            self.resolver(solicitud)
            _, pico = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        return pico / 1024

    def _armar(self, matriz, orden, metodo, motivo, extra=None):
        ruta, costo, tramos = matriz.ruta_expandida(orden)
        metricas = {
            "paradas": len(matriz.nodos),
            "nodos_expandidos": matriz.nodos_expandidos,
            "tiempo_matriz_s": matriz.tiempo_s,
        }
        metricas.update(extra or {})
        return {"ruta": ruta, "costo": costo, "orden_paradas": list(orden),
                "metodo": metodo, "motivo": motivo, "tramos": tramos,
                "metricas": metricas}

    def _metodo_tramos(self, matriz):
        return (f"{matriz.buscador} por tramo")

    def _motivo_tramos(self, matriz, criterio):
        if matriz.buscador == "A*":
            return (f"exacto: A* con heurística admisible, disponible para "
                    f"el criterio {criterio}")
        return (f"exacto: UCS, porque el criterio {criterio} no tiene "
                "heurística admisible informativa o no hay coordenadas")

    def _tipo_a(self, s):
        if s.destino is None:
            raise ValueError("El tipo a requiere destino")
        matriz = self._matriz(s, [s.origen, s.destino])
        return self._armar(matriz, [s.origen, s.destino],
                           self._metodo_tramos(matriz),
                           self._motivo_tramos(matriz, s.criterio))

    def _tipo_b(self, s):
        if s.destino is None:
            raise ValueError("El tipo b requiere destino")
        orden = [s.origen, *s.paradas, s.destino]
        if len(set(orden)) != len(orden):
            raise ValueError("Origen, paradas y destino deben ser distintos")
        matriz = self._matriz(s, orden)
        return self._armar(
            matriz, orden, self._metodo_tramos(matriz),
            "orden fijo dado por la solicitud; " + self._motivo_tramos(
                matriz, s.criterio))

    def _tipo_c(self, s):
        if s.destino is None:
            raise ValueError("El tipo c requiere destino")
        obligatorias = list(s.restricciones.get("obligatorias", ()))
        orden = [s.origen, *obligatorias, s.destino]
        if len(set(orden)) != len(orden):
            raise ValueError("Origen, obligatorias y destino distintos")
        if len(obligatorias) > 1:
            return self._orden_libre(s, "fijo")
        matriz = self._matriz(s, orden)
        bloqueados = s.restricciones.get("bloqueados", ())
        partes = []
        if obligatorias:
            partes.append("una parada obligatoria intermedia: orden "
                          "determinado")
        if bloqueados:
            partes.append(f"{len(bloqueados)} tramo(s) bloqueado(s) "
                          "excluidos de todas las búsquedas")
        return self._armar(
            matriz, orden, self._metodo_tramos(matriz),
            "; ".join(partes) + "; " + self._motivo_tramos(matriz,
                                                           s.criterio))

    def _orden_libre(self, s, modo):
        """Orden libre de paradas: Held-Karp si k <= umbral; si no, ACO."""
        if modo == "fijo":
            obligatorias = list(s.restricciones.get("obligatorias", ()))
            nodos = [s.origen, *obligatorias, s.destino]
            fin = len(nodos) - 1
        else:
            nodos = [s.origen, *s.paradas]
            fin = None
        if len(set(nodos)) != len(nodos):
            raise ValueError("Origen, paradas y destino deben ser distintos")
        if len(nodos) < 2:
            raise ValueError("Se requiere al menos una parada")
        matriz = self._matriz(s, nodos)
        k = len(nodos) - 1 - (1 if modo == "fijo" else 0)
        umbral = self._umbral()
        extra = {"k": k, "umbral_k": umbral, "modo": modo,
                 "presupuesto_s": self._presupuesto()}
        inicio = time.perf_counter()
        if k <= umbral:
            _, indices = held_karp(matriz.costo, 0, modo, fin)
            metodo = "Held-Karp"
            motivo = (f"exacto viable: k = {k} paradas libres <= {umbral} "
                      "(umbral medido en esta máquina para un presupuesto "
                      f"de {extra['presupuesto_s']} s)")
        else:
            simetrica = es_simetrica(matriz.costo)
            resumen = aco_semillas(matriz.costo, 0, modo, fin,
                                   semillas=SEMILLAS_ACO,
                                   busqueda_local=simetrica)
            indices = resumen["mejor"]["orden"]
            extra["matriz_simetrica"] = simetrica
            motivo = (f"exacto no viable: k = {k} paradas libres > {umbral} "
                      "(umbral medido en esta máquina para un presupuesto "
                      f"de {extra['presupuesto_s']} s); se usa la "
                      "metaheurística")
            if simetrica:
                metodo = f"ACO + 2-opt ({len(SEMILLAS_ACO)} semillas)"
            else:
                metodo = f"ACO sin 2-opt ({len(SEMILLAS_ACO)} semillas)"
                motivo += ("; la matriz de costos es asimétrica, por lo que "
                           "el ACO corre sin búsqueda local 2-opt (que "
                           "requiere simetría)")
            extra.update({
                "costo_medio_aco": resumen["costo_medio"],
                "costo_peor_aco": resumen["costo_peor"],
                "desviacion_aco": resumen["desviacion"],
                "curva_media_aco": resumen["curva_media"],
            })
        extra["tiempo_orden_s"] = time.perf_counter() - inicio
        orden = [nodos[i] for i in indices]
        return self._armar(matriz, orden, metodo, motivo, extra)
