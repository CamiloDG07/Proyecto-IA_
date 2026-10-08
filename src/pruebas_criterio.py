"""Pruebas de la opción --criterio del agente autónomo.

Para cada criterio, en 12 pares (con y sin ciclo), la recomendación debe
tener el mínimo costo de ese criterio entre TODOS los caminos simples,
enumerados aparte con networkx sobre el atributo de cada arista.
"""
import sys

import networkx as nx

from agente import CRITERIOS
from agente_rutas import formatear, recomendar
from build_graph import cargar_grafo

grafo = cargar_grafo()
PARES = [("Duitama", "Puente Nacional"), ("Bucaramanga", "Bogotá"),
         ("Tunja", "Ubaté"), ("Pamplona", "Zipaquirá"),
         ("Cajicá", "Duitama"), ("Bogotá", "San Gil"),
         ("Bogotá", "Granada"), ("Mariquita", "Granada"),
         ("Chiquinquirá", "Tunja"), ("Madrid", "Guasca"),
         ("Girardot", "Honda"), ("Puerto López", "Villeta")]


def ok(condicion, mensaje):
    if not condicion:
        print(f"  FALLA: {mensaje}")
        sys.exit(1)
    print(f"  ok: {mensaje}")


def minimo_enumerado(origen, destino, atributo):
    caminos = list(nx.all_simple_paths(grafo, origen, destino))
    costos = [sum(grafo[u][v][atributo] for u, v in zip(c, c[1:]))
              for c in caminos]
    return min(costos), len(caminos)


def prueba_criterio(criterio):
    atributo = CRITERIOS[criterio]
    con_ciclo = sin_ciclo = 0
    for origen, destino in PARES:
        r = recomendar(origen, destino, grafo=grafo, criterio=criterio)
        esperado, cantidad = minimo_enumerado(origen, destino, atributo)
        obtenido = r["recomendada"]["costos"][criterio]
        if abs(obtenido - esperado) > 1e-9 * max(1.0, abs(esperado)):
            ok(False, f"{criterio}: {origen} a {destino}: {obtenido} contra "
               f"el mínimo enumerado {esperado}")
        if "Criterio elegido por el usuario: " + criterio \
                not in formatear(r):
            ok(False, f"{criterio}: la salida no dice que lo eligió el "
               "usuario")
        if cantidad > 1:
            con_ciclo += 1
        else:
            sin_ciclo += 1
    ok(con_ciclo >= 5 and sin_ciclo >= 4,
       f"{criterio}: la recomendación es el mínimo de los caminos simples "
       f"en {len(PARES)} pares ({con_ciclo} con ciclo, {sin_ciclo} sin "
       "ciclo); la salida dice que lo eligió el usuario")


def main():
    for criterio in CRITERIOS:
        prueba_criterio(criterio)
    # sin la opción, todo igual: la regla del agente
    r = recomendar("Duitama", "Puente Nacional", grafo=grafo)
    ok(r["criterio_usuario"] is None
       and "Criterio elegido" not in formatear(r)
       and "Bogotá" in r["recomendada"]["ruta"],
       "sin --criterio el agente decide con su regla (ruta por Bogotá)")
    # con el criterio peaje cambia a la ruta de menor peaje
    p = recomendar("Duitama", "Puente Nacional", grafo=grafo,
                   criterio="peaje")
    ok("Bucaramanga" in p["recomendada"]["ruta"]
       and p["recomendada"]["peaje_cop"] == 100200,
       "con --criterio peaje elige el desvío por Santander (100 200 COP)")
    ok(len(p["alternativas"]) == 1 and p["avisos"],
       "las candidatas y las advertencias se muestran igual")
    # ida y vuelta y varios destinos admiten el criterio
    v = recomendar("Duitama", "Puente Nacional", regreso=True, grafo=grafo,
                   criterio="peaje")
    ok(v["vuelta"]["ruta"] == v["ida"]["ruta"][::-1]
       and "Bucaramanga" in v["ida"]["ruta"],
       "ida y vuelta con --criterio peaje: ida por Santander y regreso "
       "invertido")
    m = recomendar("Duitama", ["Tunja", "Bogotá", "Villeta"], regreso=True,
                   grafo=grafo, criterio="distancia")
    ok(m["criterio_usuario"] == "distancia"
       and "Criterio elegido por el usuario: distancia" in formatear(m),
       "varios destinos admiten --criterio")
    # criterio inválido
    try:
        recomendar("Duitama", "Puente Nacional", grafo=grafo,
                   criterio="velocidad")
    except ValueError as error:
        ok("Criterio desconocido: velocidad" in str(error),
           f"criterio inválido: error claro ({error})")
    else:
        ok(False, "el criterio inválido debía fallar")
    print("Todas las pruebas de --criterio pasaron.")


if __name__ == "__main__":
    main()
