"""Pruebas de los mapas (src/mapa_geografico.py).

Comprueban que los km y el peaje rotulados coinciden con la suma de
aristas_red.json y con la tabla de rutas, que las figuras se regeneran desde
outputs/trazado_aristas.json sin red_vial.csv, que ningún rótulo se monta con
otro ni con la leyenda, que la letra mínima es de 7 pt al tamaño de página, y
que el código cumple pycodestyle.
"""
import itertools
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.text import Annotation, Text  # noqa: E402
from matplotlib.transforms import Bbox  # noqa: E402

import mapa_geografico as mg  # noqa: E402
from build_graph import SALIDA, cargar_grafo  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def ok(condicion, mensaje):
    if not condicion:
        print(f"  FALLA: {mensaje}")
        sys.exit(1)
    print(f"  ok: {mensaje}")


def cifras(texto):
    return [float(x.replace(" ", "")) for x in
            re.findall(r"(\d[\d ]*\.?\d*) (?:km|COP)", texto)]


def rutas_del_caso(grafo):
    agente = mg.AgenteRutas(grafo)
    return (agente.calcular_ruta(mg.ORIGEN, mg.DESTINO, "distancia")["ruta"],
            agente.calcular_ruta(mg.ORIGEN, mg.DESTINO, "peaje")["ruta"])


def prueba_cifras_rotuladas(figura, grafo):
    with open(SALIDA / "aristas_red.json", encoding="utf-8") as f:
        aristas = {frozenset((a["origen"], a["destino"])): a
                   for a in json.load(f)}
    with open(SALIDA / "tabla_rutas.tex", encoding="utf-8") as f:
        tabla = f.read()
    km_t = [float(x) for x in re.search(
        r"Distancia \(km\) & ([\d.]+) & ([\d.]+)", tabla).groups()]
    pe_t = [int(x.replace("\\,", "")) for x in re.search(
        r"Peaje total \(COP\) & ([\d\\,]+) & ([\d\\,]+)", tabla).groups()]
    textos = [t.get_text() for t in figura.axes[0].get_legend().get_texts()]
    rotulos = [t for t in textos if "km, peaje" in t]
    ok(len(rotulos) == 2, "la leyenda rotula las dos rutas con km y peaje")
    for rotulo, ruta, km_tabla, pe_tabla in zip(rotulos,
                                                rutas_del_caso(grafo),
                                                km_t, pe_t):
        pares = [frozenset(p) for p in zip(ruta, ruta[1:])]
        km = sum(aristas[p]["distancia_km"] for p in pares)
        pe = sum(aristas[p]["peaje_cop_camion"] for p in pares)
        km_r, pe_r = cifras(rotulo)[:2]
        ok(abs(km_r - km) < 0.005 and abs(km_r - km_tabla) < 0.005,
           f"km rotulados {km_r:.2f} = suma de aristas_red.json = tabla")
        ok(pe_r == pe == pe_tabla,
           f"peaje rotulado {pe_r:,.0f} = suma de aristas = tabla")


def prueba_chocontá_tunja(figura):
    texto = " ".join(t.get_text()
                     for t in figura.axes[0].get_legend().get_texts())
    disp, recta = mg.trazado_disponible("Chocontá", "Tunja")
    ok(f"{disp:.2f} km de {recta:.2f} km en línea recta" in
       texto.replace("\n", " "),
       f"la leyenda dice trazado disponible {disp:.2f} km de {recta:.2f} km")
    ok(f"{disp:.2f}" == "17.69" and f"{recta:.2f}" == "56.96",
       "las cifras leídas de outputs/ son 17.69 y 56.96")


def prueba_algoritmos(figura):
    por_bogota, por_santander = mg.algoritmos_por_via()
    texto = " ".join(t.get_text()
                     for t in figura.axes[0].get_legend().get_texts())
    ok(set(por_bogota) == {"UCS", "Voraz", "A*"}
       and set(por_santander) == {"BFS", "DFS"},
       "la ruta por Bogotá la devuelven UCS, voraz y A*; el desvío, BFS y DFS")
    ok(mg.unir(por_bogota) in texto and mg.unir(por_santander) in texto,
       "la leyenda rotula los algoritmos de cada ruta")


def cajas_de_texto(figura):
    """Cajas de los rótulos (sin la línea guía) y de la leyenda."""
    figura.canvas.draw()
    rend = figura.canvas.get_renderer()
    cajas = []
    for t in figura.axes[0].texts:
        if (not t.get_text() or t.get_color() == "#a9a79f"
                or isinstance(t, Annotation)):
            continue
        cajas.append((t.get_text().replace("\n", " "),
                      t.get_window_extent(rend)))
    for nombre, (x0, y0, x1, y1) in figura.cajas_nodos:
        cajas.append((nombre, Bbox([[x0, y0], [x1, y1]])))
    leyenda = figura.axes[0].get_legend()
    if leyenda is not None:
        cajas.append(("leyenda", leyenda.get_window_extent(rend)))
    return cajas


def prueba_sin_solapes(figura, nombre):
    cajas = cajas_de_texto(figura)
    choques = [(a, b) for (a, ba), (b, bb) in itertools.combinations(
        cajas, 2) if ba.x0 < bb.x1 and bb.x0 < ba.x1 and ba.y0 < bb.y1
        and bb.y0 < ba.y1]
    ok(not choques, f"{nombre}: ninguna caja de texto se cruza con otra "
       f"({len(cajas)} cajas)" + (f"; cruces: {choques}" if choques else ""))
    ok(figura.solapes == 0, f"{nombre}: 0 rótulos de nodos montados")


def prueba_letra_y_tamano(figura, nombre):
    tamanos = [t.get_fontsize() for t in figura.findobj(Text)
               if t.get_text().strip()]
    ok(min(tamanos) >= mg.FUENTE - 1e-9,
       f"{nombre}: letra mínima {min(tamanos):.1f} pt (>= {mg.FUENTE:.0f})")
    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "mapa.pdf"
        figura.savefig(ruta, facecolor=mg.SUPERFICIE)
        contenido = ruta.read_bytes()
    caja = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)",
                     contenido)
    ancho_pt, alto_pt = float(caja.group(1)), float(caja.group(2))
    ok(abs(ancho_pt - mg.ANCHO_IN * 72) < 0.5,
       f"{nombre}: el PDF mide {ancho_pt / 72:.3f} in de ancho (ancho de "
       f"texto) y {alto_pt / 72:.2f} in de alto: la letra impresa es la "
       "del PDF")


def prueba_sin_red_vial(grafo):
    original = mg.construir_trazado

    def prohibido():
        raise AssertionError("se intentó leer red_vial.csv")
    mg.construir_trazado = prohibido
    try:
        trazado = mg.cargar_trazado()
        for funcion in (mg.mapa_red, mg.mapa_caso_central):
            figura = funcion(grafo, trazado)
            plt.close(figura)
    finally:
        mg.construir_trazado = original
    ok(True, "las dos figuras se regeneran desde trazado_aristas.json sin "
       "red_vial.csv")
    ok(len(trazado) == 32, "el trazado cubre las 32 aristas")


def prueba_estilo():
    for archivo in ("mapa_geografico.py", "pruebas_mapa.py"):
        r = subprocess.run([sys.executable, "-m", "pycodestyle",
                            "--max-line-length=79",
                            str(RAIZ / "src" / archivo)],
                           capture_output=True, text=True)
        ok(r.returncode == 0, f"pycodestyle limpio en {archivo}"
           + (f": {r.stdout.strip()}" if r.returncode else ""))


def main():
    grafo = cargar_grafo()
    trazado = mg.cargar_trazado()
    prueba_sin_red_vial(grafo)
    central = mg.mapa_caso_central(grafo, trazado)
    red = mg.mapa_red(grafo, trazado)
    prueba_cifras_rotuladas(central, grafo)
    prueba_chocontá_tunja(central)
    prueba_algoritmos(central)
    prueba_sin_solapes(central, "caso central")
    prueba_sin_solapes(red, "mapa de la red")
    prueba_letra_y_tamano(central, "caso central")
    prueba_letra_y_tamano(red, "mapa de la red")
    prueba_estilo()
    print("Todas las pruebas de los mapas pasaron.")


if __name__ == "__main__":
    main()
