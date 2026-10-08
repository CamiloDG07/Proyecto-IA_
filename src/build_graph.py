"""Construcción del grafo de la red de carga interurbana.

Lee outputs/aristas_red.json y outputs/nodos_red.json (generados por
construir_red.py), calcula el costo compuesto por arista y guarda el grafo en
outputs/grafo_carga.gpickle.

Costo compuesto, normalizado por el máximo de cada criterio:

    c(e) = w1 * d_e / d_max + w2 * p_e / p_max + w3 * r_e / r_max

con r_e el puntaje GiZScore promedio de la arista. La normalización por el
máximo conserva la proporcionalidad con la distancia (la de mín-máx no).

Riesgo faltante: 21 de 32 aristas no tienen dato. No se imputa. Se guardan
dos variantes y un indicador booleano riesgo_disponible:
  - peso_multicriterio: riesgo faltante tratado como 0 (variante limitada,
    sesga hacia corredores sin medición);
  - peso_sin_riesgo: sin término de riesgo, con w1 y w2 renormalizados.

Costo monetario (config_costos.json, cada insumo con su fuente y su estado):

    combustible_cop   = km * precio del galón / rendimiento (km por galón)
    costo_variable_cop = km * (combustible por km + otros costos por km)
    costo_operativo_cop = peaje + costo_variable_cop

y el costo compuesto total, con un cuarto peso para el dinero:

    c_total(e) = w1 d/d_max + w2 p/p_max + w3 r/r_max + w4 cv/cv_max

con w1 + w2 + w3 + w4 = 1 (peso_total; faltante de riesgo igual a 0) y su
variante sin riesgo con los pesos restantes renormalizados
(peso_total_sin_riesgo).

Sectores críticos de mortalidad de la ANSV (solo sensibilidad, ver
cruce_mortalidad.py): peso_mortalidad reemplaza el GiZScore por
mortalidad_por_100km, normalizado por su máximo (faltante igual a 0).
"""
import json
import pickle
from pathlib import Path

import networkx as nx

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "outputs"

# Sin criterio objetivo para ponderar los tres criterios: pesos iguales.
PESOS = {"distancia": 1 / 3, "peaje": 1 / 3, "riesgo": 1 / 3}
CONFIG_COSTOS = RAIZ / "config_costos.json"
USUARIO = "dado por el usuario"


def cargar_costos(precio_galon=None, rendimiento=None, otros_km=None,
                  pesos_total=None):
    """Insumos del costo monetario resueltos desde config_costos.json.

    Los argumentos opcionales (precio del galón en COP, rendimiento en km por
    galón, otros costos en COP por km y pesos del compuesto total) anulan la
    configuración y se marcan como «dado por el usuario».
    """
    with open(CONFIG_COSTOS, encoding="utf-8") as f:
        config = json.load(f)
    ins = config["insumos"]
    precio = ins["precio_galon_acpm_cop"]["valor"]
    litros = ins["litros_por_galon"]["valor"]
    rend = 100 * litros / ins["consumo_litros_por_100km"]["valor"]
    otros = ins["otros_costos_variables_cop_por_km"]["valor"]
    estados = {
        "precio del galón": ins["precio_galon_acpm_cop"]["estado"],
        "rendimiento": ins["consumo_litros_por_100km"]["estado"],
        "otros costos por km": ins["otros_costos_variables_cop_por_km"][
            "estado"]}
    pesos = dict(config["pesos_compuesto_total"]["valor"])
    estado_pesos = config["pesos_compuesto_total"]["estado"]
    if precio_galon is not None:
        precio, estados["precio del galón"] = precio_galon, USUARIO
    if rendimiento is not None:
        rend, estados["rendimiento"] = rendimiento, USUARIO
    if otros_km is not None:
        otros, estados["otros costos por km"] = otros_km, USUARIO
    if pesos_total is not None:
        pesos, estado_pesos = dict(pesos_total), USUARIO
    combustible_km = precio / rend
    return {
        "precio_galon_cop": precio, "km_por_galon": rend,
        "otros_cop_km": otros, "combustible_cop_km": combustible_km,
        "costo_variable_cop_km": combustible_km + otros,
        "estados": estados,
        "verificados": all(e == "verificada" for e in estados.values()),
        "pesos_total": pesos, "estado_pesos_total": estado_pesos}


def cargar_datos():
    """Devuelve (nodos, aristas) leídos de los JSON de construir_red.py."""
    with open(SALIDA / "nodos_red.json", encoding="utf-8") as f:
        nodos = json.load(f)
    with open(SALIDA / "aristas_red.json", encoding="utf-8") as f:
        aristas = json.load(f)
    return nodos, aristas


def maximos(aristas, campo="distancia_km", costo_km=0.0):
    """Máximo de cada criterio (el de riesgo solo sobre datos disponibles)."""
    return {
        "distancia": max(a[campo] for a in aristas),
        "peaje": max(a["peaje_cop_camion"] for a in aristas),
        "riesgo": max(a["riesgo_gizscore_prom"] for a in aristas),
        "costo_variable": max(a[campo] for a in aristas) * costo_km,
        "mortalidad": max(a["mortalidad_por_100km"] for a in aristas),
    }


def construir_grafo(pesos=None, distancia="corregida",
                    reemplazos=None, costos=None):
    """Construye el grafo no dirigido con los atributos de cada arista.

    distancia: "corregida" (base, con la regla de doble calzada) o "cruda"
    (variante de sensibilidad, con shape__length). Ambas salen del mismo
    aristas_red.json; el atributo distancia_km toma la elegida.

    reemplazos: diccionario {(u, v): km} que sustituye la distancia de
    aristas concretas (solo para análisis de sensibilidad rotulados).

    costos: resultado de cargar_costos (por defecto, config_costos.json).
    """
    if distancia not in ("corregida", "cruda"):
        raise ValueError(f"Variante de distancia desconocida: {distancia}")
    campo = ("distancia_km" if distancia == "corregida"
             else "distancia_cruda_km")
    pesos = pesos or PESOS
    nodos, aristas = cargar_datos()
    cambios = {frozenset(par): km for par, km in (reemplazos or {}).items()}
    aristas = [dict(a, **{campo: cambios.get(
        frozenset((a["origen"], a["destino"])), a[campo])})
        for a in aristas]
    costos = costos or cargar_costos()
    c_km = costos["costo_variable_cop_km"]
    tope = maximos(aristas, campo, c_km)
    w1, w2, w3 = pesos["distancia"], pesos["peaje"], pesos["riesgo"]
    suma_sin_riesgo = w1 + w2
    wt = costos["pesos_total"]
    suma_total_sin_riesgo = (wt["distancia"] + wt["peaje"]
                             + wt["costo_variable"])

    grafo = nx.Graph()
    grafo.add_nodes_from(nodos)
    for a in aristas:
        disponible = a["riesgo_puntos_criticos"] > 0
        d = a[campo] / tope["distancia"]
        p = a["peaje_cop_camion"] / tope["peaje"]
        r = a["riesgo_gizscore_prom"] / tope["riesgo"] if disponible else 0.0
        m = (a["mortalidad_por_100km"] / tope["mortalidad"]
             if a["mortalidad_disponible"] else 0.0)
        combustible = a[campo] * costos["combustible_cop_km"]
        variable = a[campo] * c_km
        c = variable / tope["costo_variable"] if tope["costo_variable"] else 0
        grafo.add_edge(
            a["origen"], a["destino"],
            distancia_km=a[campo],
            distancia_corregida_km=a["distancia_km"],
            distancia_cruda_km=a["distancia_cruda_km"],
            peaje_nombre=a["peaje_nombre"],
            peaje_cop_camion=a["peaje_cop_camion"],
            riesgo_gizscore_prom=a["riesgo_gizscore_prom"],
            riesgo_fallecidos_hist=a["riesgo_fallecidos_hist"],
            riesgo_puntos_criticos=a["riesgo_puntos_criticos"],
            riesgo_disponible=disponible,
            sectores_mortalidad=a["sectores_mortalidad"],
            mortalidad_por_100km=a["mortalidad_por_100km"],
            mortalidad_disponible=a["mortalidad_disponible"],
            distancia_fuente=a["distancia_fuente"],
            combustible_cop=combustible,
            costo_variable_cop=variable,
            costo_operativo_cop=a["peaje_cop_camion"] + variable,
            peso_multicriterio=w1 * d + w2 * p + w3 * r,
            peso_sin_riesgo=((w1 * d + w2 * p) / suma_sin_riesgo
                             if suma_sin_riesgo else 0.0),
            peso_mortalidad=w1 * d + w2 * p + w3 * m,
            peso_total=(wt["distancia"] * d + wt["peaje"] * p
                        + wt["riesgo"] * r + wt["costo_variable"] * c),
            peso_total_sin_riesgo=((wt["distancia"] * d + wt["peaje"] * p
                                    + wt["costo_variable"] * c)
                                   / suma_total_sin_riesgo),
        )
    grafo.graph["pesos"] = dict(pesos)
    grafo.graph["maximos"] = tope
    grafo.graph["costos"] = costos
    grafo.graph["pesos_total"] = dict(wt)
    grafo.graph["variante_distancia"] = distancia
    return grafo


def estadisticas(grafo):
    """Resumen verificable del grafo."""
    n, m = grafo.number_of_nodes(), grafo.number_of_edges()
    datos = [d for _, _, d in grafo.edges(data=True)]
    return {
        "nodos": n,
        "aristas": m,
        "conexo": nx.is_connected(grafo),
        "ciclos_independientes": m - n + 1,
        "aristas_con_peaje": sum(d["peaje_cop_camion"] > 0 for d in datos),
        "aristas_con_riesgo": sum(d["riesgo_disponible"] for d in datos),
        "aristas_con_mortalidad": sum(d["mortalidad_disponible"]
                                      for d in datos),
        "distancia_total_km": round(sum(d["distancia_km"] for d in datos), 2),
        "maximos": grafo.graph["maximos"],
        "pesos": grafo.graph["pesos"],
    }


def guardar_grafo(grafo, ruta=None):
    ruta = ruta or SALIDA / "grafo_carga.gpickle"
    with open(ruta, "wb") as f:
        pickle.dump(grafo, f, protocol=4)
    return ruta


def cargar_grafo(ruta=None):
    """Carga el grafo persistido; si no se puede leer, lo reconstruye.

    El pickle depende de las versiones de Python y networkx. Si falta o no
    se puede deserializar, se reconstruye desde los JSON versionados y no
    hace falta el red_vial.csv oficial.
    """
    ruta = ruta or SALIDA / "grafo_carga.gpickle"
    try:
        with open(ruta, "rb") as f:
            return pickle.load(f)
    except (OSError, pickle.UnpicklingError, AttributeError, ImportError,
            EOFError, ValueError) as error:
        print(f"Aviso: no se pudo leer {ruta.name} ({error!r}); "
              "se reconstruye desde los JSON.")
        return construir_grafo()


def main():
    grafo = construir_grafo()
    ruta = guardar_grafo(grafo)
    stats = estadisticas(grafo)
    with open(SALIDA / "estadisticas_grafo.json", "w",
              encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    for clave, valor in stats.items():
        print(f"{clave}: {valor}")
    print(f"Grafo guardado en {ruta}")


if __name__ == "__main__":
    main()
