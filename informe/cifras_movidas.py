"""Comparación de las cifras de los informes antes y después de pasar
párrafos a tablas (outputs/reportes/cifras_movidas.csv).

Para cada informe se expande el .tex con sus \\input (tablas, lecturas y
bloques «Cómo leerla») en `master` (antes) y en el árbol de trabajo
(después) y se cuentan las cifras de cada versión. Una cifra que aparecía
antes y ya no aparece es una pérdida y se reporta; las que cambian de número
de apariciones (por ejemplo, una cifra que estaba repetida en la prosa y en
una tabla) se listan como «menos apariciones».
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
from collections import Counter
from pathlib import Path

INFORMES = ["informe_corte2.tex", "formulacion_corte1.tex"]
ENTRADA = re.compile(r"\\input\{(outputs/[^}]*\.tex)\}")
CIFRA = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")


def antes(ruta):
    r = subprocess.run(["git", "show", f"master:{ruta}"], cwd=RAIZ,
                       capture_output=True, text=True, encoding="utf-8")
    return r.stdout if r.returncode == 0 else ""


def despues(ruta):
    p = RAIZ / ruta
    return p.read_text(encoding="utf-8") if p.exists() else ""


def expandir(ruta, leer):
    texto = re.sub(r"(?m)(?<!\\)%.*$", "", leer(ruta))
    texto = texto.split("\\begin{document}")[-1]
    return ENTRADA.sub(lambda m: expandir(m.group(1), leer), texto)


def normalizar(texto):
    texto = texto.replace("\\,", "").replace("\\ ", " ")
    texto = re.sub(r"\\(?:ref|label|cite|nolinkurl|url|texttt|includegraphics|"
                   r"input)\{[^}]*\}", " ", texto)
    return texto


def cifras(texto):
    return Counter(m.group(0).rstrip(".,") for m in
                   CIFRA.finditer(normalizar(texto)))


def respaldada(cifra, despues_):
    """La cifra con menos decimales queda respaldada por otra más precisa
    que la redondea (456.9 por 456.93)."""
    if "." not in cifra:
        return False
    decimales = len(cifra.split(".")[1])
    for otra in despues_:
        if "." in otra and len(otra.split(".")[1]) > decimales:
            try:
                if round(float(otra), decimales) == float(cifra):
                    return True
            except ValueError:
                pass
    return False


def comparar():
    filas, perdidas = [], []
    for informe in INFORMES:
        a = cifras(expandir(informe, antes))
        d = cifras(expandir(informe, despues))
        for cifra in sorted(set(a) | set(d)):
            if a[cifra] == d[cifra]:
                continue
            if d[cifra] == 0:
                estado = ("respaldada por una cifra más precisa"
                          if respaldada(cifra, d) else "SIN RESPALDO")
            elif a[cifra] > d[cifra]:
                estado = "menos apariciones (quedan en tabla o figura)"
            else:
                estado = "cifra nueva (de una tabla generada)"
            filas.append([informe, cifra, a[cifra], d[cifra], estado])
            if estado == "SIN RESPALDO":
                perdidas.append((informe, cifra))
    return filas, perdidas


def main():
    filas, perdidas = comparar()
    with open(SALIDA / "cifras_movidas.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["informe", "cifra", "apariciones_antes",
                    "apariciones_despues", "estado"])
        w.writerows(filas)
    print(f"{len(filas)} cifras con cambio; {len(perdidas)} sin respaldo")
    for informe, cifra in perdidas:
        print("  ", informe, cifra)


if __name__ == "__main__":
    main()
