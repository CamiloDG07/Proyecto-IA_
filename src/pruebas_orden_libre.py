"""Pruebas de Held-Karp y del ACO multiparada.

Held-Karp se compara con fuerza bruta (todas las permutaciones) en matrices
aleatorias, simétricas y asimétricas, para los tres modos. El ACO se prueba
en validez de los tours, reproducibilidad con semilla fija y brecha no
negativa respecto del exacto.
"""
import random
from itertools import permutations

import numpy as np

from aco_multiparada import aco, aco_semillas, costo_tour, dos_opt
from held_karp import costo_de_orden, held_karp

EPS = 1e-9


def verificar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)
    print(f"  ok: {mensaje}")


def matriz_aleatoria(n, semilla, simetrica):
    azar = random.Random(semilla)
    m = np.array([[0.0 if i == j else azar.uniform(1, 10)
                   for j in range(n)] for i in range(n)])
    if simetrica:
        m = np.triu(m) + np.triu(m, 1).T
    return m


def fuerza_bruta(m, inicio, modo, fin=None):
    n = len(m)
    libres = [i for i in range(n)
              if i != inicio and not (modo == "fijo" and i == fin)]
    mejor = float("inf")
    for perm in permutations(libres):
        orden = [inicio, *perm]
        if modo == "ciclo":
            orden.append(inicio)
        elif modo == "fijo":
            orden.append(fin)
        mejor = min(mejor, costo_de_orden(m, orden))
    return mejor


def prueba_held_karp():
    print("Held-Karp contra fuerza bruta")
    casos = 0
    for n in (2, 3, 4, 5, 6, 7, 8):
        for simetrica in (True, False):
            m = matriz_aleatoria(n, 100 * n + simetrica, simetrica)
            for modo in ("ciclo", "libre", "fijo"):
                if modo == "fijo" and n < 3:
                    continue
                fin = n - 1 if modo == "fijo" else None
                costo, orden = held_karp(m, 0, modo, fin)
                esperado = fuerza_bruta(m, 0, modo, fin)
                verificar(abs(costo - esperado) < EPS and abs(
                    costo_de_orden(m, orden) - costo) < EPS,
                    f"n={n} {'sim' if simetrica else 'asim'} {modo}: "
                    f"costo y orden coinciden con fuerza bruta")
                casos += 1
    print(f"  {casos} casos")


def tour_valido(orden, n, inicio, modo, fin):
    nodos = orden[:-1] if modo == "ciclo" else orden
    if modo == "ciclo" and orden[-1] != inicio:
        return False
    if modo == "fijo" and orden[-1] != fin:
        return False
    return (orden[0] == inicio and sorted(nodos) == list(range(n)))


def prueba_dos_opt():
    print("2-opt")
    for semilla in range(5):
        m = matriz_aleatoria(9, 300 + semilla, True)
        azar = random.Random(semilla)
        for modo, fin in (("ciclo", None), ("libre", None), ("fijo", 8)):
            medio = [i for i in range(1, 9) if i != fin]
            azar.shuffle(medio)
            tour = [0, *medio] + ([fin] if modo == "fijo" else [])
            antes = costo_tour(m, tour, modo)
            nuevo, costo = dos_opt(m, tour, modo)
            verificar(costo <= antes + EPS and abs(
                costo_tour(m, nuevo, modo) - costo) < EPS and tour_valido(
                    nuevo if modo != "ciclo" else nuevo + [0], 9, 0, modo,
                    fin), f"semilla {semilla} {modo}: no empeora y es válido")
            # óptimo local: ningún intercambio de segmento mejora
            hasta = 8 if modo == "fijo" else 9
            mejora = False
            for i in range(1, hasta):
                for j in range(i + 1, hasta):
                    otro = nuevo[:i] + nuevo[i:j + 1][::-1] + nuevo[j + 1:]
                    if costo_tour(m, otro, modo) < costo - 1e-9:
                        mejora = True
            verificar(not mejora, f"semilla {semilla} {modo}: óptimo local")


def prueba_aco():
    print("ACO multiparada")
    for modo, fin in (("ciclo", None), ("libre", None), ("fijo", 9)):
        m = matriz_aleatoria(10, 777, True)
        exacto, _ = held_karp(m, 0, modo, fin)
        r = aco(m, 0, modo, fin, semilla=3)
        verificar(tour_valido(r["orden"], 10, 0, modo, fin),
                  f"{modo}: tour válido")
        verificar(abs(costo_de_orden(m, r["orden"]) - r["costo"]) < EPS,
                  f"{modo}: el costo informado es el recalculado")
        verificar(r["costo"] >= exacto - EPS,
                  f"{modo}: brecha no negativa respecto de Held-Karp")
        verificar(all(b <= a + EPS for a, b in zip(r["curva"],
                                                   r["curva"][1:])),
                  f"{modo}: curva de convergencia no creciente")
        r2 = aco(m, 0, modo, fin, semilla=3)
        verificar(r["costo"] == r2["costo"] and r["curva"] == r2["curva"],
                  f"{modo}: reproducible con semilla fija")
    resumen = aco_semillas(matriz_aleatoria(8, 5, True), 0, "ciclo")
    verificar(len(resumen["corridas"]) >= 10, "al menos 10 semillas fijas")
    verificar(resumen["costo_mejor"] <= resumen["costo_medio"] + EPS
              and resumen["costo_medio"] <= resumen["costo_peor"] + EPS,
              "mejor <= media <= peor")
    try:
        aco(matriz_aleatoria(6, 1, False), 0, "ciclo")
    except ValueError:
        verificar(True, "matriz asimétrica con 2-opt: error explícito")
    else:
        raise AssertionError("Debía rechazar la matriz asimétrica")
    asim = matriz_aleatoria(9, 41, False)
    for modo, fin in (("ciclo", None), ("libre", None), ("fijo", 8)):
        exacto, _ = held_karp(asim, 0, modo, fin)
        r = aco(asim, 0, modo, fin, semilla=2, busqueda_local=False)
        verificar(tour_valido(r["orden"], 9, 0, modo, fin)
                  and abs(costo_de_orden(asim, r["orden"]) - r["costo"])
                  < EPS and r["costo"] >= exacto - EPS,
                  f"asimétrica sin 2-opt ({modo}): válido, costo "
                  "recalculado y brecha no negativa")
    sim = matriz_aleatoria(9, 42, True)
    r = aco(sim, 0, "ciclo", semilla=2, busqueda_local=False)
    verificar(tour_valido(r["orden"], 9, 0, "ciclo", None),
              "simétrica sin 2-opt: tour válido")


def main():
    prueba_held_karp()
    prueba_dos_opt()
    prueba_aco()
    print("Todas las pruebas de orden libre pasaron.")


if __name__ == "__main__":
    main()
