"""Tablas LaTeX del informe del Corte 2, generadas desde las corridas.

Lee outputs/resultados_corte2.json, barrido_pesos.json y
sensibilidad_corte2.json (escritos por experimentos_corte2.py) y escribe en
outputs/ los archivos tabla_c2_*.tex que incluye informe_corte2.tex.
"""
import json

import networkx as nx

from build_graph import SALIDA, construir_grafo
from experimentos_corte2 import ALGORITMOS
from formato_latex import estilizar

NOMBRES_CRITERIO = {
    "distancia": "distancia",
    "compuesto_sin_riesgo": "compuesto sin riesgo",
    "compuesto": "compuesto (riesgo faltante $=0$, limitado)",
    "riesgo": "riesgo (limitado, $h=0$)",
}
METRICAS = ["expandidos", "tiempo", "memoria", "costo", "optimalidad"]
TITULOS = {
    "expandidos": "Nodos expandidos",
    "tiempo": "Tiempo medio $\\pm$ desviación estándar ($\\mu$s)",
    "memoria": "Memoria pico (KiB)",
    "costo": "Costo de la ruta",
    "optimalidad": "Optimalidad respecto de UCS",
}


def leer(nombre):
    with open(SALIDA / nombre, encoding="utf-8") as f:
        return json.load(f)


def escribir(nombre, lineas):
    with open(SALIDA / nombre, "w", encoding="utf-8") as f:
        f.write("\n".join(estilizar(lineas)) + "\n")


def miles(valor):
    return f"{valor:,.0f}".replace(",", "\\,")


def celda(c, metrica, criterio):
    if metrica == "expandidos":
        return str(c["nodos_expandidos"])
    if metrica == "tiempo":
        return (f"{c['tiempo_media_s'] * 1e6:.0f} $\\pm$ "
                f"{c['tiempo_desv_s'] * 1e6:.0f}")
    if metrica == "memoria":
        return f"{c['memoria_pico_kib']:.1f}"
    if metrica == "costo":
        return f"{c['costo']:.2f}" if criterio == "distancia" \
            else f"{c['costo']:.3f}"
    if c["optima"]:
        return "sí"
    if not c["costo_optimo"]:
        return f"no (óptimo $0$, costo {c['costo']:.3f})"
    return f"no (+{100 * c['exceso_relativo']:.1f}\\,\\%)"


def tabla_metrica(resultados, criterio, metrica):
    filas = {}
    for c in resultados:
        if c["criterio"] != criterio:
            continue
        clave = (c["origen"], c["destino"], c["rutas_simples"])
        filas.setdefault(clave, {})[c["algoritmo"]] = c
    lineas = ["\\begin{tabular}{l" + "r" * len(ALGORITMOS) + "}",
              "\\toprule",
              "\\textbf{Escenario} & " + " & ".join(
                  f"\\textbf{{{a}}}" for a in ALGORITMOS) + " \\\\",
              "\\midrule"]
    for (origen, destino, rutas), por_algoritmo in filas.items():
        marca = "$^{*}$" if rutas > 1 else ""
        valores = " & ".join(celda(por_algoritmo[a], metrica, criterio)
                             for a in ALGORITMOS)
        lineas.append(f"{origen} -- {destino}{marca} & {valores} \\\\")
    lineas += ["\\bottomrule", "\\end{tabular}"]
    return lineas


def tablas_escenarios(resultados):
    for criterio in NOMBRES_CRITERIO:
        for metrica in METRICAS:
            escribir(f"tabla_c2_{criterio}_{metrica}.tex",
                     tabla_metrica(resultados, criterio, metrica))


def tabla_barrido(barridos):
    base, cota = barridos[0], barridos[1]
    filas = [
        ("Puntos de la malla con ruta por Bogotá (compuesto)",
         f"{base['ganan_bogota_compuesto']} de {len(base['puntos'])}",
         f"{cota['ganan_bogota_compuesto']} de {len(cota['puntos'])}"),
        ("Puntos con ruta por Bogotá (sin riesgo)",
         f"{base['ganan_bogota_sin_riesgo']} de "
         f"{base['puntos_sin_riesgo_definidos']}",
         f"{cota['ganan_bogota_sin_riesgo']} de "
         f"{cota['puntos_sin_riesgo_definidos']}"),
        ("$w_1$ de cambio sobre $w_3=0$",
         f"{base['w1_umbral_sobre_w3_cero']:.4f}",
         f"{cota['w1_umbral_sobre_w3_cero']:.4f}"),
    ]
    for i, nombre in enumerate(["$\\Delta D$", "$\\Delta P$", "$\\Delta R$"]):
        filas.append((f"{nombre} (corta menos desvío)",
                      f"{base['delta_corta_menos_desvio'][i]:.4f}",
                      f"{cota['delta_corta_menos_desvio'][i]:.4f}"))
    escribir("tabla_c2_barrido.tex",
             ["\\begin{tabular}{lrr}", "\\toprule",
              "\\textbf{Medida} & \\textbf{Base} & "
              "\\textbf{Con cota inferior} \\\\", "\\midrule"]
             + [f"{a} & {b} & {c} \\\\" for a, b, c in filas]
             + ["\\bottomrule", "\\end{tabular}"])


def tabla_sensibilidad_alfa(sens):
    lineas = ["\\begin{tabular}{lrrrc}", "\\toprule",
              "\\textbf{Escenario} & \\textbf{UCS} & "
              "\\textbf{A* $\\alpha=%.6f$} & "
              "\\textbf{A* $\\alpha_{\\mathrm{ref}}=%.6f$} & "
              "\\textbf{Óptima} \\\\" % (sens["alfa_base"],
                                         sens["alfa_ref"]),
              "\\midrule"]
    for e in sens["por_escenario"][:1]:
        lineas.append(
            f"{e['origen']} -- {e['destino']} & {e['expandidos_ucs']} & "
            f"{e['expandidos_alfa_base']} & {e['expandidos_alfa_ref']} & "
            f"{'sí' if e['optima_alfa_ref'] else 'no'} \\\\")
    t = sens["todos_los_pares"]
    lineas += ["\\midrule",
               f"Suma de {t['pares']} pares & {t['expandidos_total_ucs']} & "
               f"{t['expandidos_total_alfa_base']} & "
               f"{t['expandidos_total_alfa_ref']} & "
               f"{t['pares'] - t['no_optimos']} de {t['pares']} \\\\",
               "\\bottomrule", "\\end{tabular}"]
    escribir("tabla_c2_sensibilidad_alfa.tex", lineas)


def tabla_sensibilidad_cruda(sens, barridos):
    base = sens["rutas_optimas_duitama_puente_nacional"]["base"]
    cruda = sens["rutas_optimas_duitama_puente_nacional"]["crudas"]
    nombres = {"distancia": "distancia", "peaje": "peaje",
               "riesgo": "riesgo (limitado)",
               "compuesto": "compuesto (limitado)",
               "compuesto_sin_riesgo": "compuesto sin riesgo"}
    lineas = ["\\begin{tabular}{lrrrr}", "\\toprule",
              "\\textbf{Criterio} & \\textbf{Base: vía} & "
              "\\textbf{Base: km} & \\textbf{Crudas: vía} & "
              "\\textbf{Crudas: km} \\\\", "\\midrule"]
    for criterio, nombre in nombres.items():
        b, c = base[criterio], cruda[criterio]
        lineas.append(f"{nombre} & {b['via']} & {b['distancia_km']:.2f} & "
                      f"{c['via']} & {c['distancia_km']:.2f} \\\\")
    bb, bc = barridos[0], barridos[2]
    lineas += [
        "\\midrule",
        "Barrido: ruta por Bogotá (compuesto) & "
        f"\\multicolumn{{2}}{{r}}{{{bb['ganan_bogota_compuesto']} de "
        f"{len(bb['puntos'])}}} & \\multicolumn{{2}}{{r}}"
        f"{{{bc['ganan_bogota_compuesto']} de {len(bc['puntos'])}}} \\\\",
        "Barrido: ruta por Bogotá (sin riesgo) & "
        f"\\multicolumn{{2}}{{r}}{{{bb['ganan_bogota_sin_riesgo']} de "
        f"{bb['puntos_sin_riesgo_definidos']}}} & \\multicolumn{{2}}{{r}}"
        f"{{{bc['ganan_bogota_sin_riesgo']} de "
        f"{bc['puntos_sin_riesgo_definidos']}}} \\\\",
        "$w_1$ de cambio sobre $w_3=0$ & "
        f"\\multicolumn{{2}}{{r}}{{{bb['w1_umbral_sobre_w3_cero']:.4f}}} & "
        f"\\multicolumn{{2}}{{r}}{{{bc['w1_umbral_sobre_w3_cero']:.4f}}} "
        "\\\\",
        "\\bottomrule", "\\end{tabular}"]
    escribir("tabla_c2_sensibilidad_cruda.tex", lineas)


def tabla_heuristica():
    a = leer("analisis_heuristica.json")
    filas = []
    nombres = {"distancia": "distancia",
               "compuesto_sin_riesgo": "compuesto sin riesgo",
               "compuesto": "compuesto (limitado)"}
    for criterio, datos in a["criterios"].items():
        adm, con = datos["admisibilidad"], datos["consistencia"]
        filas.append((nombres[criterio], f"{a['alfa']:.6f}",
                      adm["violaciones"], f"{adm['margen_minimo']:.6f}",
                      con["violaciones"], f"{con['margen_minimo']:.6f}"))
    p = a["geodesica_pura_distancia"]
    filas.append(("distancia, geodésica pura", "1",
                  p["admisibilidad"]["violaciones"],
                  f"{p['admisibilidad']['margen_minimo']:.2f}",
                  p["consistencia"]["violaciones"],
                  f"{p['consistencia']['margen_minimo']:.2f}"))
    encabezado = [
        "\\begin{tabular}{lrrrrr}", "\\toprule",
        "\\textbf{Heurística} & $\\alpha$ & \\textbf{Viol. adm.} & "
        "\\textbf{Margen adm.} & \\textbf{Viol. cons.} & "
        "\\textbf{Margen cons.} \\\\", "\\midrule"]
    cuerpo = [" & ".join(str(x) for x in f) + " \\\\" for f in filas]
    escribir("tabla_c2_heuristica.tex",
             encabezado + cuerpo + ["\\bottomrule", "\\end{tabular}"])
    lineas = ["\\begin{tabular}{lrrr}", "\\toprule",
              "\\textbf{Arista} & \\textbf{Carretera (km)} & "
              "\\textbf{Geodésica (km)} & \\textbf{Razón} \\\\",
              "\\midrule"]
    for r in a["aristas_con_razon_menor_que_1"]:
        u, v = r["arista"]
        lineas.append(f"{u} -- {v} & {r['carretera_km']:.2f} & "
                      f"{r['geodesica_km']:.2f} & {r['razon']:.6f} \\\\")
    escribir("tabla_c2_razones.tex",
             lineas + ["\\bottomrule", "\\end{tabular}"])


def tabla_escenarios(resultados):
    vistos = {}
    for c in resultados:
        clave = (c["origen"], c["destino"])
        if (clave not in vistos and c["criterio"] == "distancia"
                and c["algoritmo"] == "UCS"):
            vistos[clave] = c
    lineas = ["\\begin{tabular}{lcr>{\\raggedright\\arraybackslash}p{5.4cm}}",
              "\\toprule",
              "\\textbf{Escenario} & \\textbf{Rutas} & "
              "\\textbf{Saltos} & \\textbf{Motivo} \\\\",
              "\\midrule"]
    for (origen, destino), c in vistos.items():
        lineas.append(f"{origen} -- {destino} & {c['rutas_simples']} & "
                      f"{c['saltos']} & {c['motivo']} \\\\")
    escribir("tabla_c2_escenarios.tex",
             lineas + ["\\bottomrule", "\\end{tabular}"])


def tabla_limitados(resultados):
    """Criterios con heurística limitada: expandidos totales y óptimos."""
    lineas = ["\\begin{tabular}{l" + "r" * len(ALGORITMOS) + "}",
              "\\toprule",
              "\\textbf{Criterio} & " + " & ".join(
                  f"\\textbf{{{a}}}" for a in ALGORITMOS) + " \\\\",
              "\\midrule"]
    nombres = {"compuesto": "compuesto (riesgo faltante $=0$)",
               "riesgo": "riesgo ($h=0$)"}
    for criterio, nombre in nombres.items():
        celdas = []
        for algoritmo in ALGORITMOS:
            filas = [c for c in resultados if c["criterio"] == criterio
                     and c["algoritmo"] == algoritmo]
            expandidos = sum(c["nodos_expandidos"] for c in filas)
            optimos = sum(1 for c in filas if c["optima"])
            celdas.append(f"{expandidos} / {optimos}")
        lineas.append(f"{nombre} & " + " & ".join(celdas) + " \\\\")
    escribir("tabla_c2_limitados.tex",
             lineas + ["\\bottomrule", "\\end{tabular}"])


def texto_cambio_sin_riesgo():
    """Costos compuestos sin riesgo de las dos rutas, antes y después de
    corregir las distancias (generado desde el grafo)."""
    salida = {}
    for variante in ("cruda", "corregida"):
        g = construir_grafo(distancia=variante)
        caminos = list(nx.all_simple_paths(g, "Duitama", "Puente Nacional"))
        por_bogota = next(c for c in caminos if "Bogotá" in c)
        por_santander = next(c for c in caminos if "Bucaramanga" in c)
        salida[variante] = tuple(
            sum(g[u][v]["peso_sin_riesgo"] for u, v in zip(c, c[1:]))
            for c in (por_bogota, por_santander))
    (ab, as_), (db, ds) = salida["cruda"], salida["corregida"]
    ganador_antes = "el desvío por Santander" if as_ < ab \
        else "la ruta por Bogotá"
    ganador_despues = "la ruta por Bogotá" if db < ds \
        else "el desvío por Santander"
    escribir("texto_cambio_sin_riesgo.tex", [
        f"Con las distancias sin corregir, el costo compuesto sin riesgo era "
        f"{ab:.3f} por Bogotá y {as_:.3f} por Santander, y ganaba "
        f"{ganador_antes}; con las distancias corregidas es {db:.3f} por "
        f"Bogotá y {ds:.3f} por Santander, y gana {ganador_despues}."])


def main():
    resultados = leer("resultados_corte2.json")["resultados"]
    barridos = leer("barrido_pesos.json")
    sens = leer("sensibilidad_corte2.json")
    tablas_escenarios(resultados)
    tabla_barrido(barridos)
    tabla_sensibilidad_alfa(sens)
    tabla_sensibilidad_cruda(sens, barridos)
    tabla_heuristica()
    tabla_escenarios(resultados)
    tabla_limitados(resultados)
    texto_cambio_sin_riesgo()
    print("Tablas del Corte 2 escritas en", SALIDA)


if __name__ == "__main__":
    main()
