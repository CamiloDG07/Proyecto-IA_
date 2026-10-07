"""Pruebas del despachador, la matriz de costos y los métodos de orden libre.

Las referencias de costo salen de nx.shortest_path_length; las búsquedas del
proyecto no usan networkx para buscar.
"""
from itertools import permutations

import networkx as nx

from agente import CRITERIOS
from build_graph import cargar_grafo
from despachador import Despachador, Solicitud
from heuristica import cargar_coordenadas

EPS = 1e-9
BLOQUEO_CICLO = [("Bogotá", "Tocancipá")]


def verificar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)
    print(f"  ok: {mensaje}")


def costo_nx(grafo, a, b, criterio, bloqueados=()):
    vista = (nx.restricted_view(grafo, [], list(bloqueados))
             if bloqueados else grafo)
    return nx.shortest_path_length(vista, a, b, weight=CRITERIOS[criterio])


def suma_nx(grafo, orden, criterio, bloqueados=()):
    return sum(costo_nx(grafo, a, b, criterio, bloqueados)
               for a, b in zip(orden, orden[1:]))


def prueba_tipo_a(d, grafo):
    print("Tipo a: origen a destino")
    for criterio in CRITERIOS:
        r = d.resolver(Solicitud("a", "Duitama", "Puente Nacional",
                                 criterio=criterio))
        esperado = costo_nx(grafo, "Duitama", "Puente Nacional", criterio)
        verificar(abs(r["costo"] - esperado) < EPS,
                  f"costo exacto ({criterio}, {r['metodo']})")
        con_h = criterio in ("distancia", "compuesto_sin_riesgo")
        verificar(r["metodo"].startswith("A*") == con_h,
                  f"método según el criterio ({criterio})")
    r = d.resolver(Solicitud("origen_destino", "Duitama", "Puente Nacional"))
    verificar(r["ruta"][0] == "Duitama" and r["ruta"][-1] == "Puente Nacional",
              "extremos de la ruta y tipo por nombre")


def prueba_tipo_b(d, grafo):
    print("Tipo b: paradas en orden fijo")
    paradas = ("Bogotá", "Zipaquirá")
    r = d.resolver(Solicitud("b", "Duitama", "Puente Nacional", paradas))
    orden = ["Duitama", *paradas, "Puente Nacional"]
    verificar(abs(r["costo"] - suma_nx(grafo, orden, "distancia")) < EPS,
              "costo = suma de tramos exactos")
    verificar(r["orden_paradas"] == orden, "se respeta el orden fijo")
    verificar(len(r["tramos"]) == 3, "tres tramos expandidos")
    verificar(all(grafo.has_edge(a, b)
                  for a, b in zip(r["ruta"], r["ruta"][1:])),
              "la ruta expandida usa solo aristas del grafo")


def prueba_tipo_c(d, grafo):
    print("Tipo c: obligatoria intermedia y tramos bloqueados")
    r = d.resolver(Solicitud(
        "c", "Duitama", "Puente Nacional",
        restricciones={"obligatorias": ["Bucaramanga"]}))
    orden = ["Duitama", "Bucaramanga", "Puente Nacional"]
    verificar(abs(r["costo"] - suma_nx(grafo, orden, "distancia")) < EPS,
              "con Bucaramanga obligatoria: costo exacto")
    verificar("Bucaramanga" in r["ruta"], "la ruta pasa por la obligatoria")
    r = d.resolver(Solicitud(
        "c", "Duitama", "Puente Nacional",
        restricciones={"bloqueados": BLOQUEO_CICLO}))
    esperado = costo_nx(grafo, "Duitama", "Puente Nacional", "distancia",
                        BLOQUEO_CICLO)
    verificar(abs(r["costo"] - esperado) < EPS,
              "con Bogotá a Tocancipá bloqueado: costo exacto")
    verificar("Bucaramanga" in r["ruta"] and "Bogotá" not in r["ruta"],
              "el bloqueo obliga al desvío por Santander")
    r = d.resolver(Solicitud(
        "a", "Duitama", "Puente Nacional",
        restricciones={"bloqueados": BLOQUEO_CICLO}))
    verificar(abs(r["costo"] - esperado) < EPS,
              "el bloqueo también vale para el tipo a")
    try:
        d.resolver(Solicitud(
            "a", "Bogotá", "Granada",
            restricciones={"bloqueados": [("Ye de Granada", "Granada")]}))
    except ValueError:
        verificar(True, "destino aislado por el bloqueo: error explícito")
    else:
        raise AssertionError("Debía fallar con el destino aislado")


def prueba_generico():
    print("Genericidad: otro grafo con costos y sin coordenadas")
    g = nx.Graph()
    for u, v, w in [("A", "B", 4), ("B", "D", 6), ("A", "C", 1),
                    ("C", "E", 2), ("E", "D", 3), ("B", "E", 2)]:
        g.add_edge(u, v, costo=w)
    d = Despachador(g, criterios={"costo": "costo"})
    r = d.resolver(Solicitud("a", "A", "D", criterio="costo"))
    verificar(r["metodo"] == "UCS por tramo" and r["costo"] == 6,
              "sin coordenadas se usa UCS y el costo es el óptimo (6)")


def brute(grafo, origen, paradas, criterio, modo, fin=None,
          bloqueados=()):
    """Mejor orden por fuerza bruta con costos exactos de networkx."""
    mejor = float("inf")
    for perm in permutations(paradas):
        orden = [origen, *perm]
        if modo == "ciclo":
            orden.append(origen)
        elif modo == "fijo":
            orden.append(fin)
        mejor = min(mejor, suma_nx(grafo, orden, criterio, bloqueados))
    return mejor


def prueba_orden_libre(grafo, coordenadas):
    print("Orden libre: tipos d, e y c con varias obligatorias")
    d = Despachador(grafo, coordenadas)
    paradas = ("Bogotá", "Villavicencio", "Honda", "Tunja", "Girardot")
    for criterio in ("distancia", "peaje", "compuesto_sin_riesgo"):
        r = d.resolver(Solicitud("d", "Duitama", paradas=paradas,
                                 criterio=criterio))
        esperado = brute(grafo, "Duitama", paradas, criterio, "ciclo")
        verificar(abs(r["costo"] - esperado) < EPS
                  and r["metodo"] == "Held-Karp",
                  f"tipo d ({criterio}): Held-Karp = fuerza bruta")
        verificar(r["ruta"][0] == "Duitama" and r["ruta"][-1] == "Duitama",
                  "el ciclo regresa al origen")
        verificar(sorted(r["orden_paradas"][1:-1]) == sorted(paradas),
                  "visita todas las paradas una vez")
        r = d.resolver(Solicitud("e", "Duitama", paradas=paradas,
                                 criterio=criterio))
        esperado = brute(grafo, "Duitama", paradas, criterio, "libre")
        verificar(abs(r["costo"] - esperado) < EPS,
                  f"tipo e ({criterio}): sin regreso = fuerza bruta")
    obligatorias = ["Bucaramanga", "Bogotá", "Tunja"]
    r = d.resolver(Solicitud(
        "c", "Duitama", "Puente Nacional",
        restricciones={"obligatorias": obligatorias}))
    esperado = brute(grafo, "Duitama", obligatorias, "distancia", "fijo",
                     "Puente Nacional")
    verificar(abs(r["costo"] - esperado) < EPS,
              "tipo c con 3 obligatorias en orden libre = fuerza bruta")
    verificar(r["orden_paradas"][0] == "Duitama"
              and r["orden_paradas"][-1] == "Puente Nacional",
              "el destino queda al final")
    r = d.resolver(Solicitud(
        "d", "Duitama", paradas=("Bogotá", "Honda", "Tunja"),
        restricciones={"bloqueados": BLOQUEO_CICLO}))
    esperado = brute(grafo, "Duitama", ("Bogotá", "Honda", "Tunja"),
                     "distancia", "ciclo", bloqueados=BLOQUEO_CICLO)
    verificar(abs(r["costo"] - esperado) < EPS,
              "orden libre con un tramo bloqueado = fuerza bruta")


def prueba_metaheuristica(grafo, coordenadas):
    print("Cuando el exacto no es viable se usa ACO (umbral forzado a 3)")
    d = Despachador(grafo, coordenadas, umbral_k=3)
    paradas = ("Bogotá", "Villavicencio", "Honda", "Tunja", "Girardot",
               "Pamplona")
    r = d.resolver(Solicitud("d", "Duitama", paradas=paradas))
    exacto = brute(grafo, "Duitama", paradas, "distancia", "ciclo")
    verificar(r["metodo"].startswith("ACO"), "método ACO + 2-opt")
    verificar("no viable" in r["motivo"], "el motivo explica la elección")
    verificar(r["costo"] >= exacto - EPS, "brecha no negativa")
    verificar(sorted(r["orden_paradas"][1:-1]) == sorted(paradas),
              "visita todas las paradas")
    verificar("costo_medio_aco" in r["metricas"], "métricas del ACO")
    d2 = Despachador(grafo, coordenadas, umbral_k=10)
    r2 = d2.resolver(Solicitud("d", "Duitama", paradas=paradas))
    verificar(r2["metodo"] == "Held-Karp" and abs(r2["costo"] - exacto) < EPS,
              "con umbral suficiente se usa el exacto")


def main():
    grafo = cargar_grafo()
    coordenadas = cargar_coordenadas()
    d = Despachador(grafo, coordenadas)
    prueba_tipo_a(d, grafo)
    prueba_tipo_b(d, grafo)
    prueba_tipo_c(d, grafo)
    prueba_generico()
    prueba_orden_libre(grafo, coordenadas)
    prueba_metaheuristica(grafo, coordenadas)
    print("Todas las pruebas del despachador pasaron.")


if __name__ == "__main__":
    main()
