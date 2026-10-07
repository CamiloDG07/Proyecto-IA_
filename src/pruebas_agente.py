"""Pruebas del agente de rutas sobre la red de carga.

Casos reales sobre los 32 nodos: pares que cruzan el ciclo (dos rutas
posibles), pares que no lo cruzan (ruta única, verificada enumerando todos
los caminos simples) y entradas inválidas. Guarda outputs/pruebas_agente.json.
"""
import json
from pathlib import Path

import networkx as nx

from agente import CRITERIOS, AgenteRutas
from build_graph import construir_grafo

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "outputs"
TRAMO_CICLO = ("Bogotá", "Tocancipá")

# pares que no cruzan el ciclo, de distinto número de saltos
PARES_SIN_CICLO = [
    ("Bogotá", "Villavicencio"),
    ("Bogotá", "Granada"),
    ("Bogotá", "Mariquita"),
    ("Girardot", "Cambao"),
    ("Madrid", "Puerto Gaitán"),
    ("Chiquinquirá", "Tunja"),
]


def verificar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)
    print(f"  ok: {mensaje}")


def distancias_json(variante):
    """Distancia por arista leída directamente de aristas_red.json."""
    campo = ("distancia_km" if variante == "corregida"
             else "distancia_cruda_km")
    with open(SALIDA / "aristas_red.json", encoding="utf-8") as f:
        return {frozenset((a["origen"], a["destino"])): a[campo]
                for a in json.load(f)}


def suma_ruta(distancias, ruta):
    return sum(distancias[frozenset(par)] for par in zip(ruta, ruta[1:]))


def prueba_ciclo(agente, resultados):
    print("Pares que cruzan el ciclo: Duitama a Puente Nacional")
    caminos = list(nx.all_simple_paths(agente.grafo, "Duitama",
                                       "Puente Nacional"))
    verificar(len(caminos) == 2, "exactamente dos rutas simples")
    por_bogota = [c for c in caminos if "Bogotá" in c][0]
    por_santander = [c for c in caminos if "Bucaramanga" in c][0]
    distancias = distancias_json("corregida")
    corta = agente.calcular_ruta("Duitama", "Puente Nacional", "distancia")
    verificar(corta["ruta"] == por_bogota, "distancia: ruta por Bogotá")
    verificar(abs(corta["distancia_total_km"]
                  - suma_ruta(distancias, por_bogota)) < 1e-6,
              "distancia de la ruta corta = suma de aristas del JSON")
    desvio = agente.calcular_ruta("Duitama", "Puente Nacional", "distancia",
                                  tramos_bloqueados=[TRAMO_CICLO])
    verificar(desvio["ruta"] == por_santander,
              "con Bogotá a Tocancipá bloqueado: ruta por Santander")
    verificar(abs(desvio["distancia_total_km"]
                  - suma_ruta(distancias, por_santander)) < 1e-6,
              "distancia del desvío = suma de aristas del JSON")
    resultados["ciclo"] = {"corta": corta, "desvio": desvio}
    for criterio in CRITERIOS:
        r = agente.calcular_ruta("Duitama", "Puente Nacional", criterio)
        resultados["ciclo"][criterio] = r
        via = "Santander" if "Bucaramanga" in r["ruta"] else "Bogotá"
        print(f"  {criterio:21s} {r['distancia_total_km']:7.2f} km "
              f"{r['peaje_total_cop']:7d} COP vía {via}")
    # variante cruda (sensibilidad): distancias con shape__length
    cruda = AgenteRutas(construir_grafo(distancia="cruda"))
    c_corta = cruda.calcular_ruta("Duitama", "Puente Nacional", "distancia")
    c_desvio = cruda.calcular_ruta("Duitama", "Puente Nacional", "distancia",
                                   tramos_bloqueados=[TRAMO_CICLO])
    verificar(round(c_corta["distancia_total_km"], 1) == 414.8,
              "variante cruda: ruta corta = 414.8 km")
    verificar(round(c_desvio["distancia_total_km"], 1) == 668.1,
              "variante cruda: desvío = 668.1 km")
    resultados["ciclo_cruda"] = {"corta": c_corta, "desvio": c_desvio}


def prueba_sin_ciclo(agente, resultados):
    print("Pares que no cruzan el ciclo (ruta única)")
    resultados["sin_ciclo"] = []
    for origen, destino in PARES_SIN_CICLO:
        caminos = list(nx.all_simple_paths(agente.grafo, origen, destino))
        verificar(len(caminos) == 1, f"{origen} a {destino}: un solo camino")
        for criterio in CRITERIOS:
            r = agente.calcular_ruta(origen, destino, criterio)
            verificar(r["ruta"] == caminos[0],
                      f"{origen} a {destino} ({criterio}) = camino único")
        r = agente.calcular_ruta(origen, destino, "distancia")
        resultados["sin_ciclo"].append(r)


def prueba_errores(agente):
    print("Entradas inválidas")
    for args, kwargs, texto in [
        (("Bogotá", "Medellín"), {}, "ciudad fuera de la red"),
        (("Bogotá", "Tunja"), {"criterio": "tiempo"}, "criterio desconocido"),
        (("Bogotá", "Granada"),
         {"tramos_bloqueados": [("Ye de Granada", "Granada")]},
         "destino aislado por bloqueo"),
    ]:
        try:
            agente.calcular_ruta(*args, **kwargs)
        except ValueError:
            verificar(True, f"ValueError en {texto}")
        else:
            raise AssertionError(f"No falló: {texto}")


def main():
    agente = AgenteRutas()
    g = agente.grafo
    verificar(g.number_of_nodes() == 32 and g.number_of_edges() == 32,
              "grafo de 32 nodos y 32 aristas")
    verificar(nx.is_connected(g), "grafo conexo")
    resultados = {}
    prueba_ciclo(agente, resultados)
    prueba_sin_ciclo(agente, resultados)
    prueba_errores(agente)
    with open(SALIDA / "pruebas_agente.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print("Todas las pruebas pasaron.")


if __name__ == "__main__":
    main()
