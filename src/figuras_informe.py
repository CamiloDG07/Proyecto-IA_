"""Figuras de los informes, generadas desde los datos guardados en outputs/.

Cada función de figura devuelve la figura de matplotlib, con los atributos
`cajas` (cajas de texto, para comprobar que no se montan) y `solapes`, y
escribe su bloque «Cómo leerla» en outputs/lectura_*.tex con cifras leídas de
los datos guardados. Los tamaños son de ancho de texto (ANCHO_IN); la letra
mínima es FUENTE puntos. Solo se recalcula lo determinista y barato (los
conjuntos de nodos expandidos de cada búsqueda), y sus conteos se comprueban
contra los guardados. Nada de esto lee red_vial.csv: el trazado sale de
outputs/trazado_aristas.json.

Escribe outputs/fig_*.{png,pdf}.
"""
import csv
import itertools
import json
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches  # noqa: E402
import matplotlib.patheffects as efectos  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

import busquedas  # noqa: E402
import mapa_geografico as mg  # noqa: E402
from agente import CRITERIOS  # noqa: E402
from build_graph import SALIDA, cargar_grafo  # noqa: E402
from busquedas import a_estrella, bfs, dfs, ucs, voraz  # noqa: E402
from heuristica import (Heuristica, alfa_minimo,  # noqa: E402
                        cargar_coordenadas)
from lecturas_informe import bloque  # noqa: E402
from lecturas_informe import miles as miles_tex  # noqa: E402

ANCHO_IN = mg.ANCHO_IN
FUENTE = mg.FUENTE
SUPERFICIE, TINTA, TINTA_2 = mg.SUPERFICIE, mg.TINTA, mg.TINTA_2
AZUL, NARANJA = mg.AZUL, mg.NARANJA
GRIS_FONDO, GRIS_LIMITE = mg.GRIS_FONDO, mg.GRIS_LIMITE
GRIS_RED, GRIS_VIA = mg.GRIS_RED_B, mg.GRIS_VIA
ALGORITMOS = ["BFS", "DFS", "UCS", "Voraz", "A*"]
COLORES_ALG = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#7a5cc9"]
TRAMAS_ALG = ["", "///", "xxx", "...", "\\\\\\"]
MARCADORES_ALG = ["o", "s", "^", "D", "v"]
ORIGEN, DESTINO = mg.ORIGEN, mg.DESTINO
COORD = cargar_coordenadas()


def miles(valor):
    """Número con espacio como separador de miles, para texto de figura."""
    return f"{valor:,.0f}".replace(",", " ")


def leer(nombre):
    with open(SALIDA / nombre, encoding="utf-8") as f:
        return json.load(f)


def leer_csv(nombre):
    with open(SALIDA / nombre, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def guardar(fig, nombre):
    fig.savefig(SALIDA / f"{nombre}.png", dpi=200, facecolor=SUPERFICIE)
    fig.savefig(SALIDA / f"{nombre}.pdf", facecolor=SUPERFICIE)


def celda(res, origen, destino, criterio, algoritmo):
    return next(c for c in res if c["origen"] == origen
                and c["destino"] == destino and c["criterio"] == criterio
                and c["algoritmo"] == algoritmo)


# ---------------------------------------------------------------- rótulos
def rotular(ax, fig, items, fijos=(), tam=FUENTE):
    """Rótulos de puntos (x, y, texto, negrita) en coordenadas de datos, sin
    montarse entre sí ni con las cajas `fijos` (en píxeles). Devuelve
    (rótulos montados, cajas)."""
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    caja = ax.get_window_extent(rend)
    puntos = [ax.transData.transform((x, y)) for x, y, _, _ in items]
    ocupados = [(p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3) for p in puntos]
    ocupados += list(fijos)
    desp = [(5, 4, "left", "bottom"), (5, -4, "left", "top"),
            (-5, 4, "right", "bottom"), (-5, -4, "right", "top"),
            (0, 7, "center", "bottom"), (0, -7, "center", "top"),
            (9, 0, "left", "center"), (-9, 0, "right", "center"),
            (14, 10, "left", "bottom"), (-14, 10, "right", "bottom"),
            (14, -10, "left", "top"), (-14, -10, "right", "top"),
            (24, 18, "left", "bottom"), (-24, 18, "right", "bottom"),
            (24, -18, "left", "top"), (-24, -18, "right", "top"),
            (32, 0, "left", "center"), (-32, 0, "right", "center"),
            (0, 24, "center", "bottom"), (0, -24, "center", "top"),
            (38, 26, "left", "bottom"), (-38, 26, "right", "bottom"),
            (38, -26, "left", "top"), (-38, -26, "right", "top")]
    solapes, cajas = 0, []
    orden = sorted(range(len(items)), key=lambda i: sum(
        1 for j in range(len(items)) if j != i
        and np.hypot(*(puntos[i] - puntos[j])) < 50))
    for i in orden:
        x, y, texto, neg = items[i]
        mejor, mejor_sol = None, None
        for d in desp:
            t = ax.annotate(texto, xy=(x, y), xytext=d[:2],
                            textcoords="offset points", fontsize=tam,
                            ha=d[2], va=d[3],
                            fontweight="bold" if neg else "normal")
            bb = t.get_window_extent(rend)
            t.remove()
            r = (bb.x0, bb.y0, bb.x1, bb.y1)
            sol = sum(max(0, min(r[2], o[2]) - max(r[0], o[0]))
                      * max(0, min(r[3], o[3]) - max(r[1], o[1]))
                      for o in ocupados)
            if (r[0] < caja.x0 or r[2] > caja.x1 or r[1] < caja.y0
                    or r[3] > caja.y1):
                sol += 1e6
            if mejor_sol is None or sol < mejor_sol:
                mejor, mejor_sol = (d, r), sol
            if sol == 0:
                break
        d, r = mejor
        ax.annotate(texto, xy=(x, y), xytext=d[:2], zorder=9,
                    textcoords="offset points", fontsize=tam, ha=d[2],
                    va=d[3], color=TINTA,
                    fontweight="bold" if neg else "normal",
                    arrowprops=dict(arrowstyle="-", lw=0.5, color=TINTA_2,
                                    shrinkA=0, shrinkB=2),
                    path_effects=[efectos.withStroke(
                        linewidth=2.2, foreground=SUPERFICIE)])
        ocupados.append(r)
        cajas.append((texto, r))
        if mejor_sol > 0:
            solapes += 1
    return solapes, cajas


def unir_cajas(fig, cajas, solapes):
    fig.cajas = getattr(fig, "cajas", []) + list(cajas)
    fig.solapes = getattr(fig, "solapes", 0) + solapes


# ---------------------------------------------------------------- mapas
def fondo(ax, lon, lat, ejes=False):
    """Límites departamentales y proporción geográfica en el eje."""
    ax.set_xlim(*lon)
    ax.set_ylim(*lat)
    ax.set_aspect(1 / np.cos(np.radians(np.mean(lat))))
    ax.set_facecolor(SUPERFICIE)
    for nombre, anillos in mg.departamentos():
        for a in anillos:
            ax.fill(a[:, 0], a[:, 1], color=GRIS_FONDO, ec=GRIS_LIMITE,
                    lw=0.6, zorder=0)
    for borde in ax.spines.values():
        borde.set_color(GRIS_LIMITE)
    if not ejes:
        ax.set_xticks([])
        ax.set_yticks([])


def trazo(ax, trazado, u, v, **estilo):
    """Trazo de una arista; donde el trazado queda a más de UMBRAL_KM del
    nodo, línea punteada recta (tramo sin trazado en la fuente)."""
    clave = mg.clave_de(trazado, u, v)
    t = trazado[clave]
    o, d = clave.split("|")
    for parte in t["partes"]:
        p = np.array(parte)
        ax.plot(p[:, 1], p[:, 0], **estilo)
    for nodo, ext, km in ((o, t["extremo_origen"], t["km_extremo_origen"]),
                          (d, t["extremo_destino"],
                           t["km_extremo_destino"])):
        if km > mg.UMBRAL_KM:
            ax.plot([COORD[nodo][1], ext[1]], [COORD[nodo][0], ext[0]],
                    color=estilo.get("color"), ls=(0, (1, 2)),
                    lw=max(estilo.get("lw", 1.0) * 0.8, 1.0),
                    zorder=estilo.get("zorder", 2))


def punto_en_trazo(trazado, u, v):
    """(longitud, latitud) de un vértice central del trazado de la arista."""
    t = trazado[mg.clave_de(trazado, u, v)]
    parte = max(t["registro_largo"], key=len)
    lat, lon = parte[len(parte) // 2]
    return lon, lat


def red_gris(ax, grafo, trazado, lw=0.9):
    for u, v in grafo.edges:
        trazo(ax, trazado, u, v, color=GRIS_RED, lw=lw,
              solid_capstyle="round", zorder=1)


def ruta_negra(ax, trazado, ruta, lw=2.4, color=TINTA, zorder=4):
    for u, v in zip(ruta, ruta[1:]):
        trazo(ax, trazado, u, v, color=color, lw=lw,
              solid_capstyle="round", zorder=zorder)


# ------------------------------------------------ B1: mapas de expansión
def expansiones(grafo, origen, destino, criterio="distancia"):
    """Nodos expandidos y generados de las cinco búsquedas, con los mismos
    argumentos que las corridas guardadas; devuelve para cada una el
    resultado, la secuencia de expandidos y el conjunto de generados."""
    coord = cargar_coordenadas()
    h = Heuristica(grafo, coord, criterio, alfa_minimo(grafo, coord))
    h = h.precalcular(grafo, destino)
    atributo = CRITERIOS[criterio]
    casos = [("BFS", bfs, ()), ("DFS", dfs, ()), ("UCS", ucs, ()),
             ("Voraz", voraz, (h,)), ("A*", a_estrella, (h,))]
    salida = {}
    original = busquedas._vecinos
    for nombre, funcion, extra in casos:
        vistos = []

        def registrar(g, n, vistos=vistos):
            vistos.append(n)
            return original(g, n)
        busquedas._vecinos = registrar
        try:
            r = funcion(grafo, origen, destino, atributo, *extra)
        finally:
            busquedas._vecinos = original
        generados = {origen}
        for n in vistos:
            generados |= set(grafo[n])
        salida[nombre] = {"resultado": r, "expandidos": vistos,
                          "generados": generados}
    return salida


def fig_expansion(grafo, trazado):
    res = leer("resultados_corte2.json")["resultados"]
    exp = expansiones(grafo, ORIGEN, DESTINO)
    for nombre in ALGORITMOS:
        guardado = celda(res, ORIGEN, DESTINO, "distancia", nombre)
        r = exp[nombre]["resultado"]
        assert len(exp[nombre]["expandidos"]) == guardado[
            "nodos_expandidos"] == r["nodos_expandidos"], nombre
        assert r["nodos_generados"] == guardado["nodos_generados"], nombre
        assert r["ruta"] == guardado["ruta"], nombre
    coord = cargar_coordenadas()
    lon, lat = (-74.45, -72.35), (4.45, 7.55)
    fig, axes = plt.subplots(2, 3, figsize=(ANCHO_IN, 6.0))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.01,
                        wspace=0.04, hspace=0.16)
    for ax, nombre in zip(axes.flat, ALGORITMOS):
        fondo(ax, lon, lat)
        red_gris(ax, grafo, trazado)
        info = exp[nombre]
        ruta_negra(ax, trazado, info["resultado"]["ruta"])
        expandidos = set(info["expandidos"])
        solo = info["generados"] - expandidos
        otros = [n for n in grafo if n not in expandidos | solo]
        ax.scatter([coord[n][1] for n in otros], [coord[n][0] for n in otros],
                   s=5, color=GRIS_VIA, zorder=3)
        ax.scatter([coord[n][1] for n in solo], [coord[n][0] for n in solo],
                   s=22, marker="s", facecolor=SUPERFICIE,
                   edgecolor=NARANJA, lw=1.2, zorder=5)
        ax.scatter([coord[n][1] for n in expandidos],
                   [coord[n][0] for n in expandidos], s=22, marker="o",
                   color=AZUL, edgecolor=TINTA, lw=0.5, zorder=6)
        guardado = celda(res, ORIGEN, DESTINO, "distancia", nombre)
        ax.set_title(f"{nombre}: {guardado['nodos_expandidos']} expandidos\n"
                     f"{guardado['nodos_generados']} generados, "
                     f"{guardado['costo']:.2f} km", fontsize=FUENTE,
                     color=TINTA, pad=3)
        s, c = rotular(ax, fig, [(coord[ORIGEN][1], coord[ORIGEN][0],
                                  "Duitama", True),
                                 (coord[DESTINO][1], coord[DESTINO][0],
                                  "P. Nacional", True)])
        unir_cajas(fig, c, s)
    ax = axes.flat[5]
    ax.axis("off")
    entradas = [
        Line2D([0], [0], marker="o", color="none", mfc=AZUL, mec=TINTA,
               label="Nodo expandido"),
        Line2D([0], [0], marker="s", color="none", mfc=SUPERFICIE,
               mec=NARANJA, mew=1.2, label="Generado, sin expandir"),
        Line2D([0], [0], marker="o", color="none", mfc=GRIS_VIA,
               mec=GRIS_VIA, ms=3, label="Resto de la red"),
        Line2D([0], [0], color=TINTA, lw=2.4, label="Ruta devuelta"),
        Line2D([0], [0], color=GRIS_RED, lw=0.9, label="Tramo de la red"),
        Line2D([0], [0], color=GRIS_VIA, lw=1.2, ls=(0, (1, 2)),
               label="Tramo sin trazado\nen la fuente")]
    ax.legend(handles=entradas, loc="center", fontsize=FUENTE, frameon=True,
              facecolor=SUPERFICIE, edgecolor=GRIS_LIMITE,
              title="Duitama a Puente Nacional,\ncriterio distancia",
              title_fontsize=FUENTE, labelspacing=0.8)
    fig.legend_caja = ax.get_legend()
    # bloque Cómo leerla
    por_via = {a: ("Santander" if "Bucaramanga" in exp[a]["resultado"]["ruta"]
                   else "Bogotá") for a in ALGORITMOS}
    central = {a: celda(res, ORIGEN, DESTINO, "distancia", a)
               for a in ALGORITMOS}
    cuentas = ", ".join(f"{a} {central[a]['nodos_expandidos']}"
                        for a in ALGORITMOS)
    santander = ", ".join(a for a in ALGORITMOS if por_via[a] == "Santander")
    bogota = ", ".join(a for a in ALGORITMOS if por_via[a] == "Bogotá")
    bloque(
        "c2_fig_expansion",
        "un panel por algoritmo sobre el mapa; círculos azules, nodos "
        "expandidos; cuadrados huecos naranja, nodos generados sin "
        "expandir; línea negra, la ruta devuelta; punteada, tramo sin "
        "trazado en la fuente.",
        f"nodos expandidos: {cuentas}; devuelven la ruta por Santander "
        f"{santander} y por Bogotá {bogota}.",
        "Medido: los conjuntos se recalcularon con las mismas búsquedas y "
        "su tamaño coincide con los nodos expandidos guardados.")
    return fig


def corto(nombre):
    return nombre.replace("Puente ", "P. ").replace("Puerto ", "P. ")


# ------------------------------------------ B5: comparación de algoritmos
def fig_comparacion(grafo, trazado):
    res = leer("resultados_corte2.json")["resultados"]
    pares, vistos = [], set()
    for c in res:
        k = (c["origen"], c["destino"])
        if c["criterio"] == "distancia" and k not in vistos:
            vistos.add(k)
            pares.append((k, c["rutas_simples"]))
    fig, axes = plt.subplots(3, 1, figsize=(ANCHO_IN, 6.9), sharex=True)
    fig.subplots_adjust(left=0.115, right=0.99, top=0.9, bottom=0.17,
                        hspace=0.09)
    ancho = 0.16
    x = np.arange(len(pares))
    series = {"nodos_expandidos": [], "tiempo": [], "memoria": []}
    for i, alg in enumerate(ALGORITMOS):
        cs = [celda(res, o, d, "distancia", alg) for (o, d), _ in pares]
        valores = [[c["nodos_expandidos"] for c in cs],
                   [c["tiempo_media_s"] * 1e6 for c in cs],
                   [c["memoria_pico_kib"] for c in cs]]
        desv = [c["tiempo_desv_s"] * 1e6 for c in cs]
        series["nodos_expandidos"].append(valores[0])
        series["tiempo"].append(valores[1])
        series["memoria"].append(valores[2])
        for k, ax in enumerate(axes):
            err = None
            if k == 1:
                bajo = [min(d, 0.9 * m) for d, m in zip(desv, valores[1])]
                err = [bajo, desv]
            ax.bar(x + (i - 2) * ancho, valores[k], ancho,
                   color=COLORES_ALG[i],
                   edgecolor=TINTA, linewidth=0.5, hatch=TRAMAS_ALG[i],
                   yerr=err, ecolor=TINTA, capsize=1.2,
                   error_kw=dict(lw=0.6), label=alg, zorder=3)
    etiquetas = ["Nodos expandidos",
                 "Tiempo medio (µs), con desviación\n(escala logarítmica)",
                 "Memoria pico (KiB)"]
    for ax, et in zip(axes, etiquetas):
        ax.set_ylabel(et, fontsize=FUENTE, color=TINTA_2)
        ax.tick_params(labelsize=FUENTE, colors=TINTA_2)
        ax.grid(axis="y", color="#e6e5e1", lw=0.6, zorder=0)
        for borde in ("top", "right"):
            ax.spines[borde].set_visible(False)
    axes[1].set_yscale("log")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(
        [corto(o) + "–" + corto(d) + ("*" if n > 1 else "")
         for (o, d), n in pares], rotation=55, ha="right", fontsize=FUENTE)
    axes[0].legend(ncol=5, loc="lower center", bbox_to_anchor=(0.5, 1.0),
                   fontsize=FUENTE, frameon=False, columnspacing=1.2,
                   handlelength=1.6)
    fig.text(0.115, 0.012, "* Par que cruza el ciclo (dos rutas simples). "
             "Criterio distancia.", fontsize=FUENTE, color=TINTA_2)
    fig.series = series
    fig.pares = pares
    central = {a: celda(res, ORIGEN, DESTINO, "distancia", a)
               for a in ALGORITMOS}
    bloque(
        "c2_fig_comparacion",
        "tres paneles con los diez escenarios en el eje horizontal: nodos "
        "expandidos, tiempo medio con su desviación (escala logarítmica) y "
        "memoria pico; una barra con trama distinta por algoritmo.",
        "en el caso central, nodos expandidos: " + ", ".join(
            f"{a} {central[a]['nodos_expandidos']}" for a in ALGORITMOS)
        + f"; tiempo medio de A* {central['A*']['tiempo_media_s'] * 1e6:.0f} "
        f"µs y de UCS {central['UCS']['tiempo_media_s'] * 1e6:.0f} µs.",
        "Medido: las desviaciones llegan a "
        f"{max(c['tiempo_desv_s'] / c['tiempo_media_s'] for c in res):.2f} "
        "veces la media, de modo que las diferencias de tiempo son "
        "indicativas.")
    return fig


# ------------------------------------------------ B3 y C3: dispersión
def datos_dispersion():
    filas = leer_csv("auditoria_aristas.csv")
    return [(r["origen"], r["destino"], float(r["geodesica_km"]),
             float(r["distancia_carretera_km"])) for r in filas]


def dispersion(con_alfa):
    datos = datos_dispersion()
    alfa = leer("analisis_heuristica.json")["alfa"] if con_alfa else None
    fig, ax = plt.subplots(figsize=(ANCHO_IN, 4.5))
    fig.subplots_adjust(left=0.1, right=0.985, top=0.98, bottom=0.11)
    tope = max(max(d[2], d[3]) for d in datos) * 1.05
    ax.plot([0, tope], [0, tope], color=TINTA, lw=1.0, zorder=2)
    if con_alfa:
        ax.plot([0, tope], [0, alfa * tope], color=NARANJA, lw=1.4,
                ls="--", zorder=2)
    sobre = [d for d in datos if d[3] >= d[2]]
    bajo = [d for d in datos if d[3] < d[2]]
    ax.scatter([d[2] for d in sobre], [d[3] for d in sobre], s=20,
               marker="o", color=AZUL, edgecolor=TINTA, lw=0.5, zorder=4)
    ax.scatter([d[2] for d in bajo], [d[3] for d in bajo], s=26,
               marker="v", color=NARANJA, edgecolor=TINTA, lw=0.5, zorder=4)
    ax.set_xlim(0, tope)
    ax.set_ylim(0, tope)
    ax.set_xlabel("Distancia geodésica entre los nodos (km)",
                  fontsize=FUENTE, color=TINTA_2)
    ax.set_ylabel("Distancia por carretera (km)", fontsize=FUENTE,
                  color=TINTA_2)
    ax.tick_params(labelsize=FUENTE, colors=TINTA_2)
    ax.grid(color="#e6e5e1", lw=0.6, zorder=0)
    for borde in ("top", "right"):
        ax.spines[borde].set_visible(False)
    items = [(d[2], d[3], f"{corto(d[0])}–{corto(d[1])}", False)
             for d in bajo]
    fig.canvas.draw()
    s, c = rotular(ax, fig, items)
    unir_cajas(fig, c, s)
    entradas = [Line2D([0], [0], color=TINTA, lw=1.0,
                       label="carretera = geodésica"),
                Line2D([0], [0], marker="o", color="none", mfc=AZUL,
                       mec=TINTA, label="carretera ≥ geodésica"),
                Line2D([0], [0], marker="v", color="none", mfc=NARANJA,
                       mec=TINTA, label="carretera < geodésica")]
    if con_alfa:
        entradas.insert(1, Line2D([0], [0], color=NARANJA, lw=1.4, ls="--",
                                  label=f"y = {alfa:.6f} x"))
    leg = ax.legend(handles=entradas, loc="lower right", fontsize=FUENTE,
                    frameon=True, facecolor=SUPERFICIE, edgecolor=GRIS_LIMITE)
    fig.leyenda = leg
    fig.datos = datos
    fig.alfa = alfa
    return fig, datos, alfa, sobre, bajo


def fig_heuristica(grafo, trazado):
    fig, datos, alfa, sobre, bajo = dispersion(True)
    minimo = min(datos, key=lambda d: d[3] / d[2])
    bloque(
        "c2_fig_heuristica",
        "cada punto es una de las 32 aristas: distancia geodésica en el eje "
        "horizontal y distancia por carretera en el vertical; la recta "
        "continua es y = x y la discontinua es y = alfa x.",
        f"{len(bajo)} aristas quedan bajo y = x y todas quedan sobre "
        f"y = alfa x, con alfa = {alfa:.6f}; la razón mínima es "
        f"{minimo[3] / minimo[2]:.4f} en {minimo[0]} a {minimo[1]}.",
        "Medido: la arista que fija alfa es la de menor razón "
        f"({minimo[3]:.2f} km por carretera frente a {minimo[2]:.2f} km en "
        "línea recta); su sector está truncado en la fuente.")
    return fig


def fig_c1_coherencia(grafo, trazado):
    fig, datos, alfa, sobre, bajo = dispersion(False)
    minimo = min(datos, key=lambda d: d[3] / d[2])
    bloque(
        "c1_fig_coherencia",
        "cada punto es una de las 32 aristas: distancia geodésica en el eje "
        "horizontal y distancia por carretera en el vertical; la recta es "
        "y = x.",
        f"{len(sobre)} aristas tienen carretera igual o mayor que la "
        f"geodésica y {len(bajo)} la tienen menor.",
        "Medido: la menor razón es "
        f"{minimo[3] / minimo[2]:.4f} en {minimo[0]} a {minimo[1]}; las "
        "aristas bajo la recta son las que la auditoría marca por "
        "carretera menor que la geodésica.")
    return fig


# ------------------------------------------------ B6: umbral de Held-Karp
def fig_umbral(grafo, trazado):
    u = leer("umbral_held_karp.json")
    ks = [m["k"] for m in u["mediciones"]]
    sesiones = len(u["sesiones"])
    fig, axes = plt.subplots(1, 2, figsize=(ANCHO_IN, 3.1))
    fig.subplots_adjust(left=0.1, right=0.985, top=0.97, bottom=0.2,
                        wspace=0.3)
    ax = axes[0]
    for s in range(sesiones):
        ax.plot(ks, [m["medianas_s"][s] for m in u["mediciones"]],
                marker=MARCADORES_ALG[s], color=COLORES_ALG[s], lw=1.2,
                ms=4, mec=TINTA, mew=0.4, label=f"Sesión {s + 1}")
    ax.axhline(u["presupuesto_s"], color=TINTA, lw=1.0, ls="--")
    ax.text(ks[0], u["presupuesto_s"] * 1.2,
            f"presupuesto de {u['presupuesto_s']:g} s", fontsize=FUENTE,
            color=TINTA, va="bottom", ha="left")
    ax.axvline(u["k_exacto"], color=TINTA_2, lw=1.0, ls=":")
    ax.text(u["k_exacto"] - 0.3, 0.0025, f"K = {u['k_exacto']}",
            fontsize=FUENTE, color=TINTA, ha="right")
    ax.set_yscale("log")
    ax.set_xlabel("Paradas libres k", fontsize=FUENTE, color=TINTA_2)
    ax.set_ylabel("Tiempo mediano (s)", fontsize=FUENTE, color=TINTA_2)
    ax.legend(fontsize=FUENTE, loc="center left", bbox_to_anchor=(0.0, 0.62),
              frameon=False)
    ax.set_xticks(range(8, 23, 2))
    ax = axes[1]
    ax.plot(ks, [m["memoria_pico_mib"] for m in u["mediciones"]], marker="o",
            color=AZUL, lw=1.2, ms=4, mec=TINTA, mew=0.4,
            label="Memoria pico")
    ax.axhline(u["limite_memoria_mib"], color=TINTA, lw=1.0, ls="--")
    ax.text(ks[0], u["limite_memoria_mib"] * 0.8,
            f"límite de {u['limite_memoria_mib']:.0f} MiB (25 % de la RAM)",
            fontsize=FUENTE, color=TINTA, va="top")
    ax.set_xticks(range(8, 23, 2))
    ax.set_yscale("log")
    ax.set_xlabel("Paradas libres k", fontsize=FUENTE, color=TINTA_2)
    ax.set_ylabel("Memoria pico (MiB)", fontsize=FUENTE, color=TINTA_2)
    for ax in axes:
        ax.tick_params(labelsize=FUENTE, colors=TINTA_2)
        ax.grid(color="#e6e5e1", lw=0.6, zorder=0)
        for borde in ("top", "right"):
            ax.spines[borde].set_visible(False)
    fig.umbral = u
    m19 = next(m for m in u["mediciones"] if m["k"] == u["k_exacto"])
    m20 = next(m for m in u["mediciones"] if m["k"] == u["k_exacto"] + 1)
    bloque(
        "c2_fig_umbral",
        "izquierda, tiempo mediano de Held-Karp contra k en escala "
        "logarítmica, una curva por sesión de medición, con el presupuesto "
        "y K marcados; derecha, memoria pico contra k.",
        f"con k = {u['k_exacto']} las {sesiones} sesiones caben en el "
        f"presupuesto (de {min(m19['medianas_s']):.3f} a "
        f"{max(m19['medianas_s']):.3f} s); con k = {u['k_exacto'] + 1} la "
        f"mayor llega a {max(m20['medianas_s']):.3f} s.",
        f"Medido: la memoria pico con k = {ks[-1]} es "
        f"{u['mediciones'][-1]['memoria_pico_mib']:.1f} MiB, bajo el límite; "
        "el umbral lo fija el tiempo. Hipótesis: la variación entre "
        "sesiones se debe al estado de la máquina; no se midió.")
    return fig


# ------------------------------------------------------------ B4: ACO
def fig_aco(grafo, trazado):
    filas = leer_csv("convergencia_aco.csv")
    val = leer("validacion_agente.json")["instancias"]
    grupos = {"Red de carga": lambda f: f["familia"] == "red de carga",
              "Taller (n = 20)": lambda f: f["familia"].startswith(
                  "euclidiana n=20")}
    fig, axes = plt.subplots(2, 1, figsize=(ANCHO_IN, 6.2))
    fig.subplots_adjust(left=0.1, right=0.985, top=0.98, bottom=0.1,
                        hspace=0.32)
    ax = axes[0]
    curvas = {}
    for i, (nombre, filtro) in enumerate(grupos.items()):
        por_iter = {}
        for f in filas:
            if filtro(f):
                por_iter.setdefault(int(f["iteracion"]), []).append(
                    float(f["brecha_pct"]))
        it = sorted(por_iter)
        y = [float(np.mean(por_iter[k])) for k in it]
        curvas[nombre] = (it, y)
        ax.plot(it, y, color=COLORES_ALG[i], lw=1.6,
                ls="-" if i == 0 else "--", marker=MARCADORES_ALG[i],
                markevery=10, ms=4, mec=TINTA, mew=0.4, label=nombre)
    ax.set_xlabel("Iteración", fontsize=FUENTE, color=TINTA_2)
    ax.set_ylabel("Brecha de la media de 10 semillas (%)", fontsize=FUENTE,
                  color=TINTA_2)
    ax.legend(fontsize=FUENTE, frameon=False)
    ax = axes[1]
    etiquetas = ["Red\nn=5", "Red\nn=10", "Red\nn=15", "Red\nn=20",
                 "Red\nn=32", "Taller\nn=20", "Euclid.\nn=100",
                 "Euclid.\nn=200"]
    filtros = [lambda r, n=n: r["familia"] == "red de carga" and r["n"] == n
               for n in (5, 10, 15, 20, 32)]
    filtros.append(lambda r: r["familia"].startswith("euclidiana n=20"))
    filtros += [lambda r, n=n: "mayor" in r["familia"] and r["n"] == n
                for n in (100, 200)]
    variantes = [("aco", "Con 2-opt"),
                 ("aco_sin_2opt", "Sin 2-opt, inicio aleatorio"),
                 ("aco_sin_2opt_inicio_fijo", "Sin 2-opt, inicio fijo")]
    x = np.arange(len(etiquetas))
    ancho = 0.26
    valores = {}
    for j, (clave, nombre) in enumerate(variantes):
        ys = []
        for flt in filtros:
            rs = [r for r in val if flt(r) and clave in r]
            ys.append(np.mean([r[clave]["brecha_media_pct"] for r in rs])
                      if rs else np.nan)
        valores[clave] = ys
        ax.bar(x + (j - 1) * ancho, np.nan_to_num(ys), ancho,
               color=COLORES_ALG[j], edgecolor=TINTA, lw=0.5,
               hatch=TRAMAS_ALG[j], label=nombre, zorder=3)
        for xi, yi in zip(x, ys):
            if np.isnan(yi):
                ax.text(xi + (j - 1) * ancho, 0.1, "n/d", fontsize=FUENTE,
                        ha="center", color=TINTA_2, rotation=90)
    ax.axhline(0, color=TINTA, lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas, fontsize=FUENTE)
    ax.set_ylabel("Brecha media (%)", fontsize=FUENTE, color=TINTA_2)
    ax.legend(fontsize=FUENTE, frameon=False, loc="upper left")
    ax.grid(axis="y", color="#e6e5e1", lw=0.6, zorder=0)
    for a in axes:
        a.tick_params(labelsize=FUENTE, colors=TINTA_2)
        for borde in ("top", "right"):
            a.spines[borde].set_visible(False)
    fig.valores = valores
    taller = valores["aco"][5], valores["aco_sin_2opt"][5], valores[
        "aco_sin_2opt_inicio_fijo"][5]
    bloque(
        "c2_fig_aco",
        "arriba, brecha de la media de 10 semillas del ACO con 2-opt en cada "
        "iteración (red de carga y taller); abajo, brecha media por grupo "
        "con 2-opt, sin 2-opt con inicio aleatorio y sin 2-opt con inicio "
        "fijo.",
        f"en el taller la brecha media es {taller[0]:.3f} % con 2-opt, "
        f"{taller[1]:.3f} % sin 2-opt con inicio aleatorio y "
        f"{taller[2]:.3f} % con inicio fijo; en n = 100 y 200 sin 2-opt es "
        f"{valores['aco_sin_2opt'][6]:.3f} % y "
        f"{valores['aco_sin_2opt'][7]:.3f} %.",
        "Medido: la brecha con inicio fijo se debía al inicio de las "
        "hormigas, no a la ausencia de 2-opt; el aporte del 2-opt crece con "
        "n. «n/d»: no se corrió esa variante.")
    return fig


# ------------------------------------------------------ B8: perfil
def fig_perfil(grafo, trazado):
    p = leer("perfil_topologico.json")
    nodos = sorted(grafo)
    idx = {n: i for i, n in enumerate(nodos)}
    n = len(nodos)
    clases = {"camino_unico": 1, "paso_obligatorio": 2, "atajo": 3}
    m = np.zeros((n, n))
    for clave, d in p["detalle"].items():
        a, b = clave.split("|")
        m[idx[a], idx[b]] = m[idx[b], idx[a]] = clases[d["clase"]]
    from matplotlib.colors import ListedColormap
    colores = [SUPERFICIE, "#c9c7bf", "#1d4f91", "#f4a582"]
    fig, ax = plt.subplots(figsize=(ANCHO_IN, 6.1))
    fig.subplots_adjust(left=0.2, right=0.99, top=0.83, bottom=0.07)
    ax.imshow(m, cmap=ListedColormap(colores), vmin=0, vmax=3,
              interpolation="nearest")
    art = set(p["puntos_de_articulacion"])
    etiquetas = [("● " + c) if c in art else c for c in nodos]
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(etiquetas, rotation=90, fontsize=FUENTE)
    ax.set_yticklabels(etiquetas, fontsize=FUENTE)
    for lab, c in zip(ax.get_xticklabels(), nodos):
        lab.set_fontweight("bold" if c in art else "normal")
    for lab, c in zip(ax.get_yticklabels(), nodos):
        lab.set_fontweight("bold" if c in art else "normal")
    ax.set_xticks(np.arange(-0.5, n, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n, 1), minor=True)
    ax.grid(which="minor", color=SUPERFICIE, lw=0.5)
    ax.tick_params(which="both", length=0)
    ax.xaxis.tick_top()
    ax.tick_params(axis="x", pad=2)
    ax.tick_params(axis="y", pad=2)
    for borde in ax.spines.values():
        borde.set_visible(False)
    parche = matplotlib.patches.Patch
    ax.legend(handles=[
        parche(fc=colores[1], ec=TINTA, lw=0.5, label="Camino único"),
        parche(fc=colores[2], ec=TINTA, lw=0.5, label="Paso obligatorio"),
        parche(fc=colores[3], ec=TINTA, lw=0.5, label="Atajo")],
        loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=3,
        fontsize=FUENTE, frameon=False)
    fig.text(0.2, 0.005, "● Punto de articulación (nodo cuya eliminación "
             "desconecta la red).", fontsize=FUENTE, color=TINTA_2)
    k = p["pares_por_clase"]
    ciclo = nx.cycle_basis(grafo)[0]
    atajos = {frozenset(c.split("|")) for c, d in p["detalle"].items()
              if d["clase"] == "atajo"}
    assert atajos == {frozenset(par) for par in itertools.combinations(
        ciclo, 2)}, "los atajos no son los pares del ciclo"
    fig.matriz = m
    bloque(
        "c2_fig_perfil",
        "matriz de 32 por 32 ciudades; el color de cada celda es la clase "
        "del par (camino único, paso obligatorio o atajo); los nodos con "
        "punto y en negrita son puntos de articulación.",
        f"de los {p['pares']} pares, {k['paso_obligatorio']} son de paso "
        f"obligatorio, {k['atajo']} de atajo y {k['camino_unico']} de camino "
        f"único; hay {len(art)} puntos de articulación.",
        "Medido: las tres clases son excluyentes y suman "
        f"{sum(k.values())}; los atajos son los pares del ciclo, que "
        "tienen dos caminos sin nodo intermedio en común.")
    return fig


# ----------------------------------------- B7 y C1: mapa de cobertura
def datos_cobertura():
    aristas = leer("aristas_red.json")
    audit = {(r["origen"], r["destino"]): r["anomalia"]
             for r in leer_csv("auditoria_aristas.csv")}
    filas = []
    for a in aristas:
        k = (a["origen"], a["destino"])
        filas.append({"u": a["origen"], "v": a["destino"],
                      "peaje": bool(a["peaje_nombre"]),
                      "riesgo": a["riesgo_puntos_criticos"] > 0,
                      "marca": bool(audit[k])})
    return filas


def fig_cobertura(grafo, trazado):
    filas = datos_cobertura()
    coord = cargar_coordenadas()
    lon, lat = (-75.25, -71.75), (3.35, 7.65)
    fig, ax = mg.crear_figura(lon, lat, relleno_alto=0.25)
    mg.preparar_eje(ax, lon, lat)
    for f in filas:
        if f["marca"]:
            trazo(ax, trazado, f["u"], f["v"], color="#f6c3a8", lw=7.5,
                  solid_capstyle="round", zorder=1)
    for f in filas:
        estilo = (dict(color=AZUL, lw=2.4) if f["riesgo"]
                  else dict(color=GRIS_VIA, lw=1.5))
        trazo(ax, trazado, f["u"], f["v"], solid_capstyle="round",
              zorder=3, **estilo)
    for f in filas:
        if f["peaje"]:
            x, y = punto_en_trazo(trazado, f["u"], f["v"])
            ax.scatter([x], [y], s=26, marker="D", color=TINTA,
                       edgecolor=SUPERFICIE, lw=0.6, zorder=6)
    ax.scatter([coord[n][1] for n in grafo], [coord[n][0] for n in grafo],
               s=14, color=SUPERFICIE, edgecolors=TINTA, lw=0.8, zorder=5)
    s, c = mg.rotular_nodos(ax, fig, coord, list(grafo))
    unir_cajas(fig, [(n, r) for n, r in c], s)
    entradas = [
        Line2D([0], [0], color=AZUL, lw=2.4,
               label="Arista con dato de riesgo"),
        Line2D([0], [0], color=GRIS_VIA, lw=1.5,
               label="Arista sin dato de riesgo"),
        Line2D([0], [0], marker="D", color="none", mfc=TINTA,
               mec=SUPERFICIE, label="Arista con peaje"),
        Line2D([0], [0], color="#f6c3a8", lw=7.5,
               label="Marcada por la auditoría geométrica")]
    ax.legend(handles=entradas, loc="upper left", fontsize=FUENTE,
              frameon=True, facecolor=SUPERFICIE, edgecolor=GRIS_LIMITE,
              framealpha=0.97)
    mg.fuente(fig)
    fig.filas = filas
    return fig, filas


def bloques_cobertura(filas):
    n = len(filas)
    r = sum(f["riesgo"] for f in filas)
    p = sum(f["peaje"] for f in filas)
    m = sum(f["marca"] for f in filas)
    sin = n - r
    comun = ("el color azul indica dato de riesgo, el rombo negro peaje y el "
             "halo naranja claro una arista marcada por la auditoría "
             "geométrica.")
    bloque("c2_fig_cobertura",
           "mapa de la red; " + comun,
           f"de las {n} aristas, {r} tienen dato de riesgo, {p} tienen peaje "
           f"y {m} están marcadas por la auditoría.",
           f"Medido: {sin} aristas no tienen dato de riesgo y valen 0 en los "
           "criterios que lo incluyen; por eso riesgo y compuesto prefieren "
           "el desvío por falta de datos.")
    bloque("c1_fig_cobertura",
           "mapa de la red; " + comun,
           f"de las {n} aristas, {r} tienen dato de riesgo, {p} tienen peaje "
           f"y {m} están marcadas por la auditoría.",
           f"Medido: {sin} aristas no tienen dato de riesgo y valen 0 en el "
           "costo compuesto.")


# ------------------------------------------- B2: mapas del agente autónomo
def fig_agente(grafo, trazado):
    from agente_rutas import recomendar
    coord = cargar_coordenadas()
    a = recomendar("Duitama", ["Puente Nacional"], grafo=grafo)
    b = recomendar("Bogotá", ["Granada"], grafo=grafo)
    c = recomendar("Duitama", ["Tunja", "Bogotá", "Villeta"], True,
                   grafo=grafo)
    paneles = [((-74.45, -72.35), (4.45, 7.55)),
               ((-74.4, -73.45), (3.4, 4.9)),
               ((-74.75, -72.85), (4.35, 6.3))]
    h = 2.9
    anchos = [h * (p[0][1] - p[0][0]) * np.cos(np.radians(np.mean(p[1])))
              / (p[1][1] - p[1][0]) for p in paneles]
    total = sum(anchos)
    fig = plt.figure(figsize=(ANCHO_IN, h + 0.7))
    izq, sep = 0.012, 0.012
    escala = (1 - 2 * izq - 2 * sep) / total
    x0 = izq
    axes = []
    for w in anchos:
        axes.append(fig.add_axes([x0, 0.012, w * escala, h / (h + 0.7)]))
        x0 += w * escala + sep
    for ax, (lon, lat) in zip(axes, paneles):
        fondo(ax, lon, lat)
        red_gris(ax, grafo, trazado)

    def pie(ax, texto, y=0.99):
        ax.text(0.5, y, texto, transform=ax.transAxes, ha="center",
                va="bottom", fontsize=FUENTE, color=TINTA)
    # (a) recomendada y alternativa
    ax = axes[0]
    rec, alt = a["recomendada"], a["alternativas"][0]
    ruta_negra(ax, trazado, alt["ruta"], lw=3.6, color=NARANJA, zorder=3)
    for u, v in zip(rec["ruta"], rec["ruta"][1:]):
        trazo(ax, trazado, u, v, color=AZUL, lw=2.2, zorder=4,
              path_effects=[efectos.withStroke(linewidth=3.8,
                                               foreground=TINTA)])
    pie(ax, f"(a) Recomendada: {rec['km']:.2f} km,\n"
        f"{miles(rec['peaje_cop'])} COP. Alternativa:\n"
        f"{alt['km']:.2f} km, {miles(alt['peaje_cop'])} COP")
    # (b) ruta única
    ax = axes[1]
    rb = b["recomendada"]
    for u, v in zip(rb["ruta"], rb["ruta"][1:]):
        trazo(ax, trazado, u, v, color=AZUL, lw=2.2, zorder=4,
              path_effects=[efectos.withStroke(linewidth=3.8,
                                               foreground=TINTA)])
    pie(ax, f"(b) Ruta única: {rb['km']:.2f} km,\n"
        f"{miles(rb['peaje_cop'])} COP;\nsin alternativas")
    # (c) orden de visita
    ax = axes[2]
    orden = c["recomendada"]["orden_paradas"]
    rc = c["recomendada"]
    for u, v in zip(rc["ruta"], rc["ruta"][1:]):
        trazo(ax, trazado, u, v, color=AZUL, lw=2.2, zorder=4,
              path_effects=[efectos.withStroke(linewidth=3.8,
                                               foreground=TINTA)])
    metodo = c["recomendada"]["metodo"]
    pie(ax, f"(c) {metodo}: {rc['km']:.2f} km,\n"
        f"{miles(rc['peaje_cop'])} COP;\norden de visita numerado")
    paradas = [(1, orden[0])] + [(i + 1, n) for i, n in enumerate(
        orden[1:-1], start=1)]
    for num, nodo in paradas:
        ax.scatter([coord[nodo][1]], [coord[nodo][0]], s=120, color=SUPERFICIE,
                   edgecolor=TINTA, lw=1.0, zorder=7)
        ax.text(coord[nodo][1], coord[nodo][0], str(num), fontsize=FUENTE,
                ha="center", va="center", zorder=8, fontweight="bold",
                color=TINTA)
    ax.text(0.03, 0.03, "\n".join(f"{num} {nodo}" for num, nodo in paradas)
            + "\n1 al regreso", transform=ax.transAxes, fontsize=FUENTE,
            va="bottom", ha="left", zorder=9, color=TINTA,
            bbox=dict(boxstyle="round,pad=0.25", fc=SUPERFICIE,
                      ec=GRIS_LIMITE))
    # nodos rotulados en (a) y (b)
    for ax, ruta, (lon, lat) in ((axes[0], None, paneles[0]),
                                 (axes[1], rb["ruta"], paneles[1])):
        nodos = ([ORIGEN, DESTINO] if ruta is None else ruta)
        ax.scatter([coord[n][1] for n in nodos], [coord[n][0] for n in nodos],
                   s=22, color=SUPERFICIE, edgecolor=TINTA, lw=0.9, zorder=6)
        s, cj = rotular(ax, fig, [(coord[n][1], coord[n][0], corto(n), False)
                                  for n in nodos])
        unir_cajas(fig, cj, s)
    fig.agente = (a, b, c)
    bloque(
        "c2_fig_agente",
        "tres mapas, uno por solicitud de la tabla de ejemplos; (a) ruta "
        "recomendada en azul con borde oscuro y alternativa en naranja, (b) "
        "ruta única, (c) orden de visita numerado con el método; punteada, "
        "tramo sin trazado en la fuente.",
        f"(a) recomienda {rec['km']:.2f} km y "
        f"{miles_tex(rec['peaje_cop'])} COP "
        f"y deja una alternativa de {alt['km']:.2f} km; (b) tiene un solo "
        f"camino; (c) ordena las paradas con {metodo}.",
        "Medido: (c) tiene k = "
        f"{c['recomendada']['metricas']['k']} paradas libres, no más que "
        f"K = {c['recomendada']['metricas']['umbral_k']}, por eso el orden "
        "es exacto.")
    return fig


# ----------------------------------------------- B9: ACO frente a PSO
EXTERNO = {"barrido": r"D:\camilo\Documentos\Comparacion-ACO-vs-PSO-TSP-"
                      r"\resultados\barrido_resumen.csv"}
FUENTE_ACO_PSO = ("Comparacion-ACO-vs-PSO-TSP-/resultados/"
                  "barrido_resumen.csv")


def extraer_aco_pso():
    """Extrae del repositorio del equipo las cifras de ACO y PSO con 2048
    agentes, 100 iteraciones (108 en n = 200 000)."""
    with open(EXTERNO["barrido"], encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    salida = []
    for n, it in (("20", "100"), ("2000", "100"), ("200000", "108")):
        par = {x["algoritmo"]: x for x in filas if x["n"] == n
               and x["agentes"] == "2048" and x["iteraciones"] == it}
        a, p = par["ACO"], par["PSO"]
        salida.append({
            "n": n, "agentes": 2048, "iteraciones": it,
            "L_ACO": a["L"], "t_ACO": a["t"], "L_PSO": p["L"], "t_PSO": p["t"],
            "razon_L": float(p["L"]) / float(a["L"]),
            "razon_t": float(p["t"]) / float(a["t"]),
            "semillas_ACO": a["ns"], "semillas_PSO": p["ns"],
            "fuente": FUENTE_ACO_PSO})
    with open(SALIDA / "comparacion_aco_pso.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(salida[0]))
        w.writeheader()
        w.writerows(salida)
    return salida


def tabla_aco_pso():
    """Tabla compacta de ACO frente a PSO (outputs/tabla_aco_pso.tex)."""
    filas = leer_csv("comparacion_aco_pso.csv")
    lineas = ["\\begin{tabular}{rrrrrrr}", "\\toprule",
              "\\textbf{$n$} & \\textbf{$L$ ACO} & \\textbf{$L$ PSO} & "
              "\\textbf{$L_{\\mathrm{PSO}}/L_{\\mathrm{ACO}}$} & "
              "\\textbf{$t$ ACO (s)} & \\textbf{$t$ PSO (s)} & "
              "\\textbf{$t_{\\mathrm{PSO}}/t_{\\mathrm{ACO}}$} \\\\",
              "\\midrule"]
    for f in filas:
        n = f"{int(f['n']):,}".replace(",", "\\,")
        lineas.append(
            f"{n} & {float(f['L_ACO']):.4f} & {float(f['L_PSO']):.4f} & "
            f"{float(f['razon_L']):.2f} & {float(f['t_ACO']):.3f} & "
            f"{float(f['t_PSO']):.3f} & {float(f['razon_t']):.2f} \\\\")
    lineas += ["\\bottomrule", "\\end{tabular}"]
    with open(SALIDA / "tabla_aco_pso.tex", "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


def fig_aco_pso(grafo, trazado):
    filas = leer_csv("comparacion_aco_pso.csv")
    fig, axes = plt.subplots(1, 2, figsize=(ANCHO_IN, 2.9))
    fig.subplots_adjust(left=0.1, right=0.985, top=0.97, bottom=0.2,
                        wspace=0.3)
    x = np.arange(len(filas))
    ancho = 0.35
    etiquetas = [f"n = {int(f['n']):,}".replace(",", " ") for f in filas]
    for ax, (cl_a, cl_p, rz, etq) in zip(axes, [
            ("L_ACO", "L_PSO", "razon_L", "Longitud del recorrido"),
            ("t_ACO", "t_PSO", "razon_t", "Tiempo (s)")]):
        va = [float(f[cl_a]) for f in filas]
        vp = [float(f[cl_p]) for f in filas]
        ax.bar(x - ancho / 2, va, ancho, color=COLORES_ALG[0],
               edgecolor=TINTA, lw=0.5, label="ACO", zorder=3)
        ax.bar(x + ancho / 2, vp, ancho, color=COLORES_ALG[1],
               edgecolor=TINTA, lw=0.5, hatch="///", label="PSO", zorder=3)
        for xi, a, p, f in zip(x, va, vp, filas):
            ax.text(xi, max(a, p) * 1.25, f"×{float(f[rz]):.2f}",
                    ha="center", fontsize=FUENTE, color=TINTA)
        ax.set_yscale("log")
        ax.set_ylim(top=max(max(va), max(vp)) * 8)
        ax.set_xticks(x)
        ax.set_xticklabels(etiquetas, fontsize=FUENTE)
        ax.set_ylabel(etq + " (escala logarítmica)", fontsize=FUENTE,
                      color=TINTA_2)
        ax.tick_params(labelsize=FUENTE, colors=TINTA_2)
        ax.grid(axis="y", color="#e6e5e1", lw=0.6, zorder=0)
        for borde in ("top", "right"):
            ax.spines[borde].set_visible(False)
    axes[0].legend(fontsize=FUENTE, frameon=False, loc="upper left")
    fig.filas = filas
    f0, f2, f3 = filas
    bloque(
        "c2_fig_aco_pso",
        "dos paneles en escala logarítmica por tamaño n: longitud del "
        "recorrido y tiempo de ACO y de PSO; sobre cada par, la razón "
        "PSO/ACO.",
        f"la longitud de PSO es {float(f0['razon_L']):.2f}, "
        f"{float(f2['razon_L']):.1f} y {float(f3['razon_L']):.1f} veces la "
        "de ACO con n = 20, 2 000 y 200 000; PSO tarda "
        f"{float(f0['razon_t']):.2f}, {float(f2['razon_t']):.2f} y "
        f"{float(f3['razon_t']):.2f} veces el tiempo de ACO.",
        "Medido: PSO con w = 0.7 y c1 = c2 = 1.5, sin búsqueda local; con "
        "n = 200 000 hay una sola corrida. Hipótesis: con otros parámetros "
        "o con búsqueda local el resultado podría cambiar; no se probó.")
    return fig


# ------------------------------------------- C2: rutas de los casos de prueba
def fig_c1_casos(grafo, trazado):
    p = leer("pruebas_agente.json")
    coord = cargar_coordenadas()
    casos = [("Ruta corta", p["ciclo"]["corta"]),
             ("Desvío", p["ciclo"]["desvio"]),
             ("Ruta única", p["sin_ciclo"][1]),
             ("Ruta única", p["sin_ciclo"][2]),
             ("Ruta única", p["sin_ciclo"][4]),
             ("Ruta única", p["sin_ciclo"][5])]
    fig, axes = plt.subplots(2, 3, figsize=(ANCHO_IN, 5.2))
    fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.01,
                        wspace=0.05, hspace=0.24)
    for ax, (nombre, caso) in zip(axes.flat, casos):
        ruta = caso["ruta"]
        lons = [coord[n][1] for n in ruta]
        lats = [coord[n][0] for n in ruta]
        pad = 0.25
        lon = (min(lons) - pad, max(lons) + pad)
        lat = (min(lats) - pad, max(lats) + pad)
        # misma proporción para todos los paneles
        ancho, alto = lon[1] - lon[0], lat[1] - lat[0]
        objetivo = 1.15
        if alto / ancho < objetivo:
            extra = (ancho * objetivo - alto) / 2
            lat = (lat[0] - extra, lat[1] + extra)
        else:
            extra = (alto / objetivo - ancho) / 2
            lon = (lon[0] - extra, lon[1] + extra)
        fondo(ax, lon, lat)
        red_gris(ax, grafo, trazado)
        for u, v in zip(ruta, ruta[1:]):
            trazo(ax, trazado, u, v, color=AZUL, lw=2.2, zorder=4,
                  path_effects=[efectos.withStroke(linewidth=3.8,
                                                   foreground=TINTA)])
        visibles = [n for n in ruta]
        ax.scatter([coord[n][1] for n in visibles],
                   [coord[n][0] for n in visibles], s=18, color=SUPERFICIE,
                   edgecolor=TINTA, lw=0.8, zorder=6)
        km = caso["distancia_total_km"]
        ax.set_title(f"{nombre}: {corto(caso['origen'])} a "
                     f"{corto(caso['destino'])}\n{km:.2f} km, "
                     f"{miles(caso['peaje_total_cop'])} COP, "
                     f"{caso['tiempo_s'] * 1000:.1f} ms", fontsize=FUENTE,
                     color=TINTA, pad=3)
        nodos_rot = [ruta[0], ruta[-1]] if len(ruta) > 4 else ruta
        s, cj = rotular(ax, fig, [(coord[n][1], coord[n][0], corto(n),
                                   n in (ruta[0], ruta[-1]))
                                  for n in nodos_rot])
        unir_cajas(fig, cj, s)
    fig.casos = casos
    bloque(
        "c1_fig_casos",
        "un panel por caso de prueba del agente; la línea azul con borde "
        "oscuro es la ruta devuelta y la red va en gris; la línea punteada "
        "marca un tramo sin trazado en la fuente; el título da la distancia, "
        "el peaje y el tiempo de cómputo.",
        "los dos primeros paneles son el par que cruza el ciclo, con la ruta "
        f"corta ({casos[0][1]['distancia_total_km']:.2f} km) y el desvío "
        f"({casos[1][1]['distancia_total_km']:.2f} km); los otros cuatro "
        "son pares de ruta única.",
        "Medido: el tiempo de cómputo de cada caso es el de una sola "
        "corrida y es indicativo.")
    return fig


FIGURAS = [
    ("fig_expansion", fig_expansion),
    ("fig_agente", fig_agente),
    ("fig_heuristica", fig_heuristica),
    ("fig_aco", fig_aco),
    ("fig_comparacion", fig_comparacion),
    ("fig_umbral", fig_umbral),
    ("fig_perfil", fig_perfil),
    ("fig_aco_pso", fig_aco_pso),
    ("fig_c1_coherencia", fig_c1_coherencia),
    ("fig_c1_casos", fig_c1_casos)]


def generar(nombre, funcion, grafo, trazado):
    fig = funcion(grafo, trazado)
    guardar(fig, nombre)
    return fig


def main(seleccion=None):
    grafo = cargar_grafo()
    trazado = mg.cargar_trazado()
    if os.path.exists(EXTERNO["barrido"]):
        extraer_aco_pso()
    tabla_aco_pso()
    for nombre, funcion in FIGURAS:
        if seleccion and nombre not in seleccion:
            continue
        fig = generar(nombre, funcion, grafo, trazado)
        plt.close(fig)
    if not seleccion or "fig_cobertura" in seleccion:
        fig, filas = fig_cobertura(grafo, trazado)
        guardar(fig, "fig_cobertura")
        bloques_cobertura(filas)
        plt.close(fig)
    print("Figuras escritas en", SALIDA)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
