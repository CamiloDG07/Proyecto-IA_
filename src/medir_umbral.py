"""Mide hasta qué k es viable Held-Karp en esta máquina y fija el umbral.

Para cada k (paradas libres) se resuelve una instancia euclidiana con semilla
fija en modo ciclo, varias veces (3 como mínimo; 5 hasta k = 16), sin
tracemalloc para el tiempo, y en corridas aparte con tracemalloc para la
memoria pico (3 corridas desde k = 20, una antes). Se reportan mediana y rango
del tiempo y la memoria pico máxima.

El umbral K_EXACTO es el más restrictivo de dos límites:
  - tiempo: mayor k cuyo tiempo mediano no supera PRESUPUESTO_S, con todos los
    k menores también dentro del presupuesto;
  - memoria: mayor k medido cuya memoria pico no supera LIMITE_MEMORIA, que es
    la fracción FRACCION_RAM de la memoria instalada.
El presupuesto de tiempo y la fracción de memoria son decisiones declaradas;
los umbrales son mediciones. No se extrapola más allá del mayor k medido.

Escribe outputs/umbral_held_karp.json, que lee despachador.py.
"""
import ctypes
import json
import os
import platform
import random
import statistics
import subprocess
import time
import tracemalloc
from datetime import date
from math import hypot

import numpy as np

from build_graph import SALIDA
from held_karp import held_karp

PRESUPUESTO_S = 5.0
FRACCION_RAM = 0.25
KS = [8, 10, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22]
PARO_S = 60.0
SEMILLA = 20261020


class _EstadoMemoria(ctypes.Structure):
    _fields_ = [("longitud", ctypes.c_ulong), ("carga", ctypes.c_ulong),
                ("total_fisica", ctypes.c_ulonglong),
                ("libre_fisica", ctypes.c_ulonglong),
                ("total_paginacion", ctypes.c_ulonglong),
                ("libre_paginacion", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("libre_virtual", ctypes.c_ulonglong),
                ("libre_extendida", ctypes.c_ulonglong)]


def memoria_instalada_gib():
    """Memoria física instalada (GiB), Windows."""
    estado = _EstadoMemoria()
    estado.longitud = ctypes.sizeof(_EstadoMemoria)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado))
    return estado.total_fisica / 2 ** 30


def nombre_procesador():
    try:
        salida = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Processor | Select-Object -First 1)"
             ".Name"], capture_output=True, text=True, timeout=30)
        nombre = salida.stdout.strip()
        return nombre or platform.processor()
    except (OSError, subprocess.SubprocessError):
        return platform.processor()


def instancia(k):
    azar = random.Random(SEMILLA + k)
    puntos = [(azar.random(), azar.random()) for _ in range(k + 1)]
    return np.array([[hypot(a[0] - b[0], a[1] - b[1]) for b in puntos]
                     for a in puntos])


def memoria_pico_mib(matriz):
    tracemalloc.start()
    held_karp(matriz, 0, "ciclo")
    _, pico = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return pico / 2 ** 20


def main():
    ram = memoria_instalada_gib()
    limite_mib = FRACCION_RAM * ram * 1024
    mediciones = []
    for k in KS:
        m = instancia(k)
        repeticiones = 5 if k <= 16 else 3
        tiempos = []
        for _ in range(repeticiones):
            inicio = time.perf_counter()
            held_karp(m, 0, "ciclo")
            tiempos.append(time.perf_counter() - inicio)
        memorias = [memoria_pico_mib(m)
                    for _ in range(3 if k >= 20 else 1)]
        fila = {"k": k, "repeticiones": repeticiones,
                "tiempos_s": tiempos,
                "mediana_s": statistics.median(tiempos),
                "minimo_s": min(tiempos), "maximo_s": max(tiempos),
                "corridas_de_memoria": len(memorias),
                "memorias_pico_mib": memorias,
                "memoria_pico_mib": max(memorias)}
        mediciones.append(fila)
        print(f"k={k:2d}  mediana {fila['mediana_s']:8.3f} s "
              f"[{fila['minimo_s']:.3f}, {fila['maximo_s']:.3f}]  "
              f"memoria {fila['memoria_pico_mib']:8.1f} MiB  "
              f"({repeticiones} rep.)", flush=True)
        if fila["mediana_s"] > PARO_S:
            break
    k_tiempo = 0
    for fila in mediciones:
        if fila["mediana_s"] <= PRESUPUESTO_S:
            k_tiempo = fila["k"]
        else:
            break
    k_memoria = max((f["k"] for f in mediciones
                     if f["memoria_pico_mib"] <= limite_mib), default=0)
    k_exacto = min(k_tiempo, k_memoria)
    salida = {
        "fecha": date.today().isoformat(),
        "presupuesto_s": PRESUPUESTO_S,
        "fraccion_ram": FRACCION_RAM,
        "limite_memoria_mib": limite_mib,
        "k_tiempo": k_tiempo,
        "k_memoria_medido": k_memoria,
        "k_exacto": k_exacto,
        "limitante": "tiempo" if k_tiempo <= k_memoria else "memoria",
        "criterio": "el más restrictivo entre el mayor k con tiempo mediano "
                    "<= presupuesto_s (con todos los k menores dentro) y el "
                    "mayor k medido con memoria pico <= limite_memoria_mib",
        "mediciones": mediciones,
        "maquina": {"python": platform.python_version(),
                    "numpy": np.__version__,
                    "procesador": nombre_procesador(),
                    "nucleos_logicos": os.cpu_count(),
                    "memoria_instalada_gib": ram,
                    "sistema": platform.platform()},
    }
    with open(SALIDA / "umbral_held_karp.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
    print(f"K_EXACTO = {k_exacto} (tiempo: {k_tiempo}, memoria medida: "
          f"{k_memoria}; límite de memoria {limite_mib:.0f} MiB)")


if __name__ == "__main__":
    main()
