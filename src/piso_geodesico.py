"""Piso geodésico de las distancias del modelo.

Una carretera no puede ser más corta que la línea recta entre sus extremos.
Cuando la distancia oficial de una arista (ya corregida por doble calzada)
es menor que la distancia geodésica entre las coordenadas de sus nodos, el
dato está incompleto: sector truncado en la fuente, entrada urbana que no
cubre la geometría de INVÍAS o coordenada del nodo en el centro del
municipio. Regla fijada de antemano:

    distancia_modelo = max(distancia_oficial, geodésica(origen, destino))

La geodésica se redondea hacia arriba a 6 decimales (nunca hacia abajo, para
que el piso no quede por debajo de la recta). El piso es una cota inferior
física, no una medida: las aristas con piso se marcan y la distancia oficial
se conserva. Con el piso, el costo de distancia de toda arista es mayor o
igual que su geodésica y, por la desigualdad triangular, h(n) = geodésica(n,
meta) es consistente y admisible en toda la red (alfa = 1).

Este módulo escribe outputs/datos/aristas_piso_geodesico.csv: las aristas cuya
distancia oficial es menor que la geodésica, con su causa documentada.
"""
import csv
import json
from math import ceil

from build_graph import SALIDA
from heuristica import cargar_coordenadas, haversine_km

DECIMALES = 6
# nodos sin punto DANE: su coordenada se derivó de la unión de tramos de INVÍAS
COORDENADA_DERIVADA = ("Cuestaboba", "La Palmera", "Ye de Granada")
TOLERANCIA = 1e-9


def techo(km, decimales=DECIMALES):
    """Redondeo hacia arriba a `decimales` (nunca por debajo de `km`)."""
    escala = 10 ** decimales
    return ceil(km * escala - 1e-9) / escala


def geodesica_arista(coordenadas, origen, destino):
    """Distancia geodésica (km) redondeada hacia arriba a 6 decimales."""
    return techo(haversine_km(*coordenadas[origen], *coordenadas[destino]))


def distancia_modelo(oficial_km, geodesica_km):
    """(distancia del modelo, piso aplicado en km)."""
    modelo = max(oficial_km, geodesica_km)
    return modelo, round(modelo - oficial_km, DECIMALES)


def causa(a, auditoria):
    """Causa documentada del piso, con la medida que la respalda."""
    par = (a["origen"], a["destino"])
    fila = auditoria[par]
    ext_o, ext_d = (float(fila["extremo_a_origen_km"]),
                    float(fila["extremo_a_destino_km"]))
    if set(par) == {"Chocontá", "Tunja"}:
        return ("sector truncado en la fuente: el trazado queda a "
                f"{max(ext_o, ext_d):.2f} km de un nodo")
    if "Bogotá" in par:
        ext = ext_o if par[0] == "Bogotá" else ext_d
        return ("entrada urbana a Bogotá: el trazado de INVÍAS empieza a "
                f"{ext:.2f} km del nodo")
    if set(par) & set(COORDENADA_DERIVADA):
        return ("coordenada del nodo derivada de la unión de tramos de "
                "INVÍAS (sin punto DANE)")
    return ("coordenada del nodo en el centro del municipio: el extremo del "
            f"trazado queda a {max(ext_o, ext_d):.2f} km del nodo")


def candidatas(aristas, coordenadas, auditoria):
    """Filas de las aristas con distancia oficial menor que la geodésica."""
    filas = []
    for a in aristas:
        oficial = a.get("distancia_oficial_km", a["distancia_km"])
        geo = geodesica_arista(coordenadas, a["origen"], a["destino"])
        modelo, piso = distancia_modelo(oficial, geo)
        if piso > TOLERANCIA:
            filas.append({
                "origen": a["origen"], "destino": a["destino"],
                "distancia_oficial_km": f"{oficial:.2f}",
                "distancia_geodesica_km": f"{geo:.2f}",
                "razon": f"{oficial / geo:.4f}",
                "piso_km": f"{piso:.2f}",
                "distancia_modelo_km": f"{modelo:.2f}",
                "causa": causa(a, auditoria)})
    return sorted(filas, key=lambda f: float(f["razon"]))


def leer_auditoria():
    with open(SALIDA / "auditoria_aristas.csv", encoding="utf-8") as f:
        return {(r["origen"], r["destino"]): r for r in csv.DictReader(f)}


def main():
    with open(SALIDA / "aristas_red.json", encoding="utf-8") as f:
        aristas = json.load(f)
    filas = candidatas(aristas, cargar_coordenadas(), leer_auditoria())
    campos = ["origen", "destino", "distancia_oficial_km",
              "distancia_geodesica_km", "razon", "piso_km",
              "distancia_modelo_km", "causa"]
    with open(SALIDA / "aristas_piso_geodesico.csv", "w", encoding="utf-8",
              newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)
    print(f"{len(filas)} aristas con distancia oficial menor que la "
          "geodésica")
    for fila in filas:
        print("  ", " | ".join(fila[c] for c in campos))


if __name__ == "__main__":
    main()
