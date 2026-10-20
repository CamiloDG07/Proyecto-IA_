"""Tablas de resumen de los informes (archivos tabla_r_*.tex).

Reemplazan los párrafos y viñetas que mezclaban varias cifras comparables
(por algoritmo, criterio, variante o instancia). Todo número sale de
outputs/ (resultados_corte2.json, sensibilidad_corte2.json,
validacion_agente.json, umbral_held_karp.json, pruebas_agente.json); nada
está escrito a mano. Cada función devuelve las filas (encabezado y cuerpo) y
`main` las escribe con el estilo de formato_latex.
"""
import networkx as nx

import formato_latex
from build_graph import SALIDA, cargar_grafo, construir_grafo
from experimentos_corte2 import ALGORITMOS
from heuristica import CRITERIOS_LIMITADOS, Heuristica, cargar_coordenadas
from lecturas_informe import bloque, cifras_dinero, costos_sin_riesgo
from tablas_corte2 import NOMBRES_CRITERIO, escribir, leer, miles

CENTRAL = ("Duitama", "Puente Nacional")
OTRO = ("Bucaramanga", "Bogotá")
CRITERIOS_CONTRASTE = ["distancia", "compuesto_sin_riesgo",
                       "costo_operativo", "compuesto_total_sin_riesgo"]


def celda_resultado(resultados, par, criterio, algoritmo):
    return next(c for c in resultados
                if (c["origen"], c["destino"]) == par
                and c["criterio"] == criterio and c["algoritmo"] == algoritmo)


def tabla(spec, encabezado, filas):
    """Líneas en el formato de siempre (toprule), que `escribir` estiliza."""
    return ([f"\\begin{{tabular}}{{{spec}}}", "\\toprule",
             " & ".join(f"\\textbf{{{h}}}" for h in encabezado) + " \\\\",
             "\\midrule"]
            + [" & ".join(str(c) for c in f) + " \\\\" for f in filas]
            + ["\\bottomrule", "\\end{tabular}"])


def via(ruta):
    return "Bogotá" if "Bogotá" in ruta else "Santander"


def filas_distancia(resultados):
    """Caso central, criterio distancia: una fila por algoritmo."""
    filas = []
    for a in ALGORITMOS:
        c = celda_resultado(resultados, CENTRAL, "distancia", a)
        filas.append([a, f"{via(c['ruta'])}, {c['costo']:.2f}", c["saltos"],
                      c["nodos_expandidos"],
                      f"{c['tiempo_media_s'] * 1e6:.0f} $\\pm$ "
                      f"{c['tiempo_desv_s'] * 1e6:.0f}"])
    return filas


def filas_sobrecosto(resultados):
    """Sobrecosto (%) respecto del óptimo, por criterio."""
    filas = []
    for criterio in CRITERIOS_CONTRASTE:
        def exceso(par, a):
            return celda_resultado(resultados, par, criterio,
                                   a)["exceso_relativo"] * 100
        optimos = max(exceso(par, a) for par in (CENTRAL, OTRO)
                      for a in ("UCS", "Voraz", "A*"))
        filas.append([NOMBRES_CRITERIO[criterio]]
                     + [f"{exceso(par, a):.1f}" for par in (CENTRAL, OTRO)
                        for a in ("BFS", "DFS")] + [f"{optimos:.1f}"])
    return filas


def filas_nodos(resultados):
    """Nodos expandidos sumados en los diez escenarios, por criterio."""
    filas = []
    for criterio in CRITERIOS_CONTRASTE:
        filas.append([NOMBRES_CRITERIO[criterio]] + [
            sum(c["nodos_expandidos"] for c in resultados
                if c["criterio"] == criterio and c["algoritmo"] == a)
            for a in ALGORITMOS])
    return filas


def filas_umbral_costo():
    """Umbral exacto del costo variable por km: con piso, sin piso y con las
    progresivas."""
    d = cifras_dinero()
    comb = d["modelo"]["combustible_cop_km"]
    nombres = {"piso": "Con piso (base)", "sin_piso": "Sin piso",
               "progresivas": "Progresivas (61.0 km)"}
    filas = []
    for clave, nombre in nombres.items():
        u = d["umbrales"][clave]
        filas.append([nombre, f"{u['km_extra']:.2f}",
                      miles(u["ahorro_peaje_cop"]),
                      f"{u['cop_por_km']:.1f}",
                      f"{comb / u['cop_por_km']:.1f}"])
    return filas


def filas_no_optimos(sens):
    """Pares que A* con alfa = 1 y sin piso no resuelve de forma óptima."""
    return [[f"{p['origen']} a {p['destino']}", f"{p['costo']:.2f}",
             f"{p['costo_optimo']:.2f}",
             f"{p['costo'] - p['costo_optimo']:.2f}"]
            for p in sens["todos_los_pares"]["detalle_no_optimos"]]


def filas_umbral_sesiones(umbral, ks=(19, 20, 22)):
    """Mediana de Held-Karp por sesión para los k que fijan el umbral."""
    filas = []
    for m in umbral["mediciones"]:
        if m["k"] not in ks:
            continue
        cabe = max(m["medianas_s"]) <= umbral["presupuesto_s"]
        filas.append([m["k"]] + [f"{x:.3f}" for x in m["medianas_s"]]
                     + [f"{m['memoria_pico_mib']:.1f}",
                        "sí" if cabe else "no"])
    return filas


def filas_tiempos(val):
    """Tiempos de Held-Karp y del ACO por tamaño de instancia."""
    red = [r for r in val if r["familia"] == "red de carga"]
    tal = [r for r in val if r["familia"].startswith("euclidiana n=20")]
    may = [r for r in val if "mayor" in r["familia"]]
    n20 = [r for r in red + tal if r["n"] == 20]
    hk = [r["exacto"]["tiempo_s"] for r in n20]
    mem = max(r["exacto"]["memoria_pico_mib"] for r in n20)
    aco = [r["aco"]["tiempo_medio_s"] for r in n20]

    def pm(x):
        return f"{x['tiempo_medio_s']:.2f} $\\pm$ {x['tiempo_desv_s']:.2f}"
    filas = [["Held-Karp (exacto)", "20", f"{min(hk):.2f} a {max(hk):.2f}",
              f"{mem:.1f}"],
             ["ACO con 2-opt", "20", f"{min(aco):.2f} a {max(aco):.2f}",
              "---"]]
    for r in may:
        filas.append(["ACO con 2-opt", str(r["n"]), pm(r["aco"]), "---"])
    for r in may:
        filas.append(["ACO sin 2-opt", str(r["n"]), pm(r["aco_sin_2opt"]),
                      "---"])
    return filas


def filas_barrido_pesos():
    """Barrido de pesos de la base (con piso): malla de tres pesos y malla
    de cuatro, con la ruta ganadora y los Δ (Bogotá menos desvío)."""
    b = leer("barrido_pesos.json")[0]
    t = leer("barrido_total.json")[0]
    d3, d4 = b["delta_corta_menos_desvio"], t["delta_corta_menos_desvio"]
    return [
        ["Bogotá gana, con riesgo",
         f"{b['ganan_bogota_compuesto']} de {len(b['puntos'])}",
         f"{t['ganan_bogota_total']} de {len(t['puntos'])}"],
        ["Bogotá gana, sin riesgo",
         f"{b['ganan_bogota_sin_riesgo']} de "
         f"{b['puntos_sin_riesgo_definidos']}",
         f"{t['ganan_bogota_sin_riesgo']} de "
         f"{t['puntos_sin_riesgo_definidos']}"],
        ["$w_1$ de cambio sobre $w_3=0$",
         f"{b['w1_umbral_sobre_w3_cero']:.4f}", "---"],
        ["$\\Delta D$", f"{d3[0]:.4f}", f"{d4[0]:.4f}"],
        ["$\\Delta P$", f"{d3[1]:.4f}", f"{d4[1]:.4f}"],
        ["$\\Delta R$", f"{d3[2]:.4f}", f"{d4[2]:.4f}"],
        ["$\\Delta C$", "---", f"{d4[3]:.4f}"]]


def filas_cambio_sin_riesgo():
    """Costo compuesto sin riesgo de las dos rutas, con las distancias sin
    corregir y con las corregidas."""
    filas = []
    for nombre, variante in (("Sin corregir", "cruda"),
                             ("Corregidas, con piso", "corregida")):
        bogota, santander = costos_sin_riesgo(variante)
        gana = "Bogotá" if bogota < santander else "Santander"
        filas.append([nombre, f"{bogota:.3f}", f"{santander:.3f}", gana])
    return filas


# Costo de la arista c(u, v) = a d(u, v) + b(u, v) y heurística h = a d_geo,
# por criterio (expresiones simbólicas; sus coeficientes se comprueban contra
# el código en pruebas_tabla_heuristica.py).
EXPRESIONES = [
    ("distancia", "$d$", "$1$", "$d_{\\mathrm{geo}}$"),
    ("compuesto sin riesgo",
     "$\\dfrac{w_1\\,d/d_{\\max} + w_2\\,p/p_{\\max}}{w_1 + w_2}$",
     "$\\dfrac{w_1}{(w_1 + w_2)\\,d_{\\max}}$", "$a\\,d_{\\mathrm{geo}}$"),
    ("costo operativo", "$p + c_{km}\\,d$", "$c_{km}$",
     "$c_{km}\\,d_{\\mathrm{geo}}$"),
    ("compuesto total sin riesgo",
     "$\\dfrac{w_1 d/d_{\\max} + w_2 p/p_{\\max} + w_4\\,d/d_{\\max}}"
     "{w_1 + w_2 + w_4}$",
     "$\\dfrac{w_1 + w_4}{(w_1 + w_2 + w_4)\\,d_{\\max}}$",
     "$a\\,d_{\\mathrm{geo}}$"),
    ("compuesto (limitado)",
     "$w_1\\,d/d_{\\max} + w_2\\,p/p_{\\max} + w_3\\,r/r_{\\max}$",
     "$w_1/d_{\\max}$", "$a\\,d_{\\mathrm{geo}}$"),
    ("compuesto total (limitado)",
     "$w_1 d/d_{\\max} + w_2 p/p_{\\max} + w_3 r/r_{\\max} + "
     "w_4\\,d/d_{\\max}$",
     "$(w_1 + w_4)/d_{\\max}$", "$a\\,d_{\\mathrm{geo}}$"),
    ("compuesto con mortalidad (limitado)",
     "$w_1\\,d/d_{\\max} + w_2\\,p/p_{\\max} + w_3\\,m/m_{\\max}$",
     "$w_1/d_{\\max}$", "$a\\,d_{\\mathrm{geo}}$"),
    ("peaje", "$p$", "$0$", "$0$"),
    ("riesgo", "$r$", "$0$", "$0$")]
CLAVES_EXPRESION = ["distancia", "compuesto_sin_riesgo", "costo_operativo",
                    "compuesto_total_sin_riesgo", "compuesto",
                    "compuesto_total", "compuesto_mortalidad", "peaje",
                    "riesgo"]


def tabla_criterios_heuristica():
    """Costo de la arista, coeficiente a y heurística de cada criterio."""
    spec = (">{\\raggedright\\arraybackslash}p{2.5cm}"
            ">{\\raggedright\\arraybackslash}p{5.2cm}"
            ">{\\raggedright\\arraybackslash}p{3.4cm}"
            ">{\\raggedright\\arraybackslash}p{1.9cm}")
    lineas = formato_latex.tabla(
        spec, ["Criterio & Costo de la arista $c(u,v)$ & Coeficiente $a$ & "
               "Heurística $h(n)$ \\\\"],
        [f"{c} & {costo} & {a} & {h} \\\\"
         for c, costo, a, h in EXPRESIONES])
    with open(SALIDA / "tabla_r_criterios_heuristica.tex", "w",
              encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")
    grafo = cargar_grafo()
    coord = cargar_coordenadas()
    factores = {k: Heuristica(grafo, coord, k, 1.0).factor
                for k in CLAVES_EXPRESION}
    con = [k for k, v in factores.items() if v > 0]
    sin = [k for k, v in factores.items() if v == 0]
    limitados = [k for k in con if k in CRITERIOS_LIMITADOS]
    bloque(
        "c2_criterios_heuristica",
        "filas: los nueve criterios; columnas: costo de la arista, "
        "coeficiente $a$ de los kilómetros y heurística resultante; $w_i$ "
        "son los pesos, $d_{\\max}$, $p_{\\max}$, $r_{\\max}$ y $m_{\\max}$ "
        "los máximos de la red y $c_{km}$ el costo variable por km.",
        f"{len(con)} criterios tienen $a > 0$ y una heurística con la "
        f"geodésica; {len(sin)} ({' y '.join(sin)}) tienen $a = 0$ y $h = 0$, "
        "con lo que A* se reduce a UCS; "
        f"{len(limitados)} criterios con $a > 0$ son limitados "
        "(riesgo faltante igual a 0 o mortalidad) y se reportan rotulados.",
        "Medido: los coeficientes $a$ de la tabla coinciden con los del "
        "código de la heurística y el costo de cada arista del grafo es "
        "$a\\,d + b$ con $b \\ge 0$ (pruebas automáticas del "
        "repositorio).")
    return lineas


def filas_pruebas_ciclo():
    """Corte 1: distancia de las dos rutas de los casos que cruzan el ciclo,
    con el modelo y con las distancias sin corregir (con piso)."""
    modelo, cruda = cargar_grafo(), construir_grafo(distancia="cruda")
    bloqueo = ("Bogotá", "Tocancipá")
    filas = []
    for caso, quitar in (("Sin bloqueos", False),
                         ("Bogotá a Tocancipá bloqueado", True)):
        celdas = [caso]
        for g in (modelo, cruda):
            h = g.copy()
            if quitar:
                h.remove_edge(*bloqueo)
            ruta = nx.dijkstra_path(h, "Duitama", "Puente Nacional",
                                    weight="distancia_km")
            km = sum(h[u][v]["distancia_km"] for u, v in zip(ruta, ruta[1:]))
            celdas += [via(ruta), f"{km:.2f}"]
        filas.append(celdas)
    return filas


def main():
    resultados = leer("resultados_corte2.json")["resultados"]
    sens = leer("sensibilidad_corte2.json")
    escribir("tabla_r_distancia.tex", tabla(
        "lrrrr", ["Algoritmo", "Ruta y costo (km)", "Saltos",
                  "Nodos", "Tiempo ($\\mu$s)"],
        filas_distancia(resultados)))
    escribir("tabla_r_sobrecosto.tex", tabla(
        "lrrrrr", ["Criterio", "BFS central", "DFS central", "BFS Buc.",
                   "DFS Buc.", "Óptimos"],
        filas_sobrecosto(resultados)))
    escribir("tabla_r_nodos.tex", tabla(
        "lrrrrr", ["Criterio"] + ALGORITMOS, filas_nodos(resultados)))
    escribir("tabla_r_umbral_costo.tex", tabla(
        "lrrrr", ["Variante", "Km extra", "Ahorro peaje (COP)",
                  "Umbral (COP/km)", "Veces"],
        filas_umbral_costo()))
    escribir("tabla_r_barrido_pesos.tex", tabla(
        "lrr", ["Medida", "Tres pesos", "Cuatro pesos"],
        filas_barrido_pesos()))
    escribir("tabla_r_no_optimos.tex", tabla(
        "lrrr", ["Par", "A* devuelve (km)", "Óptimo (km)", "Exceso (km)"],
        filas_no_optimos(sens)))
    escribir("tabla_r_umbral_sesiones.tex", tabla(
        "rrrrrc", ["$k$", "S1 (s)", "S2 (s)", "S3 (s)", "Memoria (MiB)",
                   "Cabe en 5 s"],
        filas_umbral_sesiones(leer("umbral_held_karp.json"))))
    escribir("tabla_r_cambio_sin_riesgo.tex", tabla(
        "lrrc", ["Distancias", "Por Bogotá", "Por Santander", "Gana"],
        filas_cambio_sin_riesgo()))
    escribir("tabla_r_pruebas_ciclo.tex", tabla(
        "lcrcr", ["Caso", "Modelo: vía", "Modelo: km", "Sin corregir: vía",
                  "Sin corregir: km"],
        filas_pruebas_ciclo()))
    tabla_criterios_heuristica()
    escribir("tabla_r_tiempos.tex", tabla(
        "lrrr", ["Método", "$n$", "Tiempo (s)", "Memoria (MiB)"],
        filas_tiempos(leer("validacion_agente.json")["instancias"])))
    print("Tablas de resumen escritas en outputs/ (tabla_r_*.tex)")


if __name__ == "__main__":
    main()
