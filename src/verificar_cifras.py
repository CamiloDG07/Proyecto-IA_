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
from itertools import permutations
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
chequear("ruta por Bogotá (km)", 309.10, round(d_corta, 2))
chequear("ruta por Santander (km)", 654.25, round(d_desv, 2))
ct = g["Chocontá"]["Tunja"]["distancia_km"]
ct_reg = g["Chocontá"]["Tunja"]["distancia_cruda_km"]
geo_ct = haversine_km(*co["Chocontá"], *co["Tunja"])
chequear("Chocontá-Tunja base: valor oficial registrado (km)", 17.69, ct)
chequear("Chocontá-Tunja registrada (km)", 17.69, ct_reg)
arista_ct = next(a for a in json.loads(leer("outputs/aristas_red.json"))
                 if (a["origen"], a["destino"]) == ("Chocontá", "Tunja"))
chequear("Chocontá-Tunja fuente y marca", ("registro", True), (
    arista_ct["distancia_fuente"], arista_ct["distancia_truncada"]))
chequear("Chocontá-Tunja diferencia de progresivas (km)", 61.0,
         arista_ct["distancia_progresivas_km"])
chequear("Chocontá-Tunja geodésica (km)", 56.96, round(geo_ct, 2))
chequear("razón Chocontá-Tunja base", 0.3106, round(ct / geo_ct, 4), 5e-5)
chequear("razón Chocontá-Tunja con progresivas", 1.071,
         round(61.0 / geo_ct, 3))
chequear("PR final de Chocontá a Tunja menos PR de Tocancipá-Chocontá",
         61.0, round(120.0 - 59.0, 1))
chequear("hueco de progresivas (km)", 49.1, round(108.096 - 59.0, 1), 0.05)
chequear("cota inferior de la ruta por Bogotá (km)", 348.37,
         round(d_corta - ct + round(geo_ct, 2), 2), 0.006)
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
chequear("distancia total de la red (km)", 1886.00, round(sum(
    d["distancia_km"] for _u, _v, d in g.edges(data=True)), 2), 0.005)
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
chequear("alfa", 0.31057, heur["alfa"], 1e-9)
chequear("razón mínima exacta", 0.3105704113,
         round(heur["razon_minima_exacta"], 10), 1e-10)
chequear("alfa_ref (sin Chocontá a Tunja)", 0.458156, sens["alfa_ref"],
         1e-9)
chequear("margen mínimo distancia (km)", 0.000023, round(
    heur["criterios"]["distancia"]["admisibilidad"]["margen_minimo"], 6),
    1e-9)
chequear("violaciones en todas las heurísticas", 0, sum(
    v["admisibilidad"]["violaciones"] + v["consistencia"]["violaciones"]
    for v in heur["criterios"].values()))
chequear("heurísticas verificadas", 7, len(heur["criterios"]))
p = heur["geodesica_pura_distancia"]
chequear("violaciones adm. alfa=1", 66, p["admisibilidad"]["violaciones"])
chequear("violaciones cons. alfa=1", 141, p["consistencia"]["violaciones"])
chequear("peor margen alfa=1", -56.51,
         round(p["admisibilidad"]["margen_minimo"], 2))
citas("Corte 2", c2, [("alfa", "0.310570"), ("alfa_ref", "0.458156"),
                      ("violaciones", "66 violaciones"),
                      ("peor margen", "$-56.51$")])

# ---- 4. Escenarios ---------------------------------------------------------
saltos = sorted({c["saltos"] for c in res if c["criterio"] == "distancia"
                 and c["algoritmo"] == "UCS" and c["rutas_simples"] == 1})
chequear("saltos de los pares de ruta única", [1, 2, 3, 4, 6], saltos)
chequear("repeticiones", 2000, res[0]["repeticiones"])
pre = [c["precalculo_h_media_s"] * 1e6 for c in res
       if c["precalculo_h_media_s"] is not None]
chequear("precálculo medio (us)", 35.3, round(sum(pre) / len(pre), 1), 0.05)
chequear("precálculo mínimo (us)", 6.5, round(min(pre), 1), 0.05)
chequear("precálculo máximo (us)", 51.5, round(max(pre), 1), 0.05)
chequear("máx desviación/media", 2.76, round(max(
    c["tiempo_desv_s"] / c["tiempo_media_s"] for c in res), 2), 0.005)


def cel(o, d, crit, alg):
    return next(c for c in res if c["origen"] == o and c["destino"] == d
                and c["criterio"] == crit and c["algoritmo"] == alg)


def exceso(o, d, crit, alg):
    return round(100 * cel(o, d, crit, alg)["exceso_relativo"], 1)


chequear("BFS exceso (%)", 111.7,
         exceso("Duitama", "Puente Nacional", "distancia", "BFS"), 0.05)
chequear("BFS saltos", 7,
         cel("Duitama", "Puente Nacional", "distancia", "BFS")["saltos"])
chequear("UCS saltos", 8,
         cel("Duitama", "Puente Nacional", "distancia", "UCS")["saltos"])
chequear("DFS Bucaramanga-Bogotá exceso (%)", 35.8,
         exceso("Bucaramanga", "Bogotá", "distancia", "DFS"), 0.05)
for crit, esperado in (
        ("distancia", {"BFS": 143, "DFS": 142, "UCS": 144, "Voraz": 50,
                       "A*": 120}),
        ("compuesto_sin_riesgo", {"BFS": 143, "DFS": 142, "UCS": 141,
                                  "Voraz": 50, "A*": 129})):
    real = {a: sum(c["nodos_expandidos"] for c in res
                   if c["criterio"] == crit and c["algoritmo"] == a)
            for a in esperado}
    chequear(f"expandidos totales {crit}", esperado, real)
a_ = cel("Duitama", "Puente Nacional", "distancia", "A*")
u_ = cel("Duitama", "Puente Nacional", "distancia", "UCS")
chequear("A* central media y desv (us)", (68, 21),
         (round(a_["tiempo_media_s"] * 1e6), round(a_["tiempo_desv_s"] * 1e6)),
         0.5)
chequear("UCS central media y desv (us)", (81, 18),
         (round(u_["tiempo_media_s"] * 1e6), round(u_["tiempo_desv_s"] * 1e6)),
         0.5)
chequear("expandidos centrales A*, UCS", (20, 25),
         (a_["nodos_expandidos"], u_["nodos_expandidos"]))
chequear("sin riesgo BFS exceso", 11.9, exceso(
    "Duitama", "Puente Nacional", "compuesto_sin_riesgo", "BFS"), 0.05)
chequear("sin riesgo DFS Buc-Bog exceso", 2.8, exceso(
    "Bucaramanga", "Bogotá", "compuesto_sin_riesgo", "DFS"), 0.05)
citas("Corte 2", c2, [("exceso BFS", "111.7"), ("exceso DFS", "35.8"),
                      ("precálculo", "35.3"), ("desviación", "2.76"),
                      ("sin riesgo", "11.9"), ("sin riesgo DFS", "2.8"),
                      ("totales A* y UCS", "UCS 144, voraz 50 y A* 120")])

# ---- 5. Barrido de pesos ---------------------------------------------------
b0, b1 = bar[0], bar[1]
chequear("puntos", 66, len(b0["puntos"]))
chequear("Bogotá gana (compuesto) base", 19, b0["ganan_bogota_compuesto"])
chequear("umbral w1 base", 0.4095,
         round(b0["w1_umbral_sobre_w3_cero"], 4), 5e-5)
chequear("sin riesgo base", 37, b0["ganan_bogota_sin_riesgo"])
chequear("sin riesgo definidos", 65, b0["puntos_sin_riesgo_definidos"])
chequear("umbral w1 con la cota inferior", 0.4389,
         round(b1["w1_umbral_sobre_w3_cero"], 4), 5e-5)
chequear("Bogotá gana (compuesto) con la cota inferior", 17,
         b1["ganan_bogota_compuesto"])
b3 = bar[3]
chequear("barrido con las progresivas: umbral, Bogotá y sin riesgo",
         (0.4422, 17, 36), (round(b3["w1_umbral_sobre_w3_cero"], 4),
                            b3["ganan_bogota_compuesto"],
                            b3["ganan_bogota_sin_riesgo"]))
cambia = [(f["w1"], f["w2"], f["w3"]) for f, k in zip(
    b0["puntos"], b1["puntos"]) if f["compuesto"] != k["compuesto"]]
chequear("puntos que cambian (compuesto)",
         [(0.5, 0.2, 0.3), (0.5, 0.3, 0.2)], cambia)
cambia2 = [(f["w1"], f["w2"], f["w3"]) for f, k in zip(
    b0["puntos"], b1["puntos"]) if f["sin_riesgo"] != k["sin_riesgo"]]
chequear("puntos que cambian (sin riesgo)", [(0.3, 0.4, 0.3)], cambia2)
citas("Corte 2", c2, [("umbral base", "0.4095"), ("umbral cota", "0.4389"),
                      ("umbral progresivas", "0.4422"),
                      ("sin riesgo", "37 de 65")])

# ---- 6. Sensibilidad de A* -------------------------------------------------
chequear("alfa base", 0.31057, sens["alfa_base"], 1e-9)
e0 = next(e for e in sens["por_escenario"] if e["origen"] == "Duitama")
chequear("central alfa_ref, base, UCS", (17, 20, 25),
         (e0["expandidos_alfa_ref"], e0["expandidos_alfa_base"],
          e0["expandidos_ucs"]))
t = sens["todos_los_pares"]
chequear("pares óptimos con alfa_ref", 991, t["pares"] - t["no_optimos"])
d0 = t["detalle_no_optimos"][0]
chequear("par no óptimo con alfa_ref", ("Bucaramanga", "Tunja", 482.01,
                                        481.34),
         (d0["origen"], d0["destino"], round(d0["costo"], 2),
          round(d0["costo_optimo"], 2)))
chequear("exceso del par no óptimo (%)", 0.14, round(
    100 * (d0["costo"] - d0["costo_optimo"]) / d0["costo_optimo"], 2), 0.005)
chequear("totales UCS, alfa base, alfa_ref", (15872, 13377, 12223),
         (t["expandidos_total_ucs"], t["expandidos_total_alfa_base"],
          t["expandidos_total_alfa_ref"]))
chequear("A* contra UCS en distancia (120 y 144)", (120, 144), (sum(
    c["nodos_expandidos"] for c in res
    if c["criterio"] == "distancia" and c["algoritmo"] == "A*"), sum(
    c["nodos_expandidos"] for c in res
    if c["criterio"] == "distancia" and c["algoritmo"] == "UCS")))

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
chequear("óptimo por estructura con 32 ciudades", 2808.65,
         round(r32["referencia"]["costo"], 2), 0.005)
chequear("32 ciudades: 10 de 10", 10,
         r32["aco"]["semillas_que_igualan_referencia"])


def grupo(clave, ms):
    return (round(sum(r[clave]["brecha_media_pct"] for r in ms) / len(ms), 3),
            sum(r[clave]["semillas_que_igualan_referencia"] for r in ms))


def de_red(n):
    return [r for r in red if r["n"] == n]


chequear("inicio fijo n=15", (2.608, 20),
         grupo("aco_sin_2opt_inicio_fijo", de_red(15)))
chequear("inicio fijo n=20", (2.836, 13),
         grupo("aco_sin_2opt_inicio_fijo", de_red(20)))
chequear("inicio aleatorio sin 2-opt en la red (brecha, semillas)", (0, 130),
         (sum(grupo("aco_sin_2opt", de_red(n))[0]
              for n in (5, 10, 15, 20, 32)),
          sum(grupo("aco_sin_2opt", de_red(n))[1]
              for n in (5, 10, 15, 20, 32))))
chequear("con 2-opt 120/120 en las instancias con exacto", 120, sum(
    r["aco"]["semillas_que_igualan_referencia"] for r in con_ex))
chequear("brecha de la iteración 1 en la red (máx., %)", 0.029, round(max(
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
chequear("Held-Karp n=20, tiempos mín y máx (s)", (1.05, 1.12),
         (round(min(hk), 2), round(max(hk), 2)))
chequear("Held-Karp n=20, memoria (MiB)", 111.8,
         round(red[9]["exacto"]["memoria_pico_mib"], 1), 0.05)
at = [r["aco"]["tiempo_medio_s"] for r in red + tal if r["n"] == 20]
chequear("ACO n=20, tiempos mín y máx (s)", (0.06, 0.06),
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
chequear("n=100: tiempo del ACO", (1.0, 0.01), (
    round(may[0]["aco"]["tiempo_medio_s"], 2),
    round(may[0]["aco"]["tiempo_desv_s"], 2)))
chequear("n=100 sin 2-opt", (0.85, 0.02, 5.599), (
    round(may[0]["aco_sin_2opt"]["tiempo_medio_s"], 2),
    round(may[0]["aco_sin_2opt"]["tiempo_desv_s"], 2),
    round(may[0]["aco_sin_2opt"]["brecha_media_pct"], 3)))
chequear("n=200 sin 2-opt", (4.67, 0.18, 6.209), (
    round(may[1]["aco_sin_2opt"]["tiempo_medio_s"], 2),
    round(may[1]["aco_sin_2opt"]["tiempo_desv_s"], 2),
    round(may[1]["aco_sin_2opt"]["brecha_media_pct"], 3)))
chequear("n=200: tiempo y memoria", (5.92, 0.23, 5391), (
    round(may[1]["aco"]["tiempo_medio_s"], 2),
    round(may[1]["aco"]["tiempo_desv_s"], 2),
    round(may[1]["aco"]["memoria_pico_kib"])))
chequear("inicios de 2-opt", (301, 151), (
    may[0]["referencia"]["inicios"], may[1]["referencia"]["inicios"]))
citas("Corte 2", c2, [("óptimo 32", "2808.65"), ("inicio fijo n=15", "2.608"),
                      ("inicio fijo n=20", "2.836"),
                      ("Held-Karp", "entre 1.05 s y 1.12 s"),
                      ("n=200", "5.92"), ("n=100 sin 2-opt", "0.85")])

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
chequear("texto del perfil cita 385, 111, 374, 105, 17 y 10", True, all(
    x in tex_perfil for x in ("385", "111", "374", "105", "17", "10 puntos")))
r_iv = recomendar("Duitama", ["Puente Nacional"], True,
                  bloquear_regreso="Tunja-Chocontá", grafo=g)
chequear("ida y vuelta con bloqueo: margen del regreso (%)", 11.9,
         round(r_iv["detalle_regreso"]["margen_pct"], 1), 0.05)
chequear("ida y vuelta con bloqueo: total km", 963.35,
         round(r_iv["total"]["km"], 2), 0.005)
chequear("ida y vuelta con bloqueo: total peaje", 271000,
         round(r_iv["total"]["peaje_cop"]))
for o, d, esp in (("Chiquinquirá", "Chocontá", 570.3),
                  ("Cajicá", "Zipaquirá", 20480.8),
                  ("Duitama", "Presidente", 578.0)):
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
         (357628, 528428), (round(rb["costo_variable_cop"]),
                            round(rb["costo_operativo_cop"])))
rs = next(a for a in rec["alternativas"])
chequear("ruta por Santander: combustible y costo operativo (COP)",
         (756965, 857165), (round(rs["costo_variable_cop"]),
                            round(rs["costo_operativo_cop"])))
chequear("criterio por defecto con un insumo supuesto",
         "compuesto_sin_riesgo", rec["criterio_efectivo"])
u = rec["umbral_costo"]
chequear("umbral exacto (COP/km), ahorro y km extra", (204.5, 70600, 345.15),
         (round(u["cop_por_km"], 1), u["ahorro_peaje_cop"], u["km_extra"]))
umbrales = {}
for nombre, km in (("base", None), ("cota", 56.96), ("progresivas", 61.0)):
    gv = g if km is None else construir_grafo(
        reemplazos={("Chocontá", "Tunja"): km})
    umbrales[nombre] = round(umbral_exacto(
        gv, "Duitama", "Puente Nacional")["cop_por_km"], 1)
chequear("umbrales derivados de los datos: base, cota y progresivas",
         (204.5, 230.8, 233.9), tuple(umbrales.values()))
chequear("combustible contra cada umbral (veces)", (5.7, 5.0, 4.9), tuple(
    round(por_km / x, 1) for x in umbrales.values()))
texto_dinero = leer("outputs/texto_c2_dinero.tex")
chequear("dinero: la frase se incluye desde outputs/", True,
         r"\input{outputs/texto_c2_dinero.tex}" in leer("informe_corte2.tex"))
citas("texto del dinero", texto_dinero, [
    ("ahorro", "70\\,600"), ("km extra", "345.15"),
    ("umbral base", "204.5"), ("cota", "230.8"), ("progresivas", "233.9"),
    ("combustible", "1\\,157.0"), ("veces", "5.7, 5.0, 4.9 veces")])
citas("Corte 2", c2, [("combustible", "1\\,157.0"), ("precio", "11\\,320"),
                      ("rendimiento", "9.784"), ("consumo", "38.69"),
                      ("progresivas", "61.0"), ("hueco", "49.1")])

# ---- 11. Corte 1: frases narrativas ----------------------------------------
vigentes = {("Bogotá", 309.10), ("Santander", 654.25)}
sin_corregir = {("Bogotá", 414.84), ("Santander", 668.14)}
for mm in re.finditer(r"(\d+\.\d+) km por (Bogotá|Santander)", c1):
    valor, via = float(mm.group(1)), mm.group(2)
    ctx = c1[max(0, mm.start() - 150):mm.end() + 150]
    ok = ((via, valor) in vigentes
          or ((via, valor) in sin_corregir and "sin corregir" in ctx))
    chequear(f"Corte 1: «{mm.group(0)}» es vigente o dice «sin corregir»",
             True, ok)
for mm in re.finditer(r"414\.8\d?|668\.1\d?", c1):
    ctx = c1[max(0, mm.start() - 200):mm.end() + 200]
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
chequear("Corte 1: desvío más largo (km) y menos peaje (COP)", (345.15, 70600),
         (float(mm.group(1)), int(mm.group(2).replace("\\,", ""))))
chequear("Corte 1: desvío calculado desde el grafo", (345.15, 70600),
         (round(d_desv - d_corta, 2), peaje(ruta_b) - peaje(ruta_s)), 0.005)
citas("Corte 1", c1, [
    ("costo en Bogotá", "528\\,428"), ("combustible en Bogotá", "357\\,628"),
    ("costo en Santander", "857\\,165"),
    ("combustible en Santander", "756\\,965"), ("umbral", "204.5"),
    ("umbral cota", "230.8"), ("umbral progresivas", "233.9"),
    ("combustible por km", "1\\,157.0"), ("truncada", "marcado como truncado"),
    ("ocho aristas", "Ocho aristas"), ("precio", "11\\,320"),
    ("consumo", "38.69"), ("regla", "razón entre la longitud de la geometría"),
    ("hueco", "49.1")])

# ---- 12. Guion de la demostración ------------------------------------------
citas("guion", guion, [
    ("ruta por Bogotá", "309.10"), ("alfa", "0.310570"),
    ("margen mínimo", "0.000023"), ("violaciones", "66 violaciones"),
    ("barrido", "19 de 66"), ("umbral del barrido", "0.4095"),
    ("DFS", "598.17 km contra 408.49 km"), ("umbral", "204.5"),
    ("combustible", "357 628"), ("total Bogotá", "528 428"),
    ("total Santander", "857 165"), ("margen del agente", "11.9 %"),
    ("ida y vuelta", "963.35"), ("margen 1", "570.3 %"),
    ("margen 2", "20 480.8 %"), ("margen 3", "578.0 %")])
chequear("guion: sin cifras del estado anterior", 0, sum(
    guion.count(x) for x in ("352.41", "1006.66", "483.0 %", "6.7 %",
                             "578 537", "0.4422")))
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
chequear("conclusión: sin corregir (Bogotá 3.290, desvío 3.197)",
         (3.290, 3.197), (round(_c[0], 3), round(_c[1], 3)))
chequear("conclusión: corregidas (Bogotá 3.149, desvío 3.524)",
         (3.149, 3.524), (round(_k[0], 3), round(_k[1], 3)))
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
