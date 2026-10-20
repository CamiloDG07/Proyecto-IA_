"""Contrasta las cifras de los informes y del guion con los datos del repo.

Cada comprobación compara un valor escrito en el texto (informe del Corte 1,
informe del Corte 2 o guion de la demostración) con el que salen de
outputs/, del grafo o de la ejecución del agente. Imprime una línea por
cifra y termina con código 1 si hay alguna discrepancia.

Uso: python src/verificar_cifras.py
"""
import csv
import json
import os
import re
import shlex
import subprocess
import sys
from itertools import combinations, permutations
from pathlib import Path

import networkx as nx

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.stdout.reconfigure(encoding="utf-8")

from agente_rutas import recomendar  # noqa: E402
from build_graph import cargar_grafo, construir_grafo  # noqa: E402
from heuristica import cargar_coordenadas, haversine_km  # noqa: E402
from umbral_costo import umbral_exacto  # noqa: E402

filas = []


def cargar(nombre):
    with open(RAIZ / "outputs" / nombre, encoding="utf-8") as f:
        return json.load(f)


def leer(ruta):
    with open(RAIZ / ruta, encoding="utf-8") as f:
        return f.read()


def expandir(ruta):
    """Texto de un .tex sin comentarios y con los \\input de outputs/."""
    t = re.sub(r"(?m)(?<!\\)%.*$", "", leer(ruta))
    return re.sub(r"\\input\{(outputs/[^}]*\.tex)\}",
                  lambda m: leer(m.group(1)), t)


def chequear(texto, esperado, real, tol=0.0):
    if isinstance(real, (int, float)) and not isinstance(real, bool):
        ok = abs(real - esperado) <= tol
    else:
        ok = real == esperado
    filas.append((ok, texto, esperado, real))


def citas(donde, texto, lista):
    """Cada cadena de `lista` debe aparecer en `texto` (cifra citada)."""
    plano = " ".join(texto.split())
    for etiqueta, cadena in lista:
        chequear(f"{donde}: cita {etiqueta} «{cadena}»", True,
                 cadena in plano)


def miles(valor):
    return f"{valor:,.0f}".replace(",", "\\,")


def miles_guion(valor):
    return f"{valor:,.0f}".replace(",", " ")


res = cargar("resultados_corte2.json")["resultados"]
bar = cargar("barrido_pesos.json")
sens = cargar("sensibilidad_corte2.json")
heur = cargar("analisis_heuristica.json")
umb = cargar("umbral_held_karp.json")
val = cargar("validacion_agente.json")["instancias"]
est = cargar("verificacion_estructura.json")
g = cargar_grafo()
co = cargar_coordenadas()
with open(RAIZ / "outputs" / "auditoria_distancias.csv",
          encoding="utf-8") as _f:
    aud = list(csv.DictReader(_f))
c1 = expandir("formulacion_corte1.tex")
c2 = expandir("informe_corte2.tex")
guion = leer("guion_demostracion.md")

# ---- 1. Red y distancias ---------------------------------------------------
chequear("nodos", 32, g.number_of_nodes())
chequear("aristas", 32, g.number_of_edges())
chequear("ciclos independientes", 1, g.number_of_edges()
         - g.number_of_nodes() + nx.number_connected_components(g))
chequear("registros corregidos por doble calzada", 9,
         sum(1 for r in aud if r["patron"].startswith("doble")))
d_corta = nx.shortest_path_length(g, "Duitama", "Puente Nacional",
                                  weight="distancia_km")
h = g.copy()
h.remove_edge("Bogotá", "Tocancipá")
d_desv = nx.shortest_path_length(h, "Duitama", "Puente Nacional",
                                 weight="distancia_km")
chequear("ruta por Bogotá (km), con piso", 370.54, round(d_corta, 2))
chequear("ruta por Santander (km)", 654.25, round(d_desv, 2))
sin_piso = construir_grafo(piso_geodesico=False)
hs = sin_piso.copy()
hs.remove_edge("Bogotá", "Tocancipá")
chequear("ruta por Bogotá (km), sin piso (distancias oficiales)", 309.10,
         round(nx.shortest_path_length(sin_piso, "Duitama", "Puente Nacional",
                                       weight="distancia_km"), 2))
chequear("ruta por Santander (km), sin piso", 654.25, round(
    nx.shortest_path_length(hs, "Duitama", "Puente Nacional",
                            weight="distancia_km"), 2))
ct = g["Chocontá"]["Tunja"]["distancia_km"]
geo_ct = haversine_km(*co["Chocontá"], *co["Tunja"])
aristas_json = json.loads(leer("outputs/aristas_red.json"))
arista_ct = next(a for a in aristas_json
                 if (a["origen"], a["destino"]) == ("Chocontá", "Tunja"))
ct_of = arista_ct["distancia_oficial_km"]
chequear("Chocontá-Tunja oficial (km)", 17.69, ct_of)
chequear("Chocontá-Tunja del modelo (km): la recta", 56.96, round(ct, 2))
chequear("Chocontá-Tunja piso, fuente y marca", (True, "registro", True), (
    arista_ct["distancia_piso_aplicado"], arista_ct["distancia_fuente"],
    arista_ct["distancia_truncada"]))
chequear("Chocontá-Tunja diferencia de progresivas (km)", 61.0,
         arista_ct["distancia_progresivas_km"])
chequear("Chocontá-Tunja geodésica (km)", 56.96, round(geo_ct, 2))
chequear("razón oficial de Chocontá-Tunja", 0.3106, round(ct_of / geo_ct, 4),
         5e-5)
chequear("razón con progresivas", 1.071, round(61.0 / geo_ct, 3))
chequear("PR final de Chocontá a Tunja menos PR de Tocancipá-Chocontá",
         61.0, round(120.0 - 59.0, 1))
chequear("hueco de progresivas (km)", 49.1, round(108.096 - 59.0, 1), 0.05)
ev = json.loads(leer("outputs/evaluacion_progresivas.json"))[
    "Chocontá - Tunja"]
chequear("regla de progresivas: falla (b), (c) y (d); no se adopta",
         (["b", "c", "d"], False), (
             [k for k in "abcde" if not ev["reglas"][k]["cumple"]],
             ev["reglas"]["adoptar"]))
chequear("regla de progresivas: hueco, extremo a Tunja y razón",
         (49.1, 11, 1.486), (
             round(ev["mediciones"]["hueco_km"], 1),
             round(ev["mediciones"]["extremo_destino_km"]),
             round(ev["mediciones"]["razon_geometria"], 3)))
# piso geodésico
con_piso = [a for a in aristas_json if a["distancia_piso_aplicado"]]
chequear("aristas con piso geodésico", 8, len(con_piso))
chequear("aristas con piso (oficial, recta, modelo)", sorted([
    ("Chocontá", "Tunja", 17.69, 56.96, 56.96),
    ("Madrid", "Bogotá", 9.12, 19.91, 19.91),
    ("Bogotá", "Tocancipá", 22.12, 41.19, 41.19),
    ("Cajicá", "Zipaquirá", 9.10, 12.15, 12.15),
    ("Ye de Granada", "Granada", 2.43, 3.04, 3.04),
    ("Girardot", "El Espinal", 19.36, 20.42, 20.42),
    ("Bogotá", "Guasca", 34.88, 35.12, 35.12),
    ("Tunja", "Duitama", 47.73, 47.78, 47.78)]), sorted((
        a["origen"], a["destino"], a["distancia_oficial_km"],
        round(a["distancia_geodesica_km"], 2), round(a["distancia_km"], 2))
        for a in con_piso))
chequear("piso: distancia del modelo >= geodésica en las 32 aristas", True,
         all(a["distancia_km"] >= haversine_km(
             *co[a["origen"]], *co[a["destino"]]) - 1e-9
             for a in aristas_json))
chequear("sin piso: la distancia del modelo es la oficial exacta", True, all(
    a["distancia_km"] == a["distancia_oficial_km"]
    for a in aristas_json if not a["distancia_piso_aplicado"]))
chequear("suma del piso (km)", 74.14, round(
    sum(a["distancia_piso_km"] for a in aristas_json), 2), 0.005)
chequear("distancia total de la red, modelo y oficial (km)", (1960.14, 1886.0),
         (round(sum(d["distancia_km"] for _u, _v, d in g.edges(data=True)), 2),
          round(sum(d["distancia_oficial_km"]
                    for _u, _v, d in g.edges(data=True)), 2)))
razon = [float(f["razon"]) for f in csv.DictReader(
    open(RAIZ / "outputs" / "auditoria_aristas.csv", encoding="utf-8"))]
chequear("aristas con carretera menor que la geodésica", 8,
         sum(1 for x in razon if x < 1))
sin_riesgo = sum(1 for _u, _v, d in g.edges(data=True)
                 if not d["riesgo_disponible"])
chequear("aristas sin riesgo", 21, sin_riesgo)
chequear("aristas con riesgo", 11, 32 - sin_riesgo)
chequear("pares 25 grafos", 600,
         len(list(permutations(range(30), 2))[::37]) * 25)
chequear("pares de la red", 992,
         g.number_of_nodes() * (g.number_of_nodes() - 1))

# ---- 2. Mortalidad ANSV ----------------------------------------------------
mort = cargar("validacion_riesgo_mortalidad.json")
chequear("mortalidad: aristas con sector", 16, sum(
    1 for _u, _v, d in g.edges(data=True) if d["mortalidad_disponible"]))
chequear("mortalidad: Spearman con el GiZScore", -0.033,
         mort["spearman_mortalidad_vs_gizscore"])
chequear("mortalidad: aristas con GiZScore y con sector", (11, 7),
         (mort["aristas_con_gizscore"],
          mort["de_ellas_con_sector_de_mortalidad"]))
chequear("mortalidad: cobertura antes, solo mortalidad y unión",
         (11, 16, 20), (mort["cobertura_antes"],
                        mort["cobertura_solo_mortalidad"],
                        mort["cobertura_despues_union"]))
citas("Corte 2", c2, [("Spearman", "$-0.033$"),
                      ("cobertura", "cubren 16 de 32")])
citas("Corte 1", c1, [("Spearman", "$-0.033$"),
                      ("cobertura", "16 de")])

# ---- 3. Heurística ---------------------------------------------------------
chequear("alfa con piso", 1.0, heur["alfa"])
chequear("razón mínima con piso >= 1 (tolerancia 1e-9)", True,
         heur["razon_minima_exacta"] >= 1 - 1e-9)
chequear("razón mínima con piso (6 decimales)", 1.0,
         round(heur["razon_minima_exacta"], 6))
spd = heur["sin_piso"]
chequear("alfa sin piso", 0.31057, spd["alfa"], 1e-9)
chequear("razón mínima exacta sin piso", 0.3105704113,
         round(spd["razon_minima_exacta"], 10), 1e-10)
chequear("alfa de la sensibilidad de A* (con y sin piso)", (1.0, 0.31057),
         (sens["alfa_piso"], sens["alfa_sin_piso"]))
margen_piso = heur["criterios"]["distancia"]["admisibilidad"][
    "margen_minimo"]
chequear("margen mínimo de la distancia con piso: cero (< 1e-6 km)", True,
         -1e-12 <= margen_piso < 1e-6)
chequear("margen mínimo de la distancia sin piso (km)", 0.000023, round(
    spd["criterios"]["distancia"]["admisibilidad"]["margen_minimo"], 6), 1e-9)
chequear("violaciones con piso en todas las heurísticas", 0, sum(
    v["admisibilidad"]["violaciones"] + v["consistencia"]["violaciones"]
    for v in heur["criterios"].values()))
chequear("violaciones sin piso con su alfa en todas las heurísticas", 0, sum(
    v["admisibilidad"]["violaciones"] + v["consistencia"]["violaciones"]
    for v in spd["criterios"].values()))
chequear("heurísticas verificadas", 7, len(heur["criterios"]))
p = spd["geodesica_pura_distancia"]
chequear("violaciones adm. sin piso con alfa=1", 66,
         p["admisibilidad"]["violaciones"])
chequear("violaciones cons. sin piso con alfa=1", 141,
         p["consistencia"]["violaciones"])
chequear("peor margen sin piso con alfa=1", -56.51,
         round(p["admisibilidad"]["margen_minimo"], 2))
citas("Corte 2", c2, [("alfa sin piso", "0.310570"),
                      ("razón mínima", "1.0000000059")])
citas("tabla de heurísticas", leer("outputs/tabla_c2_heuristica.tex"),
      [("violaciones", "& 66 &"), ("peor margen", "-56.51")])

# ---- 4. Escenarios ---------------------------------------------------------
saltos = sorted({c["saltos"] for c in res if c["criterio"] == "distancia"
                 and c["algoritmo"] == "UCS" and c["rutas_simples"] == 1})
chequear("saltos de los pares de ruta única", [1, 2, 3, 4, 6], saltos)
chequear("repeticiones", 2000, res[0]["repeticiones"])
pre = [c["precalculo_h_media_s"] * 1e6 for c in res
       if c["precalculo_h_media_s"] is not None]
chequear("precálculo medio (us)", 36.9, round(sum(pre) / len(pre), 1), 0.05)
chequear("precálculo mínimo (us)", 6.7, round(min(pre), 1), 0.05)
chequear("precálculo máximo (us)", 71.2, round(max(pre), 1), 0.05)
chequear("máx desviación/media", 1.49, round(max(
    c["tiempo_desv_s"] / c["tiempo_media_s"] for c in res), 2), 0.005)


def cel(o, d, crit, alg):
    return next(c for c in res if c["origen"] == o and c["destino"] == d
                and c["criterio"] == crit and c["algoritmo"] == alg)


def exceso(o, d, crit, alg):
    return round(100 * cel(o, d, crit, alg)["exceso_relativo"], 1)


chequear("BFS exceso (%)", 76.6,
         exceso("Duitama", "Puente Nacional", "distancia", "BFS"), 0.05)
chequear("BFS saltos", 7,
         cel("Duitama", "Puente Nacional", "distancia", "BFS")["saltos"])
chequear("UCS saltos", 8,
         cel("Duitama", "Puente Nacional", "distancia", "UCS")["saltos"])
chequear("DFS Bucaramanga-Bogotá exceso (%)", 49.0,
         exceso("Bucaramanga", "Bogotá", "distancia", "DFS"), 0.05)
for crit, esperado in (
        ("distancia", {"BFS": 143, "DFS": 142, "UCS": 139, "Voraz": 50,
                       "A*": 64}),
        ("compuesto_sin_riesgo", {"BFS": 143, "DFS": 142, "UCS": 138,
                                  "Voraz": 50, "A*": 99})):
    real = {a: sum(c["nodos_expandidos"] for c in res
                   if c["criterio"] == crit and c["algoritmo"] == a)
            for a in esperado}
    chequear(f"expandidos totales {crit}", esperado, real)
a_ = cel("Duitama", "Puente Nacional", "distancia", "A*")
u_ = cel("Duitama", "Puente Nacional", "distancia", "UCS")
chequear("A* central media y desv (us)", (56, 7),
         (round(a_["tiempo_media_s"] * 1e6), round(a_["tiempo_desv_s"] * 1e6)),
         0.5)
chequear("UCS central media y desv (us)", (89, 5),
         (round(u_["tiempo_media_s"] * 1e6), round(u_["tiempo_desv_s"] * 1e6)),
         0.5)
chequear("expandidos centrales A*, UCS", (14, 27),
         (a_["nodos_expandidos"], u_["nodos_expandidos"]))
chequear("sin riesgo BFS exceso", 4.7, exceso(
    "Duitama", "Puente Nacional", "compuesto_sin_riesgo", "BFS"), 0.05)
chequear("sin riesgo DFS Buc-Bog exceso", 8.7, exceso(
    "Bucaramanga", "Bogotá", "compuesto_sin_riesgo", "DFS"), 0.05)
citas("Corte 2", c2, [("exceso BFS", "76.6"), ("exceso DFS", "49.0"),
                      ("precálculo", "36.9"), ("desviación", "1.49"),
                      ("sin riesgo", "4.7"), ("sin riesgo DFS", "8.7")])
citas("tabla de nodos", leer("outputs/tabla_r_nodos.tex"),
      [("totales con distancia", "& 143 & 142 & 139 & 50 & 64 \\\\")])

# ---- 5. Barrido de pesos ---------------------------------------------------
b0, b1, b2, b3 = bar
chequear("puntos", 66, len(b0["puntos"]))
chequear("barrido con piso: Bogotá, umbral y sin riesgo", (17, 0.4576, 35, 65),
         (b0["ganan_bogota_compuesto"],
          round(b0["w1_umbral_sobre_w3_cero"], 4),
          b0["ganan_bogota_sin_riesgo"], b0["puntos_sin_riesgo_definidos"]))
chequear("barrido sin piso: Bogotá, umbral y sin riesgo", (19, 0.4095, 37),
         (b1["ganan_bogota_compuesto"],
          round(b1["w1_umbral_sobre_w3_cero"], 4),
          b1["ganan_bogota_sin_riesgo"]))
chequear("barrido con las progresivas: Bogotá, umbral y sin riesgo",
         (17, 0.4611, 35), (b3["ganan_bogota_compuesto"],
                            round(b3["w1_umbral_sobre_w3_cero"], 4),
                            b3["ganan_bogota_sin_riesgo"]))
chequear("barrido con las distancias crudas (con piso)", (11, 0.574, 28),
         (b2["ganan_bogota_compuesto"],
          round(b2["w1_umbral_sobre_w3_cero"], 4),
          b2["ganan_bogota_sin_riesgo"]))
chequear("barrido: el piso no toca peaje ni riesgo (delta P y R)", True,
         all(b["delta_corta_menos_desvio"][1:3] == b0[
             "delta_corta_menos_desvio"][1:3] for b in (b1, b2, b3)))
cambia = [(f["w1"], f["w2"], f["w3"]) for f, k in zip(
    b0["puntos"], b1["puntos"]) if f["compuesto"] != k["compuesto"]]
chequear("puntos que cambian sin piso (compuesto)",
         [(0.5, 0.2, 0.3), (0.5, 0.3, 0.2)], cambia)
cambia2 = [(f["w1"], f["w2"], f["w3"]) for f, k in zip(
    b0["puntos"], b1["puntos"]) if f["sin_riesgo"] != k["sin_riesgo"]]
chequear("puntos que cambian sin piso (sin riesgo)",
         [(0.3, 0.4, 0.3), (0.4, 0.5, 0.1)], cambia2)
citas("Corte 2", c2, [("umbral con piso", "0.4576"),
                      ("umbral sin piso", "0.4095"),
                      ("umbral progresivas", "0.4611"),
                      ("sin riesgo", "35 de 65")])
tot = cargar("barrido_total.json")
chequear("barrido de cuatro pesos: con piso, sin piso y progresivas",
         ((137, 215), (149, 224), (137, 215)), tuple(
             (x["ganan_bogota_total"], x["ganan_bogota_sin_riesgo"])
             for x in tot))

# ---- 6. Sensibilidad de A* -------------------------------------------------
e0 = next(e for e in sens["por_escenario"] if e["origen"] == "Duitama")
chequear("central: UCS y A* con piso; UCS, A* y A* alfa=1 sin piso",
         (27, 14, 25, 20, 14), (e0["expandidos_ucs_piso"],
                                e0["expandidos_astar_piso"],
                                e0["expandidos_ucs_sin_piso"],
                                e0["expandidos_astar_sin_piso"],
                                e0["expandidos_astar_sin_piso_alfa1"]))
t = sens["todos_los_pares"]
chequear("A* con piso: reexpansiones en los 992 pares", 0,
         t["reexpansiones_astar_piso"])
chequear("A* sin piso con alfa=1: pares no óptimos", 3,
         t["no_optimos_sin_piso_alfa1"])
chequear("pares no óptimos sin piso con alfa=1", [
    ("Bucaramanga", "Barbosa", 544.84, 544.17),
    ("Bucaramanga", "Sáchica", 517.16, 516.49),
    ("Bucaramanga", "Tunja", 482.01, 481.34)], [
        (d["origen"], d["destino"], round(d["costo"], 2),
         round(d["costo_optimo"], 2)) for d in t["detalle_no_optimos"]])
chequear("totales de nodos: UCS y A* con piso", (15872, 8584),
         (t["expandidos_total_ucs_piso"], t["expandidos_total_astar_piso"]))
chequear("totales de nodos sin piso: UCS, A* y A* alfa=1",
         (15872, 13377, 8321), (t["expandidos_total_ucs_sin_piso"],
                                t["expandidos_total_astar_sin_piso"],
                                t["expandidos_total_astar_sin_piso_alfa1"]))
chequear("A* contra UCS en distancia (64 y 139)", (64, 139), (sum(
    c["nodos_expandidos"] for c in res
    if c["criterio"] == "distancia" and c["algoritmo"] == "A*"), sum(
    c["nodos_expandidos"] for c in res
    if c["criterio"] == "distancia" and c["algoritmo"] == "UCS")))
citas("tabla de sensibilidad de A*",
      leer("outputs/tabla_c2_sensibilidad_alfa.tex"),
      [("A* piso", "8584"), ("A* sin piso", "13377"),
       ("A* alfa=1 sin piso", "8321")])

# ---- 7. Umbral de Held-Karp y máquina --------------------------------------
chequear("RAM (GiB)", 15.88, round(umb["maquina"]["memoria_instalada_gib"], 2),
         0.005)
chequear("límite memoria (MiB)", 4064, round(umb["limite_memoria_mib"]), 0.5)
m = {x["k"]: x for x in cargar("umbral_sesion_2.json")["mediciones"]}
ant = cargar("umbral_sesion_1.json")
ma = {x["k"]: x for x in ant["mediciones"]}
S3 = {x["k"]: x for x in cargar("umbral_sesion_3.json")["mediciones"]}
for k, esp in ((19, (2.735, 1.227, 1.694)), (20, (5.986, 2.475, 3.676))):
    chequear(f"k={k} por sesión", esp, tuple(
        round(x[k]["mediana_s"], 3) for x in (ma, m, S3)))
chequear("k=22 memoria", 1009.8, round(m[22]["memoria_pico_mib"], 1), 0.05)
chequear("K_exacto", 19, umb["k_exacto"])
chequear("K_exacto sesión anterior", 19, ant["k_exacto"])


def variacion(k):
    return (max(x[k]["mediana_s"] for x in (ma, m, S3))
            / min(x[k]["mediana_s"] for x in (ma, m, S3)))


chequear("variación máx k 16-20", 2.75,
         round(max(variacion(k) for k in range(16, 21)), 2), 0.005)
chequear("variación k>=21", 1.70,
         round(max(variacion(21), variacion(22)), 2), 0.005)
chequear("procesador", "Intel(R) Core(TM) i7-8750H CPU @ 2.20GHz",
         umb["maquina"]["procesador"])
chequear("python y numpy", ("3.14.3", "2.5.2"),
         (umb["maquina"]["python"], umb["maquina"]["numpy"]))

# ---- 8. Validación del despachador y del ACO -------------------------------
red = [r for r in val if r["familia"] == "red de carga"]
tal = [r for r in val if r["familia"].startswith("euclidiana n=20")]
may = [r for r in val if "mayor" in r["familia"]]
con_ex = [r for r in red if "exacto" in r]
chequear("instancias de red con exacto", 12, len(con_ex))
chequear("30/30 por n hasta 20", True, all(sum(
    r["aco"]["semillas_que_igualan_referencia"]
    for r in con_ex if r["n"] == n) == 30 for n in (5, 10, 15, 20)))
r32 = next(r for r in red if r["n"] == 32)
chequear("óptimo por estructura con 32 ciudades", 2895.49,
         round(r32["referencia"]["costo"], 2), 0.005)
chequear("32 ciudades: 10 de 10", 10,
         r32["aco"]["semillas_que_igualan_referencia"])


def grupo(clave, ms):
    return (round(sum(r[clave]["brecha_media_pct"] for r in ms) / len(ms), 3),
            sum(r[clave]["semillas_que_igualan_referencia"] for r in ms))


def de_red(n):
    return [r for r in red if r["n"] == n]


chequear("inicio fijo n=15", (2.012, 22),
         grupo("aco_sin_2opt_inicio_fijo", de_red(15)))
chequear("inicio fijo n=20", (1.832, 19),
         grupo("aco_sin_2opt_inicio_fijo", de_red(20)))
chequear("inicio aleatorio sin 2-opt en la red (brecha, semillas)", (0, 130),
         (sum(grupo("aco_sin_2opt", de_red(n))[0]
              for n in (5, 10, 15, 20, 32)),
          sum(grupo("aco_sin_2opt", de_red(n))[1]
              for n in (5, 10, 15, 20, 32))))
chequear("con 2-opt 120/120 en las instancias con exacto", 120, sum(
    r["aco"]["semillas_que_igualan_referencia"] for r in con_ex))
chequear("brecha de la iteración 1 en la red (máx., %)", 0.0, round(max(
    100 * abs(r["aco"]["curva_media"][0] - r["referencia"]["costo"])
    / r["referencia"]["costo"] for r in red), 3), 5e-4)
chequear("euclidianas n=20: brecha media con 2-opt", 0.040,
         round(sum(r["aco"]["brecha_media_pct"] for r in tal) / 5, 3), 5e-4)
chequear("euclidianas n=20: 48/50", 48, sum(
    r["aco"]["semillas_que_igualan_referencia"] for r in tal))
chequear("euclidianas n=20: semilla 1, 8/10", 8,
         tal[0]["aco"]["semillas_que_igualan_referencia"])
chequear("euclidianas n=20 sin 2-opt aleatorio", (0.357, 32), (
    round(sum(r["aco_sin_2opt"]["brecha_media_pct"] for r in tal) / 5, 3),
    sum(r["aco_sin_2opt"]["semillas_que_igualan_referencia"]
        for r in tal)))
chequear("euclidianas n=20: mejor corrida = óptimo", True, all(
    abs(r["aco"]["brecha_mejor_pct"]) < 1e-6 for r in tal))
chequear("euclidianas n=20 inicio fijo", (2.212, 1), (
    round(sum(r["aco_sin_2opt_inicio_fijo"]["brecha_media_pct"]
              for r in tal) / 5, 3),
    sum(r["aco_sin_2opt_inicio_fijo"]["semillas_que_igualan_referencia"]
        for r in tal)))
hk = [r["exacto"]["tiempo_s"] for r in red + tal
      if r["n"] == 20 and "exacto" in r]
chequear("Held-Karp n=20, tiempos mín y máx (s)", (1.12, 1.19),
         (round(min(hk), 2), round(max(hk), 2)))
chequear("Held-Karp n=20, memoria (MiB)", 111.8,
         round(red[9]["exacto"]["memoria_pico_mib"], 1), 0.05)
at = [r["aco"]["tiempo_medio_s"] for r in red + tal if r["n"] == 20]
chequear("ACO n=20, tiempos mín y máx (s)", (0.06, 0.07),
         (round(min(at), 2), round(max(at), 2)))
chequear("exacto en ms hasta n=10", True, all(
    r["exacto"]["tiempo_s"] < 0.01 for r in red
    if "exacto" in r and r["n"] <= 10))
chequear("estructura: coincidencias y discrepancias", (300, 0),
         (est["coincidencias"], len(est["discrepancias"])))
for r in may:
    chequear(f"n={r['n']}: brecha mejor y media",
             {100: (-0.315, -0.171), 200: (-1.937, -1.4)}[r["n"]],
             (round(r["aco"]["brecha_mejor_pct"], 3),
              round(r["aco"]["brecha_media_pct"], 3)))
chequear("n=100: tiempo del ACO", (1.07, 0.03), (
    round(may[0]["aco"]["tiempo_medio_s"], 2),
    round(may[0]["aco"]["tiempo_desv_s"], 2)))
chequear("n=100 sin 2-opt", (0.89, 0.03, 5.599), (
    round(may[0]["aco_sin_2opt"]["tiempo_medio_s"], 2),
    round(may[0]["aco_sin_2opt"]["tiempo_desv_s"], 2),
    round(may[0]["aco_sin_2opt"]["brecha_media_pct"], 3)))
chequear("n=200 sin 2-opt", (4.84, 0.15, 6.209), (
    round(may[1]["aco_sin_2opt"]["tiempo_medio_s"], 2),
    round(may[1]["aco_sin_2opt"]["tiempo_desv_s"], 2),
    round(may[1]["aco_sin_2opt"]["brecha_media_pct"], 3)))
chequear("n=200: tiempo y memoria", (6.05, 0.07, 5391), (
    round(may[1]["aco"]["tiempo_medio_s"], 2),
    round(may[1]["aco"]["tiempo_desv_s"], 2),
    round(may[1]["aco"]["memoria_pico_kib"])))
chequear("inicios de 2-opt", (301, 151), (
    may[0]["referencia"]["inicios"], may[1]["referencia"]["inicios"]))
citas("Corte 2", c2, [("óptimo 32", "2895.49"), ("inicio fijo n=15", "2.012"),
                      ("inicio fijo n=20", "1.832"),
                      ("n=200", "6.05"),
                      ("n=100 sin 2-opt", "0.89")])

# ---- 9. Perfil topológico e ida y vuelta -----------------------------------
per = cargar("perfil_topologico.json")
chequear("perfil: pares con 1 y 2 caminos", (111, 385), (
    per["pares_por_numero_de_caminos"]["1"],
    per["pares_por_numero_de_caminos"]["2"]))
chequear("perfil: obligatorio, atajo, único", (374, 105, 17), (
    per["pares_por_clase"]["paso_obligatorio"],
    per["pares_por_clase"]["atajo"], per["pares_por_clase"]["camino_unico"]))
chequear("perfil: puntos de articulación", 10,
         len(per["puntos_de_articulacion"]))
tex_perfil = leer("outputs/texto_perfil_topologico.tex")
chequear("margen mínimo de todos los pares con alternativa (%)", 1.2, min(
    100 * (min(a["costos"]["compuesto_sin_riesgo"]
               for a in rr["alternativas"] + rr["descartadas"])
           / rr["recomendada"]["costos"]["compuesto_sin_riesgo"] - 1)
    for rr in (recomendar(o, [d], grafo=g)
               for o, d in combinations(sorted(g.nodes), 2))
    if rr["alternativas"] + rr["descartadas"]).__round__(1), 0.05)
chequear("texto del perfil cita 385, 111, 374, 105, 17 y 10", True, all(
    x in tex_perfil for x in ("385", "111", "374", "105", "17", "10 puntos")))
r_iv = recomendar("Duitama", ["Puente Nacional"], True,
                  bloquear_regreso="Tunja-Chocontá", grafo=g)
chequear("ida y vuelta con bloqueo: margen del regreso (%)", 4.7,
         round(r_iv["detalle_regreso"]["margen_pct"], 1), 0.05)
chequear("ida y vuelta con bloqueo: total km", 1024.79,
         round(r_iv["total"]["km"], 2), 0.005)
chequear("ida y vuelta con bloqueo: total peaje", 271000,
         round(r_iv["total"]["peaje_cop"]))
for o, d, esp in (("Chiquinquirá", "Chocontá", 496.9),
                  ("Cajicá", "Zipaquirá", 15800.1),
                  ("Duitama", "Presidente", 603.4)):
    rr = recomendar(o, [d], grafo=g)
    c0 = rr["recomendada"]["costos"]["compuesto_sin_riesgo"]
    c1_ = min(a["costos"]["compuesto_sin_riesgo"]
              for a in rr["alternativas"] + rr["descartadas"])
    chequear(f"guion: margen {o} a {d} (%)", esp,
             round(100 * (c1_ - c0) / c0, 1), 0.05)

# ---- 10. Costo monetario ---------------------------------------------------
cfg = json.loads(leer("config_costos.json"))["insumos"]
chequear("insumos: estados", ("verificada", "verificada", "verificada",
                              "supuesto del equipo"), (
    cfg["precio_galon_acpm_cop"]["estado"],
    cfg["consumo_litros_por_100km"]["estado"],
    cfg["litros_por_galon"]["estado"],
    cfg["otros_costos_variables_cop_por_km"]["estado"]))
chequear("insumos: precio, consumo y otros costos", (11320, 38.69, 0), (
    cfg["precio_galon_acpm_cop"]["valor"],
    cfg["consumo_litros_por_100km"]["valor"],
    cfg["otros_costos_variables_cop_por_km"]["valor"]))
por_km = (cfg["precio_galon_acpm_cop"]["valor"]
          / cfg["litros_por_galon"]["valor"]
          * cfg["consumo_litros_por_100km"]["valor"] / 100)
chequear("costo variable por km (COP)", 1157.0, round(por_km, 1))
chequear("rendimiento (km por galón)", 9.784, round(
    cfg["litros_por_galon"]["valor"] * 100
    / cfg["consumo_litros_por_100km"]["valor"], 3), 5e-4)
rec = recomendar("Duitama", ["Puente Nacional"], grafo=g)
rb = rec["recomendada"]
chequear("ruta por Bogotá: combustible y costo operativo (COP)",
         (428710, 599510), (round(rb["costo_variable_cop"]),
                            round(rb["costo_operativo_cop"])))
rs = next(a for a in rec["alternativas"])
chequear("ruta por Santander: combustible y costo operativo (COP)",
         (756965, 857165), (round(rs["costo_variable_cop"]),
                            round(rs["costo_operativo_cop"])))
chequear("criterio por defecto con un insumo supuesto",
         "compuesto_sin_riesgo", rec["criterio_efectivo"])
u = rec["umbral_costo"]
chequear("umbral exacto (COP/km), ahorro y km extra", (248.8, 70600, 283.71),
         (round(u["cop_por_km"], 1), u["ahorro_peaje_cop"],
          round(u["km_extra"], 2)))
umbrales = {}
for nombre, gv in (("piso", g), ("sin_piso", sin_piso),
                   ("progresivas", construir_grafo(
                       reemplazos={("Chocontá", "Tunja"): 61.0}))):
    umbrales[nombre] = umbral_exacto(
        gv, "Duitama", "Puente Nacional")["cop_por_km"]
chequear("umbrales derivados de los datos: con piso, sin piso y progresivas",
         (248.8, 204.5, 252.4), tuple(round(x, 1) for x in umbrales.values()))
chequear("combustible contra cada umbral (veces)", (4.6, 5.7, 4.6), tuple(
    round(por_km / x, 1) for x in umbrales.values()))
texto_dinero = leer("outputs/texto_c2_dinero.tex")
chequear("dinero: la frase se incluye desde outputs/", True,
         r"\input{outputs/texto_c2_dinero.tex}" in leer("informe_corte2.tex"))
citas("texto del dinero", texto_dinero, [
    ("ahorro", "70\\,600"), ("combustible", "1\\,157.0")])
citas("tabla del umbral de costo", leer("outputs/tabla_r_umbral_costo.tex"),
      [("con piso", "283.71 & 70\\,600 & 248.8 & 4.6"),
       ("sin piso", "345.15 & 70\\,600 & 204.5 & 5.7"),
       ("progresivas", "279.67 & 70\\,600 & 252.4 & 4.6")])
citas("tabla de tiempos", leer("outputs/tabla_r_tiempos.tex"),
      [("Held-Karp", "1.12 a 1.19"), ("memoria", "111.8")])
citas("tabla de pruebas del ciclo", leer("outputs/tabla_r_pruebas_ciclo.tex"),
      [("sin corregir sin bloqueo", "456.93"),
       ("sin corregir bloqueado", "668.14")])
citas("Corte 2", c2, [("combustible", "1\\,157.0"), ("precio", "11\\,320"),
                      ("rendimiento", "9.784"), ("consumo", "38.69"),
                      ("progresivas", "61.0"), ("hueco", "49.1")])

# ---- 11. Corte 1: frases narrativas ----------------------------------------
vigentes = {("Bogotá", 370.54), ("Santander", 654.25)}
sin_corregir = {("Bogotá", 456.93), ("Santander", 668.14)}
sin_piso_km = {("Bogotá", 309.10)}
for mm in re.finditer(r"(\d+\.\d+) km por (Bogotá|Santander)", c1):
    valor, via = float(mm.group(1)), mm.group(2)
    ctx = c1[max(0, mm.start() - 150):mm.end() + 150]
    ok = ((via, valor) in vigentes
          or ((via, valor) in sin_corregir and "sin corregir" in ctx)
          or ((via, valor) in sin_piso_km
              and ("oficial" in ctx or "sin piso" in ctx)))
    chequear(f"Corte 1: «{mm.group(0)}» es vigente o dice «sin corregir»",
             True, ok)
for mm in re.finditer(r"456\.9\d?|668\.1\d?", c1):
    ctx = c1[max(0, mm.start() - 600):mm.end() + 200].lower()
    chequear(f"Corte 1: cifra sin corregir {mm.group(0)} rotulada", True,
             "sin corregir" in ctx)
mm = re.search(r"tiene (\d+) ciudades y (\d+) tramos", c1)
chequear("Corte 1: ciudades y tramos de la red", (32, 32),
         (int(mm.group(1)), int(mm.group(2))))
con = 32 - sin_riesgo
mm = re.search(r"Solo (\d+) de las (\d+) aristas tienen dato", c1)
chequear("Corte 1: aristas con dato de riesgo", (con, 32),
         (int(mm.group(1)), int(mm.group(2))))
mm = re.search(r"(\d+) de las (\d+) aristas no tienen dato", c1)
chequear("Corte 1: aristas sin dato de riesgo", (32 - con, 32),
         (int(mm.group(1)), int(mm.group(2))))
mm = re.search(r"La red pasó de (\d+) a (\d+) nodos y de (\d+) a (\d+)", c1)
chequear("Corte 1: la red pasó a 32 nodos y 32 aristas", (32, 32),
         (int(mm.group(2)), int(mm.group(4))))
mm = re.search(r"En (\d+) registros la longitud registrada", c1)
chequear("Corte 1: registros de doble calzada corregidos", 9,
         int(mm.group(1)))
ruta_b = nx.shortest_path(g, "Duitama", "Puente Nacional",
                          weight="distancia_km")
ruta_s = nx.shortest_path(h, "Duitama", "Puente Nacional",
                          weight="distancia_km")


def peaje(ruta):
    return sum(g[a][b]["peaje_cop_camion"] or 0
               for a, b in zip(ruta, ruta[1:]))


mm = re.search(r"El desvío es ([\d.]+) km más largo, pero tiene ([\d\\,]+) "
               r"COP menos de\s+peaje", c1)
chequear("Corte 1: desvío más largo (km) y menos peaje (COP)", (283.71, 70600),
         (float(mm.group(1)), int(mm.group(2).replace("\\,", ""))))
chequear("Corte 1: desvío calculado desde el grafo", (283.71, 70600),
         (round(d_desv - d_corta, 2), peaje(ruta_b) - peaje(ruta_s)), 0.005)
citas("Corte 1", c1, [
    ("costo en Bogotá", "599\\,510"), ("combustible en Bogotá", "428\\,710"),
    ("costo en Santander", "857\\,165"),
    ("combustible en Santander", "756\\,965"), ("umbral", "248.8"),
    ("umbral sin piso", "204.5"), ("umbral progresivas", "252.4"),
    ("combustible por km", "1\\,157.0"), ("truncada", "marcado como truncado"),
    ("8 aristas", "8 aristas con la carretera"), ("precio", "11\\,320"),
    ("consumo", "38.69"), ("regla", "razón entre la longitud de la geometría"),
    ("hueco", "49.1"), ("piso", "piso geodésico"),
    ("Chocontá", "56.96 km"), ("tabla del piso", "tab:piso")])

# ---- 12. Guion de la demostración ------------------------------------------
citas("guion", guion, [
    ("ruta por Bogotá", "370.54"), ("sin piso", "309.10"),
    ("alfa sin piso", "0.310570"), ("violaciones", "66 violaciones"),
    ("barrido", "17 de 66"), ("umbral del barrido", "0.4576"),
    ("DFS", "613.25 km contra 411.54 km"), ("umbral", "248.8"),
    ("combustible", "428 710"), ("total Bogotá", "599 510"),
    ("total Santander", "857 165"), ("margen del agente", "4.7 %"),
    ("ida y vuelta", "1024.79"), ("margen 1", "496.9 %"),
    ("margen 2", "15 800.1 %"), ("margen 3", "603.4 %"),
    ("margen mínimo", "1.2 %"), ("piso", "piso geodésico")])
chequear("guion: sin cifras del estado anterior", 0, sum(
    guion.count(x) for x in ("963.35", "11.9 %", "528 428", "570.3 %",
                             "20 480.8 %", "578.0 %", "0.000023 km",
                             "357 628")))
patron = re.compile(r"```\n(python src/.*?)```", re.S)


def correr(comando):
    return subprocess.run(
        [sys.executable, "-B"] + shlex.split(comando)[1:], cwd=RAIZ,
        capture_output=True, encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})


for bloque in patron.findall(guion):
    lineas = bloque.rstrip("\n").split("\n")
    if len(lineas) > 1 and lineas[1] == "":
        comando, esperado = lineas[0], [x.rstrip() for x in lineas[2:]
                                        if x.strip()]
        corrida = correr(comando)
        real = [x.rstrip() for x in corrida.stdout.strip().splitlines()
                if x.strip()]
        chequear(f"guion: salida de «{comando}» igual a la real", True,
                 corrida.returncode == 0 and real == esperado)
        continue
    for comando in lineas:
        archivo = shlex.split(comando)[1]
        if archivo.endswith(("agente_rutas.py", "demostracion.py",
                             "agente.py", "heuristica.py")):
            chequear(f"guion: «{comando}» termina sin error", 0,
                     correr(comando).returncode)

# ---- 13. Conclusiones del Corte 2 y palabras prohibidas --------------------
from lecturas_informe import costos_sin_riesgo as _csr  # noqa: E402
_c, _k = _csr("cruda"), _csr("corregida")
chequear("conclusión: sin corregir (Bogotá 3.415, desvío 3.197)",
         (3.415, 3.197), (round(_c[0], 3), round(_c[1], 3)))
chequear("conclusión: corregidas (Bogotá 3.367, desvío 3.524)",
         (3.367, 3.524), (round(_k[0], 3), round(_k[1], 3)))
informe2 = leer("informe_corte2.tex")
informe1 = leer("formulacion_corte1.tex")
chequear("sin PSO en los informes", 0,
         len(re.findall("PSO", informe1 + informe2)))
chequear("sin «Anexo» en los informes ni en el guion", 0,
         len(re.findall("Anexo", informe1 + informe2 + guion)))
chequear("«taller» solo en la frase de la referencia [aco]", 0, len(
    re.findall(r"(?i)taller", re.sub(
        r"\\bibitem\{aco\}.*?\n\n", "", informe2, flags=re.S) + informe1)))
chequear("Corte 1 sin vocabulario del Corte 2", 0, len(re.findall(
    r"(?i)heur[ií]stic|algoritm|\bA\*|Held|\bACO\b|despachador|Corte 2",
    informe1)))

malos = [f for f in filas if not f[0]]
for ok, texto, esp, real in filas:
    print(("OK    " if ok else "FALLA ")
          + f"{texto}: texto={esp} | datos={real}")
print(f"\n{len(filas)} cifras verificadas, {len(malos)} discrepancias")
sys.exit(1 if malos else 0)
