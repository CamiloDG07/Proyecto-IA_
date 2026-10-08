"""Estilo único de las tablas de los informes.

Todas las tablas (las que escriben los generadores y las escritas a mano en
los .tex) pasan por este módulo: cuadrícula completa, encabezado en negrita
sobre gris claro, rótulo de fila en negrita y separación vertical cómoda.

Los generadores arman sus filas con el orden de siempre (encabezado, cuerpo,
cierre) y llaman a ``estilizar``; ``tabla`` construye el entorno desde cero.
No cambia el contenido de ninguna celda: solo la presentación.
"""
import re
import sys

GRIS_ENCABEZADO = "gray!20"
ESTIRAMIENTO = "1.2"
ENTORNOS = ("tabular", "longtable")


def _tokens_spec(spec):
    """Separa la especificación de columnas en una lista de columnas.

    Cada columna puede llevar prefijos ``>{...}`` y un ``p{...}``.
    """
    columnas, i = [], 0
    while i < len(spec):
        inicio = i
        while spec[i] == ">":
            nivel = 0
            i += 1
            while True:
                if spec[i] == "{":
                    nivel += 1
                elif spec[i] == "}":
                    nivel -= 1
                    if nivel == 0:
                        i += 1
                        break
                i += 1
        if spec[i] in "pmb":
            i += 1
            nivel = 0
            while True:
                if spec[i] == "{":
                    nivel += 1
                elif spec[i] == "}":
                    nivel -= 1
                    if nivel == 0:
                        i += 1
                        break
                i += 1
        else:
            i += 1
        columnas.append(spec[inicio:i])
    return columnas


def spec_con_cuadricula(spec):
    """``lrr`` pasa a ``|l|r|r|``; respeta ``>{...}p{...}``."""
    return "|" + "|".join(_tokens_spec(spec)) + "|"


def _celdas(fila):
    """Divide una fila en celdas por ``&`` que no están dentro de llaves."""
    cuerpo = fila.rstrip()
    assert cuerpo.endswith("\\\\"), fila
    cuerpo = cuerpo[:-2]
    celdas, nivel, actual, i = [], 0, "", 0
    while i < len(cuerpo):
        c = cuerpo[i]
        if c == "\\" and i + 1 < len(cuerpo):
            actual += cuerpo[i:i + 2]
            i += 2
            continue
        if c == "{":
            nivel += 1
        elif c == "}":
            nivel -= 1
        if c == "&" and nivel == 0:
            celdas.append(actual.strip())
            actual = ""
        else:
            actual += c
        i += 1
    celdas.append(actual.strip())
    return celdas


def _negrita(celda):
    if not celda or celda.startswith("\\textbf") \
            or celda.startswith("\\multicolumn"):
        return celda
    return "\\textbf{" + celda + "}"


def _negrita_multicolumn(celda):
    """Pone en negrita el texto de un ``\\multicolumn`` de encabezado."""
    m = re.match(r"(\\multicolumn\{[^}]*\}\{[^}]*\})\{(.*)\}$", celda)
    if m and not m.group(2).startswith("\\textbf"):
        return m.group(1) + "{\\textbf{" + m.group(2) + "}}"
    return celda


def fila_encabezado(celdas):
    celdas = [_negrita_multicolumn(_negrita(c)) for c in celdas]
    return ("\\rowcolor{" + GRIS_ENCABEZADO + "} " + " & ".join(celdas)
            + " \\\\")


def fila_cuerpo(celdas):
    if celdas:
        celdas = [_negrita(celdas[0])] + celdas[1:]
    return " & ".join(celdas) + " \\\\"


def _unir_filas(lineas):
    """Junta las líneas que forman una misma fila (terminan en ``\\\\``)."""
    filas, actual = [], ""
    for linea in lineas:
        actual = (actual + " " + linea.strip()).strip() if actual \
            else linea.strip()
        if actual.endswith("\\\\"):
            filas.append(actual)
            actual = ""
    assert not actual, actual
    return filas


def tabla(spec, encabezado, cuerpo, entorno="tabular", preambulo=()):
    """Construye una tabla con el estilo único.

    ``encabezado`` y ``cuerpo`` son listas de filas (cadenas terminadas en
    ``\\\\``). Una fila que sea solo ``\\midrule`` en el cuerpo se ignora:
    todas las filas ya van separadas por ``\\hline``.
    """
    s = spec_con_cuadricula(spec)
    lineas = ["\\renewcommand{\\arraystretch}{" + ESTIRAMIENTO + "}",
              "\\begin{" + entorno + "}{" + s + "}"]
    lineas += list(preambulo)
    lineas.append("\\hline")
    for f in encabezado:
        lineas += [fila_encabezado(_celdas(f)), "\\hline"]
    if entorno == "longtable":
        lineas.append("\\endhead")
    for f in cuerpo:
        lineas += [fila_cuerpo(_celdas(f)), "\\hline"]
    lineas.append("\\end{" + entorno + "}")
    return lineas


def estilizar(lineas):
    """Convierte las líneas de una tabla al estilo único.

    Acepta el formato de siempre: ``\\begin{tabular|longtable}{spec}``,
    ``\\toprule``, encabezado, ``\\midrule``, cuerpo (con ``\\midrule``
    opcionales entre grupos) y ``\\bottomrule``. Si la tabla ya tiene el
    estilo nuevo (no trae ``\\toprule``), la devuelve igual.
    """
    if not any("\\toprule" in linea for linea in lineas):
        return list(lineas)
    primera = next(i for i, linea in enumerate(lineas)
                   if re.match(r"\\begin\{(tabular|longtable)\}", linea))
    m = re.match(r"\\begin\{(tabular|longtable)\}(.*)$", lineas[primera])
    entorno, resto = m.group(1), m.group(2)
    spec, nivel, fin = "", 0, 0
    for fin, c in enumerate(resto):
        if c == "{":
            nivel += 1
            if nivel == 1:
                continue
        elif c == "}":
            nivel -= 1
            if nivel == 0:
                break
        spec += c
    previas = [linea for linea in lineas[:primera]]
    posteriores_spec = resto[fin + 1:].strip()
    ultima = max(i for i, linea in enumerate(lineas)
                 if linea.startswith("\\end{" + entorno + "}"))
    interior = lineas[primera + 1:ultima]
    # líneas antes de \toprule (por ejemplo, el título de un longtable)
    t = next(i for i, linea in enumerate(interior) if "\\toprule" in linea)
    preambulo = [linea for linea in interior[:t]]
    resto_i = interior[t + 1:]
    medio = next(i for i, linea in enumerate(resto_i)
                 if linea.strip() == "\\midrule")
    encabezado = _unir_filas(resto_i[:medio])
    cuerpo_crudo = [linea for linea in resto_i[medio + 1:]
                    if linea.strip() not in ("\\midrule", "\\bottomrule",
                                             "\\endhead")
                    and not linea.startswith("\\addlinespace")]
    cuerpo = _unir_filas(cuerpo_crudo)
    salida = list(previas)
    salida += tabla(spec, encabezado, cuerpo, entorno, preambulo)
    if posteriores_spec:
        salida[len(previas) + 1] += posteriores_spec
    return salida


def estilizar_archivo_tex(ruta):
    """Aplica el estilo a todas las tablas escritas a mano en un .tex."""
    texto = open(ruta, encoding="utf-8", newline="").read()
    fin_linea = "\r\n" if "\r\n" in texto else "\n"
    lineas = texto.replace("\r\n", "\n").split("\n")
    salida, i = [], 0
    while i < len(lineas):
        if re.match(r"\\begin\{(tabular|longtable)\}", lineas[i]):
            entorno = re.match(r"\\begin\{(\w+)\}", lineas[i]).group(1)
            j = i
            while not lineas[j].startswith("\\end{" + entorno + "}"):
                j += 1
            salida += estilizar(lineas[i:j + 1])
            i = j + 1
        else:
            salida.append(lineas[i])
            i += 1
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        f.write(fin_linea.join(salida))


if __name__ == "__main__":
    for ruta in sys.argv[1:]:
        estilizar_archivo_tex(ruta)
