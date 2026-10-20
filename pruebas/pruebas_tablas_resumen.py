"""Pruebas de las tablas de resumen (informe/tablas_resumen.py).

Comprueban que cada tabla tiene a lo sumo 6 columnas, que sus cifras
coinciden con las de outputs/ recalculadas aparte y que los archivos están
en el estilo único (cuadrícula y encabezado gris).
"""
import sys
from pathlib import Path
if True:  # carpetas de código en el path
    sys.path[:0] = [str(Path(__file__).resolve().parents[1] / c)
                    for c in ("src", "experimentos", "informe", "pruebas")]
from rutas import RAIZ, SALIDA
import json
import re
import subprocess
import sys
from pathlib import Path

import tablas_resumen as tr

TABLAS = ["distancia", "sobrecosto", "nodos", "umbral_costo", "no_optimos",
          "umbral_sesiones", "tiempos", "cambio_sin_riesgo",
          "pruebas_ciclo"]


def ok(condicion, mensaje):
    if not condicion:
        print(f"  FALLA: {mensaje}")
        sys.exit(1)
    print(f"  ok: {mensaje}")


def cargar(nombre):
    with open(SALIDA / nombre, encoding="utf-8") as f:
        return json.load(f)


def filas_archivo(nombre):
    texto = (SALIDA / f"tabla_r_{nombre}.tex").read_text(encoding="utf-8")
    filas = [x for x in texto.splitlines() if x.rstrip().endswith("\\\\")
             and not x.startswith("\\rowcolor")]
    return texto, [[c.strip().replace("\\textbf{", "").rstrip("}")
                    for c in x.rstrip(" \\").split(" & ")] for x in filas]


def main():
    tr.main()
    for nombre in TABLAS:
        texto, filas = filas_archivo(nombre)
        columnas = max(len(f) for f in filas)
        ok(columnas <= 6, f"{nombre}: {columnas} columnas (máximo 6)")
        ok("\\rowcolor{gray!20}" in texto and "\\hline" in texto,
           f"{nombre}: estilo de cuadrícula y encabezado gris")
        ok(all(len(f) == columnas for f in filas),
           f"{nombre}: todas las filas tienen {columnas} celdas")

    res = cargar("resultados_corte2.json")["resultados"]
    # nodos de los diez escenarios, recalculados aparte
    _, filas = filas_archivo("nodos")
    for fila in filas:
        criterio = next(k for k, v in tr.NOMBRES_CRITERIO.items()
                        if v == fila[0])
        esperado = [sum(c["nodos_expandidos"] for c in res
                        if c["criterio"] == criterio and c["algoritmo"] == a)
                    for a in tr.ALGORITMOS]
        ok([int(x) for x in fila[1:]] == esperado,
           f"nodos de {criterio}: {esperado}")
    # sobrecosto: el óptimo de UCS, voraz y A* es 0 y DFS cuesta más
    _, filas = filas_archivo("sobrecosto")
    ok(all(float(f[5]) == 0.0 for f in filas),
       "UCS, voraz y A* son óptimos en los cuatro criterios")
    ok(all(float(f[2]) > 0 for f in filas),
       "DFS paga sobrecosto en el caso central con los cuatro criterios")
    # distancia: cada fila coincide con la celda del JSON
    _, filas = filas_archivo("distancia")
    for fila in filas:
        c = tr.celda_resultado(res, tr.CENTRAL, "distancia", fila[0])
        ok(fila[1] == f"{tr.via(c['ruta'])}, {c['costo']:.2f}"
           and int(fila[3]) == c["nodos_expandidos"],
           f"distancia, {fila[0]}: ruta, costo y nodos del JSON")
    # umbral de costo: el umbral separa las dos rutas
    d = tr.cifras_dinero()
    _, filas = filas_archivo("umbral_costo")
    u = d["umbrales"]["piso"]
    ok(abs(float(filas[0][3]) - u["cop_por_km"]) < 0.05
       and abs(float(filas[0][1]) - u["km_extra"]) < 0.005,
       "umbral con piso igual al de umbral_costo.py")
    # pares no óptimos
    sens = cargar("sensibilidad_corte2.json")
    _, filas = filas_archivo("no_optimos")
    ok(len(filas) == sens["todos_los_pares"]["no_optimos_sin_piso_alfa1"],
       "pares no óptimos de la tabla = 3 del JSON")
    # Corte 1: distancias del modelo igual a las de pruebas_agente.json
    pruebas = cargar("pruebas_agente.json")["ciclo"]
    _, filas = filas_archivo("pruebas_ciclo")
    ok(float(filas[0][2]) == pruebas["corta"]["distancia_total_km"]
       and float(filas[1][2]) == pruebas["desvio"]["distancia_total_km"],
       "pruebas del ciclo: distancias del modelo = pruebas_agente.json")
    # sin cifras escritas a mano: el módulo no tiene literales numéricos
    # con decimales fuera de formatos
    fuente = (RAIZ / "informe" / "tablas_resumen.py").read_text(
        encoding="utf-8")
    ok(not re.search(r"(?<![\w.{:])\d+\.\d{2,}(?![\w}])",
                     re.sub(r'f?"[^"\n]*"', "", fuente)),
       "tablas_resumen.py no contiene cifras escritas a mano")
    r = subprocess.run([sys.executable, "-m", "pycodestyle",
                        str(RAIZ / "informe" / "tablas_resumen.py"),
                        str(Path(__file__))], capture_output=True, text=True)
    ok(r.returncode == 0, "pycodestyle limpio" + r.stdout[:200])
    print("Todas las pruebas de las tablas de resumen pasaron.")


if __name__ == "__main__":
    main()
