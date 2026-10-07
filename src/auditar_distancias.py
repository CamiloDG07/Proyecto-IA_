"""Auditoría de las distancias por registro y verificación de la regla.

Para cada registro (sin unir) de los sectores usados en el grafo calcula
tres medidas oficiales a partir de red_vial.csv:

  A: longitud registrada (shape__length), en km, con la columna calzada;
  B: tramo entre progresivas, en km. Columnas usadas:
       poste_de_referencia_inicial y poste_de_referencia_final (PR, en km)
       distancia_inicial y distancia_final (desplazamiento sobre el PR, que
       se interpreta en metros; la interpretación se contrasta con A en los
       registros de calzada sencilla).
     B_pr = |PR_final - PR_inicial|;
     B_tot = |(PR_final + distancia_final / 1000)
              - (PR_inicial + distancia_inicial / 1000)|;
  C: longitud a lo largo de la geometría del registro, en km: C_suma es la
     suma de todas sus partes y C_camino el camino más corto entre sus
     extremos (aproximado, ver auditar_aristas.py).

Regla de corrección (fijada de antemano): por registro, distancia = B_tot si
1.7 <= A / B_tot <= 2.3 (doble calzada digitalizada); en cualquier otro caso,
A. Los registros fuera de la banda con A / B_tot menor que 0.8 o mayor que
1.2 se marcan como patrón no estándar y conservan A. La regla se aplica en
construir_red.py (REGLA_BANDA); este script la verifica con una segunda
medida oficial: en cada registro corregido, |B_tot - C_camino| / C_camino no
debe superar 0.15 cuando C_camino es finito.

Escribe outputs/auditoria_distancias.csv.
"""
import csv
import re
import sys

import numpy as np

from auditar_aristas import camino_geometria, extremos, hav
from build_graph import SALIDA
from construir_red import REGLA_BANDA, TRAMO_EXTRA_LONGITUD, TRAMOS
from obtener_coordenadas import DATOS

TOLERANCIA_CAMINO = 0.15
BANDA_ESTANDAR = (0.8, 1.2)


def aristas_por_sector():
    """sector -> texto de la(s) arista(s) que lo usan."""
    mapa = {}
    for sector, origen, destino, _ in TRAMOS:
        texto = f"{origen} - {destino}"
        mapa.setdefault(sector, []).append(texto)
        extra = TRAMO_EXTRA_LONGITUD.get((sector, origen, destino))
        if extra:
            mapa.setdefault(extra, []).append(texto)
    return {s: " / ".join(v) for s, v in mapa.items()}


def razon(a, b):
    return "" if not b else f"{a / b:.3f}"


def clasificar(a, b_tot):
    """(patrón, aplicada_km) según la regla fijada."""
    if not b_tot:
        return "sin progresivas", a
    r = a / b_tot
    if REGLA_BANDA[0] <= r <= REGLA_BANDA[1]:
        return "doble calzada (corregido)", b_tot
    if r < BANDA_ESTANDAR[0] or r > BANDA_ESTANDAR[1]:
        return "patrón no estándar", a
    return "registro simple", a


def main():
    csv.field_size_limit(sys.maxsize)
    sectores = aristas_por_sector()
    filas, fallas = [], []
    with open(DATOS / "red_vial.csv", encoding="utf-8") as f:
        indices = {}
        for r in csv.DictReader(f):
            sector = r["sector"].strip()
            if sector not in sectores:
                continue
            indices[sector] = indices.get(sector, 0) + 1
            partes = []
            for parte in re.findall(r"\(([^()]+)\)", r["multiline"]):
                pts = np.array([[float(v) for v in q.split()]
                                for q in parte.split(",")])
                partes.append(pts[:, ::-1])
            suma = sum(float(hav(p[:-1, 0], p[:-1, 1],
                                 p[1:, 0], p[1:, 1]).sum()) for p in partes)
            a, b = extremos(np.vstack(partes))
            camino = camino_geometria(partes, a, b)
            km = float(r["shape__length"]) / 1000
            pri = float(r["poste_de_referencia_inicial"])
            prf = float(r["poste_de_referencia_final"])
            di = float(r["distancia_inicial"] or 0)
            df = float(r["distancia_final"] or 0)
            b_pr = abs(prf - pri)
            b_total = abs((prf + df / 1000) - (pri + di / 1000))
            patron, aplicada = clasificar(km, b_total)
            camino_ok = bool(np.isfinite(camino))
            dif = abs(b_total - camino) / camino if camino_ok else None
            if patron.startswith("doble calzada"):
                if dif is None:
                    verif = "sin camino finito"
                elif dif > TOLERANCIA_CAMINO:
                    verif = "FALLA"
                    fallas.append((sectores[sector], sector, dif))
                else:
                    verif = "ok"
            else:
                verif = ""
            filas.append([
                sectores[sector], sector, indices[sector], r["calzada"],
                f"{km:.3f}", r["poste_de_referencia_inicial"],
                r["poste_de_referencia_final"], r["distancia_inicial"],
                r["distancia_final"], f"{b_pr:.3f}", f"{b_total:.3f}",
                f"{suma:.3f}", f"{camino:.3f}" if camino_ok else "",
                razon(km, b_pr), razon(km, b_total), razon(km, suma),
                razon(km, camino) if camino_ok else "", patron,
                f"{aplicada:.3f}", "" if dif is None else f"{dif:.3f}",
                verif])
    filas.sort(key=lambda x: (x[0], x[1], x[2]))
    with open(SALIDA / "auditoria_distancias.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.writer(f)
        w.writerow(["arista", "sector", "registro", "calzada",
                    "A_longitud_registrada_km", "pr_inicial", "pr_final",
                    "distancia_inicial_m", "distancia_final_m",
                    "B_pr_km", "B_total_km", "C_suma_km", "C_camino_km",
                    "A_sobre_B_pr", "A_sobre_B_total", "A_sobre_C_suma",
                    "A_sobre_C_camino", "patron", "valor_aplicado_km",
                    "dif_relativa_B_C_camino", "verificacion_camino"])
        w.writerows(filas)
    corregidos = sum(1 for x in filas if x[17].startswith("doble calzada"))
    print(f"{len(filas)} registros en {len(sectores)} sectores; "
          f"{corregidos} corregidos; verificación contra el camino: "
          f"{len(fallas)} fallas")
    for falla in fallas:
        print("  FALLA:", falla)
    return len(fallas)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
