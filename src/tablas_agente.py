"""Tablas LaTeX y figuras de convergencia del agente multifuncional.

Lee outputs/validacion_agente.json, umbral_held_karp.json y
verificacion_estructura.json y escribe tabla_ag_*.tex y las figuras
convergencia_aco (red de carga y taller) y convergencia_aco_mayores en
outputs/.

Nomenclatura: n = ciudades de la instancia; k = paradas libres (n - 1 con
regreso al origen).

Color: la paleta categórica validada (azul, naranja, aguamarina, amarillo,
magenta); tres colores tienen contraste menor que 3:1 con el fondo, por lo
que cada curva lleva rótulo directo y marcador propio, y los valores
completos están en las tablas.
"""
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from build_graph import SALIDA  # noqa: E402

SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
COLORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
MARCADORES = ["o", "s", "^", "D", "v"]
NS_RED = (5, 10, 15, 20, 32)


def leer(nombre):
    with open(SALIDA / nombre, encoding="utf-8") as f:
        return json.load(f)


def escribir(nombre, lineas):
    with open(SALIDA / nombre, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


def etiqueta(r):
    if r["familia"] == "red de carga":
        return f"Red, $n={r['n']}$ (\\#{r['instancia']})"
    if r["familia"].startswith("euclidiana n=20"):
        return f"Taller $n=20$, semilla {r['instancia']}"
    return f"Euclidiana $n={r['n']}$"


def referencia_corta(r):
    tipo = r["referencia"]["tipo"]
    if "Held-Karp" in tipo:
        return "exacto"
    if "unicíclica" in tipo:
        return "estructura"
    return "2-opt"


def costo(r, valor):
    return f"{valor:.2f}" if r["familia"] == "red de carga" else \
        f"{valor:.4f}"


def grupos(instancias):
    """Grupos del cuerpo: red por n y taller (n = 20), con sus instancias."""
    salida = []
    red = [r for r in instancias if r["familia"] == "red de carga"]
    for n in NS_RED:
        miembros = [r for r in red if r["n"] == n]
        nombre = (f"Red, $n={n}$" if n != 32 else "Red, $n=32$ (todas)")
        salida.append((nombre, miembros))
    taller = [r for r in instancias
              if r["familia"].startswith("euclidiana n=20")]
    salida.append(("Taller, $n=20$", taller))
    return salida


def media(valores):
    return sum(valores) / len(valores)


def pct(valor):
    """Porcentaje con tres decimales; evita el cero negativo."""
    return f"{0.0 if abs(valor) < 5e-4 else valor:.3f}"


def seg(valor):
    """Segundos con 3 decimales (4 si es menor que 0.01)."""
    return f"{valor:.4f}" if valor < 0.01 else f"{valor:.3f}"


def tabla_resumen(instancias):
    """UNA tabla de validación para el cuerpo del informe."""
    lineas = ["\\begin{tabular}{lcrrrrr}", "\\toprule",
              "\\textbf{Grupo} & \\textbf{Inst.} & "
              "\\textbf{Brecha media (\\%)} & "
              "\\textbf{Br. mejor, máx. (\\%)} & \\textbf{Igualan} & "
              "\\textbf{ACO t (s)} & \\textbf{Exacto t (s)} \\\\",
              "\\midrule"]
    for nombre, miembros in grupos(instancias):
        brechas = [r["aco"]["brecha_media_pct"] for r in miembros]
        mejores = [r["aco"]["brecha_mejor_pct"] for r in miembros]
        iguales = sum(r["aco"]["semillas_que_igualan_referencia"]
                      for r in miembros)
        total = 10 * len(miembros)
        t_aco = media([r["aco"]["tiempo_medio_s"] for r in miembros])
        exactos = [r["exacto"]["tiempo_s"] for r in miembros
                   if "exacto" in r]
        t_ex = seg(media(exactos)) if exactos else "---"
        lineas.append(
            f"{nombre} & {len(miembros)} & {pct(media(brechas))} & "
            f"{pct(max(mejores))} & {iguales}/{total} & {t_aco:.3f} & "
            f"{t_ex} \\\\")
    escribir("tabla_ag_resumen.tex",
             lineas + ["\\bottomrule", "\\end{tabular}"])


def tabla_costos(instancias):
    lineas = ["\\begin{tabular}{llrrrrrr}", "\\toprule",
              "\\textbf{Instancia} & \\textbf{Ref.} & \\textbf{Costo ref.} & "
              "\\textbf{Mejor} & \\textbf{Medio} & "
              "\\textbf{Br. mejor (\\%)} & \\textbf{Br. media (\\%)} & "
              "\\textbf{Igualan} \\\\", "\\midrule"]
    for r in instancias:
        a = r["aco"]
        lineas.append(
            f"{etiqueta(r)} & {referencia_corta(r)} & "
            f"{costo(r, r['referencia']['costo'])} & "
            f"{costo(r, a['costo_mejor'])} & {costo(r, a['costo_medio'])} & "
            f"{pct(a['brecha_mejor_pct'])} & "
            f"{pct(a['brecha_media_pct'])} & "
            f"{a['semillas_que_igualan_referencia']}/10 \\\\")
    escribir("tabla_ag_costos.tex", lineas + ["\\bottomrule",
                                              "\\end{tabular}"])


def tabla_recursos(instancias):
    lineas = ["\\begin{tabular}{lrrrr}", "\\toprule",
              "\\textbf{Instancia} & \\textbf{ACO t (s)} & "
              "\\textbf{ACO mem. (KiB)} & \\textbf{Exacto t (s)} & "
              "\\textbf{Exacto mem. (MiB)} \\\\", "\\midrule"]
    for r in instancias:
        a, e = r["aco"], r.get("exacto")
        exacto = (f"{e['tiempo_s']:.3f} & {e['memoria_pico_mib']:.1f}"
                  if e else "--- & ---")
        lineas.append(
            f"{etiqueta(r)} & {a['tiempo_medio_s']:.3f} $\\pm$ "
            f"{a['tiempo_desv_s']:.3f} & {a['memoria_pico_kib']:.0f} & "
            f"{exacto} \\\\")
    escribir("tabla_ag_recursos.tex", lineas + ["\\bottomrule",
                                                "\\end{tabular}"])


def tabla_sin_2opt(instancias):
    """ACO sin búsqueda local frente al ACO con 2-opt, por grupo."""
    lineas = ["\\begin{tabular}{lrrrr}", "\\toprule",
              "\\textbf{Grupo} & \\textbf{Br. con 2-opt (\\%)} & "
              "\\textbf{Igualan con} & "
              "\\textbf{Br. sin 2-opt (\\%)} & "
              "\\textbf{Igualan sin} \\\\", "\\midrule"]
    for nombre, miembros in grupos(instancias):
        con = [r["aco"] for r in miembros]
        sin = [r["aco_sin_2opt"] for r in miembros]
        total = 10 * len(miembros)
        lineas.append(
            f"{nombre} & "
            f"{pct(media([a['brecha_media_pct'] for a in con]))} & "
            f"{sum(a['semillas_que_igualan_referencia'] for a in con)}"
            f"/{total} & "
            f"{pct(media([a['brecha_media_pct'] for a in sin]))} & "
            f"{sum(a['semillas_que_igualan_referencia'] for a in sin)}"
            f"/{total} \\\\")
    escribir("tabla_ag_sin_2opt.tex",
             lineas + ["\\bottomrule", "\\end{tabular}"])


def tabla_umbral(umbral):
    limite = umbral["limite_memoria_mib"]
    lineas = ["\\begin{tabular}{rrrrrcc}", "\\toprule",
              "\\textbf{$k$} & \\textbf{Rep.} & "
              "\\textbf{Mediana (s)} & \\textbf{Rango (s)} & "
              "\\textbf{Memoria pico (MiB)} & "
              "\\textbf{Tiempo} & \\textbf{Memoria} \\\\", "\\midrule"]
    for m in umbral["mediciones"]:
        ok_t = "sí" if m["mediana_s"] <= umbral["presupuesto_s"] else "no"
        ok_m = "sí" if m["memoria_pico_mib"] <= limite else "no"
        lineas.append(
            f"{m['k']} & {m['repeticiones']} & {m['mediana_s']:.3f} & "
            f"{m['minimo_s']:.3f} a {m['maximo_s']:.3f} & "
            f"{m['memoria_pico_mib']:.1f} & {ok_t} & {ok_m} \\\\")
    escribir("tabla_ag_umbral.tex", lineas + ["\\bottomrule",
                                              "\\end{tabular}"])


def tabla_estructura(verificacion):
    longitudes = [int(k) for k in verificacion["longitudes_de_ciclo"]]
    largos = f"{min(longitudes)} a {max(longitudes)}"
    filas = [
        ("Grafos aleatorios de un solo ciclo", str(verificacion["grafos"])),
        ("Nodos por grafo", verificacion["nodos"]),
        ("Coincidencias con Held-Karp", str(verificacion["coincidencias"])),
        ("Discrepancias", str(len(verificacion["discrepancias"]))),
        ("Mayor diferencia absoluta",
         f"{verificacion['mayor_diferencia_absoluta']:.2e}"),
        ("Longitud del ciclo (aristas)", largos),
    ]
    escribir("tabla_ag_estructura.tex",
             ["\\begin{tabular}{lr}", "\\toprule",
              "\\textbf{Medida} & \\textbf{Valor} \\\\", "\\midrule"]
             + [f"{a} & {b} \\\\" for a, b in filas]
             + ["\\bottomrule", "\\end{tabular}"])


def brecha(r):
    """Brecha (%) de la media del mejor global; |x| < 1e-9 se toma como 0."""
    ref = r["referencia"]["costo"]
    g = 100 * (np.array(r["aco"]["curva_media"]) - ref) / ref
    return np.where(np.abs(g) < 1e-9, 0.0, g)


def separar(valores, minimo):
    """Posiciones de rótulo sin solaparse, en el orden de los valores."""
    orden = sorted(range(len(valores)), key=lambda i: valores[i])
    pos = {}
    anterior = None
    for i in orden:
        y = valores[i] if anterior is None else max(valores[i],
                                                    anterior + minimo)
        pos[i] = y
        anterior = y
    return [pos[i] for i in range(len(valores))]


def panel(ax, series, titulo, ylabel=None):
    ax.set_facecolor(SUPERFICIE)
    finales = [float(c[-1]) for _, c in series]
    todos = np.concatenate([np.asarray(c) for _, c in series])
    rango = max(float(todos.max() - todos.min()), 1e-9)
    posiciones = separar(finales, 0.07 * rango)
    for i, (nombre, curva) in enumerate(series):
        x = np.arange(1, len(curva) + 1)
        ax.plot(x, curva, color=COLORES[i], lw=1.8, zorder=3 + i)
        ax.plot(x[::12], np.asarray(curva)[::12], MARCADORES[i],
                color=COLORES[i], ms=5, mec=SUPERFICIE, mew=0.8,
                zorder=4 + i)
        ax.annotate(nombre, (x[-1], curva[-1]),
                    xytext=(x[-1] + 2, posiciones[i]), fontsize=7.5,
                    color=TINTA, va="center", annotation_clip=False)
    ax.set_title(titulo, fontsize=9.5, color=TINTA)
    ax.set_xlabel("Iteración", color=TINTA)
    if ylabel:
        ax.set_ylabel(ylabel, color=TINTA)
    ax.set_xlim(1, 100)
    ax.grid(color="#e6e5e1", lw=0.6)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)


def guardar(fig, nombre):
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(SALIDA / f"{nombre}.{ext}", dpi=200,
                    facecolor=SUPERFICIE)
    plt.close(fig)


def figura_convergencia(instancias):
    red = [r for r in instancias if r["familia"] == "red de carga"]
    peor_red = max(float(np.max(np.abs(brecha(r)))) for r in red)
    taller = [r for r in instancias
              if r["familia"].startswith("euclidiana n=20")]
    series_taller = [(f"sem. {r['instancia']}", brecha(r)) for r in taller]
    fig, ejes = plt.subplots(1, 2, figsize=(9.5, 4.4), facecolor=SUPERFICIE)
    media_red = np.mean([brecha(r) for r in red], axis=0)
    panel(ejes[0], [(f"{len(red)} instancias", media_red)],
          "Red de carga ($n$ = 5 a 32 ciudades)",
          "Brecha de la media del mejor global (%)")
    ejes[0].set_ylim(-1, 1)
    ejes[0].text(
        50, 0.35, "brecha 0 desde la iteración 1\n"
        f"(máxima en las {len(red)} instancias: {peor_red:.1f} %)",
        ha="center", fontsize=8.5, color=TINTA_2)
    panel(ejes[1], series_taller, "Euclidiana $n=20$ del taller (exacto)")
    fig.suptitle("Convergencia del ACO + 2-opt: media de 10 semillas",
                 fontsize=11, color=TINTA)
    guardar(fig, "convergencia_aco")


def figura_mayores(instancias):
    mayores = [r for r in instancias if "mayor" in r["familia"]]
    series = [(f"n={r['n']}", brecha(r)) for r in mayores]
    fig, ax = plt.subplots(figsize=(5.2, 4.2), facecolor=SUPERFICIE)
    panel(ax, series, "Euclidiana mayor (ref.: mejor con 2-opt)",
          "Brecha de la media del mejor global (%)")
    fig.suptitle("ACO + 2-opt: media de 10 semillas", fontsize=11,
                 color=TINTA)
    guardar(fig, "convergencia_aco_mayores")


def main():
    datos = leer("validacion_agente.json")["instancias"]
    tabla_resumen(datos)
    tabla_costos(datos)
    tabla_recursos(datos)
    tabla_sin_2opt(datos)
    tabla_umbral(leer("umbral_held_karp.json"))
    tabla_estructura(leer("verificacion_estructura.json"))
    figura_convergencia(datos)
    figura_mayores(datos)
    print("Tablas y figuras del agente escritas en", SALIDA)


if __name__ == "__main__":
    main()
