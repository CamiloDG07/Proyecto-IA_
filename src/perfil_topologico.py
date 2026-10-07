"""Perfil topológico de la red de 32 nodos sobre sus 496 pares de ciudades.

Para cada par cuenta los caminos simples (1 o 2 en esta red de un solo ciclo)
y lo clasifica:

  - paso obligatorio: existe un nodo intermedio (distinto de los extremos)
    presente en todos los caminos simples del par;
  - atajo: existen dos caminos simples del par sin ningún nodo intermedio en
    común (la arista directa cuenta como camino sin nodos intermedios);
  - camino único: un solo camino simple y sin nodos intermedios (dos
    ciudades unidas por una arista que no pertenece al ciclo).

Las tres clases son excluyentes (si hay dos caminos con intermedios
disjuntos, ningún nodo intermedio está en todos) y cubren los 496 pares. Un
par de paso obligatorio puede tener, además, dos caminos: entonces tiene un
tramo alternativo entre uno de sus extremos y el nodo obligatorio.

También lista los puntos de articulación (nodos cuya eliminación desconecta
la red). Escribe outputs/perfil_topologico.json y la frase que cita el
informe, outputs/texto_perfil_topologico.tex.
"""
import itertools
import json

import networkx as nx

from build_graph import SALIDA, cargar_grafo


def clasificar_par(grafo, a, b):
    """Caminos simples de a a b y clase del par."""
    caminos = list(nx.all_simple_paths(grafo, a, b))
    intermedios = [set(c[1:-1]) for c in caminos]
    obligatorios = set.intersection(*intermedios)
    atajo = any(not (x & y) for x, y in itertools.combinations(
        intermedios, 2))
    if obligatorios:
        clase = "paso_obligatorio"
    elif atajo:
        clase = "atajo"
    else:
        clase = "camino_unico"
    return {"caminos": len(caminos), "clase": clase,
            "obligatorios": sorted(obligatorios)}


def perfil(grafo):
    pares = {}
    for a, b in itertools.combinations(sorted(grafo), 2):
        pares[f"{a}|{b}"] = clasificar_par(grafo, a, b)
    por_caminos = {}
    por_clase = {}
    for p in pares.values():
        por_caminos[str(p["caminos"])] = por_caminos.get(
            str(p["caminos"]), 0) + 1
        por_clase[p["clase"]] = por_clase.get(p["clase"], 0) + 1
    obligatorio_con_dos = sum(1 for p in pares.values()
                              if p["clase"] == "paso_obligatorio"
                              and p["caminos"] == 2)
    return {
        "nodos": grafo.number_of_nodes(),
        "aristas": grafo.number_of_edges(),
        "ciclos_independientes": grafo.number_of_edges()
        - grafo.number_of_nodes() + nx.number_connected_components(grafo),
        "pares": len(pares),
        "pares_por_numero_de_caminos": por_caminos,
        "pares_por_clase": por_clase,
        "paso_obligatorio_con_dos_caminos": obligatorio_con_dos,
        "puntos_de_articulacion": sorted(nx.articulation_points(grafo)),
        "definiciones": {
            "paso_obligatorio": "algún nodo intermedio está en todos los "
                                "caminos simples del par",
            "atajo": "hay dos caminos simples sin nodos intermedios en "
                     "común",
            "camino_unico": "un solo camino simple, sin nodos intermedios"},
        "detalle": pares}


def frases(p):
    c, k = p["pares_por_numero_de_caminos"], p["pares_por_clase"]
    articulacion = p["puntos_de_articulacion"]
    lista = ", ".join(articulacion[:-1]) + " y " + articulacion[-1]
    return (
        f"Sobre los {p['pares']} pares de ciudades, {c['2']} tienen dos "
        f"caminos simples y {c['1']} tienen uno solo. Del total, "
        f"{k['paso_obligatorio']} pares tienen paso obligatorio (un nodo "
        f"intermedio presente en todos sus caminos), {k['atajo']} tienen "
        f"atajo (dos caminos sin ningún nodo intermedio en común) y "
        f"{k['camino_unico']} son de camino único, sin nodo intermedio. La "
        f"red tiene {len(articulacion)} puntos de articulación, nodos cuya "
        f"eliminación la desconecta: {lista}.\n")


def main():
    p = perfil(cargar_grafo())
    with open(SALIDA / "perfil_topologico.json", "w",
              encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=1)
    with open(SALIDA / "texto_perfil_topologico.tex", "w",
              encoding="utf-8") as f:
        f.write(frases(p))
    print(f"Perfil escrito en {SALIDA}: {p['pares_por_numero_de_caminos']} "
          f"{p['pares_por_clase']} articulación "
          f"{len(p['puntos_de_articulacion'])}")


if __name__ == "__main__":
    main()
