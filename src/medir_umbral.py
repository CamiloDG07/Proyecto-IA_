"""Mide hasta qué k es viable Held-Karp en esta máquina y fija el umbral.

Para cada k (paradas libres) se resuelve una instancia euclidiana con semilla
fija en modo ciclo, varias veces, sin tracemalloc para el tiempo y en una
corrida aparte con tracemalloc para la memoria pico. El umbral K_EXACTO es el
mayor k cuyo tiempo mediano no supera PRESUPUESTO_S, con todos los k menores
también dentro del presupuesto. El presupuesto es una decisión declarada
("tiempo útil" de una solicitud), no una medición; el umbral sí lo es.

Escribe outputs/umbral_held_karp.json, que lee despachador.py.
"""
import json
import os
import platform
import random
import statistics
import time
import tracemalloc
from datetime import date
from math import hypot

import numpy as np

from build_graph import SALIDA
from held_karp import held_karp

PRESUPUESTO_S = 5.0
KS = [8, 10, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22]
PARO_S = 60.0
SEMILLA = 20261020


def instancia(k):
    azar = random.Random(SEMILLA + k)
    puntos = [(azar.random(), azar.random()) for _ in range(k + 1)]
    return np.array([[hypot(a[0] - b[0], a[1] - b[1]) for b in puntos]
                     for a in puntos])


def main():
    mediciones = []
    for k in KS:
        m = instancia(k)
        repeticiones = 5 if k <= 16 else (3 if k <= 19 else 1)
        tiempos = []
        for _ in range(repeticiones):
            inicio = time.perf_counter()
            held_karp(m, 0, "ciclo")
            tiempos.append(time.perf_counter() - inicio)
        tracemalloc.start()
        held_karp(m, 0, "ciclo")
        _, pico = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        fila = {"k": k, "repeticiones": repeticiones,
                "tiempos_s": tiempos,
                "mediana_s": statistics.median(tiempos),
                "memoria_pico_mib": pico / 2 ** 20}
        mediciones.append(fila)
        print(f"k={k:2d}  mediana {fila['mediana_s']:8.3f} s  "
              f"memoria {fila['memoria_pico_mib']:8.1f} MiB  "
              f"({repeticiones} rep.)")
        if fila["mediana_s"] > PARO_S:
            break
    k_exacto = 0
    for fila in mediciones:
        if fila["mediana_s"] <= PRESUPUESTO_S:
            k_exacto = fila["k"]
        else:
            break
    salida = {
        "fecha": date.today().isoformat(),
        "presupuesto_s": PRESUPUESTO_S,
        "k_exacto": k_exacto,
        "criterio": "mayor k con tiempo mediano <= presupuesto_s, con todos "
                    "los k menores dentro del presupuesto",
        "mediciones": mediciones,
        "maquina": {"python": platform.python_version(),
                    "numpy": np.__version__,
                    "procesador": platform.processor(),
                    "hilos": os.cpu_count(),
                    "sistema": platform.platform()},
    }
    with open(SALIDA / "umbral_held_karp.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
    print(f"K_EXACTO = {k_exacto} (presupuesto {PRESUPUESTO_S} s)")


if __name__ == "__main__":
    main()
