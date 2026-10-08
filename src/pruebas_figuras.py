"""Pruebas de las figuras de los informes (src/figuras_informe.py).

Comprueban que los números rotulados coinciden con outputs/, que las figuras
se regeneran desde outputs/ y outputs/trazado_aristas.json sin el
red_vial.csv de 238 MB, que la letra mínima es de 7 pt a ancho de texto, que
ninguna caja de texto se cruza con otra ni con la leyenda y que el código
cumple pycodestyle.
"""
import itertools
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.text import Annotation, Text  # noqa: E402
from matplotlib.transforms import Bbox  # noqa: E402

import figuras_informe as fi  # noqa: E402
import mapa_geografico as mg  # noqa: E402
from build_graph import cargar_grafo  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def ok(condicion, mensaje):
    if not condicion:
        print(f"  FALLA: {mensaje}")
        sys.exit(1)
    print(f"  ok: {mensaje}")


def textos(fig):
    return " ".join(t.get_text().replace("\n", " ")
                    for t in fig.findobj(Text))


def cajas(fig):
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    res = [(n, Bbox([[r[0], r[1]], [r[2], r[3]]]))
           for n, r in getattr(fig, "cajas", [])]
    for ax in fig.axes:
        for t in ax.texts:
            if (t.get_text() and not isinstance(t, Annotation)
                    and t.get_color() != "#a9a79f"):
                res.append((t.get_text(), t.get_window_extent(rend)))
        leg = ax.get_legend()
        if leg is not None:
            res.append(("leyenda", leg.get_window_extent(rend)))
    return res


def revisar(fig, nombre):
    c = cajas(fig)
    choques = [(a, b) for (a, ba), (b, bb) in itertools.combinations(c, 2)
               if ba.x0 < bb.x1 and bb.x0 < ba.x1 and ba.y0 < bb.y1
               and bb.y0 < ba.y1]
    ok(not choques, f"{nombre}: ninguna caja de texto se cruza con otra "
       f"({len(c)} cajas)" + (f"; cruces: {choques[:3]}" if choques else ""))
    ok(getattr(fig, "solapes", 0) == 0, f"{nombre}: 0 rótulos montados")
    tam = [t.get_fontsize() for t in fig.findobj(Text) if t.get_text().strip()]
    minimo = getattr(fig, "fuente_minima", fi.FUENTE)
    ok(min(tam) >= minimo - 1e-9,
       f"{nombre}: letra mínima {min(tam):.1f} pt (>= {minimo:.0f})")
    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "f.pdf"
        fig.savefig(ruta, facecolor=fi.SUPERFICIE)
        pdf = ruta.read_bytes()
    caja = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)", pdf)
    ancho, alto = float(caja.group(1)) / 72, float(caja.group(2)) / 72
    ok(abs(ancho - fi.ANCHO_IN) < 0.01 and alto < 9.2,
       f"{nombre}: PDF de {ancho:.3f} x {alto:.2f} in (ancho de texto)")


def main():
    grafo = cargar_grafo()
    original = mg.construir_trazado

    def prohibido():
        raise AssertionError("se intentó leer red_vial.csv")
    mg.construir_trazado = prohibido
    try:
        trazado = mg.cargar_trazado()
        figs = {}
        for nombre, funcion in fi.FIGURAS:
            figs[nombre] = funcion(grafo, trazado)
        figs["fig_cobertura"] = fi.fig_cobertura(grafo, trazado)[0]
    finally:
        mg.construir_trazado = original
    ok(True, f"las {len(figs)} figuras se regeneran desde outputs/ sin "
       "red_vial.csv")
    res = fi.leer("resultados_corte2.json")["resultados"]
    # mapas de expansión
    t = textos(figs["fig_expansion"])
    for a in fi.ALGORITMOS:
        c = fi.celda(res, fi.ORIGEN, fi.DESTINO, "distancia", a)
        veredicto = "no óptima" if c["costo"] > fi.celda(
            res, fi.ORIGEN, fi.DESTINO, "distancia", "UCS")["costo"] \
            else "óptima"
        ok(f"{a}: {c['nodos_expandidos']} expandidos" in t
           and f"{c['costo']:.2f} km, {veredicto}" in t,
           f"expansión: {a} rotula {c['nodos_expandidos']} expandidos, "
           f"{c['costo']:.2f} km y {veredicto} (los guardados)")
        ok(figs["fig_expansion"].estados[a][0] == c["nodos_expandidos"],
           f"expansión: {a} recalcula {c['nodos_expandidos']} nodos "
           "expandidos (los guardados)")
    # comparación de algoritmos
    fig = figs["fig_comparacion"]
    for i, a in enumerate(fi.ALGORITMOS):
        esp = [fi.celda(res, o, d, "distancia", a)["nodos_expandidos"]
               for (o, d), _ in fig.pares]
        ok(esp == fig.series["nodos_expandidos"][i],
           f"comparación: barras de nodos expandidos de {a} = outputs")
        tiempos = [fi.celda(res, o, d, "distancia", a)["tiempo_media_s"]
                   * 1e6 for (o, d), _ in fig.pares]
        ok(np.allclose(tiempos, fig.series["tiempo"][i]),
           f"comparación: barras de tiempo de {a} = outputs")
    # heurística y coherencia
    alfa = fi.leer("analisis_heuristica.json")["alfa"]
    ok(f"y = {alfa:.6f} x" in textos(figs["fig_heuristica"]),
       f"heurística: la recta rotulada es y = {alfa:.6f} x")
    datos = fi.datos_dispersion()
    bajo = sum(1 for d in datos if d[3] < d[2])
    for nombre in ("fig_heuristica", "fig_c1_coherencia"):
        etiquetas = [n for n, _ in figs[nombre].cajas]
        ok(len(etiquetas) == bajo,
           f"{nombre}: {bajo} aristas bajo y = x rotuladas")
    # ACO
    fig = figs["fig_aco"]
    val = fi.leer("validacion_agente.json")["instancias"]
    eucl = [r for r in val if r["familia"].startswith("euclidiana n=20")]
    esp = np.mean([r["aco_sin_2opt"]["brecha_media_pct"] for r in eucl])
    ok(abs(fig.valores["aco_sin_2opt"][5] - esp) < 1e-9,
       f"ACO: brecha de las euclidianas n = 20 sin 2-opt {esp:.3f} % = "
       "validacion_agente")
    # umbral
    u = fi.leer("umbral_held_karp.json")
    ok(f"K_exacto = {u['k_exacto']}" in textos(figs["fig_umbral"]),
       f"umbral: K_exacto = {u['k_exacto']} anotado")
    esperado = [max(m["medianas_s"]) for m in u["mediciones"]
                if 16 <= m["k"] <= 22]
    ok(figs["fig_umbral"].peores == esperado,
       "umbral: las barras son el peor tiempo de las sesiones (outputs)")
    ok(all(f"{v:.3f}" in textos(figs["fig_umbral"]) for v in esperado
           if v < 10), "umbral: valor rotulado sobre cada barra")
    # perfil
    p = fi.leer("perfil_topologico.json")
    m = figs["fig_perfil"].matriz
    ok(int((m == 3).sum()) // 2 == p["pares_por_clase"]["atajo"]
       and int((m == 2).sum()) // 2 == p["pares_por_clase"][
           "paso_obligatorio"] and int((m == 1).sum()) // 2 == p[
           "pares_por_clase"]["camino_unico"],
       "perfil: las celdas de cada clase = pares de cada clase")
    # casos del Corte 1
    pa = fi.leer("pruebas_agente.json")
    t = textos(figs["fig_c1_casos"])
    for _, caso in figs["fig_c1_casos"].casos:
        ok(f"{caso['distancia_total_km']:.2f} km" in t and fi.miles(
            caso["peaje_total_cop"]) in t
           and f"{caso['tiempo_s'] * 1000:.1f} ms" in t,
           f"casos: {caso['origen']} a {caso['destino']} rotula "
           f"{caso['distancia_total_km']:.2f} km, peaje y tiempo de "
           "pruebas_agente.json")
    ok(pa["ciclo"]["corta"]["distancia_total_km"] == 352.41,
       "casos: la ruta corta del caso central mide 352.41 km")
    # agente
    a, b, c = figs["fig_agente"].agente
    t = textos(figs["fig_agente"])
    ok(f"{a['recomendada']['km']:.2f} km" in t
       and f"{b['recomendada']['km']:.2f} km" in t
       and f"{c['recomendada']['km']:.2f} km" in t,
       "agente: los km rotulados de (a), (b) y (c) = salida del agente")
    for nombre, fig in figs.items():
        revisar(fig, nombre)
    for fig in figs.values():
        plt.close(fig)
    r = subprocess.run([sys.executable, "-m", "pycodestyle",
                        "--max-line-length=79",
                        str(RAIZ / "src" / "figuras_informe.py"),
                        str(RAIZ / "src" / "pruebas_figuras.py")],
                       capture_output=True, text=True)
    ok(r.returncode == 0, "pycodestyle limpio" + r.stdout)
    print("Todas las pruebas de las figuras pasaron.")


if __name__ == "__main__":
    main()
