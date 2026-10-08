"""Umbral exacto del costo variable por km entre las dos rutas de un par.

Para un par de ciudades con dos rutas simples (A: menos km y más peaje; B:
más km y menos peaje), el costo operativo de cada ruta es peaje + c * km,
con c el costo variable por km. A es más barata si

    c > (peaje_A - peaje_B) / (km_B - km_A)

y B si c es menor. La fórmula es cerrada; src/pruebas_costos.py la verifica
contra la enumeración de todos los caminos simples y contra la inversión de
la recomendación a ambos lados del umbral.
"""
import networkx as nx

from agente_rutas import umbral_costo_variable


def rutas_del_par(grafo, origen, destino, bloqueados=()):
    """Todas las rutas simples del par, con km y peaje (sin tramos
    bloqueados)."""
    vista = nx.restricted_view(grafo, [], list(bloqueados))
    rutas = []
    for camino in nx.all_simple_paths(vista, origen, destino):
        tramos = [grafo[u][v] for u, v in zip(camino, camino[1:])]
        rutas.append({"ruta": camino,
                      "km": sum(t["distancia_km"] for t in tramos),
                      "peaje_cop": sum(t["peaje_cop_camion"]
                                       for t in tramos)})
    return rutas


def umbral_exacto(grafo, origen, destino, bloqueados=()):
    """Umbral en COP/km, o None si el par no tiene dos rutas en disyuntiva."""
    return umbral_costo_variable(
        rutas_del_par(grafo, origen, destino, bloqueados))
