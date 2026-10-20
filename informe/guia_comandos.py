"""Genera y verifica GUIA_DE_COMANDOS.md desde la ejecución real del paquete.

Uso:
    python informe/guia_comandos.py generar --paquete DIR --python PY
        [--plantilla informe/guia_plantilla.md] [--salida GUIA.md]
        [--tiempos tiempos.json]
    python informe/guia_comandos.py verificar --paquete DIR --python PY
        [--guia GUIA.md] [--csv verificacion_guia.csv]
    python informe/guia_comandos.py pdf --guia GUIA.md --salida GUIA.pdf

La plantilla tiene bloques ```powershell con los comandos, cada uno seguido
de una línea `{{salida N}}`: el modo `generar` ejecuta el comando dentro del
paquete descomprimido, con el Python indicado, y escribe en su lugar las
primeras N líneas de la salida real (con «…» si se recortó). Los bloques
```powershell-manual se muestran pero no se ejecutan (instalación, corridas
largas, construcción de la red). El modo `verificar` recorre la guía ya
generada, ejecuta cada bloque ```powershell y compara su salida con el
fragmento mostrado, sin los tiempos (que varían entre corridas). El modo
`pdf` arma la guía impresa con LaTeX.
"""
import csv
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

BLOQUE = re.compile(r"```(powershell|powershell-manual|text)\n(.*?)```",
                    re.S)
SALIDA_MARCA = re.compile(r"\{\{salida (\d+)\}\}")
TIEMPOS = [(re.compile(r" +\d+(?:\.\d+)? us"), " <t> us"),
           (re.compile(r"(tiempo\w*: )[\d.e+-]+"), r"\1<t>"),
           (re.compile(r"\(\d+ s\)"), "(<t> s)"),
           (re.compile(r"(reescriben): .*"), r"\1: <archivos>")]


def normalizar(texto):
    for patron, reemplazo in TIEMPOS:
        texto = patron.sub(reemplazo, texto)
    return texto


def ejecutar(comando, paquete, python):
    """Ejecuta un comando `python ...` en el paquete; (rc, salida, s)."""
    argumentos = shlex.split(comando)
    if argumentos[0] != "python":
        raise SystemExit("solo se ejecutan comandos python: " + comando)
    t0 = time.time()
    r = subprocess.run([python, "-B", *argumentos[1:]], cwd=paquete,
                       capture_output=True, encoding="utf-8",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return r.returncode, r.stdout.replace("\r\n", "\n"), time.time() - t0


def comandos_de(bloque):
    return [c.strip() for c in bloque.strip().split("\n")
            if c.strip() and not c.strip().startswith("#")]


def recortar(salida, n):
    lineas = salida.rstrip("\n").split("\n")
    if len(lineas) <= n:
        return "\n".join(lineas)
    return "\n".join(lineas[:n] + ["…"])


def generar(args):
    plantilla = Path(args["plantilla"]).read_text(encoding="utf-8")
    paquete, python = args["paquete"], args["python"]
    partes, pos, n_ejecutados = [], 0, 0
    pendiente = None
    for m in BLOQUE.finditer(plantilla):
        partes.append(plantilla[pos:m.start()])
        pos = m.end()
        tipo, cuerpo = m.group(1), m.group(2)
        partes.append(m.group(0))
        pendiente = (tipo, cuerpo)
        # ¿le sigue una marca {{salida N}}?
        resto = plantilla[pos:]
        marca = SALIDA_MARCA.match(resto.lstrip("\n"))
        if tipo == "powershell" and marca:
            salto = len(resto) - len(resto.lstrip("\n"))
            pos += salto + marca.end()
            salida = []
            for comando in comandos_de(cuerpo):
                rc, texto, _ = ejecutar(comando, paquete, python)
                if rc != 0:
                    raise SystemExit(f"falla (rc {rc}): {comando}")
                salida.append(texto)
                n_ejecutados += 1
            partes.append("\n\n```text\n"
                          + recortar("".join(salida), int(marca.group(1)))
                          + "\n```")
    partes.append(plantilla[pos:])
    texto = "".join(partes)
    if args.get("tiempos"):
        datos = json.loads(Path(args["tiempos"]).read_text(encoding="utf-8"))
        texto = re.sub(r"\{\{tiempo ([^}]+)\}\}",
                       lambda m: duracion(datos[m.group(1)]), texto)
    Path(args["salida"]).write_text(texto, encoding="utf-8", newline="\n")
    print(f"guía escrita: {n_ejecutados} comandos ejecutados")


def duracion(segundos):
    m, s = divmod(round(segundos), 60)
    return f"{m} min {s} s" if m else f"{s} s"


def verificar(args):
    guia = Path(args["guia"]).read_text(encoding="utf-8")
    paquete, python = args["paquete"], args["python"]
    bloques = list(BLOQUE.finditer(guia))
    filas, malos = [], 0
    for i, m in enumerate(bloques):
        if m.group(1) != "powershell":
            continue
        sig = bloques[i + 1] if i + 1 < len(bloques) else None
        fragmento = None
        if sig is not None and sig.group(1) == "text" and \
                guia[m.end():sig.start()].strip() == "":
            fragmento = sig.group(2).rstrip("\n")
        for comando in comandos_de(m.group(2)):
            rc, salida, seg = ejecutar(comando, paquete, python)
            coincide = ""
            if fragmento is not None:
                lineas = fragmento.split("\n")
                truncado = lineas[-1] == "…"
                esperado = lineas[:-1] if truncado else lineas
                real = salida.rstrip("\n").split("\n")[:len(esperado)]
                coincide = (normalizar("\n".join(real))
                            == normalizar("\n".join(esperado)))
            ok = rc == 0 and coincide in ("", True)
            malos += not ok
            filas.append([comando, rc, coincide if coincide != "" else "n/a",
                          len(fragmento.split("\n")) if fragmento else 0,
                          f"{seg:.1f}"])
            print(("OK   " if ok else "FALLA"), f"{seg:5.1f} s", comando)
    with open(args["csv"], "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["comando", "codigo_salida", "salida_coincide",
                    "lineas_mostradas", "segundos"])
        w.writerows(filas)
    print(f"{len(filas) - malos} de {len(filas)} comandos verificados")
    return 1 if malos else 0


# ------------------------------------------------------------------- PDF
def escapar(t):
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                 ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"),
                 ("}", r"\}"), ("~", r"\textasciitilde{}"),
                 ("^", r"\textasciicircum{}")):
        t = t.replace(a, b)
    return t


def en_linea(t):
    """Código `x` y negrita **x** de una línea de texto."""
    partes = re.split(r"(`[^`]+`|\*\*[^*]+\*\*)", t)
    salida = []
    for p in partes:
        if p.startswith("`"):
            codigo = escapar(p[1:-1]).replace(r"\_", r"\_\allowbreak{}")
            codigo = codigo.replace("/", r"/\allowbreak{}")
            salida.append(r"\texttt{" + codigo + "}")
        elif p.startswith("**"):
            salida.append(r"\textbf{" + escapar(p[2:-2]) + "}")
        else:
            salida.append(escapar(p))
    return "".join(salida)


def tabla_tex(lineas):
    filas = [[c.strip() for c in f.strip().strip("|").split("|")]
             for f in lineas if not re.match(r"^\s*\|[-:| ]+\|\s*$", f)]
    n = len(filas[0])
    ancho = {2: ("0.30", "0.62"), 3: ("0.22", "0.40", "0.30")}.get(n)
    if ancho:
        cols = "|" + "|".join(f"p{{{a}\\linewidth}}" for a in ancho) + "|"
    else:
        cols = "|" + "l|" * n
    out = [r"\begin{center}\small", r"\renewcommand{\arraystretch}{1.15}",
           r"\begin{tabular}{" + cols + "}", r"\hline"]
    for i, f in enumerate(filas):
        celdas = " & ".join(r"\textbf{" + en_linea(c) + "}" if i == 0
                            else en_linea(c) for c in f)
        pre = r"\rowcolor{gray!20} " if i == 0 else ""
        out.append(pre + celdas + r" \\ \hline")
    out += [r"\end{tabular}", r"\end{center}"]
    return out


def condensar(md, maximo=5):
    """Versión impresa: salidas de `maximo` líneas y sin las salidas de los
    comandos adicionales del guion (el .md las trae completas)."""
    salida, omitir = [], False
    for parte in re.split(r"(```text\n.*?```)", md, flags=re.S):
        if parte.startswith("```text\n"):
            if omitir:
                continue
            lineas = parte[8:-3].rstrip("\n").split("\n")
            if len(lineas) > maximo:
                lineas = lineas[:maximo] + ["…"]
            parte = "```text\n" + "\n".join(lineas) + "\n```"
        else:
            parte = parte.replace(
                "hecha desde el paquete descomprimido en un entorno "
                "virtual nuevo.",
                "hecha desde el paquete descomprimido en un entorno "
                "virtual nuevo. Esta versión impresa recorta las salidas a "
                f"{maximo} líneas; `GUIA_DE_COMANDOS.md` trae fragmentos de "
                "10 a 30 líneas.")
            parte = parte.replace("(fragmentos de 10 líneas)",
                                  "(sus salidas están en la guía en .md)")
            if "**Otros comandos del guion" in parte:
                omitir = True
            if "\n## 4." in parte:
                omitir = False
        salida.append(parte)
    return "".join(salida)


def a_tex(md):
    cuerpo, lineas, i = [], md.split("\n"), 0
    while i < len(lineas):
        linea = lineas[i]
        if linea.startswith("```"):
            tipo = linea[3:]
            j = i + 1
            while not lineas[j].startswith("```"):
                j += 1
            codigo = "\n".join(lineas[i + 1:j])
            tam = (r"\footnotesize" if tipo.startswith("powershell")
                   else r"\fontsize{6.2}{7.2}\selectfont")
            cuerpo.append("{" + tam)
            cuerpo.append(r"\begin{Verbatim}[breaklines=true,"
                          r"breakanywhere=true,frame=leftline,"
                          r"framesep=1mm,rulecolor=\color{gray}]")
            cuerpo.append(codigo)
            cuerpo.append(r"\end{Verbatim}}")
            i = j + 1
            continue
        if linea.startswith("|"):
            j = i
            while j < len(lineas) and lineas[j].startswith("|"):
                j += 1
            cuerpo += tabla_tex(lineas[i:j])
            i = j
            continue
        m = re.match(r"^(#{1,3}) (.*)", linea)
        if m:
            nivel = len(m.group(1))
            if nivel == 1:
                cuerpo.append(r"\begin{center}{\Large\bfseries "
                              + en_linea(m.group(2)) + r"}\end{center}")
            else:
                cuerpo.append(r"\subsection*{" + en_linea(m.group(2)) + "}")
            i += 1
            continue
        if linea.startswith("- "):
            cuerpo.append(r"\begin{itemize}\itemsep0pt")
            while i < len(lineas) and lineas[i].startswith("- "):
                cuerpo.append(r"\item " + en_linea(lineas[i][2:]))
                i += 1
            cuerpo.append(r"\end{itemize}")
            continue
        if linea.strip().startswith("<!--") or not linea.strip():
            cuerpo.append("")
        else:
            cuerpo.append(en_linea(linea))
        i += 1
    return "\n".join(cuerpo)


ENCABEZADO = r"""\documentclass[9pt,a4paper]{extarticle}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish,es-tabla]{babel}
\usepackage{geometry}
\geometry{margin=1.2cm}
\usepackage{fvextra}
\usepackage{array}
\usepackage[table]{xcolor}
\usepackage{mathptmx}
\usepackage{xurl}
\usepackage{setspace}
\setlength{\parindent}{0pt}
\setlength{\parskip}{3pt}
\pagestyle{plain}
\begin{document}
\sloppy
"""


def pdf(args):
    md = Path(args["guia"]).read_text(encoding="utf-8")
    salida = Path(args["salida"])
    carpeta = salida.parent / "_guia_tmp"
    carpeta.mkdir(exist_ok=True)
    tex = carpeta / "GUIA_DE_COMANDOS.tex"
    tex.write_text(ENCABEZADO + a_tex(condensar(md)) + "\n\\end{document}\n",
                   encoding="utf-8")
    for _ in range(2):
        r = subprocess.run(["pdflatex", "-interaction=nonstopmode",
                            tex.name], cwd=carpeta, capture_output=True)
    pdf_generado = carpeta / "GUIA_DE_COMANDOS.pdf"
    if not pdf_generado.exists():
        sys.exit("pdflatex falló: " + r.stdout.decode("latin-1")[-1500:])
    salida.write_bytes(pdf_generado.read_bytes())
    print("PDF:", salida)


def leer_args(lista):
    ordenes = {"generar", "verificar", "pdf"}
    if not lista or lista[0] not in ordenes:
        sys.exit(__doc__)
    args = {"orden": lista[0],
            "plantilla": str(Path(__file__).with_name("guia_plantilla.md"))}
    for i in range(1, len(lista), 2):
        args[lista[i].lstrip("-")] = lista[i + 1]
    return args


if __name__ == "__main__":
    a = leer_args(sys.argv[1:])
    if a["orden"] == "generar":
        generar(a)
    elif a["orden"] == "verificar":
        sys.exit(verificar(a))
    else:
        pdf(a)
