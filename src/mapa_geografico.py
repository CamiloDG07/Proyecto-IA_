"""Mapas de la red sobre coordenadas geográficas, con el trazado real.

Dibuja, para cada arista, la geometría de su sector en red_vial.csv
(columna multiline) y, donde la geometría no llega al nodo (a más de
UMBRAL_KM), una línea punteada recta entre el nodo y el extremo del trazado,
rotulada «tramo sin trazado en la fuente». El fondo son los límites
departamentales del DANE (MGN 2020,
data/carga/mgn2020_departamentos_dane.json); no se usan mosaicos.

Escribe outputs/trazado_aristas.json (trazado simplificado, con tolerancia de
unos 45 m; se regenera desde red_vial.csv si falta), outputs/mapa_red.{png,pdf}
y outputs/mapa_caso_central.{png,pdf}.
"""
import csv
import json
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as efectos  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

from agente import AgenteRutas  # noqa: E402
from build_graph import SALIDA, cargar_grafo  # noqa: E402
from construir_red import TRAMO_EXTRA_LONGITUD, TRAMOS  # noqa: E402
from diagrama_red import aristas_del_ciclo  # noqa: E402
from heuristica import cargar_coordenadas, haversine_km  # noqa: E402
from obtener_coordenadas import DATOS  # noqa: E402

UMBRAL_KM = 5.0
TOLERANCIA_GRADOS = 0.0004
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
AZUL = "#2a78d6"
NARANJA = "#eb6834"
GRIS_VIA = "#6b6a66"
GRIS_FONDO = "#efeee9"
GRIS_LIMITE = "#cfcdc6"
GRIS_RED_B = "#b9b8b3"
ORIGEN, DESTINO = "Duitama", "Puente Nacional"


# ---------------------------------------------------------------- trazado
def simplificar(pts, tol):
    """Douglas-Peucker iterativo sobre un arreglo (n, 2)."""
    n = len(pts)
    if n < 3:
        return pts
    mantener = np.zeros(n, bool)
    mantener[[0, -1]] = True
    pila = [(0, n - 1)]
    while pila:
        a, b = pila.pop()
        if b <= a + 1:
            continue
        seg = pts[b] - pts[a]
        resto = pts[a + 1:b] - pts[a]
        norma = np.hypot(*seg)
        if norma == 0:
            d = np.hypot(resto[:, 0], resto[:, 1])
        else:
            d = np.abs(seg[0] * resto[:, 1] - seg[1] * resto[:, 0]) / norma
        i = int(d.argmax())
        if d[i] > tol:
            k = a + 1 + i
            mantener[k] = True
            pila += [(a, k), (k, b)]
    return pts[mantener]


def extremos(pts):
    """Dos extremos de la geometría por doble barrido (lat, lon)."""
    def lejos(p):
        return haversine_vec(p[0], p[1], pts[:, 0], pts[:, 1]).argmax()
    a = pts[lejos(pts[0])]
    b = pts[lejos(a)]
    return a, b


def haversine_vec(lat1, lon1, lat2, lon2):
    f1, f2 = np.radians(lat1), np.radians(lat2)
    h = (np.sin((f2 - f1) / 2) ** 2
         + np.cos(f1) * np.cos(f2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6371.0088 * np.arcsin(np.sqrt(h))


def puntos_del_registro(registro):
    return sum(len(p) for p in registro)


def construir_trazado():
    """Lee red_vial.csv y arma el trazado de las 32 aristas."""
    csv.field_size_limit(sys.maxsize)
    coord = cargar_coordenadas()
    sectores = {}
    for sector, o, d, _ in TRAMOS:
        extra = TRAMO_EXTRA_LONGITUD.get((sector, o, d))
        sectores[(o, d)] = [sector] + ([extra] if extra else [])
    usados = {s for v in sectores.values() for s in v}
    por_sector = {}
    with open(DATOS / "red_vial.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            s = r["sector"].strip()
            if s in usados:
                registro = []
                for parte in re.findall(r"\(([^()]+)\)", r["multiline"]):
                    pts = np.array([[float(v) for v in q.split()]
                                    for q in parte.split(",")])
                    registro.append(pts[:, ::-1])
                por_sector.setdefault(s, []).append(registro)
    salida = {}
    for (o, d), nombres in sectores.items():
        registros = [reg for s in nombres for reg in por_sector[s]]
        partes = [p for reg in registros for p in reg]
        todo = np.vstack(partes)
        a, b = extremos(todo)
        po, pd_ = coord[o], coord[d]
        directo = (haversine_km(*po, *a) + haversine_km(*pd_, *b))
        cruzado = (haversine_km(*po, *b) + haversine_km(*pd_, *a))
        ea, eb = (a, b) if directo <= cruzado else (b, a)
        salida[f"{o}|{d}"] = {
            "sectores": nombres,
            "partes": [np.round(simplificar(p, TOLERANCIA_GRADOS), 5).tolist()
                       for p in partes],
            "registro_largo": [
                np.round(simplificar(p, TOLERANCIA_GRADOS), 5).tolist()
                for p in max(registros, key=puntos_del_registro)],
            "extremo_origen": np.round(ea, 5).tolist(),
            "extremo_destino": np.round(eb, 5).tolist(),
            "km_extremo_origen": haversine_km(*po, *ea),
            "km_extremo_destino": haversine_km(*pd_, *eb)}
    with open(SALIDA / "trazado_aristas.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False)
    return salida


def cargar_trazado():
    ruta = SALIDA / "trazado_aristas.json"
    if not ruta.exists():
        return construir_trazado()
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def departamentos():
    """Anillos (lon, lat) y nombre de cada departamento (DANE, MGN 2020)."""
    with open(DATOS / "mgn2020_departamentos_dane.json",
              encoding="utf-8") as f:
        datos = json.load(f)
    res = []
    for x in datos["features"]:
        anillos = [np.array(a) for a in x["geometry"]["rings"]]
        res.append((x["attributes"]["DPTO_CNMBR"].title(), anillos))
    return res


# ---------------------------------------------------------------- dibujo
def preparar_eje(ax, lon, lat, fondo=True):
    lat0 = np.mean(lat)
    ax.set_xlim(*lon)
    ax.set_ylim(*lat)
    ax.set_aspect(1 / np.cos(np.radians(lat0)))
    ax.set_facecolor(SUPERFICIE)
    if fondo:
        for nombre, anillos in departamentos():
            for a in anillos:
                ax.fill(a[:, 0], a[:, 1], color=GRIS_FONDO,
                        ec=GRIS_LIMITE, lw=0.7, zorder=0)
    for borde in ("top", "right"):
        ax.spines[borde].set_visible(False)
    ax.set_xlabel("Longitud (°)", fontsize=8, color=TINTA_2)
    ax.set_ylabel("Latitud (°)", fontsize=8, color=TINTA_2)
    ax.tick_params(labelsize=7, colors=TINTA_2)


def rotular_departamentos(ax, lon, lat):
    for nombre, anillos in departamentos():
        mayor = max(anillos, key=lambda a: abs(np.cumsum(
            a[:-1, 0] * a[1:, 1] - a[1:, 0] * a[:-1, 1])[-1]))
        x, y = mayor[:, 0].mean(), mayor[:, 1].mean()
        if lon[0] + 0.1 < x < lon[1] - 0.1 and lat[0] + 0.1 < y < lat[1] - 0.1:
            ax.text(x, y, nombre.upper(), fontsize=7, color="#a9a79f",
                    ha="center", va="center", style="italic", zorder=0.5)


def dibujar_aristas(ax, grafo, trazado, color_de, ancho_de, orden_de,
                    discontinua=lambda u, v: False):
    """Trazo de cada arista; punteado recto donde falta el trazado. Las
    aristas discontinuas se dibujan con un solo registro (el más largo)."""
    coord = cargar_coordenadas()
    for u, v in grafo.edges:
        clave = f"{u}|{v}" if f"{u}|{v}" in trazado else f"{v}|{u}"
        t = trazado[clave]
        o, d = clave.split("|")
        color, ancho = color_de(u, v), ancho_de(u, v)
        estilo = dict(color=color, lw=ancho, solid_capstyle="round",
                      zorder=orden_de(u, v))
        partes = t["partes"]
        if discontinua(u, v):
            estilo.update(ls=(0, (3, 2)), solid_capstyle="butt")
            partes = t["registro_largo"]
        for parte in partes:
            p = np.array(parte)
            ax.plot(p[:, 1], p[:, 0], **estilo)
        for nodo, ext, km in ((o, t["extremo_origen"],
                               t["km_extremo_origen"]),
                              (d, t["extremo_destino"],
                               t["km_extremo_destino"])):
            if km > UMBRAL_KM:
                ax.plot([coord[nodo][1], ext[1]], [coord[nodo][0], ext[0]],
                        color=color, lw=max(ancho * 0.8, 1.0), ls=(0, (1, 2)),
                        zorder=orden_de(u, v))
    return coord


def rotular_nodos(ax, fig, coord, nodos, tam=7.0, fuertes=()):
    """Etiquetas sin solaparse: prueba 8 posiciones por nodo y elige la
    primera cuyo rectángulo no cruce otra etiqueta ni otro nodo."""
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    ocupados = []
    puntos = {n: ax.transData.transform((coord[n][1], coord[n][0]))
              for n in nodos}
    for p in puntos.values():
        ocupados.append((p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4))
    desplazamientos = [(7, 5, "left", "bottom"), (7, -5, "left", "top"),
                       (-7, 5, "right", "bottom"), (-7, -5, "right", "top"),
                       (0, 9, "center", "bottom"), (0, -9, "center", "top"),
                       (12, 0, "left", "center"), (-12, 0, "right", "center")]
    # primero los nodos más aislados
    orden = sorted(nodos, key=lambda n: sum(
        1 for m in nodos if m != n and np.hypot(
            *(puntos[n] - puntos[m])) < 60))
    dpi = fig.dpi / 72
    for n in orden:
        mejor, mejor_sol = None, None
        for dx, dy, ha, va in desplazamientos:
            t = ax.annotate(n, xy=(coord[n][1], coord[n][0]),
                            xytext=(dx, dy), textcoords="offset points",
                            fontsize=tam, ha=ha, va=va, color=TINTA,
                            arrowprops=dict(arrowstyle="-", lw=0.5,
                                            color=TINTA_2, shrinkA=0,
                                            shrinkB=2),
                            fontweight="bold" if n in fuertes else "normal",
                            zorder=6,
                            path_effects=[efectos.withStroke(
                                linewidth=2.2, foreground=SUPERFICIE)])
            bb = t.get_window_extent(rend)
            r = (bb.x0, bb.y0, bb.x1, bb.y1)
            sol = sum(max(0, min(r[2], o[2]) - max(r[0], o[0]))
                      * max(0, min(r[3], o[3]) - max(r[1], o[1]))
                      for o in ocupados)
            if sol == 0:
                if mejor:
                    mejor[0].remove()
                mejor, mejor_sol = (t, r), 0
                break
            if mejor_sol is None or sol < mejor_sol:
                if mejor:
                    mejor[0].remove()
                mejor, mejor_sol = (t, r), sol
            else:
                t.remove()
        ocupados.append(mejor[1])
        _ = dpi


def barra_escala(ax, lat, x0, lat0, km=100):
    grados = km / (111.32 * np.cos(np.radians(np.mean(lat))))
    ax.plot([x0, x0 + grados], [lat0, lat0], color=TINTA, lw=2,
            solid_capstyle="butt", zorder=7)
    ax.text(x0 + grados / 2, lat0 + 0.05, f"{km} km", fontsize=7,
            ha="center", va="bottom", color=TINTA, zorder=7)


def leyenda(ax, entradas, ubicacion="upper right"):
    ax.legend(handles=entradas, loc=ubicacion, fontsize=7, frameon=True,
              facecolor=SUPERFICIE, edgecolor=GRIS_LIMITE, framealpha=0.95)


def fuente(fig):
    fig.text(0.01, 0.005, "Fuentes: INVÍAS, Red Vial (trazado); DANE, MGN "
             "2020 (límites departamentales); DANE, DIVIPOLA (nodos).",
             fontsize=6, color=TINTA_2, ha="left", va="bottom")


# ---------------------------------------------------------------- figuras
def mapa_red(grafo, trazado):
    ciclo, aristas_ciclo = aristas_del_ciclo(grafo)
    lon, lat = (-75.25, -71.75), (3.35, 7.65)
    fig, ax = plt.subplots(figsize=(7.2, 8.6))
    preparar_eje(ax, lon, lat)
    rotular_departamentos(ax, lon, lat)

    def en(u, v):
        return frozenset((u, v)) in aristas_ciclo

    coord = dibujar_aristas(
        ax, grafo, trazado, lambda u, v: AZUL if en(u, v) else GRIS_VIA,
        lambda u, v: 2.3 if en(u, v) else 1.4,
        lambda u, v: 3 if en(u, v) else 2)
    xs = [coord[n][1] for n in grafo]
    ys = [coord[n][0] for n in grafo]
    ax.scatter(xs, ys, s=16, color=SUPERFICIE, edgecolors=TINTA, lw=0.9,
               zorder=5)
    rotular_nodos(ax, fig, coord, list(grafo), tam=7.0)
    barra_escala(ax, lat, -72.95, 5.15)
    leyenda(ax, [
        Line2D([0], [0], color=AZUL, lw=2.3, label="Ciclo de la red"),
        Line2D([0], [0], color=GRIS_VIA, lw=1.4, label="Resto de la red"),
        Line2D([0], [0], color=TINTA_2, lw=1.2, ls=(0, (1, 2)),
               label="Tramo sin trazado en la fuente"),
        Line2D([0], [0], marker="o", color="none", mfc=SUPERFICIE,
               mec=TINTA, label="Ciudad")], "upper left")
    fuente(fig)
    return fig


def costos_ruta(grafo, ruta):
    pares = list(zip(ruta, ruta[1:]))
    return (sum(grafo[u][v]["distancia_km"] for u, v in pares),
            sum(grafo[u][v]["peaje_cop_camion"] for u, v in pares))


def mapa_caso_central(grafo, trazado):
    agente = AgenteRutas(grafo)
    corta = agente.calcular_ruta(ORIGEN, DESTINO, "distancia")["ruta"]
    desvio = agente.calcular_ruta(ORIGEN, DESTINO, "peaje")["ruta"]
    if "Bogotá" not in corta or "Bucaramanga" not in desvio:
        raise ValueError("Las rutas del caso central no son las esperadas")
    pares_corta = {frozenset(p) for p in zip(corta, corta[1:])}
    pares_desvio = {frozenset(p) for p in zip(desvio, desvio[1:])}
    lon, lat = (-74.45, -72.35), (4.45, 7.55)
    fig, ax = plt.subplots(figsize=(7.2, 8.0))
    preparar_eje(ax, lon, lat)
    rotular_departamentos(ax, lon, lat)

    def color(u, v):
        k = frozenset((u, v))
        return AZUL if k in pares_corta else NARANJA if k in pares_desvio \
            else GRIS_RED_B

    def ancho(u, v):
        k = frozenset((u, v))
        return 3.0 if k in pares_corta | pares_desvio else 1.1
    coord = dibujar_aristas(ax, grafo, trazado, color, ancho,
                            lambda u, v: 4 if frozenset((u, v))
                            in pares_corta | pares_desvio else 2,
                            lambda u, v: frozenset((u, v)) in pares_desvio)
    en_rutas = set(corta) | set(desvio)
    visibles = [n for n in grafo if lon[0] < coord[n][1] < lon[1]
                and lat[0] < coord[n][0] < lat[1]]
    ax.scatter([coord[n][1] for n in visibles], [coord[n][0]
                                                 for n in visibles],
               s=[34 if n in en_rutas else 12 for n in visibles],
               color=SUPERFICIE, edgecolors=TINTA, lw=0.9, zorder=6)
    for nodo, marca in ((ORIGEN, "o"), (DESTINO, "s")):
        ax.scatter([coord[nodo][1]], [coord[nodo][0]], s=70, marker=marca,
                   color=TINTA, zorder=7)
    rotular_nodos(ax, fig, coord, visibles, tam=7.2,
                  fuertes=(ORIGEN, DESTINO))
    km_c, pe_c = costos_ruta(grafo, corta)
    km_d, pe_d = costos_ruta(grafo, desvio)

    def miles(x):
        return f"{x:,.0f}".replace(",", " ")

    leyenda(ax, [
        Line2D([0], [0], color=AZUL, lw=3.0,
               label=f"Por Bogotá: {km_c:.2f} km, peaje {miles(pe_c)} COP"),
        Line2D([0], [0], color=NARANJA, lw=3.0, ls=(0, (3, 2)),
               label=f"Por Santander: {km_d:.2f} km, peaje "
                     f"{miles(pe_d)} COP"),
        Line2D([0], [0], color=GRIS_RED_B, lw=1.1, label="Resto de la red"),
        Line2D([0], [0], color=TINTA_2, lw=1.2, ls=(0, (1, 2)),
               label="Tramo sin trazado en la fuente"),
        Line2D([0], [0], marker="o", color="none", mfc=TINTA, mec=TINTA,
               label="Origen: Duitama"),
        Line2D([0], [0], marker="s", color="none", mfc=TINTA, mec=TINTA,
               label="Destino: Puente Nacional")], "upper left")
    barra_escala(ax, lat, -73.0, 4.75, 50)
    fuente(fig)
    return fig


def main():
    grafo = cargar_grafo()
    trazado = cargar_trazado()
    for nombre, figura in (("mapa_red", mapa_red(grafo, trazado)),
                           ("mapa_caso_central",
                            mapa_caso_central(grafo, trazado))):
        figura.savefig(SALIDA / f"{nombre}.png", dpi=200,
                       facecolor=SUPERFICIE, bbox_inches="tight")
        figura.savefig(SALIDA / f"{nombre}.pdf", facecolor=SUPERFICIE,
                       bbox_inches="tight")
        plt.close(figura)
    print("Mapas escritos en", SALIDA)


if __name__ == "__main__":
    main()
