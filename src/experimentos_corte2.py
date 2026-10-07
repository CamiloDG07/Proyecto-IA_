"""Experimentos del Corte 2: escenarios, barrido de pesos y sensibilidad.

Escenarios (pares origen-destino), todos sobre la red corregida de 32 nodos:
  - pares que cruzan el ciclo, con dos rutas simples distintas (el caso
    central es Duitama a Puente Nacional): solo aquí pueden diferir las rutas
    de los cinco algoritmos;
  - pares que no cruzan el ciclo (ruta única): solo difieren los nodos
    expandidos, el tiempo y la memoria; con 1 a 6 saltos.
El número de rutas simples de cada par se comprueba al ejecutar.

Criterios: distancia y compuesto_sin_riesgo (heurística geodésica con
alfa = 0.310570); compuesto (riesgo faltante igual a 0) y riesgo se reportan
aparte como limitados; en riesgo la heurística admisible es h = 0 (A* se
reduce a UCS).

Mediciones: el tiempo se mide sin tracemalloc, REPETICIONES veces por celda
(media y desviación estándar); la memoria pico, en una corrida aparte con
tracemalloc.

Escribe outputs/resultados_corte2.json, outputs/barrido_pesos.json y
outputs/sensibilidad_corte2.json.
"""
import json
from itertools import product

import networkx as nx

from agente import CRITERIOS
from build_graph import SALIDA, construir_grafo
from busquedas import a_estrella, bfs, dfs, medir, ucs, voraz
from heuristica import Heuristica, alfa_minimo, cargar_coordenadas

REPETICIONES = 2000
PASO_MALLA = 0.1
COTA_CHOCONTA_TUNJA = ("Chocontá", "Tunja")
COTA_KM = 56.96
CRITERIOS_EXPERIMENTO = [
    ("distancia", False),
    ("compuesto_sin_riesgo", False),
    ("compuesto", True),
    ("riesgo", True),
]
ALGORITMOS = ["BFS", "DFS", "UCS", "Voraz", "A*"]

# (origen, destino, justificación)
ESCENARIOS = [
    ("Duitama", "Puente Nacional", "caso central: dos rutas reales"),
    ("Tunja", "Ubaté", "ciclo: ambos extremos sobre el ciclo"),
    ("Bucaramanga", "Bogotá", "ciclo: lado de Santander contra Bogotá"),
    ("Barbosa", "Zipaquirá", "ciclo: origen en una hoja fuera del ciclo"),
    ("Bogotá", "Villavicencio", "ruta única, 1 salto"),
    ("Girardot", "Cambao", "ruta única, 1 salto, sin tocar Bogotá"),
    ("Chiquinquirá", "Tunja", "ruta única, 2 saltos"),
    ("Bogotá", "Granada", "ruta única, 3 saltos"),
    ("Madrid", "Puerto Gaitán", "ruta única, 4 saltos"),
    ("Mariquita", "Granada", "ruta única, 6 saltos (la más larga)"),
]


def algoritmos(grafo, atributo, h, origen, destino):
    """Cinco funciones de búsqueda listas para medir."""
    return {
        "BFS": (bfs, (grafo, origen, destino, atributo)),
        "DFS": (dfs, (grafo, origen, destino, atributo)),
        "UCS": (ucs, (grafo, origen, destino, atributo)),
        "Voraz": (voraz, (grafo, origen, destino, atributo, h)),
        "A*": (a_estrella, (grafo, origen, destino, atributo, h)),
    }


def correr_escenarios(grafo, coordenadas, alfa):
    resultados = []
    for origen, destino, motivo in ESCENARIOS:
        rutas_simples = len(list(nx.all_simple_paths(grafo, origen,
                                                     destino)))
        for criterio, limitado in CRITERIOS_EXPERIMENTO:
            atributo = CRITERIOS[criterio]
            h = Heuristica(grafo, coordenadas, criterio, alfa)
            optimo = ucs(grafo, origen, destino, atributo)["costo"]
            for nombre, (funcion, args) in algoritmos(
                    grafo, atributo, h, origen, destino).items():
                m = medir(funcion, REPETICIONES, *args)
                r = m["resultado"]
                resultados.append({
                    "origen": origen, "destino": destino, "motivo": motivo,
                    "rutas_simples": rutas_simples,
                    "criterio": criterio, "limitado": limitado,
                    "h_cero": h.factor == 0.0,
                    "algoritmo": nombre, "ruta": r["ruta"],
                    "saltos": r["saltos"], "costo": r["costo"],
                    "costo_optimo": optimo,
                    "optima": abs(r["costo"] - optimo) < 1e-9,
                    "exceso_relativo": (r["costo"] - optimo) / optimo
                    if optimo else 0.0,
                    "nodos_expandidos": r["nodos_expandidos"],
                    "nodos_generados": r["nodos_generados"],
                    "frontera_max": r["frontera_max"],
                    "reexpansiones": r["reexpansiones"],
                    "tiempo_media_s": m["tiempo_media_s"],
                    "tiempo_desv_s": m["tiempo_desv_s"],
                    "memoria_pico_kib": m["memoria_pico_kib"],
                    "repeticiones": m["repeticiones"],
                })
        print(f"  {origen} - {destino}: {rutas_simples} ruta(s) simple(s)")
    return resultados


def sensibilidad_alfa(grafo, coordenadas, alfa):
    """A* con alfa_ref (mínimo de razón sin Chocontá-Tunja), rotulado.

    Esta h no es admisible en la red por el defecto de Chocontá a Tunja.
    Se compara con alfa = 0.310570 y con UCS en los escenarios y en todos
    los pares de nodos (criterio distancia).
    """
    alfa_ref = alfa_minimo(grafo, coordenadas,
                           excluir=[COTA_CHOCONTA_TUNJA])
    atributo = CRITERIOS["distancia"]
    h_ref = Heuristica(grafo, coordenadas, "distancia", alfa_ref)
    h_base = Heuristica(grafo, coordenadas, "distancia", alfa)
    por_escenario = []
    for origen, destino, _ in ESCENARIOS:
        u = ucs(grafo, origen, destino, atributo)
        a0 = a_estrella(grafo, origen, destino, atributo, h_base)
        a1 = a_estrella(grafo, origen, destino, atributo, h_ref)
        por_escenario.append({
            "origen": origen, "destino": destino,
            "costo_optimo": u["costo"],
            "expandidos_ucs": u["nodos_expandidos"],
            "expandidos_alfa_base": a0["nodos_expandidos"],
            "expandidos_alfa_ref": a1["nodos_expandidos"],
            "costo_alfa_ref": a1["costo"],
            "optima_alfa_ref": abs(a1["costo"] - u["costo"]) < 1e-9,
            "reexpansiones_alfa_ref": a1["reexpansiones"],
        })
    pares = [(o, d) for o in grafo for d in grafo if o != d]
    no_optimos, exp_ucs, exp_base, exp_ref = [], 0, 0, 0
    for o, d in pares:
        u = ucs(grafo, o, d, atributo)
        a0 = a_estrella(grafo, o, d, atributo, h_base)
        a1 = a_estrella(grafo, o, d, atributo, h_ref)
        exp_ucs += u["nodos_expandidos"]
        exp_base += a0["nodos_expandidos"]
        exp_ref += a1["nodos_expandidos"]
        if abs(a1["costo"] - u["costo"]) > 1e-9:
            no_optimos.append({"origen": o, "destino": d,
                               "costo": a1["costo"],
                               "costo_optimo": u["costo"]})
    return {
        "rotulo": "sensibilidad: h con alfa_ref, no admisible por "
                  "Chocontá a Tunja",
        "alfa_base": alfa, "alfa_ref": alfa_ref,
        "por_escenario": por_escenario,
        "todos_los_pares": {
            "pares": len(pares), "no_optimos": len(no_optimos),
            "detalle_no_optimos": no_optimos[:20],
            "expandidos_total_ucs": exp_ucs,
            "expandidos_total_alfa_base": exp_base,
            "expandidos_total_alfa_ref": exp_ref,
        },
    }


def malla_pesos(paso=PASO_MALLA):
    """Todos los (w1, w2, w3) en múltiplos de `paso` que suman 1."""
    n = round(1 / paso)
    return [(i * paso, j * paso, (n - i - j) * paso)
            for i, j in product(range(n + 1), repeat=2) if i + j <= n]


def sumas_ruta(grafo, ruta):
    """Sumas de los términos normalizados de una ruta (con w = 1 cada uno)."""
    tope = grafo.graph["maximos"]
    d = p = r = 0.0
    for u, v in zip(ruta, ruta[1:]):
        e = grafo[u][v]
        d += e["distancia_km"] / tope["distancia"]
        p += e["peaje_cop_camion"] / tope["peaje"]
        if e["riesgo_disponible"]:
            r += e["riesgo_gizscore_prom"] / tope["riesgo"]
    return d, p, r


def barrido(variante, distancia="corregida", reemplazos=None):
    """Ruta ganadora de Duitama a Puente Nacional en la malla de pesos."""
    origen, destino = "Duitama", "Puente Nacional"
    base = construir_grafo(distancia=distancia, reemplazos=reemplazos)
    caminos = list(nx.all_simple_paths(base, origen, destino))
    por_bogota = next(c for c in caminos if "Bogotá" in c)
    por_santander = next(c for c in caminos if "Bucaramanga" in c)
    puntos = []
    for w in malla_pesos():
        pesos = {"distancia": w[0], "peaje": w[1], "riesgo": w[2]}
        g = construir_grafo(pesos, distancia, reemplazos)
        fila = {"w1": round(w[0], 1), "w2": round(w[1], 1),
                "w3": round(w[2], 1)}
        for nombre, atributo in (("compuesto", "peso_multicriterio"),
                                 ("sin_riesgo", "peso_sin_riesgo")):
            if nombre == "sin_riesgo" and w[0] + w[1] == 0:
                fila[nombre], fila["costo_" + nombre] = None, None
                continue
            r = ucs(g, origen, destino, atributo)
            fila[nombre] = "Bogotá" if "Bogotá" in r["ruta"] else "Santander"
            fila["costo_" + nombre] = r["costo"]
        puntos.append(fila)
    dc = sumas_ruta(base, por_bogota)
    dd = sumas_ruta(base, por_santander)
    # frontera: w1*dD + w2*dP + w3*dR = 0, con d = corta - desvío
    delta = [dc[i] - dd[i] for i in range(3)]
    # cambio sobre la arista w3 = 0 (w1 + w2 = 1): w1* = -dP / (dD - dP)
    umbral = None
    if abs(delta[0] - delta[1]) > 1e-12:
        w1 = -delta[1] / (delta[0] - delta[1])
        umbral = w1 if 0.0 <= w1 <= 1.0 else None
    # coherencia entre la malla y la forma lineal de la frontera
    incoherentes = 0
    for f in puntos:
        lineal = f["w1"] * delta[0] + f["w2"] * delta[1] \
            + f["w3"] * delta[2]
        esperado = "Bogotá" if lineal < 0 else "Santander"
        if abs(lineal) > 1e-9 and esperado != f["compuesto"]:
            incoherentes += 1
    return {
        "variante": variante, "distancia": distancia,
        "reemplazos": {"-".join(k): v for k, v in (reemplazos or {}).items()},
        "ruta_bogota": por_bogota, "ruta_santander": por_santander,
        "sumas_bogota": dc, "sumas_santander": dd,
        "delta_corta_menos_desvio": delta,
        "w1_umbral_sobre_w3_cero": umbral,
        "puntos_incoherentes_con_forma_lineal": incoherentes,
        "puntos": puntos,
        "ganan_bogota_compuesto": sum(
            1 for f in puntos if f["compuesto"] == "Bogotá"),
        "ganan_bogota_sin_riesgo": sum(
            1 for f in puntos if f["sin_riesgo"] == "Bogotá"),
        "puntos_sin_riesgo_definidos": sum(
            1 for f in puntos if f["sin_riesgo"] is not None),
    }


def rutas_optimas_por_criterio(distancia, reemplazos=None):
    """Ruta óptima de Duitama a Puente Nacional por criterio."""
    g = construir_grafo(distancia=distancia, reemplazos=reemplazos)
    salida = {}
    for criterio, atributo in CRITERIOS.items():
        r = ucs(g, "Duitama", "Puente Nacional", atributo)
        km = sum(g[u][v]["distancia_km"] for u, v in zip(r["ruta"],
                                                         r["ruta"][1:]))
        salida[criterio] = {
            "via": "Bogotá" if "Bogotá" in r["ruta"] else "Santander",
            "distancia_km": round(km, 2), "costo": r["costo"]}
    return salida


def main():
    grafo = construir_grafo()
    coordenadas = cargar_coordenadas()
    alfa = alfa_minimo(grafo, coordenadas)
    print(f"Escenarios (alfa = {alfa:.6f}, {REPETICIONES} repeticiones)")
    resultados = correr_escenarios(grafo, coordenadas, alfa)
    with open(SALIDA / "resultados_corte2.json", "w",
              encoding="utf-8") as f:
        json.dump({"alfa": alfa, "repeticiones": REPETICIONES,
                   "resultados": resultados}, f, ensure_ascii=False,
                  indent=1)
    print("Sensibilidad de A* con alfa_ref")
    sens = sensibilidad_alfa(grafo, coordenadas, alfa)
    print("Barrido de pesos")
    cota = {COTA_CHOCONTA_TUNJA: COTA_KM}
    barridos = [
        barrido("base (red corregida)"),
        barrido("sensibilidad con cota inferior", reemplazos=cota),
        barrido("sensibilidad con distancias crudas", distancia="cruda"),
    ]
    with open(SALIDA / "barrido_pesos.json", "w", encoding="utf-8") as f:
        json.dump(barridos, f, ensure_ascii=False, indent=1)
    sens["rutas_optimas_duitama_puente_nacional"] = {
        "base": rutas_optimas_por_criterio("corregida"),
        "cota_inferior": rutas_optimas_por_criterio("corregida", cota),
        "crudas": rutas_optimas_por_criterio("cruda"),
    }
    with open(SALIDA / "sensibilidad_corte2.json", "w",
              encoding="utf-8") as f:
        json.dump(sens, f, ensure_ascii=False, indent=1)
    for b in barridos:
        print(f"  {b['variante']}: gana Bogotá en "
              f"{b['ganan_bogota_compuesto']} de {len(b['puntos'])} puntos "
              f"(compuesto), umbral w1 sobre w3=0: "
              f"{b['w1_umbral_sobre_w3_cero']}")
    t = sens["todos_los_pares"]
    print(f"  A* alfa_ref={sens['alfa_ref']:.6f}: "
          f"{t['no_optimos']} de {t['pares']} pares no óptimos")


if __name__ == "__main__":
    main()
