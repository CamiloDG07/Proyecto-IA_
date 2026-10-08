"""Agente autónomo de rutas: el usuario da origen y destino(s).

Uso:
    python src/agente_rutas.py ORIGEN DESTINO [DESTINO ...] [--regreso]
    python src/agente_rutas.py ORIGEN DESTINO --regreso \
        --bloquear-regreso "A-B;C-D"
    python src/agente_rutas.py ORIGEN DESTINO [--criterio CRITERIO]
    python src/agente_rutas.py ORIGEN DESTINO [--precio-galon COP]
        [--rendimiento KM_POR_GALON] [--costo-otros-km COP]
        [--pesos D,P,R,C]

--criterio es opcional (distancia, peaje, riesgo, compuesto,
compuesto_sin_riesgo, costo_operativo, compuesto_total,
compuesto_total_sin_riesgo o compuesto_mortalidad). Sin la opción, el agente
decide con su regla. Con la opción, la recomendación es la ruta de menor costo
según ese criterio, la salida dice que lo eligió el usuario y las candidatas y
las advertencias se muestran igual; en un empate de costo se prefiere la de
menor compuesto sin riesgo.

Costo monetario: config_costos.json trae el precio del galón de ACPM, el
rendimiento del camión de dos ejes y otros costos por km, cada uno con su
fuente y su estado («verificada» o «supuesto del equipo»). --precio-galon,
--rendimiento, --costo-otros-km y --pesos (los cuatro pesos del compuesto
total: distancia, peaje, riesgo y costo variable, que suman 1) los anulan y se
rotulan en la salida como «dado por el usuario». Regla del criterio por
defecto: el agente recomienda por costo_operativo (peaje más costo variable)
solo si todos sus insumos tienen estado «verificada»; si alguno es «supuesto
del equipo» o lo da el usuario, el criterio por defecto sigue siendo el
compuesto sin riesgo, el costo se calcula con ese supuesto marcado y la salida
lo advierte.

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
  - Un destino con regreso: ida y vuelta. La ida es la recomendación de
    origen a destino. Sin bloqueos, el regreso es la ida invertida (los
    costos son simétricos). Con --bloquear-regreso "A-B;C-D", el regreso se
    resuelve como una segunda solicitud de origen a destino (del destino al
    origen) con esos tramos bloqueados solo en el regreso. Solo vale para un
    destino con --regreso; con varios destinos es un error.
  - Varios destinos: orden libre de las paradas, con o sin regreso,
    resuelto por el despachador (Held-Karp si k <= K_exacto, ACO si no) con
    el criterio compuesto sin riesgo.
No reimplementa búsquedas: usa el despachador, que usa busquedas.py y
heuristica.py.
"""
import csv
import sys
import textwrap

from build_graph import SALIDA, cargar_costos, cargar_grafo, construir_grafo
from agente import CRITERIOS
from despachador import Despachador, Solicitud
from heuristica import cargar_coordenadas, haversine_km

CRITERIOS_CANDIDATAS = ("distancia", "peaje", "compuesto_sin_riesgo",
                        "costo_operativo")
CRITERIOS_COMPARADOS = ("distancia", "peaje", "riesgo",
                        "compuesto_sin_riesgo", "compuesto",
                        "costo_operativo")
POR_DEFECTO = "compuesto_sin_riesgo"
CRITERIO_MONETARIO = "costo_operativo"
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
    sumas = {c: 0.0 for c in CRITERIOS}
    variable = 0.0
    con_dato = 0
    for u, v in _aristas(ruta):
        e = grafo[u][v]
        km += e["distancia_km"]
        peaje += e["peaje_cop_camion"]
        compuesto += e["peso_multicriterio"]
        variable += e["costo_variable_cop"]
        for c, atributo in CRITERIOS.items():
            sumas[c] += e[atributo]
        puntaje += (pesos["distancia"] * e["distancia_km"] / tope["distancia"]
                    + pesos["peaje"] * e["peaje_cop_camion"]
                    / tope["peaje"]) / suma
        if e["riesgo_disponible"]:
            riesgo += e["riesgo_gizscore_prom"]
            con_dato += 1
    tramos = max(len(ruta) - 1, 1)
    costos = dict(sumas, distancia=km, peaje=peaje, riesgo=riesgo,
                  compuesto_sin_riesgo=puntaje, compuesto=compuesto)
    return {"ruta": list(ruta), "saltos": len(ruta) - 1, "km": km,
            "peaje_cop": peaje, "riesgo": riesgo,
            "costo_variable_cop": variable,
            "costo_operativo_cop": peaje + variable,
            "cobertura_riesgo_pct": 100 * con_dato / tramos,
            "costos": costos}


def _avisos(grafo, ruta, auditadas):
    """Advertencias por aristas con limitación conocida."""
    avisos = []
    tramos = _aristas(ruta)
    usadas = {frozenset(t) for t in tramos}
    if ARISTA_TRUNCADA in usadas:
        e = grafo["Chocontá"]["Tunja"]
        geo = haversine_km(*COORDENADAS["Chocontá"], *COORDENADAS["Tunja"])
        if e["distancia_fuente"] == "progresivas":
            avisos.append(
                "La ruta usa Chocontá a Tunja, cuyo sector está truncado en "
                f"la fuente: su distancia ({e['distancia_km']:.2f} km frente "
                f"a {geo:.2f} km en línea recta) sale de las progresivas "
                "oficiales y no de la longitud registrada.")
        else:
            avisos.append(
                f"La ruta usa Chocontá a Tunja, sector truncado en la "
                f"fuente ({e['distancia_km']:.2f} km frente a {geo:.2f} km "
                "en línea recta): su distancia está subestimada.")
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


def umbral_costo_variable(candidatas):
    """Costo variable por km (COP/km) que invierte la recomendación.

    Con dos rutas no dominadas A (menos km, más peaje) y B (más km, menos
    peaje), costo = peaje + c * km: A es más barata si c supera
    (peaje_A - peaje_B) / (km_B - km_A) y B si c es menor. Devuelve None si
    una ruta domina a la otra o no hay exactamente dos.
    """
    if len(candidatas) != 2:
        return None
    a, b = sorted(candidatas, key=lambda c: c["km"])
    if not (a["km"] < b["km"] and a["peaje_cop"] > b["peaje_cop"]):
        return None
    return {"cop_por_km": (a["peaje_cop"] - b["peaje_cop"])
            / (b["km"] - a["km"]),
            "ruta_menos_km": a["ruta"], "ruta_menos_peaje": b["ruta"],
            "ahorro_peaje_cop": a["peaje_cop"] - b["peaje_cop"],
            "km_extra": b["km"] - a["km"]}


def _un_destino(grafo, despachador, origen, destino, pesos, auditadas,
                bloqueados=(), elegido=None, defecto=POR_DEFECTO):
    metodos, rutas = [], {}
    bloqueados = list(bloqueados)
    generadores = list(CRITERIOS_CANDIDATAS)
    if elegido and elegido not in generadores:
        generadores.append(elegido)
    for criterio in generadores:
        base = despachador.resolver(Solicitud(
            "a", origen, destino, criterio=criterio,
            restricciones={"bloqueados": bloqueados}))
        metodos.append({"criterio": criterio, "metodo": base["metodo"],
                        "motivo": base["motivo"],
                        "nodos_expandidos": base["metricas"][
                            "nodos_expandidos"]})
        rutas.setdefault(tuple(base["ruta"]), criterio)
        for arista in _aristas(base["ruta"]):
            try:
                alt = despachador.resolver(Solicitud(
                    "a", origen, destino, criterio=criterio,
                    restricciones={"bloqueados": bloqueados + [arista]}))
            except ValueError:
                continue
            rutas.setdefault(tuple(alt["ruta"]), f"alternativa de {criterio}")
    candidatas = [_evaluar(grafo, r, pesos) for r in rutas]
    descartadas = [c for c in candidatas if any(
        o is not c and o["km"] <= c["km"] and o["peaje_cop"] <= c["peaje_cop"]
        and (o["km"] < c["km"] or o["peaje_cop"] < c["peaje_cop"])
        for o in candidatas)]
    vigentes = [c for c in candidatas if c not in descartadas]
    clave = elegido or defecto
    if elegido:

        def orden(c):
            return (c["costos"][elegido], c["costos"]["compuesto_sin_riesgo"],
                    c["km"])
        mejor = min(candidatas, key=orden)
        descartadas = [c for c in descartadas if c is not mejor]
        vigentes = [mejor] + sorted(
            [c for c in vigentes if c is not mejor], key=orden)
    else:
        vigentes.sort(key=lambda c: (c["costos"][clave],
                                     c["costos"]["compuesto_sin_riesgo"]))
        mejor = vigentes[0]
    prefiere = {}
    for criterio in CRITERIOS_COMPARADOS:
        minimo = min(c["costos"][criterio] for c in candidatas)
        for c in candidatas:
            if c["costos"][criterio] <= minimo + 1e-9:
                prefiere.setdefault(tuple(c["ruta"]), []).append(criterio)
    alternativas = []
    base = mejor["costos"][clave]
    for c in vigentes[1:]:
        margen = c["costos"][clave] - base
        alternativas.append(dict(c, margen=margen, margen_pct=(
            100 * margen / base if base else None)))
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
            "umbral_costo": umbral_costo_variable(vigentes),
            "criterio_efectivo": clave,
            "metodos": metodos, "alternativas": alternativas,
            "descartadas": descartadas, "prefiere": {
                " > ".join(r): k for r, k in prefiere.items()},
            "avisos": avisos,
            "nodos_expandidos": sum(m["nodos_expandidos"] for m in metodos)}


def parsear_bloqueos(texto, grafo):
    """Lista de tramos (A, B) de un texto «A-B;C-D», validados contra la
    red."""
    if not isinstance(texto, str) or not texto.strip():
        raise ValueError("Formato de bloqueo inválido: use \"A-B;C-D\" "
                         "(ciudades separadas por guion, tramos por punto "
                         "y coma)")
    tramos = []
    for trozo in texto.split(";"):
        partes = [x.strip() for x in trozo.split("-")]
        if len(partes) != 2 or not all(partes):
            raise ValueError(f"Formato de bloqueo inválido: «{trozo}»; "
                             "use \"A-B;C-D\"")
        for ciudad in partes:
            if ciudad not in grafo:
                raise ValueError(f"Ciudad fuera de la red en el bloqueo: "
                                 f"{ciudad}")
        if not grafo.has_edge(*partes):
            raise ValueError(f"No existe el tramo {partes[0]}-{partes[1]} "
                             "en la red")
        tramos.append(tuple(partes))
    return tramos


def _ida_y_vuelta(grafo, despachador, origen, destino, pesos, auditadas,
                  bloqueos, elegido=None, defecto=POR_DEFECTO):
    """Ida recomendada y regreso: la ida invertida o, con bloqueos, la
    recomendación del destino al origen con esos tramos bloqueados."""
    ida = _un_destino(grafo, despachador, origen, destino, pesos, auditadas,
                      elegido=elegido, defecto=defecto)
    mejor = ida["recomendada"]
    regreso = {"bloqueos": bloqueos}
    if bloqueos:
        try:
            v = _un_destino(grafo, despachador, destino, origen, pesos,
                            auditadas, bloqueados=bloqueos, elegido=elegido,
                            defecto=defecto)
        except ValueError as error:
            raise ValueError(
                "Los tramos bloqueados en el regreso desconectan "
                f"{destino} de {origen}") from error
        vuelta = v["recomendada"]
        regreso.update(metodos=v["metodos"], alternativas=v["alternativas"],
                       avisos=v["avisos"],
                       nodos_expandidos=v["nodos_expandidos"])
        clave = elegido or defecto
        base = mejor["costos"][clave]
        regreso["margen_pct"] = (100 * (vuelta["costos"][clave] - base)
                                 / base if base else None)
        regreso["origen_del_regreso"] = "recalculado con los bloqueos"
    else:
        vuelta = _evaluar(grafo, mejor["ruta"][::-1], pesos)
        regreso.update(metodos=[], alternativas=[], avisos=[],
                       nodos_expandidos=0, margen_pct=0.0,
                       origen_del_regreso="ida invertida")
    ida.update({
        "tipo": "ida_y_vuelta", "ida": mejor, "vuelta": vuelta,
        "detalle_regreso": regreso,
        "total": {"km": mejor["km"] + vuelta["km"],
                  "peaje_cop": mejor["peaje_cop"] + vuelta["peaje_cop"],
                  "costo_operativo_cop": mejor["costo_operativo_cop"]
                  + vuelta["costo_operativo_cop"]},
        "nodos_expandidos": ida["nodos_expandidos"]
        + regreso["nodos_expandidos"]})
    return ida


def _varios(grafo, despachador, origen, destinos, regreso, pesos, auditadas,
            elegido=None, defecto=POR_DEFECTO):
    tipo = "d" if regreso else "e"
    salida = despachador.resolver(Solicitud(
        tipo, origen, paradas=tuple(destinos),
        criterio=elegido or defecto))
    ev = _evaluar(grafo, salida["ruta"], pesos)
    ev.update({"orden_paradas": salida["orden_paradas"],
               "metodo": salida["metodo"], "motivo": salida["motivo"],
               "metricas": salida["metricas"]})
    avisos = _avisos(grafo, salida["ruta"], auditadas)
    metodo = {"criterio": elegido or defecto, "metodo": salida["metodo"],
              "motivo": salida["motivo"],
              "nodos_expandidos": salida["metricas"]["nodos_expandidos"]}
    return {"tipo": salida["tipo"], "recomendada": ev, "umbral_costo": None,
            "criterio_efectivo": elegido or defecto, "metodos": [metodo],
            "alternativas": [], "descartadas": [], "prefiere": {},
            "avisos": avisos,
            "nodos_expandidos": salida["metricas"]["nodos_expandidos"]}


def criterio_por_defecto(grafo):
    """costo_operativo si todos sus insumos son «verificada»; si no, el
    compuesto sin riesgo."""
    if grafo.graph["costos"]["verificados"]:
        return CRITERIO_MONETARIO
    return POR_DEFECTO


def recomendar(origen, destinos, regreso=False, pesos=None, grafo=None,
               bloquear_regreso=None, criterio=None, costos=None):
    """Mejor ruta con su explicación. destinos es una lista de ciudades.

    pesos: pesos de distancia y peaje de la regla de recomendación (iguales
    por defecto); se normalizan por el máximo de cada atributo en la red.
    bloquear_regreso: texto «A-B;C-D» (o lista de tramos) bloqueados solo en
    el regreso; solo con un destino y regreso=True.
    criterio: criterio elegido por el usuario (opcional); sin él, el agente
    aplica su regla (ver criterio_por_defecto).
    costos: resultado de cargar_costos con los valores dados por el usuario;
    si se da, se reconstruye el grafo con ellos.
    """
    if criterio is not None and criterio not in CRITERIOS:
        raise ValueError(f"Criterio desconocido: {criterio}; use uno de "
                         + ", ".join(CRITERIOS))
    if grafo is None:
        grafo = (construir_grafo(costos=costos) if costos is not None
                 else cargar_grafo())
    defecto = criterio_por_defecto(grafo)
    pesos = pesos or PESOS_IGUALES
    if isinstance(destinos, str):
        destinos = [destinos]
    destinos = list(destinos)
    _validar(grafo, origen, destinos)
    bloqueos = []
    if bloquear_regreso:
        if not regreso:
            raise ValueError("El bloqueo en el regreso requiere --regreso")
        if len(destinos) != 1:
            raise ValueError("El bloqueo en el regreso solo se admite con "
                             "un destino")
        bloqueos = (parsear_bloqueos(bloquear_regreso, grafo)
                    if isinstance(bloquear_regreso, str)
                    else [tuple(x) for x in bloquear_regreso])
    despachador = Despachador(grafo, COORDENADAS)
    auditadas = _leer_auditadas()
    if len(destinos) == 1 and regreso:
        r = _ida_y_vuelta(grafo, despachador, origen, destinos[0], pesos,
                          auditadas, bloqueos, criterio, defecto)
    elif len(destinos) == 1:
        r = _un_destino(grafo, despachador, origen, destinos[0], pesos,
                        auditadas, elegido=criterio, defecto=defecto)
    else:
        r = _varios(grafo, despachador, origen, destinos, regreso, pesos,
                    auditadas, criterio, defecto)
    r.update({"criterio_usuario": criterio, "origen": origen,
              "criterio_por_defecto": defecto,
              "modelo_costos": grafo.graph["costos"],
              "criterio_efectivo": criterio or defecto,
              "destinos": destinos, "regreso": regreso,
              "pesos": dict(pesos), "alfa": despachador.alfa,
              "limitaciones": _limitaciones(
                  grafo, r["recomendada"]["ruta"], auditadas)})
    return r


def _texto_criterio(r):
    return (f"Criterio elegido por el usuario: {r['criterio_usuario']} "
            "(el agente no aplicó su regla de compuesto sin riesgo)")


def _linea_ruta(titulo, m):
    return [f"{titulo}: {' > '.join(m['ruta'])}",
            f"  Distancia: {m['km']:.2f} km   Peaje: "
            f"{m['peaje_cop']:,.0f} COP".replace(",", " "),
            f"  Costo variable: {m['costo_variable_cop']:,.0f} COP   "
            f"Costo operativo (peaje + variable): "
            f"{m['costo_operativo_cop']:,.0f} COP".replace(",", " ")]


def _lineas_modelo_costos(r):
    """Insumos del costo monetario con su estado, y su advertencia."""
    c = r["modelo_costos"]
    e = c["estados"]
    lineas = [
        "Insumos del costo monetario: "
        f"precio del galón {c['precio_galon_cop']:,.0f} COP "
        f"({e['precio del galón']}); rendimiento {c['km_por_galon']:.2f} km "
        f"por galón ({e['rendimiento']}); otros costos por km "
        f"{c['otros_cop_km']:,.0f} COP ({e['otros costos por km']}); "
        f"costo variable {c['costo_variable_cop_km']:,.1f} COP por km"
        .replace(",", " ")]
    pesos = c["pesos_total"]
    lineas.append(
        "  Pesos del compuesto total (distancia, peaje, riesgo, costo "
        f"variable): {pesos['distancia']:g}, {pesos['peaje']:g}, "
        f"{pesos['riesgo']:g}, {pesos['costo_variable']:g} "
        f"({c['estado_pesos_total']})")
    if not c["verificados"] and not r.get("criterio_usuario"):
        no = [k for k, v in e.items() if v != "verificada"]
        lineas.append(
            "  Advertencia: el criterio por defecto sigue siendo el "
            "compuesto sin riesgo porque no todos los insumos del costo "
            "operativo están verificados (" + ", ".join(no) + "); el costo "
            "se calcula con ese valor marcado.")
    return lineas


def _texto_margen(margen, criterio):
    """Margen con la unidad del criterio con que se escogió la ruta."""
    if criterio in ("peaje", "costo_operativo"):
        return f"{margen:,.0f} COP"
    if criterio == "distancia":
        return f"{margen:.2f} km"
    return f"{margen:.3f}"


def _lineas_umbral(r):
    u = r.get("umbral_costo")
    if not u:
        return []
    return [
        "Umbral del costo variable por km: la recomendación por costo "
        "operativo cambia en "
        f"{u['cop_por_km']:,.1f} COP/km (ahorro de peaje de "
        f"{u['ahorro_peaje_cop']:,.0f} COP entre {u['km_extra']:.2f} km "
        "extra). Con un costo variable mayor gana "
        f"{' > '.join(u['ruta_menos_km'])}; con uno menor gana "
        f"{' > '.join(u['ruta_menos_peaje'])}.".replace(",", " ")]


def _formatear_ida_y_vuelta(r):
    ida, vuelta = r["ida"], r["vuelta"]
    reg, total = r["detalle_regreso"], r["total"]
    lineas = [f"Origen: {r['origen']}  Destino: {r['destinos'][0]}  "
              "Regreso: sí",
              "Tipo de problema decidido: ida_y_vuelta"]
    if r.get("criterio_usuario"):
        lineas.append(_texto_criterio(r))
    lineas += _lineas_modelo_costos(r)
    lineas += _linea_ruta("Ida", ida)
    lineas.append(f"  Riesgo (suma de GiZScore con dato): {ida['riesgo']:.2f};"
                  f" dato en el {ida['cobertura_riesgo_pct']:.0f} % de los "
                  "tramos")
    lineas += _linea_ruta("Vuelta", vuelta)
    if reg["bloqueos"]:
        bloqueados = "; ".join(f"{a}-{b}" for a, b in reg["bloqueos"])
        criterio = r.get("criterio_usuario") or "compuesto sin riesgo"
        margen = ("sin porcentaje (costo base 0)"
                  if reg["margen_pct"] is None
                  else f"{reg['margen_pct']:+.1f} %")
        lineas.append(f"  Regreso recalculado con los tramos bloqueados "
                      f"solo en el regreso: {bloqueados}; costo {criterio} "
                      f"{margen} respecto de la ida invertida")
    else:
        lineas.append("  Sin bloqueos, el regreso es la ida invertida")
    lineas.append(f"Total ida y vuelta: {total['km']:.2f} km   Peaje: "
                  f"{total['peaje_cop']:,.0f} COP   Costo operativo: "
                  f"{total['costo_operativo_cop']:,.0f} COP"
                  .replace(",", " "))
    lineas.append("Método y heurística de la ida:")
    for x in r["metodos"]:
        lineas.append(f"  {x['criterio']}: {x['metodo']}; "
                      f"{x['nodos_expandidos']} nodos expandidos")
    if reg["metodos"]:
        lineas.append("Método y heurística del regreso:")
        for x in reg["metodos"]:
            lineas.append(f"  {x['criterio']}: {x['metodo']}; "
                          f"{x['nodos_expandidos']} nodos expandidos")
    lineas.append(f"  alfa de la heurística: {r['alfa']:.6f}; total de nodos "
                  f"expandidos: {r['nodos_expandidos']}")
    avisos = list(r["avisos"]) + [f"Regreso: {a}" for a in reg["avisos"]]
    if avisos:
        lineas.append("Advertencias:")
        lineas += [f"  - {a}" for a in avisos]
    return "\n".join(textwrap.fill(x, ANCHO, subsequent_indent="      ")
                     for x in lineas)


def formatear(r):
    """Texto legible de la recomendación."""
    if r["tipo"] == "ida_y_vuelta":
        return _formatear_ida_y_vuelta(r)
    m = r["recomendada"]
    pesos = r["pesos"]
    lineas = [f"Origen: {r['origen']}  Destinos: {', '.join(r['destinos'])}"
              f"  Regreso: {'sí' if r['regreso'] else 'no'}",
              f"Tipo de problema decidido: {r['tipo']}"]
    if r.get("criterio_usuario"):
        lineas.append(_texto_criterio(r))
    lineas.append(f"Ruta recomendada: {' > '.join(m['ruta'])}")
    if "orden_paradas" in m:
        lineas.append("Orden de las paradas: "
                      + " > ".join(m["orden_paradas"]))
    lineas += _lineas_modelo_costos(r)
    lineas += [
        f"  Distancia: {m['km']:.2f} km   Peaje: {m['peaje_cop']:,.0f} COP"
        .replace(",", " "),
        f"  Costo variable: {m['costo_variable_cop']:,.0f} COP   Costo "
        f"operativo (peaje + variable): {m['costo_operativo_cop']:,.0f} COP"
        .replace(",", " "),
        f"  Riesgo (suma de GiZScore con dato): {m['riesgo']:.2f}; dato en el "
        f"{m['cobertura_riesgo_pct']:.0f} % de los tramos",
        f"  Costo compuesto sin riesgo: "
        f"{m['costos']['compuesto_sin_riesgo']:.3f}",
        ("Regla: menor costo " + (
            f"{r['criterio_usuario']} (criterio del usuario)"
            if r.get("criterio_usuario") else
            "operativo = peaje + costo variable (todos los insumos están "
            "verificados)" if r["criterio_por_defecto"] == CRITERIO_MONETARIO
            else
            "compuesto sin riesgo = suma por tramo de "
            "(w_d*km/máx_km + w_p*peaje/máx_peaje)/(w_d+w_p), con "
            f"w_d = {pesos['distancia']:g} y w_p = {pesos['peaje']:g}")),
        "Método y heurística:"]
    for x in r["metodos"]:
        lineas.append(f"  {x['criterio']}: {x['metodo']}; {x['motivo']}; "
                      f"{x['nodos_expandidos']} nodos expandidos")
    lineas.append(f"  alfa de la heurística: {r['alfa']:.6f}; total de nodos "
                  f"expandidos: {r['nodos_expandidos']}")
    if r["alternativas"]:
        lineas.append("Alternativas no dominadas:")
        for a in r["alternativas"]:
            porcentaje = ("" if a["margen_pct"] is None
                          else f" ({a['margen_pct']:.1f} %)")
            lineas.append(
                f"  {' > '.join(a['ruta'])}: {a['km']:.2f} km, "
                f"{a['peaje_cop']:,.0f} COP, margen "
                f"{_texto_margen(a['margen'], r['criterio_efectivo'])}"
                f"{porcentaje} sobre la recomendada".replace(",", " "))
    if r["descartadas"]:
        lineas.append("Descartadas por dominadas en km y peaje:")
        for a in r["descartadas"]:
            lineas.append(f"  {' > '.join(a['ruta'])}: {a['km']:.2f} km, "
                          f"{a['peaje_cop']:,.0f} COP".replace(",", " "))
    lineas += _lineas_umbral(r)
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


def _opcion(resto, nombre):
    """Valor de --nombre X o --nombre=X (y lo quita de la lista), o None."""
    for i, a in enumerate(resto):
        if a == nombre:
            if i + 1 >= len(resto):
                raise ValueError(f"{nombre} requiere un valor")
            valor = resto[i + 1]
            del resto[i:i + 2]
            return valor
        if a.startswith(nombre + "="):
            del resto[i]
            return a.split("=", 1)[1]
    return None


def _numero(texto, nombre):
    try:
        valor = float(texto)
    except ValueError:
        raise ValueError(f"{nombre} requiere un número, no «{texto}»") \
            from None
    if valor < 0:
        raise ValueError(f"{nombre} no puede ser negativo")
    return valor


def _pesos_total(texto):
    try:
        w = [float(x) for x in texto.split(",")]
    except ValueError:
        raise ValueError("--pesos requiere cuatro números separados por "
                         "coma: distancia,peaje,riesgo,costo") from None
    if len(w) != 4 or min(w) < 0 or abs(sum(w) - 1) > 1e-9:
        raise ValueError("--pesos requiere cuatro números no negativos "
                         "que sumen 1: distancia,peaje,riesgo,costo")
    return dict(zip(("distancia", "peaje", "riesgo", "costo_variable"), w))


def main(argumentos):
    regreso = "--regreso" in argumentos
    resto = [a for a in argumentos if a != "--regreso"]
    try:
        bloqueo = _opcion(resto, "--bloquear-regreso")
        criterio = _opcion(resto, "--criterio")
        precio = _opcion(resto, "--precio-galon")
        rendimiento = _opcion(resto, "--rendimiento")
        otros = _opcion(resto, "--costo-otros-km")
        pesos = _opcion(resto, "--pesos")
        costos = None
        if rendimiento is not None and _numero(
                rendimiento, "--rendimiento") <= 0:
            raise ValueError("--rendimiento debe ser mayor que 0")
        if any(x is not None for x in (precio, rendimiento, otros, pesos)):
            costos = cargar_costos(
                precio_galon=(None if precio is None
                              else _numero(precio, "--precio-galon")),
                rendimiento=(None if rendimiento is None
                             else _numero(rendimiento, "--rendimiento")),
                otros_km=(None if otros is None
                          else _numero(otros, "--costo-otros-km")),
                pesos_total=None if pesos is None else _pesos_total(pesos))
        ciudades = resto
        if len(ciudades) < 2:
            print(__doc__)
            return 1
        print(formatear(recomendar(ciudades[0], ciudades[1:], regreso,
                                   bloquear_regreso=bloqueo,
                                   criterio=criterio, costos=costos)))
    except ValueError as error:
        print(f"Error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
