"""Auditoría geométrica de las 32 aristas contra la geometría de INVÍAS.

Para cada arista compara el sector usado en el cruce (distancia por
carretera) con la distancia geodésica entre las coordenadas oficiales de sus
nodos, y con los extremos de la geometría del sector (multiline de
red_vial.csv). Los extremos de un sector se estiman con un doble barrido
sobre todos sus vértices: el vértice más lejano a uno cualquiera, y el más
lejano a este. Escribe outputs/auditoria_aristas.csv.

Anomalías marcadas (umbrales fijos, no ajustados a los datos):
  - razon < 1: la carretera mide menos que la línea recta entre los nodos;
  - extremo a más de 5 km del nodo: la geometría del sector no llega al
    nodo (sector truncado, de otra zona, o la fuente no cubre el tramo
    urbano);
  - nodo a más de 5 km de la geometría del sector;
  - longitud del registro mayor que 1.5 veces el camino más corto entre los
    extremos de su propia geometría (posible suma de ambas calzadas).

La distancia por carretera es la que usa el grafo (aristas_red.json). El
camino de la geometría se mide como camino más corto entre extremos sobre
el grafo de vértices del sector.
"""
import csv
import json
import re
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

from build_graph import SALIDA
from construir_red import TRAMO_EXTRA_LONGITUD, TRAMOS
from obtener_coordenadas import DATOS, haversine_km

UMBRAL_KM = 5.0
UMBRAL_CALZADA = 1.5


def hav(lat1, lon1, lat2, lon2):
    """Haversine vectorizado, en km."""
    f1, f2 = np.radians(lat1), np.radians(lat2)
    a = (np.sin((f2 - f1) / 2) ** 2
         + np.cos(f1) * np.cos(f2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6371.0088 * np.arcsin(np.sqrt(a))


def vertices_por_sector():
    """Vértices (lat, lon) y longitud (km) de cada sector usado."""
    csv.field_size_limit(sys.maxsize)
    usados = {t[0] for t in TRAMOS} | set(TRAMO_EXTRA_LONGITUD.values())
    puntos, largos = {}, {}
    with open(DATOS / "red_vial.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            s = r["sector"].strip()
            if s not in usados:
                continue
            for parte in re.findall(r"\(([^()]+)\)", r["multiline"]):
                pts = np.array([[float(v) for v in q.split()]
                                for q in parte.split(",")])
                puntos.setdefault(s, []).append(pts[:, ::-1])
            largos.setdefault(s, []).append(float(r["shape__length"]) / 1000)
    return puntos, largos


def camino_geometria(partes, a, b):
    """Camino más corto (km) entre los extremos a y b sobre las partes."""
    indice = {}
    origen, destino, peso = [], [], []

    def clave(p):
        return (round(p[0], 6), round(p[1], 6))

    def nodo(p):
        return indice.setdefault(clave(p), len(indice))

    for parte in partes:
        ids = [nodo(p) for p in parte]
        d = hav(parte[:-1, 0], parte[:-1, 1], parte[1:, 0], parte[1:, 1])
        origen += ids[:-1]
        destino += ids[1:]
        peso += list(d)
    ia, ib = nodo(a), nodo(b)
    n = len(indice)
    m = coo_matrix((peso + peso, (origen + destino, destino + origen)),
                   shape=(n, n)).tocsr()
    return float(dijkstra(m, directed=False, indices=ia)[ib])


def extremos(pts):
    """Dos extremos de la geometría por doble barrido."""
    d0 = hav(pts[0, 0], pts[0, 1], pts[:, 0], pts[:, 1])
    a = pts[d0.argmax()]
    d1 = hav(a[0], a[1], pts[:, 0], pts[:, 1])
    b = pts[d1.argmax()]
    return a, b


def escribir_markdown(filas):
    """Tabla markdown de la auditoría, para VERIFICACION.md."""
    enc = ["Arista", "Carretera (km)", "Geodésica (km)", "Razón",
           "Extremo a nodo, máx. (km)", "Registro / camino", "Anomalía"]
    lineas = ["| " + " | ".join(enc) + " |", "|" + "---|" * len(enc)]
    for f in filas:
        lineas.append(
            f"| {f[0]} - {f[1]} | {f[3]} | {f[4]} | {float(f[5]):.3f} | "
            f"{max(float(f[6]), float(f[7])):.2f} | {f[11] or '-'} | "
            f"{f[12] or '-'} |")
    with open(SALIDA / "auditoria_aristas.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


def main():
    with open(DATOS / "coordenadas_nodos.csv", encoding="utf-8") as f:
        coord = {r["nodo"]: (float(r["latitud"]), float(r["longitud"]))
                 for r in csv.DictReader(f)}
    puntos, largos = vertices_por_sector()
    with open(SALIDA / "aristas_red.json", encoding="utf-8") as f:
        en_grafo = {(a["origen"], a["destino"]): a["distancia_km"]
                    for a in json.load(f)}
    filas = []
    for sector, origen, destino, _ in TRAMOS:
        extra = TRAMO_EXTRA_LONGITUD.get((sector, origen, destino))
        partes = puntos[sector] + (puntos[extra] if extra else [])
        pts = np.vstack(partes)
        km = en_grafo[(origen, destino)]
        po, pd_ = coord[origen], coord[destino]
        geo = haversine_km(*po, *pd_)
        a, b = extremos(pts)
        directo = (haversine_km(*po, *a) + haversine_km(*pd_, *b))
        cruzado = (haversine_km(*po, *b) + haversine_km(*pd_, *a))
        ea, eb = (a, b) if directo <= cruzado else (b, a)
        ext_o = haversine_km(*po, *ea)
        ext_d = haversine_km(*pd_, *eb)
        nodo_o = float(hav(po[0], po[1], pts[:, 0], pts[:, 1]).min())
        nodo_d = float(hav(pd_[0], pd_[1], pts[:, 0], pts[:, 1]).min())
        razon = km / geo
        camino = camino_geometria(partes, a, b)
        sobre_camino = km / camino if np.isfinite(camino) and camino else None
        marcas = []
        if razon < 1:
            marcas.append("carretera menor que geodésica")
        if max(ext_o, ext_d) > UMBRAL_KM:
            marcas.append("extremo lejos del nodo")
        if max(nodo_o, nodo_d) > UMBRAL_KM:
            marcas.append("nodo lejos de la geometría")
        if sobre_camino is None:
            marcas.append("geometría sin camino entre extremos")
        elif sobre_camino > UMBRAL_CALZADA:
            marcas.append("registro mayor que el camino de la geometría")
        filas.append([origen, destino,
                      sector + (f" + {extra}" if extra else ""),
                      f"{km:.2f}", f"{geo:.2f}", f"{razon:.4f}",
                      f"{ext_o:.2f}", f"{ext_d:.2f}",
                      f"{nodo_o:.2f}", f"{nodo_d:.2f}",
                      f"{camino:.2f}",
                      "" if sobre_camino is None else f"{sobre_camino:.3f}",
                      "; ".join(marcas)])
    with open(SALIDA / "auditoria_aristas.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["origen", "destino", "sector", "distancia_carretera_km",
                    "geodesica_km", "razon", "extremo_a_origen_km",
                    "extremo_a_destino_km", "origen_a_geometria_km",
                    "destino_a_geometria_km", "camino_geometria_km",
                    "registro_sobre_camino", "anomalia"])
        w.writerows(filas)
    escribir_markdown(filas)
    marcadas = [r for r in filas if r[-1]]
    print(f"{len(filas)} aristas auditadas, {len(marcadas)} con anomalía")


if __name__ == "__main__":
    main()
