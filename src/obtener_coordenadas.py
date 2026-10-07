"""Coordenadas de los 32 nodos desde fuentes oficiales, con verificación.

Fuente primaria (DANE, DIVIPOLA, corte 30 de diciembre de 2024, descargada
de datos.gov.co el 7 de octubre de 2026):
  - gdxc-w37w: DIVIPOLA, códigos de municipios (cabecera municipal)
  - xaxy-8nri: DIVIPOLA, códigos de cabeceras y centros poblados

La elección entre municipios homónimos (Barbosa y Granada) está
escrita de forma explícita en MUNICIPIOS. Los nodos que no son municipio ni
centro poblado con coordenada DANE verificable se estiman como el punto de
unión de los dos tramos de INVÍAS (geometría multiline de red_vial.csv)
que llegan al nodo. Cada punto DANE se compara contra los extremos de los
tramos de INVÍAS adyacentes y la distancia queda en
outputs/verificacion_coordenadas.csv.

Escribe data/carga/coordenadas_nodos.csv.
"""
import csv
import json
import re
import sys
from math import asin, cos, radians, sin, sqrt

from build_graph import RAIZ, SALIDA
from construir_red import TRAMO_EXTRA_LONGITUD, TRAMOS

DATOS = RAIZ / "data" / "carga"
MUNICIPIOS_CSV = DATOS / "divipola_municipios_gdxc-w37w.csv"
CENTROS_CSV = DATOS / "divipola_centros_poblados_xaxy-8nri.csv"
FUENTE_MUN = ("DANE, DIVIPOLA Códigos municipios (datos.gov.co/resource/"
              "gdxc-w37w), corte 30-12-2024, descargado 7-10-2026")
FUENTE_CP = ("DANE, DIVIPOLA Códigos cabeceras y centros poblados "
             "(datos.gov.co/resource/xaxy-8nri), corte 30-12-2024, "
             "descargado 7-10-2026")
FUENTE_INVIAS = ("INVÍAS, Red Vial (datos.gov.co/resource/ie7y-asdn), "
                 "geometría multiline, descargado 6-10-2026")

# nodo -> código DIVIPOLA del municipio (elección explícita de homónimos)
MUNICIPIOS = {
    "Bogotá": "11001", "Tocancipá": "25817", "Chocontá": "25183",
    "Tunja": "15001", "Duitama": "15238", "Barbosa": "68077",
    "Chiquinquirá": "15176", "Sáchica": "15638", "Cajicá": "25126",
    "Zipaquirá": "25899", "Ubaté": "25843", "Puente Nacional": "68572",
    "Madrid": "25430", "Guasca": "25322",
    "Villavicencio": "50001", "Granada": "50313", "Puerto López": "50573",
    "Puerto Gaitán": "50568", "Villeta": "25875", "Honda": "73349",
    "Mariquita": "73443", "Fusagasugá": "25290", "Girardot": "25307",
    "El Espinal": "73268", "San Gil": "68679", "Bucaramanga": "68001",
    "Pamplona": "54518",
}
# nodo -> código DIVIPOLA del centro poblado
CENTROS = {"Cambao": "25662001", "Presidente": "54174006"}
# sin coordenada DANE verificable: se estima la unión de tramos INVÍAS
SIN_DANE = ["Cuestaboba", "La Palmera", "Ye de Granada"]
OBSERVACION_NOMBRE = {
    "Ubaté": "Municipio Villa de San Diego de Ubaté",
    "Mariquita": "Municipio San Sebastián de Mariquita",
    "El Espinal": "Municipio Espinal",
}


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia geodésica en km (esfera de radio 6371.0088 km)."""
    f1, f2 = radians(lat1), radians(lat2)
    a = (sin((f2 - f1) / 2) ** 2
         + cos(f1) * cos(f2) * sin(radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6371.0088 * asin(sqrt(a))


def decimal(texto):
    return float(texto.replace(",", "."))


def puntos_dane():
    """Coordenadas DANE por nodo: (lat, lon, fuente, observación)."""
    res = {}
    with open(MUNICIPIOS_CSV, encoding="utf-8") as f:
        filas = {r["cod_mpio"]: r for r in csv.DictReader(f)}
    for nodo, cod in MUNICIPIOS.items():
        r = filas[cod]
        obs = (f"{r['nom_mpio'].title()}, {r['dpto'].title()} "
               f"(cód. {cod}); cabecera municipal")
        if nodo in OBSERVACION_NOMBRE:
            obs = (f"{OBSERVACION_NOMBRE[nodo]}, {r['dpto'].title()} "
                   f"(cód. {cod}); cabecera municipal")
        res[nodo] = (decimal(r["latitud"]), decimal(r["longitud"]),
                     FUENTE_MUN, obs)
    with open(CENTROS_CSV, encoding="utf-8") as f:
        cp = {r["codigo_centro_poblado"]: r for r in csv.DictReader(f)}
    for nodo, cod in CENTROS.items():
        r = cp[cod]
        obs = (f"Centro poblado {r['nombre_centro_poblado'].title()}, "
               f"{r['nombre_municipio'].title()}, "
               f"{r['nombre_departamento'].title()} (cód. {cod})")
        res[nodo] = (decimal(r["latitud"]), decimal(r["longitud"]),
                     FUENTE_CP, obs)
    return res


def extremos_invias():
    """Extremos de la geometría INVÍAS por sector usado en el grafo."""
    csv.field_size_limit(sys.maxsize)
    sectores = {t[0] for t in TRAMOS}
    sectores |= set(TRAMO_EXTRA_LONGITUD.values())
    res = {}
    with open(DATOS / "red_vial.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            s = r["sector"].strip()
            if s not in sectores:
                continue
            partes = re.findall(r"\(([^()]+)\)", r["multiline"])
            for parte in partes:
                pares = [tuple(map(float, p.split()))
                         for p in parte.split(",")]
                pts = res.setdefault(s, [])
                pts.append((pares[0][1], pares[0][0]))
                pts.append((pares[-1][1], pares[-1][0]))
    return res


def sectores_de(nodo):
    """Sectores INVÍAS de los tramos que llegan al nodo."""
    out = []
    for sector, o, d, _ in TRAMOS:
        if nodo in (o, d):
            out.append(sector)
            extra = TRAMO_EXTRA_LONGITUD.get((sector, o, d))
            if extra:
                out.append(extra)
    return out


def union_invias(nodo, extremos, ref=None):
    """Punto de unión de los tramos del nodo y la separación de extremos.

    Con ref (lat, lon) elige, entre los extremos de los tramos adyacentes,
    el más cercano a ref. Sin ref busca el par de extremos de tramos
    distintos más próximo entre sí y devuelve su punto medio.
    """
    grupos = [extremos[s] for s in sectores_de(nodo)]
    if ref is not None:
        todos = [p for g in grupos for p in g]
        mejor = min(todos, key=lambda p: haversine_km(*ref, *p))
        return mejor, haversine_km(*ref, *mejor)
    mejor, dmin = None, 1e9
    for i, ga in enumerate(grupos):
        for gb in grupos[i + 1:]:
            for pa in ga:
                for pb in gb:
                    d = haversine_km(*pa, *pb)
                    if d < dmin:
                        mejor, dmin = (pa, pb), d
    (a, b) = mejor
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), dmin


def main():
    dane = puntos_dane()
    extremos = extremos_invias()
    nodos = json.load(open(SALIDA / "nodos_red.json", encoding="utf-8"))
    faltan = set(nodos) - set(dane) - set(SIN_DANE)
    if faltan:
        raise ValueError(f"Nodos sin fuente de coordenada: {faltan}")
    filas, verif = [], []
    for nodo in sorted(nodos):
        if nodo in dane:
            lat, lon, fuente, obs = dane[nodo]
            _, sep = union_invias(nodo, extremos, ref=(lat, lon))
            verif.append((nodo, "DANE", f"{sep:.2f}"))
            obs += (f"; extremo INVÍAS más cercano a {sep:.2f} km")
        else:
            (lat, lon), sep = union_invias(nodo, extremos)
            fuente = FUENTE_INVIAS
            obs = ("Sin coordenada DANE; punto estimado como unión de los "
                   f"tramos {' y '.join(sectores_de(nodo))} "
                   f"(separación de extremos {sep:.3f} km)")
            verif.append((nodo, "INVÍAS", f"{sep:.3f}"))
        filas.append((nodo, f"{lat:.6f}", f"{lon:.6f}", fuente, obs))
    with open(DATOS / "coordenadas_nodos.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["nodo", "latitud", "longitud", "fuente", "observacion"])
        w.writerows(filas)
    with open(SALIDA / "verificacion_coordenadas.csv", "w",
              encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["nodo", "fuente_coordenada", "separacion_km"])
        w.writerows(verif)
    for fila in verif:
        print(*fila)


if __name__ == "__main__":
    main()
