"""Orden libre exacto por programación dinámica (Held-Karp).

Dada una matriz de costos entre paradas, un nodo de inicio fijo y un modo de
cierre, encuentra el orden de visita de costo mínimo:

  ciclo  recorrer todas las paradas y volver al inicio;
  libre  recorrer todas las paradas sin volver (el final es libre);
  fijo   recorrer todas las paradas terminando en un nodo dado.

Sea S el conjunto de las k paradas libres y dp[M, j] el costo mínimo de salir
del inicio, visitar exactamente el subconjunto M de S y terminar en j (j en
M):

    dp[{j}, j] = c(inicio, j)
    dp[M, j]   = min_{i en M \\ {j}} dp[M \\ {j}, i] + c(i, j)

La matriz no tiene que ser simétrica. El cómputo se vectoriza por capas de
igual tamaño de subconjunto (tiempo O(2^k k^2), memoria O(2^k k)).
"""
import numpy as np


def _capas(k):
    """Máscaras agrupadas por número de bits (popcount)."""
    todas = np.arange(1 << k, dtype=np.int64)
    bits = np.zeros(1 << k, dtype=np.int8)
    for j in range(k):
        bits += ((todas >> j) & 1).astype(np.int8)
    return [todas[bits == p] for p in range(k + 1)]


def held_karp(matriz, inicio=0, modo="ciclo", fin=None):
    """Orden óptimo de visita. Devuelve (costo, orden de índices).

    El orden incluye el inicio al principio, el final fijo al final si
    modo es fijo, y el inicio repetido al final si modo es ciclo.
    """
    c = np.asarray(matriz, dtype=float)
    n = c.shape[0]
    if modo not in ("ciclo", "libre", "fijo"):
        raise ValueError(f"Modo desconocido: {modo}")
    if modo == "fijo" and (fin is None or fin == inicio):
        raise ValueError("El modo fijo requiere un final distinto del inicio")
    libres = [i for i in range(n)
              if i != inicio and not (modo == "fijo" and i == fin)]
    k = len(libres)
    if k == 0:
        if modo == "ciclo":
            return 0.0, [inicio, inicio] if n > 1 else [inicio]
        if modo == "fijo":
            return float(c[inicio, fin]), [inicio, fin]
        return 0.0, [inicio]
    d = c[np.ix_(libres, libres)]
    salida = c[inicio, libres]
    if modo == "ciclo":
        cierre = c[libres, inicio]
    elif modo == "fijo":
        cierre = c[libres, fin]
    else:
        cierre = np.zeros(k)
    tamano = 1 << k
    dp = np.full((tamano, k), np.inf)
    padre = np.full((tamano, k), -1, dtype=np.int8)
    for j in range(k):
        dp[1 << j, j] = salida[j]
    capas = _capas(k)
    for p in range(2, k + 1):
        mascaras = capas[p]
        for j in range(k):
            con_j = mascaras[(mascaras >> j) & 1 == 1]
            previas = con_j ^ (1 << j)
            candidatos = dp[previas] + d[:, j][None, :]
            mejor = candidatos.argmin(axis=1)
            dp[con_j, j] = candidatos[np.arange(len(con_j)), mejor]
            padre[con_j, j] = mejor
    completo = tamano - 1
    total = dp[completo] + cierre
    ultimo = int(total.argmin())
    costo = float(total[ultimo])
    orden_libres = []
    mascara, actual = completo, ultimo
    while actual != -1:
        orden_libres.append(actual)
        anterior = int(padre[mascara, actual])
        mascara ^= 1 << actual
        actual = anterior
    orden_libres.reverse()
    orden = [inicio] + [libres[j] for j in orden_libres]
    if modo == "ciclo":
        orden.append(inicio)
    elif modo == "fijo":
        orden.append(fin)
    return costo, orden


def costo_de_orden(matriz, orden):
    """Costo de recorrer los nodos en el orden dado."""
    c = np.asarray(matriz, dtype=float)
    return float(sum(c[a, b] for a, b in zip(orden, orden[1:])))
