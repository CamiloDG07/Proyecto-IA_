"""Exporta a LaTeX las tablas del informe, directamente de las corridas.

Lee el grafo persistido y outputs/pruebas_agente.json; escribe en outputs/
las tablas que incluye formulacion_corte1.tex, para que ninguna cifra se
transcriba a mano.
"""
import csv
import json

from agente import CRITERIOS, AgenteRutas
from build_graph import SALIDA, cargar_grafo
from formato_latex import estilizar

TRAMO_CICLO = ("Bogotá", "Tocancipá")


def miles(valor):
    return f"{valor:,.0f}".replace(",", "\\,")


def escribir(nombre, lineas):
    with open(SALIDA / nombre, "w", encoding="utf-8") as f:
        f.write("\n".join(estilizar(lineas)) + "\n")


def tabla_estadisticas(grafo):
    with open(SALIDA / "estadisticas_grafo.json", encoding="utf-8") as f:
        e = json.load(f)
    filas = [
        ("Nodos (ciudades)", e["nodos"]),
        ("Aristas (tramos)", e["aristas"]),
        ("Grafo conexo", "sí" if e["conexo"] else "no"),
        ("Ciclos independientes ($E-V+1$)", e["ciclos_independientes"]),
        ("Aristas con peaje", f"{e['aristas_con_peaje']} de {e['aristas']}"),
        ("Aristas con dato de riesgo",
         f"{e['aristas_con_riesgo']} de {e['aristas']}"),
        ("Distancia total de la red (km)", f"{e['distancia_total_km']:.2f}"),
        ("$d_{\\max}$ (km)", f"{e['maximos']['distancia']:.2f}"),
        ("$p_{\\max}$ (COP)", miles(e["maximos"]["peaje"])),
        ("$r_{\\max}$ (GiZScore)", f"{e['maximos']['riesgo']:.3f}"),
    ]
    escribir("tabla_estadisticas.tex",
             ["\\begin{tabular}{lr}", "\\toprule",
              "\\textbf{Medida} & \\textbf{Valor} \\\\", "\\midrule"]
             + [f"{a} & {b} \\\\" for a, b in filas]
             + ["\\bottomrule", "\\end{tabular}"])


def tabla_aristas(grafo):
    lineas = [
        "\\begin{longtable}{llrlrrrr}",
        "\\caption{Aristas de la red de carga}\\label{tab:aristas}\\\\",
        "\\toprule",
        "\\textbf{Origen} & \\textbf{Destino} & \\textbf{km} & "
        "\\textbf{Peaje} & \\textbf{COP} & \\textbf{GiZ} & "
        "\\textbf{Fallec.} & \\textbf{Puntos} \\\\",
        "\\midrule", "\\endhead",
    ]
    for u, v, d in grafo.edges(data=True):
        peaje = (d["peaje_nombre"] or "---").title()
        cop = miles(d["peaje_cop_camion"]) if d["peaje_nombre"] else "---"
        if d["riesgo_disponible"]:
            riesgo = (f"{d['riesgo_gizscore_prom']:.2f} & "
                      f"{d['riesgo_fallecidos_hist']:.0f} & "
                      f"{d['riesgo_puntos_criticos']}")
        else:
            riesgo = "--- & --- & ---"
        lineas.append(f"{u} & {v} & {d['distancia_km']:.2f} & {peaje} & "
                      f"{cop} & {riesgo} \\\\")
    lineas += ["\\bottomrule", "\\end{longtable}"]
    escribir("tabla_aristas.tex", lineas)


def costos(grafo, ruta):
    tramos = [grafo[u][v] for u, v in zip(ruta, ruta[1:])]
    return {
        "km": sum(t["distancia_km"] for t in tramos),
        "peaje": sum(t["peaje_cop_camion"] for t in tramos),
        "saltos": len(tramos),
        "sin_dato": sum(not t["riesgo_disponible"] for t in tramos),
        "compuesto": sum(t["peso_multicriterio"] for t in tramos),
        "sin_riesgo": sum(t["peso_sin_riesgo"] for t in tramos),
    }


def tabla_rutas(grafo):
    agente = AgenteRutas(grafo)
    corta = agente.calcular_ruta("Duitama", "Puente Nacional",
                                 "distancia")["ruta"]
    desvio = agente.calcular_ruta("Duitama", "Puente Nacional", "distancia",
                                  tramos_bloqueados=[TRAMO_CICLO])["ruta"]
    c, d = costos(grafo, corta), costos(grafo, desvio)
    filas = [
        ("Saltos", c["saltos"], d["saltos"]),
        ("Distancia (km)", f"{c['km']:.2f}", f"{d['km']:.2f}"),
        ("Peaje total (COP)", miles(c["peaje"]), miles(d["peaje"])),
        ("Tramos sin dato de riesgo", c["sin_dato"], d["sin_dato"]),
        ("Costo compuesto, riesgo faltante $=0$", f"{c['compuesto']:.3f}",
         f"{d['compuesto']:.3f}"),
        ("Costo compuesto sin riesgo", f"{c['sin_riesgo']:.3f}",
         f"{d['sin_riesgo']:.3f}"),
    ]
    escribir("tabla_rutas.tex",
             ["\\begin{tabular}{lrr}", "\\toprule",
              "\\textbf{Medida} & \\textbf{Ruta corta (Bogotá)} & "
              "\\textbf{Desvío (Santander)} \\\\", "\\midrule"]
             + [f"{a} & {b} & {x} \\\\" for a, b, x in filas]
             + ["\\bottomrule", "\\end{tabular}"])


def tabla_criterios():
    with open(SALIDA / "pruebas_agente.json", encoding="utf-8") as f:
        pruebas = json.load(f)["ciclo"]
    lineas = ["\\begin{tabular}{lcrrrr}", "\\toprule",
              "\\textbf{Criterio} & \\textbf{Vía} & \\textbf{km} & "
              "\\textbf{Peaje (COP)} & \\textbf{Tiempo (ms)} & "
              "\\textbf{Memoria (KiB)} \\\\", "\\midrule"]
    for criterio in CRITERIOS:
        r = pruebas[criterio]
        via = "Santander" if "Bucaramanga" in r["ruta"] else "Bogotá"
        nombre = criterio.replace("_", " ")
        lineas.append(f"{nombre} & {via} & {r['distancia_total_km']:.2f} & "
                      f"{miles(r['peaje_total_cop'])} & "
                      f"{r['tiempo_s'] * 1000:.3f} & "
                      f"{r['memoria_pico_kb']:.1f} \\\\")
    lineas += ["\\bottomrule", "\\end{tabular}"]
    escribir("tabla_criterios.tex", lineas)


CODIGOS_AUDITORIA = {
    "carretera menor que geodésica": "A",
    "extremo lejos del nodo": "B",
    "nodo lejos de la geometría": "C",
    "registro mayor que el camino de la geometría": "D",
    "geometría sin camino entre extremos": "E",
}


def tabla_auditoria():
    """Solo las aristas marcadas por la auditoría (el CSV las trae todas)."""
    with open(SALIDA / "auditoria_aristas.csv", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    lineas = [
        "\\begin{tabular}{lrrrrl}",
        "\\toprule",
        "\\textbf{Arista} & \\textbf{Carr.} & \\textbf{Geod.} & "
        "\\textbf{Razón} & \\textbf{Ext.} & \\textbf{Marcas} \\\\",
        "\\midrule",
    ]
    for r in [x for x in filas if x["anomalia"]]:
        marcas = ",".join(sorted(
            CODIGOS_AUDITORIA[m] for m in r["anomalia"].split("; ") if m))
        ext = max(float(r["extremo_a_origen_km"]),
                  float(r["extremo_a_destino_km"]))
        lineas.append(
            f"{r['origen']} -- {r['destino']} & "
            f"{r['distancia_carretera_km']} & {r['geodesica_km']} & "
            f"{float(r['razon']):.3f} & {ext:.2f} & {marcas or '---'} \\\\")
    lineas += ["\\bottomrule", "\\end{tabular}"]
    escribir("tabla_auditoria.tex", lineas)


def main():
    grafo = cargar_grafo()
    tabla_estadisticas(grafo)
    tabla_aristas(grafo)
    tabla_rutas(grafo)
    tabla_criterios()
    tabla_auditoria()
    print("Tablas LaTeX escritas en", SALIDA)


if __name__ == "__main__":
    main()
