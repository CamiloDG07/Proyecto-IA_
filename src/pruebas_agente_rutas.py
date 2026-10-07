"""Pruebas del agente autónomo de rutas (src/agente_rutas.py).

Contrastan la recomendación con una enumeración independiente: todos los
caminos simples entre las dos ciudades, evaluados con el costo compuesto sin
riesgo calculado aparte. Para varios destinos se contrasta con la fuerza bruta
sobre los órdenes posibles.
"""
import itertools
import random
import sys

import networkx as nx

from agente_rutas import recomendar
from build_graph import cargar_grafo

TOLERANCIA = 1e-9
grafo = cargar_grafo()
tope = grafo.graph["maximos"]


def ok(condicion, mensaje):
    if not condicion:
        print(f"  FALLA: {mensaje}")
        sys.exit(1)
    print(f"  ok: {mensaje}")


def puntaje(ruta, wd=1.0, wp=1.0):
    return sum((wd * grafo[u][v]["distancia_km"] / tope["distancia"]
                + wp * grafo[u][v]["peaje_cop_camion"] / tope["peaje"])
               / (wd + wp) for u, v in zip(ruta, ruta[1:]))


def mejor_enumerado(origen, destino, wd=1.0, wp=1.0):
    caminos = list(nx.all_simple_paths(grafo, origen, destino))
    return min(puntaje(c, wd, wp) for c in caminos), len(caminos)


def pares_de_prueba():
    nodos = sorted(grafo)
    azar = random.Random(20261007)
    fijos = [("Duitama", "Puente Nacional"), ("Bucaramanga", "Bogotá"),
             ("Bogotá", "Granada"), ("Mariquita", "Granada"),
             ("Tunja", "Chocontá"), ("Duitama", "Bogotá"),
             ("San Gil", "Tunja"), ("Pamplona", "Ubaté")]
    pares = list(fijos)
    while len(pares) < 40:
        par = tuple(azar.sample(nodos, 2))
        if par not in pares:
            pares.append(par)
    return pares


def prueba_un_destino():
    pares = pares_de_prueba()
    con_ciclo = 0
    for origen, destino in pares:
        r = recomendar(origen, destino, grafo=grafo)
        esperado, cantidad = mejor_enumerado(origen, destino)
        con_ciclo += cantidad > 1
        if abs(r["recomendada"]["costos"]["compuesto_sin_riesgo"]
               - esperado) > TOLERANCIA:
            ok(False, f"{origen} a {destino}: la recomendación no es el "
               "mínimo de los caminos simples")
        propio = puntaje(r["recomendada"]["ruta"])
        if abs(propio - esperado) > TOLERANCIA:
            ok(False, f"{origen} a {destino}: puntaje distinto")
    ok(True, f"{len(pares)} pares: la recomendación es el mínimo de "
       "compuesto sin riesgo entre todos los caminos simples")
    ok(con_ciclo >= 5, f"{con_ciclo} de los pares cruzan el ciclo (dos "
       "caminos simples)")
    ok(len(pares) - con_ciclo >= 5, f"{len(pares) - con_ciclo} pares de "
       "ruta única")


def prueba_pesos():
    for wd, wp in ((2.0, 1.0), (1.0, 3.0)):
        for origen, destino in (("Duitama", "Puente Nacional"),
                                ("Bucaramanga", "Bogotá")):
            r = recomendar(origen, destino, pesos={"distancia": wd,
                                                   "peaje": wp},
                           grafo=grafo)
            esperado, _ = mejor_enumerado(origen, destino, wd, wp)
            c = r["recomendada"]["costos"]["compuesto_sin_riesgo"]
            ok(abs(c - esperado) < TOLERANCIA,
               f"pesos ({wd:g}, {wp:g}): {origen} a {destino}")


def prueba_no_dominadas():
    r = recomendar("Duitama", "Puente Nacional", grafo=grafo)
    m = r["recomendada"]
    for a in r["alternativas"]:
        dominada = (m["km"] <= a["km"] and m["peaje_cop"] <= a["peaje_cop"]
                    and (m["km"] < a["km"] or m["peaje_cop"] < a["peaje_cop"]))
        ok(not dominada, "las alternativas informadas no están dominadas")
        ok(a["margen"] >= 0, "el margen de cada alternativa no es negativo")


def prueba_varios_destinos():
    casos = [("Duitama", ["Tunja", "Bogotá", "Villeta"], True),
             ("Duitama", ["Tunja", "Bogotá", "Villeta"], False),
             ("Bogotá", ["Girardot", "Zipaquirá", "Tunja", "Honda"], True),
             ("Mariquita", ["Granada", "Bogotá"], False)]
    for origen, destinos, regreso in casos:
        r = recomendar(origen, destinos, regreso, grafo=grafo)
        mejor = None
        for orden in itertools.permutations(destinos):
            tramos = [origen, *orden] + ([origen] if regreso else [])
            costo = sum(nx.dijkstra_path_length(
                grafo, a, b, weight="peso_sin_riesgo")
                for a, b in zip(tramos, tramos[1:]))
            mejor = costo if mejor is None else min(mejor, costo)
        calculado = r["recomendada"]["costos"]["compuesto_sin_riesgo"]
        ok(abs(calculado - mejor) < 1e-6,
           f"{origen}, {len(destinos)} destinos, regreso={regreso}: igual "
           "al mínimo por fuerza bruta")
        ok(r["recomendada"]["ruta"][0] == origen, "la ruta sale del origen")
    r = recomendar("Duitama", ["Tunja", "Bogotá", "Villeta"], True,
                   grafo=grafo)
    ok("Held-Karp" in r["recomendada"]["metodo"],
       "pocas paradas: método exacto (Held-Karp)")


def prueba_entradas_invalidas():
    casos = [("Narnia", ["Tunja"], "fuera de la red"),
             ("Tunja", ["Narnia"], "fuera de la red"),
             ("Tunja", ["Tunja"], "distintas"),
             ("Tunja", [], "al menos un destino"),
             ("Tunja", ["Bogotá", "Bogotá"], "distintas"),
             ("Tunja", ["Bogotá", "Tunja"], "distintas")]
    for origen, destinos, texto in casos:
        try:
            recomendar(origen, destinos, grafo=grafo)
        except ValueError as error:
            ok(texto in str(error), f"error claro: {error}")
        else:
            ok(False, f"debía fallar: {origen} a {destinos}")


def prueba_avisos():
    r = recomendar("Duitama", "Puente Nacional", grafo=grafo)
    ok(any("Chocontá a Tunja" in a for a in r["avisos"]),
       "ruta por Chocontá a Tunja: trae la advertencia de sector truncado")
    ok(any("otra ruta" in a and "% de los tramos" in a
           for a in r["avisos"]),
       "los criterios con riesgo prefieren otra ruta: se avisa con la "
       "cobertura")
    r2 = recomendar("Bogotá", "Granada", grafo=grafo)
    ok(not any("Chocontá" in a for a in r2["avisos"]),
       "ruta sin Chocontá a Tunja: sin esa advertencia")


def main():
    prueba_un_destino()
    prueba_pesos()
    prueba_no_dominadas()
    prueba_varios_destinos()
    prueba_entradas_invalidas()
    prueba_avisos()
    print("Todas las pruebas del agente autónomo pasaron.")


if __name__ == "__main__":
    main()
