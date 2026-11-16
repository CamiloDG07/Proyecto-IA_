"""Tiempo de recorrido estimado de cada tramo con la función BPR.

El proyecto no tiene tiempos ni velocidades medidos. El tiempo de un tramo
se estima con la función BPR a partir del tránsito diario del peaje de la
ANI que está sobre ese tramo:

    t = t_libre * (1 + alfa * (v / c) ** beta)
    t_libre = distancia / velocidad libre
    v = factor de hora pico * tránsito diario
    c = capacidad de la calzada (sencilla o doble)

Todos los insumos están en config_tiempo.json con su estado. La distancia y
el tránsito son datos; la velocidad libre, alfa, beta, el factor de hora
pico y las capacidades son supuestos del equipo. La doble calzada sí sale de
los datos del proyecto: la fuente de INVÍAS digitaliza las dos calzadas, de
modo que la razón entre la longitud digitalizada y la registrada queda en
la banda verificada de doble calzada.

Cruce del peaje con el tramo: nombre del peaje de la arista
(outputs/datos/aristas_red.json) igual al nombre del peaje en la ANI, ambos
en mayúsculas y sin tildes. El tránsito medido en el peaje se toma como el
del tramo completo.
"""
import json
import unicodedata

from rutas import RAIZ, SALIDA

CONFIG = RAIZ / "config_tiempo.json"


def normalizar(nombre):
    """Mayúsculas sin tildes ni espacios sobrantes."""
    texto = unicodedata.normalize("NFD", nombre.upper())
    return "".join(c for c in texto
                   if unicodedata.category(c) != "Mn").strip()


def cargar_config(ruta=CONFIG):
    """Valores de config_tiempo.json en un diccionario plano."""
    with open(ruta, encoding="utf-8") as f:
        insumos = json.load(f)["insumos"]
    return {clave: dato["valor"] for clave, dato in insumos.items()}


def es_doble_calzada(arista, config):
    """Verdadero si la razón digitalizada / registrada está en la banda."""
    minimo, maximo = config["banda_doble_calzada"]
    razon = arista["distancia_cruda_km"] / arista["distancia_registrada_km"]
    return minimo <= razon <= maximo


def capacidad(doble, config):
    if doble:
        return config["capacidad_doble_calzada_veh_h"]
    return config["capacidad_calzada_sencilla_veh_h"]


def saturacion(transito_diario, doble, config):
    """Razón volumen / capacidad en la hora pico."""
    volumen = config["factor_hora_pico"] * transito_diario
    return volumen / capacidad(doble, config)


def tiempo_libre_min(distancia_km, config):
    return 60.0 * distancia_km / config["velocidad_libre_kmh"]


def factor_bpr(razon, config):
    return 1.0 + config["bpr_alfa"] * razon ** config["bpr_beta"]


def tiempo_min(distancia_km, transito_diario, doble, config):
    """Minutos de recorrido del tramo; sin tránsito conocido, el libre."""
    libre = tiempo_libre_min(distancia_km, config)
    if transito_diario is None:
        return libre
    return libre * factor_bpr(
        saturacion(transito_diario, doble, config), config)


def tramos_con_peaje(peajes_ani, config=None):
    """Cruce de las aristas de la red con los peajes de la ANI.

    peajes_ani: diccionario {nombre normalizado: id_peaje}. Devuelve una
    lista con una entrada por arista: extremos, peaje, id en la ANI (None
    si la arista no tiene peaje o el peaje no está en la ANI) y calzada.
    """
    config = config or cargar_config()
    with open(SALIDA / "aristas_red.json", encoding="utf-8") as f:
        aristas = json.load(f)
    cruce = []
    for a in aristas:
        nombre = a["peaje_nombre"]
        id_peaje = peajes_ani.get(normalizar(nombre)) if nombre else None
        cruce.append({
            "origen": a["origen"], "destino": a["destino"],
            "peaje": nombre, "id_peaje": id_peaje,
            "doble_calzada": es_doble_calzada(a, config)})
    return cruce
