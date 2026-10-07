"""ACO (colonia de hormigas) para el orden de visita de varias paradas.

Resuelve el mismo problema que Held-Karp (src/held_karp.py) sobre una matriz
de costos simétrica entre paradas, con un inicio fijo y tres modos de cierre
(ciclo, libre, fijo). Se programa desde cero con numpy.

Algoritmo (Ant System con búsqueda local):
  - visibilidad eta_ij = 1 / (c_ij + eps), con eps = EPS_REL por el costo
    medio positivo, para que costos nulos (p. ej. riesgo sin dato) no
    produzcan infinitos;
  - feromona inicial tau_0 = m / C_nn, con C_nn el costo del tour del vecino
    más cercano y m el número de hormigas;
  - cada hormiga elige el siguiente nodo con probabilidad proporcional a
    tau_ij^alfa * eta_ij^beta entre los no visitados;
  - evaporación tau <- (1 - rho) tau y depósito 1 / L_k de cada hormiga en
    las aristas de su tour; además, el mejor tour de la iteración, mejorado
    con 2-opt, deposita 1 / L adicional;
  - 2-opt (mejor mejora hasta el óptimo local) sobre el mejor tour de cada
    iteración; el mejor global se guarda ya mejorado.

Parámetros declarados (fijos para todas las instancias):
  ALFA = 1.5, BETA = 5, RHO = 0.1: configuración adoptada en el taller de ACO
  del curso (ACO_IA, docs/decisiones_diseno.md) tras su barrido de
  parámetros sobre instancias euclidianas; no se reajustó aquí.
  HORMIGAS = número de nodos del problema (m = n, como en el taller para
  n = 20), ITERACIONES = 100 (las del taller para n = 20).
  SEMILLAS: al menos 10, fijas (aco_semillas).
"""
import time

import numpy as np

ALFA = 1.5
BETA = 5.0
RHO = 0.1
ITERACIONES = 100
EPS_REL = 1e-3
SEMILLAS = tuple(range(1, 11))


def es_simetrica(matriz):
    c = np.asarray(matriz, dtype=float)
    return bool(np.allclose(c, c.T))


def _validar(c, inicio, modo, fin, busqueda_local):
    if modo not in ("ciclo", "libre", "fijo"):
        raise ValueError(f"Modo desconocido: {modo}")
    if modo == "fijo" and (fin is None or fin == inicio):
        raise ValueError("El modo fijo requiere un final distinto del inicio")
    if busqueda_local and not es_simetrica(c):
        raise ValueError("El ACO con 2-opt requiere una matriz simétrica; "
                         "con matriz asimétrica use busqueda_local=False")


def costo_tour(c, tour, modo):
    """Costo de un tour (lista de nodos); el ciclo suma el regreso."""
    total = float(sum(c[a, b] for a, b in zip(tour, tour[1:])))
    if modo == "ciclo":
        total += float(c[tour[-1], tour[0]])
    return total


def vecino_mas_cercano(c, inicio, modo, fin):
    """Tour voraz desde el inicio (el final fijo va al final)."""
    n = len(c)
    pendientes = set(range(n)) - {inicio}
    if modo == "fijo":
        pendientes.discard(fin)
    tour, actual = [inicio], inicio
    while pendientes:
        actual = min(pendientes, key=lambda j: c[actual, j])
        pendientes.remove(actual)
        tour.append(actual)
    if modo == "fijo":
        tour.append(fin)
    return tour


def dos_opt(c, tour, modo):
    """2-opt por mejor mejora. El inicio (posición 0) y, en modo fijo, el
    final (última posición) no se mueven. Devuelve (tour, costo)."""
    t = np.array(tour)
    n = len(t)
    ultimo = n - 2 if modo == "fijo" else n - 1
    if ultimo < 2:
        return [int(x) for x in t], costo_tour(c, [int(x) for x in t], modo)
    i = np.arange(1, ultimo)[:, None]
    j = np.arange(2, ultimo + 1)[None, :]
    valido = j > i
    hay_siguiente = (j + 1 < n) | (modo == "ciclo")
    indice_sig = np.where(j + 1 < n, j + 1, 0)
    while True:
        a, b = t[i - 1], t[i]
        fin_seg = t[j]
        siguiente = t[indice_sig]
        quitado = c[a, b] + np.where(hay_siguiente,
                                     c[fin_seg, siguiente], 0.0)
        puesto = c[a, fin_seg] + np.where(hay_siguiente,
                                          c[b, siguiente], 0.0)
        delta = np.where(valido, puesto - quitado, np.inf)
        k = int(delta.argmin())
        fila, columna = divmod(k, delta.shape[1])
        if delta[fila, columna] >= -1e-12:
            break
        ini, fin = fila + 1, columna + 2
        t[ini:fin + 1] = t[ini:fin + 1][::-1].copy()
    lista = [int(x) for x in t]
    return lista, costo_tour(c, lista, modo)


def aco(matriz, inicio=0, modo="ciclo", fin=None, hormigas=None,
        iteraciones=ITERACIONES, alfa=ALFA, beta=BETA, rho=RHO, semilla=1,
        busqueda_local=True):
    """Una corrida del ACO. Devuelve un diccionario con el mejor orden, su
    costo y la curva de convergencia (mejor costo global por iteración).

    busqueda_local: aplica 2-opt al mejor tour de cada iteración (requiere
    matriz simétrica). Con False es el ACO sin búsqueda local, el único modo
    válido para una matriz asimétrica; entonces el depósito de feromona es
    dirigido (solo en el sentido recorrido)."""
    c = np.asarray(matriz, dtype=float)
    _validar(c, inicio, modo, fin, busqueda_local)
    simetrica = es_simetrica(c)
    n = len(c)
    m = hormigas or n
    azar = np.random.default_rng(semilla)
    inicio_t = time.perf_counter()
    positivos = c[c > 0]
    eps = EPS_REL * (positivos.mean() if positivos.size else 1.0)
    eta = 1.0 / (c + eps)
    np.fill_diagonal(eta, 0.0)
    eta_beta = eta ** beta
    nn = vecino_mas_cercano(c, inicio, modo, fin)
    c_nn = max(costo_tour(c, nn, modo), eps)
    tau = np.full((n, n), m / c_nn)
    libres_por_tour = n - 1 - (1 if modo == "fijo" else 0)
    mejor_orden, mejor_costo = None, float("inf")
    curva = []
    for _ in range(iteraciones):
        peso = (tau ** alfa) * eta_beta
        visitado = np.zeros((m, n), dtype=bool)
        visitado[:, inicio] = True
        if modo == "fijo":
            visitado[:, fin] = True
        tours = np.empty((m, n), dtype=np.int64)
        tours[:, 0] = inicio
        actual = np.full(m, inicio)
        filas = np.arange(m)
        for paso in range(1, libres_por_tour + 1):
            p = peso[actual] * ~visitado
            suma = p.sum(axis=1)
            umbral = azar.random(m) * suma
            elegido = (p.cumsum(axis=1) >= umbral[:, None]).argmax(axis=1)
            sin_peso = suma <= 0
            if sin_peso.any():
                elegido[sin_peso] = (~visitado[sin_peso]).argmax(axis=1)
            tours[:, paso] = elegido
            visitado[filas, elegido] = True
            actual = elegido
        if modo == "fijo":
            tours[:, n - 1] = fin
        costos = c[tours[:, :-1], tours[:, 1:]].sum(axis=1)
        if modo == "ciclo":
            costos = costos + c[tours[:, -1], tours[:, 0]]
        mejor_iter = int(costos.argmin())
        if busqueda_local:
            orden_iter, costo_iter = dos_opt(
                c, [int(x) for x in tours[mejor_iter]], modo)
        else:
            orden_iter = [int(x) for x in tours[mejor_iter]]
            costo_iter = float(costos[mejor_iter])
        if costo_iter < mejor_costo:
            mejor_orden, mejor_costo = orden_iter, costo_iter
        curva.append(mejor_costo)
        tau *= (1.0 - rho)
        depositos = np.zeros((n, n))
        pesos_dep = np.repeat(1.0 / costos, n - 1)
        origen = tours[:, :-1].ravel()
        destino = tours[:, 1:].ravel()
        np.add.at(depositos, (origen, destino), pesos_dep)
        if simetrica:
            np.add.at(depositos, (destino, origen), pesos_dep)
        if modo == "ciclo":
            np.add.at(depositos, (tours[:, -1], tours[:, 0]), 1.0 / costos)
            if simetrica:
                np.add.at(depositos, (tours[:, 0], tours[:, -1]),
                          1.0 / costos)
        extra = 1.0 / costo_iter
        for a, b in zip(orden_iter, orden_iter[1:]):
            depositos[a, b] += extra
            if simetrica:
                depositos[b, a] += extra
        if modo == "ciclo":
            depositos[orden_iter[-1], orden_iter[0]] += extra
            if simetrica:
                depositos[orden_iter[0], orden_iter[-1]] += extra
        tau += depositos
    orden = list(mejor_orden)
    if modo == "ciclo":
        orden.append(inicio)
    return {"orden": orden, "costo": mejor_costo, "curva": curva,
            "semilla": semilla, "busqueda_local": busqueda_local,
            "tiempo_s": time.perf_counter() - inicio_t}


def aco_semillas(matriz, inicio=0, modo="ciclo", fin=None, semillas=SEMILLAS,
                 **parametros):
    """El ACO con varias semillas fijas; devuelve cada corrida y el
    resumen (mejor, media, peor, curva media)."""
    corridas = [aco(matriz, inicio, modo, fin, semilla=s, **parametros)
                for s in semillas]
    costos = np.array([r["costo"] for r in corridas])
    mejor = min(corridas, key=lambda r: r["costo"])
    return {
        "corridas": corridas,
        "mejor": mejor,
        "costo_mejor": float(costos.min()),
        "costo_medio": float(costos.mean()),
        "costo_peor": float(costos.max()),
        "desviacion": float(costos.std()),
        "curva_media": np.mean([r["curva"] for r in corridas],
                               axis=0).tolist(),
    }
