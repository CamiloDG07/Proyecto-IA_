"""Detección de párrafos y viñetas con cifras comparables
(outputs/reportes/candidatos_tablas.csv).

Recorre los .tex de `master` (antes de la conversión), separa párrafos y
viñetas fuera de tablas, figuras, ecuaciones y bloques «Cómo leerla» y lista
los que tienen 3 o más cifras que comparan entidades de la misma clase
(algoritmos, criterios, variantes, sesiones, instancias o aristas). La
decisión se toma contra el árbol de trabajo: «convertir» si el pasaje ya no
está como prosa y su información quedó en una tabla nueva; «ya hay tabla» si
quedó en una tabla existente; «dejar» si sigue como prosa.
"""
import sys
from pathlib import Path
if True:  # carpetas de código en el path
    sys.path[:0] = [str(Path(__file__).resolve().parents[1] / c)
                    for c in ("src", "experimentos", "informe", "pruebas")]
from rutas import RAIZ, SALIDA
import csv
import re
import subprocess
from pathlib import Path

INFORMES = ["informe_corte2.tex", "formulacion_corte1.tex"]
ENTIDADES = {
    "algoritmos": r"\b(BFS|DFS|UCS|voraz|A\*)",
    "criterios": r"\b(distancia|peaje|riesgo|compuesto|costo operativo)\b",
    "variantes": r"(sin piso|con piso|progresivas|sin corregir|cruda)",
    "sesiones": r"\b(sesi[oó]n|sesiones|S[123])\b",
    "instancias": r"(escenario|instancia|euclidiana|red de carga|n\s*=)",
    "aristas": r"(arista|Chocontá|Tunja|Bogotá|registro)",
}
CIFRA = re.compile(r"(?<![\w\\{])\d+(?:[.,]\d+)*(?![\w}])")
# pasajes que quedaron en una tabla existente y no en una nueva
YA_HAY_TABLA = ("Verificación numérica", "Valor de $\\alpha$",
                "El desvío es 283.71 km más largo")
# pasajes que conservan su prosa por no comparar entidades de una clase
DEJAR = ("Hallazgos", "Chocontá a Tunja truncada")


def fuente(ruta, rev):
    if rev:
        r = subprocess.run(["git", "show", f"{rev}:{ruta}"], cwd=RAIZ,
                           capture_output=True, text=True, encoding="utf-8")
        return r.stdout
    return (RAIZ / ruta).read_text(encoding="utf-8")


def bloques(texto):
    texto = re.sub(r"(?m)(?<!\\)%.*$", "", texto)
    previo, _, resto = texto.partition("\\begin{document}")
    texto = "\n" * previo.count("\n") + resto
    texto = re.sub(r"\\begin\{(table|figure|equation|longtable|tabular)\*?\}"
                   r".*?\\end\{\1\*?\}",
                   lambda m: "\n" * m.group(0).count("\n"), texto, flags=re.S)
    texto = re.sub(r"\\comoleerla.*", "", texto)
    lineas = texto.split("\n")
    actual, inicio, salida = [], 0, []
    for i, linea in enumerate(lineas, 1):
        corte = (not linea.strip() or linea.startswith("\\item")
                 or linea.startswith("\\begin") or linea.startswith("\\end")
                 or linea.startswith("\\section")
                 or linea.startswith("\\subsection"))
        if corte and actual:
            salida.append((inicio, i - 1, " ".join(actual)))
            actual = []
        if linea.strip() and not linea.startswith(("\\begin", "\\end",
                                                   "\\section",
                                                   "\\subsection")):
            if not actual:
                inicio = i
            actual.append(linea.strip())
    if actual:
        salida.append((inicio, len(lineas), " ".join(actual)))
    return salida


def seccion(texto, linea):
    previas = re.findall(r"\\(?:sub)?section\{([^}]*)\}",
                         "\n".join(texto.split("\n")[:linea]))
    return previas[-1] if previas else ""


def main():
    filas = []
    for informe in INFORMES:
        antes, ahora = fuente(informe, "master"), fuente(informe, None)
        plano_ahora = " ".join(ahora.split())
        for ini, fin, bloque in bloques(antes):
            cifras = CIFRA.findall(re.sub(r"\\(ref|label|cite)\{[^}]*\}", "",
                                          bloque))
            clases = [k for k, p in ENTIDADES.items()
                      if len(re.findall(p, bloque)) >= 2]
            if len(cifras) < 3 or not clases:
                continue
            sigue = " ".join(bloque.split())[:70] in plano_ahora
            if any(k in bloque for k in YA_HAY_TABLA):
                decision = "ya hay tabla"
            elif sigue or any(k in bloque for k in DEJAR):
                decision = "dejar"
            else:
                decision = "convertir"
            filas.append([informe, seccion(antes, ini), f"{ini}-{fin}",
                          len(cifras), "; ".join(clases), decision])
    with open(SALIDA / "candidatos_tablas.csv", "w",
              encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["archivo", "seccion", "lineas", "numero_de_cifras",
                    "entidades_comparadas", "decision"])
        w.writerows(filas)
    cuenta = {}
    for fila in filas:
        cuenta[fila[5]] = cuenta.get(fila[5], 0) + 1
    print(len(filas), "candidatos:", cuenta)


if __name__ == "__main__":
    main()
