"""Agente predictivo: integra la búsqueda con los modelos del Corte 3.

Uso:
    python src/agente_predictivo.py ORIGEN DESTINO [--mes AAAA-MM]

Para el mes pedido, el agente toma de outputs/datos/pronostico_red.json el
tránsito diario, el nivel de tránsito (bajo, medio o alto) y el tiempo BPR
de cada tramo, los pone en el grafo como atributos y busca con A* la ruta de
menor tiempo estimado. Después compara todas las rutas simples entre el
origen y el destino (la red tiene un solo ciclo: hay una o dos) y avisa
qué tramos se esperan con tránsito alto y cuáles no tienen dato.

Heurística del criterio de tiempo:

    h(n) = 60 * d_geo(n, meta) / velocidad libre

Es admisible y consistente: el tiempo de un tramo nunca es menor que su
tiempo libre (el factor BPR es mayor o igual que 1) y, por el piso
geodésico, la distancia de un tramo nunca es menor que la geodésica entre
sus nodos.

Este módulo no necesita scikit-learn: los modelos se entrenan en
experimentos/experimentos_corte3.py y aquí solo se leen sus pronósticos.
"""
import argparse
import json
import sys

import networkx as nx

from build_graph import construir_grafo
from busquedas import a_estrella
from heuristica import cargar_coordenadas, haversine_km
from modelo_tiempo import factor_bpr, tiempo_libre_min
from rutas import SALIDA

ARCHIVO = "pronostico_red.json"
ROTULO_ORIGEN = {
    "prueba": "predicción a un mes (periodo de prueba)",
    "pronostico": "pronóstico recursivo del modelo",
    "historico": "serie terminada: mismo mes de su último año",
    "sin_dato": "sin peaje en la fuente: tiempo libre",
}


def cargar_pronostico(ruta=None):
    with open(ruta or SALIDA / ARCHIVO, encoding="utf-8") as f:
        return json.load(f)


def meses_disponibles(pronostico):
    return pronostico["meses_prueba"] + pronostico["meses_pronostico"]


def grafo_del_mes(mes, pronostico=None, grafo=None):
    """Grafo de la red con los atributos de tiempo y de nivel del mes."""
    pronostico = pronostico or cargar_pronostico()
    if mes not in meses_disponibles(pronostico):
        raise ValueError(f"Mes fuera del pronóstico: {mes}")
    grafo = (grafo or construir_grafo()).copy()
    config = pronostico["config_tiempo"]
    for tramo in pronostico["tramos"]:
        dato = tramo["meses"].get(mes)
        arista = grafo[tramo["origen"]][tramo["destino"]]
        # sin redondear, para que h nunca supere el costo del tramo
        libre = tiempo_libre_min(arista["distancia_km"], config)
        arista["tiempo_libre_min"] = libre
        arista["doble_calzada"] = tramo["doble_calzada"]
        arista["estado_transito"] = tramo["estado"]
        if dato is None:
            arista.update(tiempo_min=libre,
                          nivel_transito=None, transito_diario=None,
                          saturacion=None, origen_dato="sin_dato")
        else:
            arista.update(tiempo_min=libre * factor_bpr(
                              dato["saturacion"], config),
                          nivel_transito=dato["clase"],
                          transito_diario=dato["transito_usado"],
                          saturacion=dato["saturacion"],
                          origen_dato=dato["origen_dato"])
    grafo.graph["mes"] = mes
    grafo.graph["velocidad_libre_kmh"] = pronostico["config_tiempo"][
        "velocidad_libre_kmh"]
    return grafo


class HeuristicaTiempo:
    """h(n, meta) en minutos: geodésica a la velocidad libre."""

    def __init__(self, velocidad_libre_kmh, coordenadas=None):
        self.velocidad = velocidad_libre_kmh
        self.coordenadas = coordenadas or cargar_coordenadas()

    def __call__(self, nodo, meta):
        return 60.0 * haversine_km(*self.coordenadas[nodo],
                                   *self.coordenadas[meta]) / self.velocidad


def verificar_heuristica(grafo, h):
    """Violaciones de admisibilidad y de consistencia (deben ser cero)."""
    costos = dict(nx.all_pairs_dijkstra_path_length(
        grafo, weight="tiempo_min"))
    tolerancia = 1e-6
    admisibilidad = sum(1 for n in grafo for m in grafo
                        if h(n, m) > costos[n][m] + tolerancia)
    consistencia = sum(
        1 for u, v in grafo.edges for m in grafo for a, b in ((u, v), (v, u))
        if h(a, m) > grafo[a][b]["tiempo_min"] + h(b, m) + tolerancia)
    return {"admisibilidad": admisibilidad, "consistencia": consistencia}


def resumen_ruta(grafo, ruta):
    """Totales y avisos de una ruta en el grafo del mes."""
    tramos = [(u, v, grafo[u][v]) for u, v in zip(ruta, ruta[1:])]
    libre = sum(t["tiempo_libre_min"] for _, _, t in tramos)
    total = sum(t["tiempo_min"] for _, _, t in tramos)
    niveles = {"bajo": 0, "medio": 0, "alto": 0, "sin dato": 0}
    for _, _, t in tramos:
        niveles[t["nivel_transito"] or "sin dato"] += 1
    return {
        "ruta": list(ruta), "saltos": len(tramos),
        "distancia_km": round(sum(t["distancia_km"]
                                  for _, _, t in tramos), 2),
        "peaje_cop": sum(t["peaje_cop_camion"] for _, _, t in tramos),
        "tiempo_libre_min": round(libre, 1),
        "tiempo_min": round(total, 1),
        "demora_min": round(total - libre, 2),
        "tramos_por_nivel": niveles,
        "tramos_alto": [f"{u} - {v}" for u, v, t in tramos
                        if t["nivel_transito"] == "alto"],
        "tramos_sin_dato": [f"{u} - {v}" for u, v, t in tramos
                            if t["nivel_transito"] is None],
        "tramos_historicos": [f"{u} - {v}" for u, v, t in tramos
                              if t["origen_dato"] == "historico"],
        "detalle": [{
            "origen": u, "destino": v,
            "distancia_km": round(t["distancia_km"], 2),
            "tiempo_min": round(t["tiempo_min"], 1),
            "nivel_transito": t["nivel_transito"],
            "transito_diario": t["transito_diario"],
            "saturacion": t["saturacion"],
            "origen_dato": t["origen_dato"]} for u, v, t in tramos],
    }


def recomendar(origen, destino, mes, pronostico=None, grafo=None):
    """Ruta de menor tiempo estimado en `mes` y sus alternativas."""
    red = grafo_del_mes(mes, pronostico, grafo)
    for nodo in (origen, destino):
        if nodo not in red:
            raise ValueError(f"Ciudad fuera de la red: {nodo}")
    if origen == destino:
        raise ValueError("El origen y el destino son la misma ciudad")
    h = HeuristicaTiempo(red.graph["velocidad_libre_kmh"])
    busqueda = a_estrella(red, origen, destino, "tiempo_min", h)
    elegida = resumen_ruta(red, busqueda["ruta"])
    alternativas = [resumen_ruta(red, r) for r in sorted(
        nx.all_simple_paths(red, origen, destino))
        if r != busqueda["ruta"]]
    avisos = []
    if elegida["tramos_alto"]:
        avisos.append("Tránsito alto previsto en: "
                      + "; ".join(elegida["tramos_alto"]) + ".")
    if elegida["tramos_sin_dato"]:
        avisos.append("Sin dato de tránsito (se usa el tiempo libre) en: "
                      + "; ".join(elegida["tramos_sin_dato"]) + ".")
    if elegida["tramos_historicos"]:
        avisos.append("Tránsito de una serie terminada (valor histórico) "
                      "en: " + "; ".join(elegida["tramos_historicos"])
                      + ".")
    for otra in alternativas:
        menos = (elegida["tramos_por_nivel"]["alto"]
                 - otra["tramos_por_nivel"]["alto"])
        if menos > 0:
            avisos.append(
                f"La alternativa de {otra['distancia_km']:.2f} km evita "
                f"{menos} tramo(s) con tránsito alto, pero tarda "
                f"{otra['tiempo_min'] - elegida['tiempo_min']:.0f} min "
                "más.")
    return {
        "origen": origen, "destino": destino, "mes": mes,
        "criterio": "tiempo_estimado", "algoritmo": "A*",
        "nodos_expandidos": busqueda["nodos_expandidos"],
        "reexpansiones": busqueda["reexpansiones"],
        "velocidad_libre_kmh": red.graph["velocidad_libre_kmh"],
        "elegida": elegida, "alternativas": alternativas,
        "avisos": avisos,
    }


def _horas(minutos):
    horas, resto = divmod(int(minutos + 0.5), 60)
    return f"{horas} h {resto:02d} min"


def formatear(r):
    e = r["elegida"]
    lineas = [
        f"Ruta de menor tiempo estimado de {r['origen']} a {r['destino']} "
        f"en {r['mes']} (A*, {r['nodos_expandidos']} nodos expandidos)",
        "  " + " > ".join(e["ruta"]),
        f"  {e['distancia_km']:.2f} km, "
        + f"{e['peaje_cop']:,}".replace(",", " ")
        + f" COP de peaje, {_horas(e['tiempo_min'])} "
        f"(libre {_horas(e['tiempo_libre_min'])}, demora "
        f"{e['demora_min']:.2f} min)",
        "  Tramo, tránsito diario, nivel, saturación, origen del dato:"]
    for d in e["detalle"]:
        transito = ("sin dato" if d["transito_diario"] is None
                    else f"{d['transito_diario']:.0f} veh/día")
        nivel = d["nivel_transito"] or "sin dato"
        razon = "" if d["saturacion"] is None else f"{d['saturacion']:.2f}"
        lineas.append(f"    {d['origen']} - {d['destino']}: {transito}, "
                      f"{nivel}, {razon or '-'}, "
                      f"{ROTULO_ORIGEN[d['origen_dato']]}")
    for otra in r["alternativas"]:
        lineas.append(
            f"Alternativa: {' > '.join(otra['ruta'])}")
        lineas.append(
            f"  {otra['distancia_km']:.2f} km, "
            f"{_horas(otra['tiempo_min'])}, "
            f"{otra['tramos_por_nivel']['alto']} tramo(s) con tránsito "
            "alto")
    if r["avisos"]:
        lineas.append("Avisos:")
        lineas.extend(f"  - {a}" for a in r["avisos"])
    lineas.append(
        f"El tiempo es una estimación (función BPR, velocidad libre de "
        f"{r['velocidad_libre_kmh']} km/h supuesta), no una medición.")
    return "\n".join(lineas)


def main(argumentos):
    pronostico = cargar_pronostico()
    lector = argparse.ArgumentParser(prog="agente_predictivo.py")
    lector.add_argument("origen")
    lector.add_argument("destino")
    lector.add_argument("--mes", default=pronostico["meses_pronostico"][0],
                        choices=meses_disponibles(pronostico))
    a = lector.parse_args(argumentos)
    try:
        print(formatear(recomendar(a.origen, a.destino, a.mes, pronostico)))
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
