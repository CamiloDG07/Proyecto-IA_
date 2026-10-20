"""Pruebas del piso geodésico de las distancias.

(a) un grafo sintético con una arista por debajo de la geodésica: el piso la
corrige y h = geodésica es consistente y admisible por enumeración; (b) el
invariante falla si se fuerza una distancia menor; (c) en la red real todas
las aristas cumplen costo >= geodésica en todas las variantes con piso; (d)
con piso no hay violaciones de admisibilidad ni de consistencia en los 992
pares ni reexpansiones en A*; (e) sin piso rige el comportamiento anterior;
(f) las aristas sin piso conservan exactamente su distancia oficial.
"""
import sys
from pathlib import Path
if True:  # carpetas de código en el path
    sys.path[:0] = [str(Path(__file__).resolve().parents[1] / c)
                    for c in ("src", "experimentos", "informe", "pruebas")]
from rutas import RAIZ
import json
import subprocess
import sys
from pathlib import Path

import networkx as nx

from build_graph import (SALIDA, cargar_grafo, construir_grafo,
                         verificar_invariante_geodesico)
from busquedas import a_estrella
from heuristica import (ATRIBUTOS, Heuristica, alfa_minimo, cargar_coordenadas,
                        haversine_km, verificar_admisibilidad,
                        verificar_consistencia)
from piso_geodesico import distancia_modelo, geodesica_arista

fallas = []


def ok(condicion, mensaje):
    print(("  ok: " if condicion else "  FALLA: ") + mensaje)
    if not condicion:
        fallas.append(mensaje)


def grafo_sintetico():
    """Cuatro nodos; la arista B-C mide menos que la recta."""
    coord = {"A": (0.0, 0.0), "B": (0.5, 0.0), "C": (1.0, 0.0),
             "D": (1.0, 0.5)}
    oficiales = {("A", "B"): 60.0, ("B", "C"): 20.0, ("C", "D"): 60.0,
                 ("A", "D"): 200.0}
    g = nx.Graph()
    for (u, v), km in oficiales.items():
        geo = geodesica_arista(coord, u, v)
        modelo, piso = distancia_modelo(km, geo)
        g.add_edge(u, v, distancia_km=modelo, distancia_oficial_km=km,
                   distancia_geodesica_km=geo, distancia_piso_km=piso,
                   distancia_piso_aplicado=piso > 0)
    g.graph["piso_geodesico"] = True
    return g, coord, oficiales


def prueba_sintetica():
    print("(a) Grafo sintético con una arista por debajo de la geodésica")
    g, coord, oficiales = grafo_sintetico()
    geo_bc = haversine_km(*coord["B"], *coord["C"])
    ok(oficiales[("B", "C")] < geo_bc, f"B-C oficial 20 km < recta "
       f"{geo_bc:.2f} km (dato incompleto)")
    ok(g["B"]["C"]["distancia_piso_aplicado"]
       and g["B"]["C"]["distancia_km"] >= geo_bc
       and g["B"]["C"]["distancia_oficial_km"] == 20.0,
       "el piso corrige B-C a la recta y conserva el valor oficial")
    ok(not g["A"]["B"]["distancia_piso_aplicado"]
       and g["A"]["B"]["distancia_km"] == 60.0,
       "A-B (ya mayor que la recta) conserva su distancia oficial")
    ok(verificar_invariante_geodesico(g) == 4,
       "el invariante geodésico se cumple en las 4 aristas")

    def h(n, m):
        return haversine_km(*coord[n], *coord[m]) if n != m else 0.0

    adm = verificar_admisibilidad(g, h, "distancia")
    con = verificar_consistencia(g, h, "distancia")
    ok(adm["violaciones"] == 0 and con["violaciones"] == 0,
       "h = geodésica es admisible y consistente por enumeración "
       f"({adm['pares']} pares, {con['casos']} casos)")
    sin = g.copy()
    sin["B"]["C"]["distancia_km"] = 20.0
    ok(verificar_consistencia(sin, h, "distancia")["violaciones"] > 0,
       "sin el piso, h = geodésica deja de ser consistente")


def prueba_invariante_falla():
    print("(b) El invariante falla si se fuerza una distancia menor")
    g = construir_grafo()
    ok(verificar_invariante_geodesico(g) == 32, "red real: 32 aristas")
    u, v, d = next(iter(g.edges(data=True)))
    original = d["distancia_km"]
    d["distancia_km"] = d["distancia_geodesica_km"] - 0.01
    try:
        verificar_invariante_geodesico(g)
        ok(False, "debía fallar con una distancia menor que la recta")
    except AssertionError:
        ok(True, f"falla al bajar {u} - {v} por debajo de su geodésica")
    d["distancia_km"] = original
    sin = construir_grafo(piso_geodesico=False)
    try:
        verificar_invariante_geodesico(sin)
        ok(False, "debía rechazar un grafo sin piso")
    except ValueError:
        ok(True, "un grafo sin piso no pasa por el invariante")


def prueba_red_real():
    print("(c) Red real: costo >= geodésica en todas las variantes con piso")
    coord = cargar_coordenadas()
    variantes = {
        "base": {},
        "cruda": {"distancia": "cruda"},
        "Chocontá a Tunja en 61.0 km": {
            "reemplazos": {("Chocontá", "Tunja"): 61.0}},
        "Chocontá a Tunja en 5 km (forzada)": {
            "reemplazos": {("Chocontá", "Tunja"): 5.0}},
    }
    for nombre, args in variantes.items():
        g = construir_grafo(**args)
        peor = min(d["distancia_km"] - haversine_km(*coord[u], *coord[v])
                   for u, v, d in g.edges(data=True))
        ok(peor >= -1e-9 and g.graph["piso_geodesico"],
           f"{nombre}: 32 aristas con costo >= geodésica (margen mínimo "
           f"{peor:.2e} km)")
    base = construir_grafo()
    ok(sum(d["distancia_piso_aplicado"]
           for _, _, d in base.edges(data=True)) == 8,
       "la base tiene 8 aristas con piso")


def prueba_admisibilidad():
    print("(d) Con piso: sin violaciones en los 992 pares y sin reexpansiones")
    g = cargar_grafo()
    coord = cargar_coordenadas()
    alfa = alfa_minimo(g, coord)
    ok(alfa == 1.0, f"alfa = {alfa} con piso")
    for criterio in ("distancia", "compuesto_sin_riesgo", "costo_operativo",
                     "compuesto_total_sin_riesgo", "compuesto",
                     "compuesto_total", "compuesto_mortalidad"):
        h = Heuristica(g, coord, criterio, alfa)
        adm = verificar_admisibilidad(g, h, criterio)
        con = verificar_consistencia(g, h, criterio)
        ok(adm["pares"] == 992 and adm["violaciones"] == 0
           and con["violaciones"] == 0,
           f"{criterio}: {adm['pares']} pares, 0 violaciones de "
           "admisibilidad y de consistencia")
    for criterio in ("distancia", "compuesto_sin_riesgo", "costo_operativo",
                     "compuesto_total_sin_riesgo"):
        h = Heuristica(g, coord, criterio, alfa)
        total = 0
        optimos = True
        for s in g:
            for t in g:
                if s == t:
                    continue
                r = a_estrella(g, s, t, ATRIBUTOS[criterio], h)
                total += r["reexpansiones"]
                esperado = nx.dijkstra_path_length(g, s, t,
                                                   weight=ATRIBUTOS[criterio])
                optimos &= abs(r["costo"] - esperado) < 1e-9
        ok(total == 0 and optimos,
           f"{criterio}: A* con cero reexpansiones y ruta óptima en los 992 "
           "pares")


def prueba_sin_piso():
    print("(e) Sin piso: el comportamiento anterior")
    coord = cargar_coordenadas()
    g = construir_grafo(piso_geodesico=False)
    alfa = alfa_minimo(g, coord)
    ok(alfa == 0.31057, f"alfa = {alfa} (mínimo de la razón oficial)")
    for criterio in ("distancia", "compuesto_sin_riesgo"):
        h = Heuristica(g, coord, criterio, alfa)
        ok(verificar_admisibilidad(g, h, criterio)["violaciones"] == 0
           and verificar_consistencia(g, h, criterio)["violaciones"] == 0,
           f"{criterio}: 0 violaciones con alfa = {alfa}")
    pura = Heuristica(g, coord, "distancia", 1.0)
    adm = verificar_admisibilidad(g, pura, "distancia")["violaciones"]
    con = verificar_consistencia(g, pura, "distancia")["violaciones"]
    with open(SALIDA / "analisis_heuristica.json", encoding="utf-8") as f:
        guardado = json.load(f)["sin_piso"]["geodesica_pura_distancia"]
    ok(adm > 0 and con > 0
       and (adm, con) == (guardado["admisibilidad"]["violaciones"],
                          guardado["consistencia"]["violaciones"]),
       f"con alfa = 1 y sin piso hay {adm} violaciones de admisibilidad y "
       f"{con} de consistencia "
       "(igual que outputs/datos/analisis_heuristica.json)")


def prueba_sin_piso_conserva_oficial():
    print("(f) Las aristas sin piso conservan su distancia oficial exacta")
    with open(SALIDA / "aristas_red.json", encoding="utf-8") as f:
        aristas = json.load(f)
    try:
        entrega = subprocess.run(
            ["git", "show", "corte2-entrega-8:outputs/aristas_red.json"],
            cwd=RAIZ, capture_output=True)
    except OSError:
        entrega = None
    if entrega is None or entrega.returncode != 0:
        print("  omitida: requiere el historial de git del repositorio "
              "(etiqueta corte2-entrega-8)")
        return
    previo = json.loads(entrega.stdout.decode("utf-8"))
    anterior = {(a["origen"], a["destino"]): a["distancia_km"]
                for a in previo}
    g = cargar_grafo()
    iguales = con_piso = 0
    for a in aristas:
        par = (a["origen"], a["destino"])
        if a["distancia_piso_aplicado"]:
            con_piso += 1
            ok_ = (a["distancia_oficial_km"] == anterior[par]
                   and a["distancia_km"] > anterior[par]
                   and g[par[0]][par[1]]["distancia_km"] == a["distancia_km"])
        else:
            ok_ = (a["distancia_km"] == a["distancia_oficial_km"]
                   == anterior[par]
                   and g[par[0]][par[1]]["distancia_km"] == anterior[par])
            iguales += ok_
        if not ok_:
            ok(False, f"{par}: distancia distinta de la entrega anterior")
    ok(iguales == 24 and con_piso == 8,
       "24 aristas sin piso con la distancia oficial exacta de "
       "corte2-entrega-8; 8 con piso conservan su valor oficial")


def main():
    prueba_sintetica()
    prueba_invariante_falla()
    prueba_red_real()
    prueba_admisibilidad()
    prueba_sin_piso()
    prueba_sin_piso_conserva_oficial()
    if fallas:
        print(f"\n{len(fallas)} pruebas fallaron")
        sys.exit(1)
    print("\nTodas las pruebas del piso geodésico pasaron.")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
