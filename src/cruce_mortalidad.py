"""Cruce de los sectores críticos de mortalidad de la ANSV (2022) con la red.

Fuente: «Sectores críticos mortalidad 2022», ANSV, datos.gov.co
(identificador ybqk-8s42, CC BY-SA 4.0), descargada a
data/carga/nuevas/sectores_criticos_mortalidad_2022_ybqk-8s42.csv.

La lista trae segmentos de a lo sumo 10 km con las coordenadas de sus dos
extremos (xi, yi, xf, yf), la prioridad por actor vial (todos, moto,
peatón y vehículo) y el código del segmento (cod). El cruce con la red es
geométrico y determinista, sin emparejar por nombre: un segmento pertenece a
una arista si sus dos extremos quedan a no más de UMBRAL_KM del trazado de la
arista (outputs/trazado_aristas.json) y, si queda cerca de varias, se asigna a
la de menor distancia máxima. Cada segmento (cod) cuenta una vez, sin importar
en cuántas listas de actores figure.

Atributo de la arista: sectores_mortalidad (cantidad de segmentos) y
mortalidad_por_100km (esa cantidad por cada 100 km de la arista). Que una
arista no figure no significa que no haya muertes: la lista solo trae los
sectores de mayor prioridad, por lo que mortalidad_disponible es verdadero
solo si figura al menos un segmento.

Escribe outputs/riesgo_mortalidad_aristas.json (con el detalle por arista) y
outputs/validacion_riesgo_mortalidad.json (validación retrospectiva contra
las aristas que ya tienen GiZScore).
"""
import csv
import json

import numpy as np

from build_graph import SALIDA

RAIZ = SALIDA.parent
FUENTE = RAIZ / "data" / "carga" / "nuevas" / (
    "sectores_criticos_mortalidad_2022_ybqk-8s42.csv")
UMBRAL_KM = 0.3
KM_POR_GRADO = 111.32


def _a_km(lat, lon, lat0):
    return np.array([lon * KM_POR_GRADO * np.cos(np.radians(lat0)),
                     lat * KM_POR_GRADO])


def _distancia_a_polilinea(p, poli):
    a, b = poli[:-1], poli[1:]
    ab = b - a
    den = (ab ** 2).sum(1)
    seguro = np.where(den > 0, den, 1)
    t = np.where(den > 0, np.clip(((p - a) * ab).sum(1) / seguro, 0, 1), 0)
    q = a + ab * t[:, None]
    return float(np.sqrt(((p - q) ** 2).sum(1)).min())


def segmentos():
    """Segmentos únicos (por cod) con sus extremos y los actores listados."""
    unicos = {}
    with open(FUENTE, encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            s = unicos.setdefault(fila["cod"], {
                "cod": fila["cod"], "corredor": fila["corredor"],
                "xi": float(fila["xi"]), "yi": float(fila["yi"]),
                "xf": float(fila["xf"]), "yf": float(fila["yf"]),
                "prioridades": {}})
            s["prioridades"][fila["actorvial"]] = int(fila["prioridad"])
    return list(unicos.values())


def asignar(trazado, segs):
    """Para cada segmento, la arista más cercana dentro del umbral."""
    lat0 = 5.5
    polis = {k: [np.array([_a_km(la, lo, lat0) for la, lo in parte])
                 for parte in d["partes"]] for k, d in trazado.items()}
    asignado = {}
    for s in segs:
        pi = _a_km(s["yi"], s["xi"], lat0)
        pf = _a_km(s["yf"], s["xf"], lat0)
        mejor = None
        for clave, ps in polis.items():
            di = min(_distancia_a_polilinea(pi, p) for p in ps)
            df = min(_distancia_a_polilinea(pf, p) for p in ps)
            d = max(di, df)
            if d <= UMBRAL_KM and (mejor is None or d < mejor[1]):
                mejor = (clave, d)
        if mejor:
            asignado[s["cod"]] = mejor
    return asignado


def calcular(aristas, trazado):
    """Atributos de mortalidad por arista (lista alineada con `aristas`)."""
    import mapa_geografico as mg
    segs = segmentos()
    asignado = asignar(trazado, segs)
    por_cod = {s["cod"]: s for s in segs}
    cuentas = {}
    for cod, (clave, d) in asignado.items():
        cuentas.setdefault(clave, []).append((cod, d))
    salida = []
    for a in aristas:
        clave = mg.clave_de(trazado, a["origen"], a["destino"])
        lista = sorted(cuentas.get(clave, []))
        n = len(lista)
        salida.append({
            "origen": a["origen"], "destino": a["destino"],
            "sectores_mortalidad": n,
            "mortalidad_por_100km": round(100 * n / a["distancia_km"], 3),
            "mortalidad_disponible": n > 0,
            "segmentos": [{"cod": c, "corredor": por_cod[c]["corredor"],
                           "prioridades": por_cod[c]["prioridades"],
                           "distancia_max_al_trazado_km": round(d, 4)}
                          for c, d in lista]})
    return salida


def rangos(valores):
    orden = sorted(range(len(valores)), key=lambda i: valores[i])
    r = [0.0] * len(valores)
    i = 0
    while i < len(orden):
        j = i
        while (j + 1 < len(orden)
               and valores[orden[j + 1]] == valores[orden[i]]):
            j += 1
        for k in range(i, j + 1):
            r[orden[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x, y):
    rx, ry = rangos(x), rangos(y)
    return float(np.corrcoef(rx, ry)[0, 1])


def validar(aristas, mortalidad):
    """Coherencia con el riesgo ya medido (GiZScore) en las aristas que lo
    tienen: orden (Spearman) y coincidencia de presencia."""
    con = [(a, m) for a, m in zip(aristas, mortalidad)
           if a["riesgo_puntos_criticos"] > 0]
    giz = [a["riesgo_gizscore_prom"] for a, _ in con]
    fall = [a["riesgo_fallecidos_hist"] for a, _ in con]
    nuevo = [m["mortalidad_por_100km"] for _, m in con]
    presentes = sum(1 for _, m in con if m["mortalidad_disponible"])
    sin_giz = [m for a, m in zip(aristas, mortalidad)
               if a["riesgo_puntos_criticos"] == 0]
    return {
        "aristas_con_gizscore": len(con),
        "de_ellas_con_sector_de_mortalidad": presentes,
        "spearman_mortalidad_vs_gizscore": round(spearman(nuevo, giz), 3),
        "spearman_mortalidad_vs_fallecidos": round(spearman(nuevo, fall), 3),
        "aristas_sin_gizscore_con_sector_de_mortalidad": sum(
            1 for m in sin_giz if m["mortalidad_disponible"]),
        "aristas_sin_gizscore": len(sin_giz),
        "cobertura_antes": len(con),
        "cobertura_despues_union": sum(
            1 for a, m in zip(aristas, mortalidad)
            if a["riesgo_puntos_criticos"] > 0
            or m["mortalidad_disponible"]),
        "cobertura_solo_mortalidad": sum(
            1 for m in mortalidad if m["mortalidad_disponible"])}


def main():
    import mapa_geografico as mg
    with open(SALIDA / "aristas_red.json", encoding="utf-8") as f:
        aristas = json.load(f)
    trazado = mg.cargar_trazado()
    mortalidad = calcular(aristas, trazado)
    with open(SALIDA / "riesgo_mortalidad_aristas.json", "w",
              encoding="utf-8") as f:
        json.dump(mortalidad, f, ensure_ascii=False, indent=1)
    v = validar(aristas, mortalidad)
    v["umbral_km"] = UMBRAL_KM
    v["fuente"] = "ANSV, Sectores críticos mortalidad 2022 (ybqk-8s42)"
    with open(SALIDA / "validacion_riesgo_mortalidad.json", "w",
              encoding="utf-8") as f:
        json.dump(v, f, ensure_ascii=False, indent=1)
    print(json.dumps(v, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
