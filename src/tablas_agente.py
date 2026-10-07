"""Tablas LaTeX y figura de convergencia del agente multifuncional.

Lee outputs/validacion_agente.json y outputs/umbral_held_karp.json y escribe
tabla_ag_*.tex y convergencia_aco.png / .pdf en outputs/.

Color: cinco series con la paleta categórica validada (azul, naranja,
aguamarina, amarillo, magenta); tres tienen contraste menor que 3:1 con el
fondo, por lo que cada curva lleva rótulo directo y marcador propio, y los
valores completos están en la tabla del informe.
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


def leer(nombre):
    with open(SALIDA / nombre, encoding="utf-8") as f:
        return json.load(f)


def escribir(nombre, lineas):
    with open(SALIDA / nombre, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


def etiqueta(r):
    if r["familia"] == "red de carga":
        if r["k"] == 32:
            return "Red, 32 ciudades"
        return f"Red, k={r['k']} (\\#{r['instancia']})"
    if r["familia"].startswith("euclidiana n=20"):
        return f"Taller n=20, semilla {r['instancia']}"
    return f"Euclidiana n={r['k']}"


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
            f"{a['brecha_mejor_pct']:.3f} & {a['brecha_media_pct']:.3f} & "
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


def tabla_umbral(umbral):
    lineas = ["\\begin{tabular}{rrrrc}", "\\toprule",
              "\\textbf{$k$} & \\textbf{Repeticiones} & "
              "\\textbf{Tiempo mediano (s)} & "
              "\\textbf{Memoria pico (MiB)} & "
              "\\textbf{Dentro del presupuesto} \\\\", "\\midrule"]
    for m in umbral["mediciones"]:
        dentro = "sí" if m["mediana_s"] <= umbral["presupuesto_s"] else "no"
        lineas.append(f"{m['k']} & {m['repeticiones']} & "
                      f"{m['mediana_s']:.3f} & {m['memoria_pico_mib']:.1f} & "
                      f"{dentro} \\\\")
    escribir("tabla_ag_umbral.tex", lineas + ["\\bottomrule",
                                              "\\end{tabular}"])


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


def figura_convergencia(instancias):
    red = [r for r in instancias if r["familia"] == "red de carga"]
    peor_red = max(float(np.max(np.abs(brecha(r)))) for r in red)
    taller = [r for r in instancias
              if r["familia"].startswith("euclidiana n=20")]
    series_taller = [(f"sem. {r['instancia']}", brecha(r)) for r in taller]
    mayores = [r for r in instancias if "mayor" in r["familia"]]
    series_mayores = [(f"n={r['k']}", brecha(r)) for r in mayores]
    fig, ejes = plt.subplots(1, 3, figsize=(13, 4.4), facecolor=SUPERFICIE)
    media_red = np.mean([brecha(r) for r in red], axis=0)
    panel(ejes[0], [(f"{len(red)} instancias", media_red)],
          "Red de carga (k = 5 a 32 ciudades)",
          "Brecha de la media del mejor global (%)")
    ejes[0].set_ylim(-1, 1)
    ejes[0].text(
        50, 0.35, "brecha 0 desde la iteración 1\n"
        f"(máxima en las {len(red)} instancias: {peor_red:.1f} %)",
        ha="center", fontsize=8.5, color=TINTA_2)
    panel(ejes[1], series_taller, "Euclidiana n=20 del taller (exacto)")
    panel(ejes[2], series_mayores,
          "Euclidiana mayor (ref.: mejor con 2-opt)")
    fig.suptitle("Convergencia del ACO + 2-opt: media de 10 semillas",
                 fontsize=11, color=TINTA)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(SALIDA / f"convergencia_aco.{ext}", dpi=200,
                    facecolor=SUPERFICIE)
    plt.close(fig)


def main():
    datos = leer("validacion_agente.json")["instancias"]
    tabla_costos(datos)
    tabla_recursos(datos)
    tabla_umbral(leer("umbral_held_karp.json"))
    figura_convergencia(datos)
    print("Tablas y figura del agente escritas en", SALIDA)


if __name__ == "__main__":
    main()
