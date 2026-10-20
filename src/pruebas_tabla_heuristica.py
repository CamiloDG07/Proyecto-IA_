"""Pruebas de la tabla de criterios de la heurística (src/tablas_resumen.py).

Comprueban, contra el grafo y src/heuristica.py, que las expresiones de la
tabla son las del código: el costo de cada arista es a d + b con a >= 0 y
b >= 0, el coeficiente a de la tabla es el factor de la heurística (con
alfa = 1) y h = a d_geo cumple la consistencia analítica
h(u) <= a d(u, v) + b(u, v) + h(v) en toda arista y para toda meta.
"""
import sys

import tablas_resumen as tr
from build_graph import cargar_grafo
from heuristica import Heuristica, cargar_coordenadas, haversine_km

TOLERANCIA = 1e-9


def ok(condicion, mensaje):
    if not condicion:
        print(f"  FALLA: {mensaje}")
        sys.exit(1)
    print(f"  ok: {mensaje}")


def coeficientes(grafo):
    """a de cada criterio según la tabla (fórmulas simbólicas evaluadas)."""
    w = grafo.graph["pesos"]
    wt = grafo.graph["pesos_total"]
    t = grafo.graph["maximos"]
    c_km = grafo.graph["costos"]["costo_variable_cop_km"]
    w1, w2 = w["distancia"], w["peaje"]
    return {
        "distancia": 1.0,
        "compuesto_sin_riesgo": w1 / ((w1 + w2) * t["distancia"]),
        "costo_operativo": c_km,
        "compuesto_total_sin_riesgo": (
            (wt["distancia"] + wt["costo_variable"])
            / ((wt["distancia"] + wt["peaje"] + wt["costo_variable"])
               * t["distancia"])),
        "compuesto": w1 / t["distancia"],
        "compuesto_total": (wt["distancia"] + wt["costo_variable"])
        / t["distancia"],
        "compuesto_mortalidad": w1 / t["distancia"],
        "peaje": 0.0, "riesgo": 0.0}


def resto(grafo, criterio, d):
    """b(u, v): la parte del costo que no depende de los kilómetros, según
    la tabla, con los máximos de la red."""
    w = grafo.graph["pesos"]
    wt = grafo.graph["pesos_total"]
    t = grafo.graph["maximos"]
    p = d["peaje_cop_camion"]
    r = d["riesgo_gizscore_prom"] if d["riesgo_disponible"] else 0.0
    m = d["mortalidad_por_100km"] if d["mortalidad_disponible"] else 0.0
    w1, w2, w3 = w["distancia"], w["peaje"], w["riesgo"]
    if criterio == "distancia":
        return 0.0
    if criterio == "compuesto_sin_riesgo":
        return w2 * p / t["peaje"] / (w1 + w2)
    if criterio == "costo_operativo":
        return p
    if criterio == "compuesto_total_sin_riesgo":
        return wt["peaje"] * p / t["peaje"] / (
            wt["distancia"] + wt["peaje"] + wt["costo_variable"])
    if criterio == "compuesto":
        return w2 * p / t["peaje"] + w3 * r / t["riesgo"]
    if criterio == "compuesto_total":
        return (wt["peaje"] * p / t["peaje"]
                + wt["riesgo"] * r / t["riesgo"])
    if criterio == "compuesto_mortalidad":
        return w2 * p / t["peaje"] + w3 * m / t["mortalidad"]
    return p if criterio == "peaje" else r


def main():
    tr.main()
    grafo = cargar_grafo()
    coord = cargar_coordenadas()
    a = coeficientes(grafo)
    ok(list(a) == tr.CLAVES_EXPRESION and len(tr.EXPRESIONES) == len(a),
       f"la tabla tiene una fila por criterio ({len(a)})")
    for criterio, ai in a.items():
        h = Heuristica(grafo, coord, criterio, 1.0)
        ok(abs(h.factor - ai) <= TOLERANCIA * max(1.0, ai),
           f"{criterio}: a de la tabla = factor de la heurística ({ai:.6g})")
        atributo = {"distancia": "distancia_km", "peaje": "peaje_cop_camion",
                    "riesgo": "riesgo_gizscore_prom"}.get(criterio)
        malas = 0
        for u, v, d in grafo.edges(data=True):
            b = resto(grafo, criterio, d)
            c = ai * d["distancia_km"] + b
            real = d[atributo] if atributo else d[{
                "compuesto_sin_riesgo": "peso_sin_riesgo",
                "costo_operativo": "costo_operativo_cop",
                "compuesto_total_sin_riesgo": "peso_total_sin_riesgo",
                "compuesto": "peso_multicriterio",
                "compuesto_total": "peso_total",
                "compuesto_mortalidad": "peso_mortalidad"}[criterio]]
            if criterio == "riesgo" and not d["riesgo_disponible"]:
                real = 0.0
            if abs(c - real) > 1e-9 * max(1.0, abs(real)) or b < 0:
                malas += 1
        ok(malas == 0, f"{criterio}: c(u,v) = a d + b con b >= 0 en las "
           f"{grafo.number_of_edges()} aristas")
        ok(ai >= 0, f"{criterio}: a >= 0")
    # consistencia analítica: h(u) <= a d(u,v) + b(u,v) + h(v), cada meta
    peor = None
    for criterio, ai in a.items():
        for meta in grafo:
            for u, v, d in grafo.edges(data=True):
                b = resto(grafo, criterio, d)
                for x, y in ((u, v), (v, u)):
                    hx = ai * haversine_km(*coord[x], *coord[meta])
                    hy = ai * haversine_km(*coord[y], *coord[meta])
                    margen = ai * d["distancia_km"] + b + hy - hx
                    peor = margen if peor is None else min(peor, margen)
    ok(peor >= -1e-6, "h = a d_geo cumple h(u) <= c(u,v) + h(v) en todas las "
       "aristas, sentidos y metas (los márgenes salen de la desigualdad)")
    print("Todas las pruebas de la tabla de criterios pasaron.")


if __name__ == "__main__":
    main()
