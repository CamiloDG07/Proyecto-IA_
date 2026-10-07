"""Agente autónomo de rutas: el usuario da origen y destino(s).

Uso:
    python src/agente_rutas.py ORIGEN DESTINO [DESTINO ...] [--regreso]

El agente decide el tipo de problema, el criterio, el algoritmo y la
heurística, y devuelve la mejor ruta con su explicación.

Regla de decisión:
  - Un destino sin regreso: origen a destino. Para cada criterio (distancia,
    peaje, compuesto sin riesgo) se calcula la ruta óptima con el despachador
    (A* con heurística admisible si el criterio la tiene; UCS en los demás) y,
    para cada ruta óptima, las rutas alternativas que quedan al bloquear una
    de sus aristas. Se evalúa cada candidata en km, peaje (COP) y riesgo; se
    descartan las dominadas en km y peaje; se recomienda la de menor costo
    compuesto sin riesgo con los pesos dados (iguales por defecto).
    Las alternativas se generan bloqueando una arista a la vez de cada ruta
    óptima: en esta red, de un solo ciclo, encuentra el otro camino; en un
    grafo con más ciclos no garantiza las k mejores rutas. Los pesos iguales
    son un supuesto de modelado (no hay datos de costo operativo por
    kilómetro para calibrarlos); la recomendación se recalcula con otros
    pesos mediante el parámetro `pesos` de recomendar.
  - Varios destinos, o un destino con regreso: orden libre de las paradas,
    resuelto por el despachador (Held-Karp si k <= K_exacto, ACO si no) con
    el criterio compuesto sin riesgo.
No reimplementa búsquedas: usa el despachador, que usa busquedas.py y
heuristica.py.
"""
import csv
import sys
import textwrap

from build_graph import SALIDA, cargar_grafo
from despachador import Despachador, Solicitud
from heuristica import cargar_coordenadas, haversine_km

CRITERIOS_CANDIDATAS = ("distancia", "peaje", "compuesto_sin_riesgo")
CRITERIOS_COMPARADOS = ("distancia", "peaje", "riesgo",
                        "compuesto_sin_riesgo", "compuesto")
PESOS_IGUALES = {"distancia": 1.0, "peaje": 1.0}
ARISTA_TRUNCADA = frozenset(("Chocontá", "Tunja"))
ANCHO = 96


def _aristas(ruta):
    return list(zip(ruta, ruta[1:]))


def _evaluar(grafo, ruta, pesos):
    """km, peaje, riesgo, cobertura y costos de una ruta (nodos)."""
    tope = grafo.graph["maximos"]
    suma = pesos["distancia"] + pesos["peaje"]
    km = peaje = riesgo = compuesto = puntaje = 0.0
    con_dato = 0
    for u, v in _aristas(ruta):
        e = grafo[u][v]
        km += e["distancia_km"]
        peaje += e["peaje_cop_camion"]
        compuesto += e["peso_multicriterio"]
        puntaje += (pesos["distancia"] * e["distancia_km"] / tope["distancia"]
                    + pesos["peaje"] * e["peaje_cop_camion"]
                    / tope["peaje"]) / suma
        if e["riesgo_disponible"]:
            riesgo += e["riesgo_gizscore_prom"]
            con_dato += 1
    tramos = max(len(ruta) - 1, 1)
    return {"ruta": list(ruta), "saltos": len(ruta) - 1, "km": km,
            "peaje_cop": peaje, "riesgo": riesgo,
            "cobertura_riesgo_pct": 100 * con_dato / tramos,
            "costos": {"distancia": km, "peaje": peaje, "riesgo": riesgo,
                       "compuesto_sin_riesgo": puntaje,
                       "compuesto": compuesto}}


def _avisos(grafo, ruta, auditadas):
    """Advertencias por aristas con limitación conocida."""
    avisos = []
    tramos = _aristas(ruta)
    usadas = {frozenset(t) for t in tramos}
    if ARISTA_TRUNCADA in usadas:
        e = grafo["Chocontá"]["Tunja"]
        geo = haversine_km(*COORDENADAS["Chocontá"], *COORDENADAS["Tunja"])
        avisos.append(
            f"La ruta usa Chocontá a Tunja, sector truncado en la fuente "
            f"({e['distancia_km']:.2f} km frente a {geo:.2f} km en línea "
            "recta): su distancia está subestimada.")
    marcadas = sorted(" - ".join(sorted(par)) for par in usadas
                      if par in auditadas and par != ARISTA_TRUNCADA)
    if marcadas:
        avisos.append("Aristas marcadas por la auditoría geométrica: "
                      + "; ".join(marcadas) + ".")
    sin_dato = sum(1 for u, v in tramos
                   if not grafo[u][v]["riesgo_disponible"])
    if sin_dato:
        avisos.append(f"{sin_dato} de {len(tramos)} tramos no tienen dato de "
                      "riesgo y valen 0 en los criterios que lo incluyen.")
    return avisos


def _limitaciones(grafo, ruta, auditadas):
    """Conteos de las limitaciones de la ruta (los mismos de _avisos)."""
    tramos = _aristas(ruta)
    usadas = {frozenset(t) for t in tramos}
    return {"truncada": ARISTA_TRUNCADA in usadas,
            "marcadas": len([p for p in usadas
                             if p in auditadas and p != ARISTA_TRUNCADA]),
            "sin_dato": sum(1 for u, v in tramos
                            if not grafo[u][v]["riesgo_disponible"]),
            "tramos": len(tramos)}


def _leer_auditadas():
    with open(SALIDA / "auditoria_aristas.csv", encoding="utf-8") as f:
        return {frozenset((r["origen"], r["destino"]))
                for r in csv.DictReader(f) if r["anomalia"]}


COORDENADAS = cargar_coordenadas()


def _validar(grafo, origen, destinos):
    if not destinos:
        raise ValueError("Se requiere al menos un destino")
    for ciudad in (origen, *destinos):
        if ciudad not in grafo:
            raise ValueError(f"Ciudad fuera de la red: {ciudad}")
    todas = [origen, *destinos]
    if len(set(todas)) != len(todas):
        raise ValueError("El origen y los destinos deben ser ciudades "
                         "distintas")


def _un_destino(grafo, despachador, origen, destino, pesos, auditadas):
    metodos, rutas = [], {}
    for criterio in CRITERIOS_CANDIDATAS:
        base = despachador.resolver(Solicitud("a", origen, destino,
                                              criterio=criterio))
        metodos.append({"criterio": criterio, "metodo": base["metodo"],
                        "motivo": base["motivo"],
                        "nodos_expandidos": base["metricas"][
                            "nodos_expandidos"]})
        rutas.setdefault(tuple(base["ruta"]), criterio)
        for arista in _aristas(base["ruta"]):
            try:
                alt = despachador.resolver(Solicitud(
                    "a", origen, destino, criterio=criterio,
                    restricciones={"bloqueados": [arista]}))
            except ValueError:
                continue
            rutas.setdefault(tuple(alt["ruta"]), f"alternativa de {criterio}")
    candidatas = [_evaluar(grafo, r, pesos) for r in rutas]
    descartadas = [c for c in candidatas if any(
        o is not c and o["km"] <= c["km"] and o["peaje_cop"] <= c["peaje_cop"]
        and (o["km"] < c["km"] or o["peaje_cop"] < c["peaje_cop"])
        for o in candidatas)]
    vigentes = [c for c in candidatas if c not in descartadas]
    vigentes.sort(key=lambda c: c["costos"]["compuesto_sin_riesgo"])
    mejor = vigentes[0]
    prefiere = {}
    for criterio in CRITERIOS_COMPARADOS:
        minimo = min(c["costos"][criterio] for c in candidatas)
        for c in candidatas:
            if c["costos"][criterio] <= minimo + 1e-9:
                prefiere.setdefault(tuple(c["ruta"]), []).append(criterio)
    alternativas = []
    for c in vigentes[1:]:
        margen = (c["costos"]["compuesto_sin_riesgo"]
                  - mejor["costos"]["compuesto_sin_riesgo"])
        alternativas.append(dict(c, margen=margen, margen_pct=100 * margen
                                 / mejor["costos"]["compuesto_sin_riesgo"]))
    avisos = _avisos(grafo, mejor["ruta"], auditadas)
    for c in alternativas:
        otros = [k for k in prefiere.get(tuple(c["ruta"]), [])
                 if k in ("riesgo", "compuesto")
                 and k not in prefiere.get(tuple(mejor["ruta"]), [])]
        if otros:
            avisos.append(
                ("El criterio " if len(otros) == 1 else "Los criterios ")
                + " y ".join(otros)
                + (" prefiere" if len(otros) == 1 else " prefieren")
                + " otra ruta: "
                f"{' > '.join(c['ruta'])}. El riesgo solo tiene dato en el "
                f"{mejor['cobertura_riesgo_pct']:.0f} % de los tramos de la "
                f"ruta recomendada y en el {c['cobertura_riesgo_pct']:.0f} % "
                "de los de la otra; el resto vale 0, por lo que esa "
                "preferencia puede deberse a falta de datos.")
    return {"tipo": "origen_destino", "recomendada": mejor,
            "metodos": metodos, "alternativas": alternativas,
            "descartadas": descartadas, "prefiere": {
                " > ".join(r): k for r, k in prefiere.items()},
            "avisos": avisos,
            "nodos_expandidos": sum(m["nodos_expandidos"] for m in metodos)}


def _varios(grafo, despachador, origen, destinos, regreso, pesos, auditadas):
    tipo = "d" if regreso else "e"
    salida = despachador.resolver(Solicitud(
        tipo, origen, paradas=tuple(destinos),
        criterio="compuesto_sin_riesgo"))
    ev = _evaluar(grafo, salida["ruta"], pesos)
    ev.update({"orden_paradas": salida["orden_paradas"],
               "metodo": salida["metodo"], "motivo": salida["motivo"],
               "metricas": salida["metricas"]})
    avisos = _avisos(grafo, salida["ruta"], auditadas)
    return {"tipo": salida["tipo"], "recomendada": ev, "metodos": [{
        "criterio": "compuesto_sin_riesgo", "metodo": salida["metodo"],
        "motivo": salida["motivo"],
        "nodos_expandidos": salida["metricas"]["nodos_expandidos"]}],
        "alternativas": [], "descartadas": [], "prefiere": {},
        "avisos": avisos,
        "nodos_expandidos": salida["metricas"]["nodos_expandidos"]}


def recomendar(origen, destinos, regreso=False, pesos=None, grafo=None):
    """Mejor ruta con su explicación. destinos es una lista de ciudades.

    pesos: pesos de distancia y peaje de la regla de recomendación (iguales
    por defecto); se normalizan por el máximo de cada atributo en la red.
    """
    grafo = grafo if grafo is not None else cargar_grafo()
    pesos = pesos or PESOS_IGUALES
    if isinstance(destinos, str):
        destinos = [destinos]
    destinos = list(destinos)
    _validar(grafo, origen, destinos)
    despachador = Despachador(grafo, COORDENADAS)
    auditadas = _leer_auditadas()
    if len(destinos) == 1 and not regreso:
        r = _un_destino(grafo, despachador, origen, destinos[0], pesos,
                        auditadas)
    else:
        r = _varios(grafo, despachador, origen, destinos, regreso, pesos,
                    auditadas)
    r.update({"origen": origen, "destinos": destinos, "regreso": regreso,
              "pesos": dict(pesos), "alfa": despachador.alfa,
              "limitaciones": _limitaciones(
                  grafo, r["recomendada"]["ruta"], auditadas)})
    return r


def formatear(r):
    """Texto legible de la recomendación."""
    m = r["recomendada"]
    pesos = r["pesos"]
    lineas = [f"Origen: {r['origen']}  Destinos: {', '.join(r['destinos'])}"
              f"  Regreso: {'sí' if r['regreso'] else 'no'}",
              f"Tipo de problema decidido: {r['tipo']}",
              f"Ruta recomendada: {' > '.join(m['ruta'])}"]
    if "orden_paradas" in m:
        lineas.append("Orden de las paradas: "
                      + " > ".join(m["orden_paradas"]))
    lineas += [
        f"  Distancia: {m['km']:.2f} km   Peaje: {m['peaje_cop']:,.0f} COP"
        .replace(",", " "),
        f"  Riesgo (suma de GiZScore con dato): {m['riesgo']:.2f}; dato en el "
        f"{m['cobertura_riesgo_pct']:.0f} % de los tramos",
        f"  Costo compuesto sin riesgo: "
        f"{m['costos']['compuesto_sin_riesgo']:.3f}",
        "Regla: menor costo compuesto sin riesgo = suma por tramo de "
        f"(w_d*km/máx_km + w_p*peaje/máx_peaje)/(w_d+w_p), con "
        f"w_d = {pesos['distancia']:g} y w_p = {pesos['peaje']:g}",
        "Método y heurística:"]
    for x in r["metodos"]:
        lineas.append(f"  {x['criterio']}: {x['metodo']}; {x['motivo']}; "
                      f"{x['nodos_expandidos']} nodos expandidos")
    lineas.append(f"  alfa de la heurística: {r['alfa']:.6f}; total de nodos "
                  f"expandidos: {r['nodos_expandidos']}")
    if r["alternativas"]:
        lineas.append("Alternativas no dominadas:")
        for a in r["alternativas"]:
            lineas.append(
                f"  {' > '.join(a['ruta'])}: {a['km']:.2f} km, "
                f"{a['peaje_cop']:,.0f} COP, margen {a['margen']:.3f} "
                f"({a['margen_pct']:.1f} %) sobre la recomendada"
                .replace(",", " "))
    if r["descartadas"]:
        lineas.append("Descartadas por dominadas en km y peaje:")
        for a in r["descartadas"]:
            lineas.append(f"  {' > '.join(a['ruta'])}: {a['km']:.2f} km, "
                          f"{a['peaje_cop']:,.0f} COP".replace(",", " "))
    if r["prefiere"]:
        lineas.append("Criterio que prefiere cada candidata:")
        for ruta, criterios in r["prefiere"].items():
            lineas.append(f"  {', '.join(criterios)}: {ruta}")
    if r["avisos"]:
        lineas.append("Advertencias:")
        lineas += [f"  - {a}" for a in r["avisos"]]
    return "\n".join(
        textwrap.fill(x, ANCHO, subsequent_indent="      ")
        for x in lineas)


def main(argumentos):
    regreso = "--regreso" in argumentos
    ciudades = [a for a in argumentos if a != "--regreso"]
    if len(ciudades) < 2:
        print(__doc__)
        return 1
    try:
        print(formatear(recomendar(ciudades[0], ciudades[1:], regreso)))
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
