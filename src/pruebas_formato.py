"""Pruebas del estilo único de tablas (formato_latex.py).

Comprueban la cuadrícula, el encabezado sombreado, el rótulo de fila en
negrita, que el contenido de las celdas no cambie y que aplicar el estilo
dos veces dé el mismo resultado.
"""
import glob
import subprocess
import sys

from build_graph import SALIDA
from formato_latex import estilizar, spec_con_cuadricula

MUESTRA = [
    "\\begin{tabular}{lrr}", "\\toprule",
    "\\textbf{Medida} & \\textbf{A} & \\textbf{B} \\\\", "\\midrule",
    "uno & 1 & 2 \\\\", "dos & 3 & 4 \\\\", "\\bottomrule",
    "\\end{tabular}"]


def ok(mensaje):
    print(f"  ok: {mensaje}")


def main():
    assert spec_con_cuadricula("lrr") == "|l|r|r|"
    assert spec_con_cuadricula(
        ">{\\raggedright\\arraybackslash}p{2cm}r") == (
        "|>{\\raggedright\\arraybackslash}p{2cm}|r|")
    ok("especificación de columnas con cuadrícula")

    salida = estilizar(MUESTRA)
    texto = "\n".join(salida)
    assert "\\toprule" not in texto and "\\midrule" not in texto
    assert salida.count("\\hline") == 4
    assert "\\rowcolor{gray!20}" in texto
    assert "\\textbf{uno} & 1 & 2 \\\\" in texto
    assert "\\renewcommand{\\arraystretch}{1.2}" in texto
    ok("cuadrícula, encabezado sombreado y rótulo en negrita")

    assert estilizar(salida) == salida
    ok("idempotente")

    largo = ["\\begin{longtable}{lr}", "\\caption{T}\\label{t}\\\\",
             "\\toprule", "\\textbf{X} & \\textbf{Y} \\\\", "\\midrule",
             "\\endhead", "a & 1 \\\\", "\\bottomrule", "\\end{longtable}"]
    res = estilizar(largo)
    assert "\\endhead" in res and "\\caption{T}\\label{t}\\\\" in res
    ok("longtable conserva título y repetición del encabezado")

    pendientes = []
    for ruta in glob.glob(str(SALIDA / "tabla_*.tex")):
        with open(ruta, encoding="utf-8") as f:
            if "\\toprule" in f.read():
                pendientes.append(ruta)
    assert not pendientes, pendientes
    ok("ninguna tabla generada conserva el estilo anterior")

    r = subprocess.run([sys.executable, "-m", "pycodestyle", __file__],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
    ok("pycodestyle limpio")
    print("Todas las pruebas del formato pasaron.")


if __name__ == "__main__":
    main()
