"""Validación del agente multifuncional.

a. Red de carga, orden libre con regreso (tipo d), criterio distancia:
   n = 5, 10, 15 y 20 ciudades (origen incluido; k = n - 1 paradas libres)
   con 3 instancias por n elegidas con semilla fija, y todas las ciudades
   (n = 32). Exacto: Held-Karp (cuando k <= K_EXACTO); ACO + 2-opt con 10
   semillas.
   Para las 32 ciudades no hay Held-Karp; se reporta además el óptimo por
   estructura (red unicíclica): 2 (W - C) + min(C, 2 (C - w_max)), con W la
   suma de todas las aristas, C la longitud del ciclo y w_max su arista más
   larga (todo ramal se recorre dos veces; el ciclo, una vez o todo menos su
   arista mayor, dos veces).
b. Instancias euclidianas de n = 20 del taller de ACO (semillas 1 a 5, mismo
   generador xorshift64): se compara el Held-Karp de este proyecto con el
   óptimo exacto que el taller calculó (outputs de ACO_IA) y se mide la
   brecha del ACO.
c. Instancias euclidianas mayores (n = 100 y 200) sin óptimo exacto; la
   referencia se rotula "mejor encontrada con 2-opt" (2-opt desde el vecino
   más cercano y desde inicios aleatorios), nunca óptimo.

El ACO usa inicio aleatorio por hormiga en modo ciclo; para las instancias
de la red y del taller se registra además el ACO sin 2-opt con inicio fijo
(aco_sin_2opt_inicio_fijo), el comportamiento anterior.

Por instancia: costo medio y mejor del ACO, brecha, tiempo (sin tracemalloc),
memoria pico (corrida aparte) y curva de convergencia. Escribe
outputs/validacion_agente.json, outputs/convergencia_aco.csv y
outputs/validacion_agente.csv.
"""
import csv
import json
import random
import statistics
import time
import tracemalloc
from math import hypot

import networkx as nx
import numpy as np

from aco_multiparada import SEMILLAS, aco, aco_semillas, dos_opt, \
    vecino_mas_cercano
from build_graph import SALIDA, cargar_grafo
from despachador import Despachador, Solicitud, cargar_medicion_umbral
from held_karp import held_karp
from heuristica import cargar_coordenadas
from matriz_costos import MatrizCostos

SEMILLA_INSTANCIAS = 20261020
KS_RED = (5, 10, 15, 20)
INSTANCIAS_POR_K = 3
SEMILLAS_TALLER = (1, 2, 3, 4, 5)
TAMANOS_MAYORES = (100, 200)
INICIOS_2OPT = {100: 300, 200: 150}
TALLER = "D:/camilo/Documentos/ACO_IA/resultados/instancia_n20.csv"
MASK = (1 << 64) - 1


# ---- instancias euclidianas del taller (generador xorshift64) -------------
class Xorshift:
    """Réplica de Rng de aco_tsp.cpp: xorshift64 con la misma semilla."""

    def __init__(self, semilla):
        self.s = (semilla * 0x9E3779B97F4A7C15 + 0x1234567) & MASK
        self.siguiente()
        self.siguiente()

    def siguiente(self):
        s = self.s
        s ^= (s << 13) & MASK
        s ^= s >> 7
        s ^= (s << 17) & MASK
        self.s = s
        return s

    def uniforme(self):
        return (self.siguiente() >> 40) / 16777216.0


def instancia_taller(n, semilla):
    """n puntos en [0, 1)^2, como `--n N --seed S` del taller."""
    azar = Xorshift(semilla * 7919 + 13)
    puntos = []
    for _ in range(n):
        x = azar.uniforme()
        y = azar.uniforme()
        puntos.append((x, y))
    return puntos


def matriz_euclidiana(puntos):
    return np.array([[hypot(a[0] - b[0], a[1] - b[1]) for b in puntos]
                     for a in puntos])


# ---- medidas ---------------------------------------------------------------
def medir_exacto(matriz):
    """Held-Karp en modo ciclo: costo, tiempo (s) y memoria pico (MiB)."""
    inicio = time.perf_counter()
    costo, orden = held_karp(matriz, 0, "ciclo")
    tiempo = time.perf_counter() - inicio
    tracemalloc.start()
    held_karp(matriz, 0, "ciclo")
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"costo": costo, "orden": orden, "tiempo_s": tiempo,
            "memoria_pico_mib": pico / 2 ** 20}


def medir_aco(matriz, referencia, busqueda_local=True,
              inicio_aleatorio=True):
    """ACO con 10 semillas: costos, brechas, tiempo, memoria y curva."""
    resumen = aco_semillas(matriz, 0, "ciclo", semillas=SEMILLAS,
                           busqueda_local=busqueda_local,
                           inicio_aleatorio=inicio_aleatorio)
    tiempos = [r["tiempo_s"] for r in resumen["corridas"]]
    tracemalloc.start()
    aco(matriz, 0, "ciclo", semilla=SEMILLAS[0],
        busqueda_local=busqueda_local, inicio_aleatorio=inicio_aleatorio)
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    costos = [r["costo"] for r in resumen["corridas"]]
    return {
        "semillas": list(SEMILLAS),
        "costos": costos,
        "costo_mejor": resumen["costo_mejor"],
        "costo_medio": resumen["costo_medio"],
        "costo_peor": resumen["costo_peor"],
        "desviacion": resumen["desviacion"],
        "brecha_mejor_pct": 100 * (resumen["costo_mejor"] - referencia)
        / referencia,
        "brecha_media_pct": 100 * (resumen["costo_medio"] - referencia)
        / referencia,
        "semillas_que_igualan_referencia": sum(
            1 for c in costos if abs(c - referencia) < 1e-9),
        "tiempo_medio_s": statistics.mean(tiempos),
        "tiempo_desv_s": statistics.pstdev(tiempos),
        "memoria_pico_kib": pico / 1024,
        "curva_media": resumen["curva_media"],
    }


def mejor_con_2opt(matriz, inicios, semilla):
    """Mejor costo hallado con 2-opt desde el vecino más cercano y desde
    `inicios` permutaciones aleatorias. NO es un óptimo."""
    n = len(matriz)
    azar = random.Random(semilla)
    _, mejor = dos_opt(matriz, vecino_mas_cercano(matriz, 0, "ciclo", None),
                       "ciclo")
    for _ in range(inicios):
        medio = list(range(1, n))
        azar.shuffle(medio)
        _, costo = dos_opt(matriz, [0, *medio], "ciclo")
        mejor = min(mejor, costo)
    return mejor


def optimo_unicicilo(grafo, atributo):
    """Óptimo del recorrido cerrado que visita todos los nodos de un grafo
    conexo con un solo ciclo (ver el docstring del módulo)."""
    total = sum(d[atributo] for _, _, d in grafo.edges(data=True))
    ciclos = nx.cycle_basis(grafo)
    if len(ciclos) != 1:
        raise ValueError("El grafo debe tener un único ciclo")
    ciclo = ciclos[0]
    pesos = [grafo[a][b][atributo]
             for a, b in zip(ciclo, ciclo[1:] + ciclo[:1])]
    c, mayor = sum(pesos), max(pesos)
    return 2 * (total - c) + min(c, 2 * (c - mayor))


# ---- validaciones ----------------------------------------------------------
def validar_red(grafo, coordenadas, despachador):
    ciudades = sorted(grafo.nodes)
    k_exacto = cargar_medicion_umbral()["k_exacto"]
    instancias = []
    pedidos = [(k, i) for k in KS_RED for i in range(INSTANCIAS_POR_K)]
    pedidos.append((len(ciudades), 0))
    for k, i in pedidos:
        if k == len(ciudades):
            seleccion = ["Bogotá"] + [c for c in ciudades if c != "Bogotá"]
        else:
            azar = random.Random(SEMILLA_INSTANCIAS + 100 * k + i)
            seleccion = azar.sample(ciudades, k)
        matriz = MatrizCostos(grafo, seleccion, "distancia_km")
        costos = matriz.costo
        libres = k - 1
        solicitud = Solicitud("d", seleccion[0], paradas=tuple(seleccion[1:]))
        t0 = time.perf_counter()
        respuesta = despachador.resolver(solicitud)
        t_desp = time.perf_counter() - t0
        registro = {
            "familia": "red de carga", "n": k, "instancia": i + 1,
            "origen": seleccion[0], "paradas_libres": libres,
            "despachador_metodo": respuesta["metodo"],
            "despachador_costo": respuesta["costo"],
            "despachador_tiempo_s": t_desp,
        }
        if libres <= k_exacto:
            exacto = medir_exacto(costos)
            registro["exacto"] = {k2: v for k2, v in exacto.items()
                                  if k2 != "orden"}
            referencia = exacto["costo"]
            registro["referencia"] = {"tipo": "óptimo exacto (Held-Karp)",
                                      "costo": referencia}
        else:
            referencia = optimo_unicicilo(grafo, "distancia_km")
            registro["referencia"] = {
                "tipo": "óptimo por estructura de la red unicíclica",
                "costo": referencia,
                "mejor_con_2opt": mejor_con_2opt(
                    costos, 200, SEMILLA_INSTANCIAS)}
        registro["aco"] = medir_aco(costos, referencia)
        registro["aco_sin_2opt"] = medir_aco(costos, referencia, False)
        registro["aco_sin_2opt_inicio_fijo"] = medir_aco(
            costos, referencia, False, inicio_aleatorio=False)
        instancias.append(registro)
        print(f"  red n={k:2d} #{i + 1}: ref {referencia:9.3f} "
              f"ACO mejor {registro['aco']['costo_mejor']:9.3f} "
              f"media {registro['aco']['costo_medio']:9.3f} "
              f"({registro['despachador_metodo']})")
    return instancias


def validar_taller():
    valores = {}
    with open(TALLER, encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            valores[int(fila["seed"])] = float(fila["optimo_exacto"])
    instancias = []
    for semilla in SEMILLAS_TALLER:
        matriz = matriz_euclidiana(instancia_taller(20, semilla))
        exacto = medir_exacto(matriz)
        referencia = exacto["costo"]
        registro = {
            "familia": "euclidiana n=20 del taller", "n": 20,
            "instancia": semilla, "paradas_libres": 19,
            "exacto": {k2: v for k2, v in exacto.items() if k2 != "orden"},
            "optimo_del_taller": valores[semilla],
            "coincide_con_el_taller": abs(referencia - valores[semilla])
            < 5e-6,
            "referencia": {"tipo": "óptimo exacto (Held-Karp)",
                           "costo": referencia},
            "aco": medir_aco(matriz, referencia),
            "aco_sin_2opt": medir_aco(matriz, referencia, False),
            "aco_sin_2opt_inicio_fijo": medir_aco(
                matriz, referencia, False, inicio_aleatorio=False),
        }
        instancias.append(registro)
        print(f"  taller semilla {semilla}: Held-Karp {referencia:.5f} "
              f"taller {valores[semilla]:.5f} "
              f"coincide={registro['coincide_con_el_taller']} | ACO mejor "
              f"{registro['aco']['costo_mejor']:.5f} media "
              f"{registro['aco']['costo_medio']:.5f}")
    return instancias


def validar_mayores():
    instancias = []
    for n in TAMANOS_MAYORES:
        matriz = matriz_euclidiana(instancia_taller(n, 1))
        t0 = time.perf_counter()
        referencia = mejor_con_2opt(matriz, INICIOS_2OPT[n],
                                    SEMILLA_INSTANCIAS)
        t_ref = time.perf_counter() - t0
        registro = {
            "familia": "euclidiana mayor (sin óptimo exacto)", "n": n,
            "instancia": 1, "paradas_libres": n - 1,
            "referencia": {"tipo": "mejor encontrada con 2-opt",
                           "inicios": INICIOS_2OPT[n] + 1,
                           "costo": referencia, "tiempo_s": t_ref},
            "aco": medir_aco(matriz, referencia),
            "aco_sin_2opt": medir_aco(matriz, referencia, False),
        }
        instancias.append(registro)
        print(f"  euclidiana n={n}: mejor con 2-opt {referencia:.4f} | ACO "
              f"mejor {registro['aco']['costo_mejor']:.4f} media "
              f"{registro['aco']['costo_medio']:.4f}")
    return instancias


def escribir_csv(instancias):
    with open(SALIDA / "convergencia_aco.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["familia", "n", "instancia", "iteracion",
                    "costo_medio_mejor_global", "brecha_pct"])
        for r in instancias:
            ref = r["referencia"]["costo"]
            for it, c in enumerate(r["aco"]["curva_media"], start=1):
                w.writerow([r["familia"], r["n"], r["instancia"], it,
                            f"{c:.6f}", f"{100 * (c - ref) / ref:.4f}"])
    with open(SALIDA / "validacion_agente.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["familia", "n", "instancia", "referencia_tipo",
                    "referencia", "aco_mejor", "aco_medio", "aco_peor",
                    "brecha_mejor_pct", "brecha_media_pct",
                    "semillas_que_igualan", "tiempo_aco_medio_s",
                    "tiempo_aco_desv_s", "memoria_aco_kib",
                    "tiempo_exacto_s", "memoria_exacto_mib",
                    "sin_2opt_brecha_media_pct", "sin_2opt_igualan",
                    "sin_2opt_inicio_fijo_brecha_media_pct",
                    "sin_2opt_inicio_fijo_igualan"])
        for r in instancias:
            a, e = r["aco"], r.get("exacto", {})
            w.writerow([
                r["familia"], r["n"], r["instancia"], r["referencia"]["tipo"],
                f"{r['referencia']['costo']:.5f}",
                f"{a['costo_mejor']:.5f}", f"{a['costo_medio']:.5f}",
                f"{a['costo_peor']:.5f}", f"{a['brecha_mejor_pct']:.3f}",
                f"{a['brecha_media_pct']:.3f}",
                a["semillas_que_igualan_referencia"],
                f"{a['tiempo_medio_s']:.4f}", f"{a['tiempo_desv_s']:.4f}",
                f"{a['memoria_pico_kib']:.1f}",
                f"{e['tiempo_s']:.4f}" if e else "",
                f"{e['memoria_pico_mib']:.1f}" if e else "",
                f"{r['aco_sin_2opt']['brecha_media_pct']:.3f}"
                if "aco_sin_2opt" in r else "",
                r["aco_sin_2opt"]["semillas_que_igualan_referencia"]
                if "aco_sin_2opt" in r else "",
                f"{r['aco_sin_2opt_inicio_fijo']['brecha_media_pct']:.3f}"
                if "aco_sin_2opt_inicio_fijo" in r else "",
                r["aco_sin_2opt_inicio_fijo"][
                    "semillas_que_igualan_referencia"]
                if "aco_sin_2opt_inicio_fijo" in r else ""])


def main():
    grafo = cargar_grafo()
    coordenadas = cargar_coordenadas()
    despachador = Despachador(grafo, coordenadas)
    print("Red de carga")
    red = validar_red(grafo, coordenadas, despachador)
    print("Instancias euclidianas del taller (n = 20)")
    taller = validar_taller()
    print("Instancias euclidianas mayores")
    mayores = validar_mayores()
    instancias = red + taller + mayores
    with open(SALIDA / "validacion_agente.json", "w",
              encoding="utf-8") as f:
        json.dump({"semillas_aco": list(SEMILLAS),
                   "k_exacto": cargar_medicion_umbral()["k_exacto"],
                   "instancias": instancias}, f, ensure_ascii=False,
                  indent=1)
    escribir_csv(instancias)
    print("Validación escrita en", SALIDA)


if __name__ == "__main__":
    main()
