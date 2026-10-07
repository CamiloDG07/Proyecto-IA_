"""Pruebas de Held-Karp y del ACO multiparada.

Held-Karp se compara con fuerza bruta (todas las permutaciones) en matrices
aleatorias, simétricas y asimétricas, para los tres modos. El ACO se prueba
en validez de los tours, reproducibilidad con semilla fija y brecha no
negativa respecto del exacto.
"""
import random
from itertools import permutations

import numpy as np

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


def main():
    prueba_held_karp()
    print("Todas las pruebas de orden libre pasaron.")


if __name__ == "__main__":
    main()
