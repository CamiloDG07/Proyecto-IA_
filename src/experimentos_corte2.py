"""Experimentos del Corte 2: escenarios, barrido de pesos y sensibilidad.

Escenarios (pares origen-destino), todos sobre la red corregida de 32 nodos
y con el piso geodésico (la distancia de cada arista no es menor que la recta
entre sus nodos; ver piso_geodesico.py):
  - pares que cruzan el ciclo, con dos rutas simples distintas (el caso
    central es Duitama a Puente Nacional): solo aquí pueden diferir las rutas
    de los cinco algoritmos;
  - pares que no cruzan el ciclo (ruta única): solo difieren los nodos
    expandidos, el tiempo y la memoria; con 1 a 6 saltos.
El número de rutas simples de cada par se comprueba al ejecutar.

Criterios: distancia, compuesto_sin_riesgo, costo_operativo y
compuesto_total_sin_riesgo (heurística geodésica con alfa = 1, admisible y
consistente por construcción con el piso);
compuesto, compuesto_total y compuesto_mortalidad (riesgo faltante igual a 0)
y riesgo se reportan aparte como limitados; en riesgo la heurística admisible
es h = 0 (A* se reduce a UCS). compuesto_mortalidad es solo sensibilidad.

Sensibilidades rotuladas: «sin piso» (distancias oficiales, alfa = mínimo de
la razón carretera/geodésica, 0.310570), Chocontá a Tunja con 61.0 km por
progresivas (con un hueco de 49.1 km; también con piso) y distancias sin
corregir por doble calzada (cruda, con piso).
Barrido de pesos: el compuesto de tres pesos (distancia, peaje y riesgo) y el
compuesto total de cuatro pesos (con el costo variable), ambos en malla de
paso 0.1.

Mediciones: el tiempo se mide sin tracemalloc, REPETICIONES veces por celda
(media y desviación estándar); la memoria pico, en una corrida aparte con
tracemalloc.

Escribe outputs/resultados_corte2.json, outputs/barrido_pesos.json,
outputs/barrido_total.json y outputs/sensibilidad_corte2.json.
"""
import json
from itertools import product

import networkx as nx

from agente import CRITERIOS
from build_graph import SALIDA, cargar_costos, construir_grafo
from busquedas import a_estrella, bfs, dfs, medir, ucs, voraz
from heuristica import Heuristica, alfa_minimo, cargar_coordenadas

REPETICIONES = 2000
PASO_MALLA = 0.1
CHOCONTA_TUNJA = ("Chocontá", "Tunja")
PROGRESIVAS_KM = 61.0   # PR 120.0 menos PR 59.0, con hueco de 49.1 km
CRITERIOS_EXPERIMENTO = [
    ("distancia", False),
    ("compuesto_sin_riesgo", False),
    ("compuesto", True),
    ("riesgo", True),
    ("costo_operativo", False),
    ("compuesto_total_sin_riesgo", False),
    ("compuesto_total", True),
    ("compuesto_mortalidad", True),
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
            # h precalculada por destino: mismos valores, sin Haversine en
            # cada evaluación; el tiempo de construir la tabla se mide aparte
            tabla = h.precalcular(grafo, destino)
            pre = medir(h.precalcular, REPETICIONES, grafo, destino)
            optimo = ucs(grafo, origen, destino, atributo)["costo"]
            for nombre, (funcion, args) in algoritmos(
                    grafo, atributo, tabla, origen, destino).items():
                m = medir(funcion, REPETICIONES, *args)
                r = m["resultado"]
                usa_h = nombre in ("Voraz", "A*")
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
                    "precalculo_h_media_s":
                        pre["tiempo_media_s"] if usa_h else None,
                    "precalculo_h_desv_s":
                        pre["tiempo_desv_s"] if usa_h else None,
                })
        print(f"  {origen} - {destino}: {rutas_simples} ruta(s) simple(s)")
    return resultados


def sensibilidad_alfa(grafo, sin_piso, coordenadas):
    """Sensibilidad «sin piso»: A* con las distancias oficiales.

    Con piso (base) alfa = 1 y h es admisible y consistente. Sin piso, alfa es
    el mínimo de la razón oficial (0.310570, admisible pero débil); con
    alfa = 1 y sin piso h deja de ser admisible. Se compara, en los
    escenarios y en los 992 pares (criterio distancia), UCS y A* con piso
    contra UCS, A* con ese alfa y A* con alfa = 1, ambos sin piso.
    """
    alfa_piso = alfa_minimo(grafo, coordenadas)
    alfa_sp = alfa_minimo(sin_piso, coordenadas)
    atributo = CRITERIOS["distancia"]
    h_piso = Heuristica(grafo, coordenadas, "distancia", alfa_piso)
    h_sp = Heuristica(sin_piso, coordenadas, "distancia", alfa_sp)
    h_pura = Heuristica(sin_piso, coordenadas, "distancia", 1.0)

    def corrida(o, d):
        u0 = ucs(grafo, o, d, atributo)
        a0 = a_estrella(grafo, o, d, atributo, h_piso)
        u1 = ucs(sin_piso, o, d, atributo)
        a1 = a_estrella(sin_piso, o, d, atributo, h_sp)
        a2 = a_estrella(sin_piso, o, d, atributo, h_pura)
        return u0, a0, u1, a1, a2

    por_escenario = []
    for origen, destino, _ in ESCENARIOS:
        u0, a0, u1, a1, a2 = corrida(origen, destino)
        por_escenario.append({
            "origen": origen, "destino": destino,
            "costo_optimo_piso": u0["costo"],
            "costo_optimo_sin_piso": u1["costo"],
            "expandidos_ucs_piso": u0["nodos_expandidos"],
            "expandidos_astar_piso": a0["nodos_expandidos"],
            "reexpansiones_astar_piso": a0["reexpansiones"],
            "expandidos_ucs_sin_piso": u1["nodos_expandidos"],
            "expandidos_astar_sin_piso": a1["nodos_expandidos"],
            "expandidos_astar_sin_piso_alfa1": a2["nodos_expandidos"],
            "costo_astar_sin_piso_alfa1": a2["costo"],
            "optima_astar_sin_piso_alfa1":
                abs(a2["costo"] - u1["costo"]) < 1e-9,
            "reexpansiones_astar_sin_piso_alfa1": a2["reexpansiones"],
        })
    pares = [(o, d) for o in grafo for d in grafo if o != d]
    no_optimos = []
    tot = {"ucs_piso": 0, "astar_piso": 0, "ucs_sin_piso": 0,
           "astar_sin_piso": 0, "astar_sin_piso_alfa1": 0}
    reexp_piso = 0
    for o, d in pares:
        u0, a0, u1, a1, a2 = corrida(o, d)
        tot["ucs_piso"] += u0["nodos_expandidos"]
        tot["astar_piso"] += a0["nodos_expandidos"]
        tot["ucs_sin_piso"] += u1["nodos_expandidos"]
        tot["astar_sin_piso"] += a1["nodos_expandidos"]
        tot["astar_sin_piso_alfa1"] += a2["nodos_expandidos"]
        reexp_piso += a0["reexpansiones"]
        if abs(a0["costo"] - u0["costo"]) > 1e-9:
            raise AssertionError(f"A* con piso no óptimo: {o} - {d}")
        if abs(a1["costo"] - u1["costo"]) > 1e-9:
            raise AssertionError(f"A* sin piso no óptimo: {o} - {d}")
        if abs(a2["costo"] - u1["costo"]) > 1e-9:
            no_optimos.append({"origen": o, "destino": d,
                               "costo": a2["costo"],
                               "costo_optimo": u1["costo"]})
    return {
        "rotulo": "sensibilidad sin piso: distancias oficiales; alfa = "
                  "mínimo de la razón; con alfa = 1 la h no es admisible",
        "alfa_piso": alfa_piso, "alfa_sin_piso": alfa_sp,
        "por_escenario": por_escenario,
        "todos_los_pares": {
            "pares": len(pares),
            "reexpansiones_astar_piso": reexp_piso,
            "no_optimos_sin_piso_alfa1": len(no_optimos),
            "detalle_no_optimos": no_optimos[:20],
            **{f"expandidos_total_{k}": v for k, v in tot.items()},
        },
    }


def malla_pesos(paso=PASO_MALLA):
    """Todos los (w1, w2, w3) en múltiplos de `paso` que suman 1."""
    n = round(1 / paso)
    return [(i * paso, j * paso, (n - i - j) * paso)
            for i, j in product(range(n + 1), repeat=2) if i + j <= n]


def malla_pesos4(paso=PASO_MALLA):
    """Todos los (w1, w2, w3, w4) en múltiplos de `paso` que suman 1."""
    n = round(1 / paso)
    return [(i * paso, j * paso, k * paso, (n - i - j - k) * paso)
            for i, j, k in product(range(n + 1), repeat=3)
            if i + j + k <= n]


def sumas_ruta4(grafo, ruta):
    """Sumas de los cuatro términos normalizados (w = 1 cada uno)."""
    tope = grafo.graph["maximos"]
    d = p = r = c = 0.0
    for u, v in zip(ruta, ruta[1:]):
        e = grafo[u][v]
        d += e["distancia_km"] / tope["distancia"]
        p += e["peaje_cop_camion"] / tope["peaje"]
        c += e["costo_variable_cop"] / tope["costo_variable"]
        if e["riesgo_disponible"]:
            r += e["riesgo_gizscore_prom"] / tope["riesgo"]
    return [d, p, r, c]


def barrido_total(variante, distancia="corregida", reemplazos=None,
                  piso=True):
    """Ruta ganadora de Duitama a Puente Nacional con cuatro pesos."""
    origen, destino = "Duitama", "Puente Nacional"
    base = construir_grafo(distancia=distancia, reemplazos=reemplazos,
                           piso_geodesico=piso)
    caminos = list(nx.all_simple_paths(base, origen, destino))
    por_bogota = next(c for c in caminos if "Bogotá" in c)
    por_santander = next(c for c in caminos if "Bucaramanga" in c)
    nombres = ("distancia", "peaje", "riesgo", "costo_variable")
    puntos = []
    for w in malla_pesos4():
        costos = cargar_costos(pesos_total=dict(zip(nombres, w)))
        g = construir_grafo(distancia=distancia, reemplazos=reemplazos,
                            costos=costos, piso_geodesico=piso)
        fila = {"w1": round(w[0], 1), "w2": round(w[1], 1),
                "w3": round(w[2], 1), "w4": round(w[3], 1)}
        for nombre, atributo in (("total", "peso_total"),
                                 ("sin_riesgo", "peso_total_sin_riesgo")):
            if nombre == "sin_riesgo" and w[0] + w[1] + w[3] == 0:
                fila[nombre], fila["costo_" + nombre] = None, None
                continue
            r = ucs(g, origen, destino, atributo)
            fila[nombre] = "Bogotá" if "Bogotá" in r["ruta"] else "Santander"
            fila["costo_" + nombre] = r["costo"]
        puntos.append(fila)
    sb, ss = sumas_ruta4(base, por_bogota), sumas_ruta4(base, por_santander)
    delta = [sb[i] - ss[i] for i in range(4)]
    incoherentes = 0
    for f in puntos:
        lineal = sum(f[k] * delta[i] for i, k in enumerate(
            ("w1", "w2", "w3", "w4")))
        esperado = "Bogotá" if lineal < 0 else "Santander"
        if abs(lineal) > 1e-9 and esperado != f["total"]:
            incoherentes += 1
    sin = [f for f in puntos if f["sin_riesgo"] is not None]
    return {
        "variante": variante, "distancia": distancia, "piso_geodesico": piso,
        "reemplazos": {"-".join(k): v for k, v in (reemplazos or {}).items()},
        "ruta_bogota": por_bogota, "ruta_santander": por_santander,
        "sumas_bogota": sb, "sumas_santander": ss,
        "delta_corta_menos_desvio": delta,
        "puntos_incoherentes_con_forma_lineal": incoherentes,
        "puntos": puntos,
        "ganan_bogota_total": sum(1 for f in puntos
                                  if f["total"] == "Bogotá"),
        "ganan_bogota_sin_riesgo": sum(1 for f in sin
                                       if f["sin_riesgo"] == "Bogotá"),
        "puntos_sin_riesgo_definidos": len(sin),
    }


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


def barrido(variante, distancia="corregida", reemplazos=None, piso=True):
    """Ruta ganadora de Duitama a Puente Nacional en la malla de pesos."""
    origen, destino = "Duitama", "Puente Nacional"
    base = construir_grafo(distancia=distancia, reemplazos=reemplazos,
                           piso_geodesico=piso)
    caminos = list(nx.all_simple_paths(base, origen, destino))
    por_bogota = next(c for c in caminos if "Bogotá" in c)
    por_santander = next(c for c in caminos if "Bucaramanga" in c)
    puntos = []
    for w in malla_pesos():
        pesos = {"distancia": w[0], "peaje": w[1], "riesgo": w[2]}
        g = construir_grafo(pesos, distancia, reemplazos,
                            piso_geodesico=piso)
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
        "variante": variante, "distancia": distancia, "piso_geodesico": piso,
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


def rutas_optimas_por_criterio(distancia, reemplazos=None, piso=True):
    """Ruta óptima de Duitama a Puente Nacional por criterio."""
    g = construir_grafo(distancia=distancia, reemplazos=reemplazos,
                        piso_geodesico=piso)
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
    print("Sensibilidad de A* sin piso")
    sin_piso = construir_grafo(piso_geodesico=False)
    sens = sensibilidad_alfa(grafo, sin_piso, coordenadas)
    print("Barrido de pesos")
    progresivas = {CHOCONTA_TUNJA: PROGRESIVAS_KM}
    barridos = [
        barrido("base (con piso geodésico)"),
        barrido("sensibilidad sin piso (distancias oficiales)", piso=False),
        barrido("sensibilidad con distancias crudas", distancia="cruda"),
        barrido("sensibilidad con progresivas (61.0 km)",
                reemplazos=progresivas),
    ]
    with open(SALIDA / "barrido_pesos.json", "w", encoding="utf-8") as f:
        json.dump(barridos, f, ensure_ascii=False, indent=1)
    print("Barrido del compuesto total (cuatro pesos)")
    totales = [
        barrido_total("base (con piso geodésico)"),
        barrido_total("sensibilidad sin piso (distancias oficiales)",
                      piso=False),
        barrido_total("sensibilidad con progresivas (61.0 km)",
                      reemplazos=progresivas),
    ]
    with open(SALIDA / "barrido_total.json", "w", encoding="utf-8") as f:
        json.dump(totales, f, ensure_ascii=False, indent=1)
    sens["rutas_optimas_duitama_puente_nacional"] = {
        "base": rutas_optimas_por_criterio("corregida"),
        "sin_piso": rutas_optimas_por_criterio("corregida", piso=False),
        "progresivas": rutas_optimas_por_criterio("corregida", progresivas),
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
    print(f"  A* sin piso con alfa = 1: {t['no_optimos_sin_piso_alfa1']} de "
          f"{t['pares']} pares no óptimos")


if __name__ == "__main__":
    main()
