"""
Construcción del grafo de la red vial (dominio: transporte de carga
interurbano con riesgo de vía; red centrada en Bogotá, EXTENDIDA con un
ciclo real vía Santander para que la red deje de ser un árbol).

Fuentes oficiales (descargadas por el usuario desde datos.gov.co):
  - red_vial.csv         -> INVÍAS, Red Vial Nacional (tramos), sin geometría
  - peajes.csv           -> INVÍAS, Peajes sobre la Red Vial Nacional
  - siniestralidad.csv   -> ANSV, Sectores Críticos de Siniestralidad Vial

Metodología (sin cambios respecto a la versión anterior, ver v1):
  - Distancia: se cruza por el texto EXACTO del campo "sector" de red_vial.csv,
    NO por "codigo_tramo" solo -- un mismo codigo_tramo (numero de ruta) cubre
    varios sub-tramos distintos con sectores y longitudes distintas.
  - Peaje: se identificó a mano, para cada arista, el peaje real de INVÍAS
    que queda sobre ese sub-tramo (categoría III, camión de 2 ejes). La
    TARIFA ya no está escrita en el script: se lee de la columna
    categoria_iii de peajes.csv (descarga oficial del 6/10/2026, ver
    data/carga/VERIFICACION.md). La correspondencia entre el peaje del
    grafo y la fila del CSV es la tabla explícita PEAJES_CSV (nombre_peaje
    exacto y c_digo_peaje), verificada una por una; si el peaje no aparece
    exactamente una vez, el script falla nombrándolo. Cada uno de los 24
    peajes tiene una única caseta (una fila), por lo que no hay que elegir
    sentido. Cambio respecto de la versión anterior (tarifas a mano de la
    descarga previa): 14 tarifas quedan idénticas y 10 cambian (Arcabuco,
    Sáchica, Casablanca, Saboyá, Oiba, Los Curos, Río Bogotá, Los Patios,
    Bicentenario y El Picacho); distancias, riesgo y estructura no cambian.
    Además se amplía el límite de campo de csv por la columna multiline
    (geometría) del red_vial.csv oficial, y las rutas de entrada y salida
    pasan a data/carga y outputs.
  - Riesgo: siniestralidad.csv no trae codigo_tramo, solo el nombre del
    corredor completo; el riesgo se asigna a nivel de corredor, no de
    sub-tramo (limitación documentada).

NUEVO EN ESTA VERSIÓN -- por qué se extendió la red:

La v1 tenía 27 nodos y 26 aristas: para un grafo conexo eso es exactamente un
ÁRBOL (sin ciclos), lo cual se detectó como un problema real para el Corte 2
(BFS/DFS/UCS/voraz/A* encontrarían siempre la MISMA única ruta posible entre
cualquier origen-destino, sin nada que comparar salvo nodos expandidos).

Se hizo un barrido sistemático de los 714 segmentos de red_vial.csv (no solo
los 26 ya elegidos), limpiando nombres (paréntesis, "Cruce Ruta NN", variantes)
para detectar coincidencias de pueblos con distinta redacción, y se calculó la
estructura real de ciclos del componente conexo de Bogotá (195 nodos, 204
aristas en la red nacional completa). Resultado: dentro del alcance regional
original (Cundinamarca, Boyacá, Meta, Tolima) la red vial troncal nacional es,
en efecto, un árbol real -- no es un defecto de qué tramos se eligieron, es la
topología real de las troncales colombianas a esa escala. El ÚNICO ciclo real
que toca los nodos del proyecto cierra a través de un desvío real
(~585 km en la v1, antes de corregir las distancias; 654.25 km en la red
corregida) por Santander (Puente Nacional -> San Gil -> Bucaramanga ->
Cuestaboba -> Pamplona -> Presidente -> La Palmera -> Duitama), verificado
con los PR
(progresiva de kilómetro) de cada segmento en red_vial.csv.

Se decidió, junto con el equipo, incorporar ese ciclo real (en vez de aceptar
el árbol o inventar una conexión) para que el proyecto sea más sustancioso:
agrega 6 nodos y 7 aristas reales, todas verificables en el mismo dataset ya
usado, y por fin le da a los algoritmos de Corte 2 una decisión real de ruta
que tomar (Tunja/Duitama <-> Zipaquirá/Ubaté/Puente Nacional, por la vía corta
de siempre o por el desvío de Santander).

Nota sobre "San Gil - Bucaramanga": red_vial.csv tiene ESTE sector registrado
en dos filas con PR complementario (PR 0-881 = 82.95 km, PR 881-180 = 26.19
km), no como una duplicación de calzada (que tendría el mismo largo en ambas
filas). Se suman los dos registros. Es la única arista de esta extensión
donde se suman dos registros en vez de tomar uno solo. (Con la regla de doble
calzada de más abajo, el registro de 26.19 km se reemplaza por su tramo entre
progresivas, 12.30 km, y la arista queda en 95.25 km.)

Para las 7 aristas nuevas no se encontró, en siniestralidad.csv, ningún
corredor con nombre exactamente igual a estos sub-tramos (sí existe un
corredor "Barbosa - Bucaramanga", pero no se pudo verificar si corresponde a
la misma Barbosa ya usada en el proyecto -el nombre está duplicado en
Colombia, Barbosa-Santander y Barbosa-Antioquia- así que, siguiendo el mismo
criterio de no inventar conexiones sin verificar, se dejó sin dato de riesgo
en vez de asumirlo). Estas 7 aristas quedan con riesgo_puntos_criticos=0,
limitación documentada igual que las demás aristas sin dato de riesgo.

Regla de doble calzada digitalizada (7 de octubre de 2026): en 9 registros la
longitud registrada (shape__length, A) es cerca del doble del tramo entre
progresivas (B_tot), porque la geometría del registro contiene ambas calzadas
(A coincide con la suma de todas las partes de su geometría en los 44
registros auditados). Regla fijada de antemano: por registro, distancia =
B_tot si 1.7 <= A / B_tot <= 2.3; en cualquier otro caso, A. Los registros se
combinan como antes (mayor por sector; suma en San Gil - Bucaramanga). La
regla se verificó con una segunda medida oficial: en los 9 registros
corregidos, |B_tot - camino de la geometría| / camino es a lo sumo 0.123
(umbral 0.15). Cada arista conserva además la distancia sin corregir en
distancia_cruda_km, para el análisis de sensibilidad. Los registros fuera de
la banda con A / B_tot menor que 0.8 o mayor que 1.2 (Bogotá - Cajicá,
Chocontá - Tunja, El Espinal - Girardot y el registro del Río Ocoa) se marcan
"patrón no estándar" en outputs/auditoria_distancias.csv y conservan A. El
valor de 167.67 km de Bogotá - Villeta es un artefacto de esta doble calzada
digitalizada y queda en 81.00 km.

Regla de adopción de una distancia por progresivas (fijada de antemano y
probada en src/pruebas_progresivas.py): la diferencia de progresivas de la Red
Vial solo reemplaza al valor registrado como base si se cumplen TODAS estas
condiciones: (a) el sector y el sector anterior son del mismo corredor y
tramo; (b) las progresivas son continuas, sin hueco ni solape (a lo sumo 0.1
km), hasta el nodo; (c) cada extremo de la progresiva queda a menos de 2 km
del nodo, medido con los postes de referencia de INVÍAS (ufg7-is7r); (d) la
razón entre la longitud de la geometría del sector y su propio tramo entre
progresivas está entre 0.85 y 1.15, o en la banda de doble calzada (1.7 a
2.3) verificada; (e) la distancia por progresivas no es menor que la
geodésica entre los nodos. Cada medición queda en
outputs/evaluacion_progresivas.json.

Solo Chocontá - Tunja es candidata (el sector registra 17.69 km, PR 108.096 a
120.0; Tocancipá - Chocontá termina en el PR 59.0, ruta 55, tramo 5501) y
incumple (b), (c) y (d): hay un hueco de 49.1 km sin sector entre los PR 59.0
y 108.096, el PR 120.0 queda a unos 11 km de Tunja y la razón de su geometría
es 1.486. Su base se conserva en el valor oficial registrado, 17.69 km, y se
marca truncada; los 61.0 km (PR 120.0 menos PR 59.0) solo se usan como
sensibilidad, junto con 56.96 km (la geodésica).

Limitaciones de la fuente detectadas en la auditoría geométrica (ver
data/carga/VERIFICACION.md y outputs/auditoria_aristas.csv):
  - Las geometrías de INVÍAS de los sectores que salen de Bogotá empiezan en
    el límite urbano (entre 8 y 19 km de la coordenada DANE de Bogotá): la
    distancia por carretera excluye la entrada urbana. No se corrige: no hay
    una fuente oficial que dé el tramo urbano.
  - La geometría del sector Chocontá - Tunja cubre solo 17.69 km de la
    arista; se conserva el valor registrado y se marca truncada.

Exclusión de Mosquera (7 de octubre de 2026): la versión anterior unía Bogotá
y Mosquera con el sector "Puente Mosquera - Cruce Avenida del Ferrocarril",
que pertenece a la ruta 29 (Troncal del Eje Cafetero), a unos 160 km de
Mosquera (Cundinamarca). La Red Vial no tiene un sector oficial de reemplazo
(el sector Madrid - Bogotá, que pasa cerca de Mosquera, ya se usa en la
arista Madrid - Bogotá). Mosquera era una hoja (solo conectaba con Bogotá),
por lo que se excluyó el nodo y su arista, con el mismo criterio que la rama
Villavicencio - Barranca de Upía - Yopal. La red queda en 32 nodos, 32
aristas y un ciclo independiente.
"""
import csv
import json
import sys
from pathlib import Path

from heuristica import cargar_coordenadas, haversine_km

csv.field_size_limit(sys.maxsize)

# banda de A / B_tot que identifica la doble calzada digitalizada (fijada de
# antemano; ver largo_corregido y src/auditar_distancias.py)
REGLA_BANDA = (1.7, 2.3)

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "data" / "carga"
SALIDA = RAIZ / "outputs"

# sector truncado en la fuente -> sector anterior del mismo tramo (candidato a
# la regla de adopción por progresivas, ver docstring)
SECTORES_POR_PROGRESIVAS = {
    ("Chocontá - Tunja", "Chocontá", "Tunja"): "Tocancipá - Chocontá",
}
TOLERANCIA_PR_KM = 0.1      # hueco o solape máximo entre progresivas
TOPE_EXTREMO_KM = 2.0       # distancia máxima del poste al nodo
BANDA_UNO = (0.85, 1.15)    # razón geometría / tramo entre progresivas

# peaje del grafo -> (nombre_peaje exacto, c_digo_peaje) en peajes.csv oficial
# del 6/10/2026; cada pareja aparece exactamente una vez en el CSV
PEAJES_CSV = {
    "EL ROBLE": ("EL ROBLE", "102"),
    "ALBARRACÍN": ("ALBARRACÍN", "103"),
    "TUTA": ("TUTA", "104"),
    "ARCABUCO": ("Arcabuco", "116"),
    "SÁCHICA": ("Sáchica", "113"),
    "FUSCA": ("FUSCA", "101"),
    "CASABLANCA": ("Casablanca", "81"),
    "SABOYÁ": ("Saboyá", "82"),
    "RÍO BOGOTÁ": ("Río Bogotá", "96"),
    "LOS PATIOS": ("Los Patios", "98"),
    "NARANJAL": ("NARANJAL", "57"),
    "OCOA": ("OCOA", "119"),
    "LA LIBERTAD": ("LA LIBERTAD", "59"),
    "YUCAO": ("YUCAO", "61"),
    "SIBERIA": ("SIBERIA", "92"),
    "BICENTENARIO": ("Bicentenario", "94"),
    "HONDA": ("HONDA", "91"),
    "CHUSACÁ": ("CHUSACÁ", "54"),
    "CHINAUTA": ("CHINAUTA", "53"),
    "FLANDES": ("FLANDES", "68"),
    "GUATAQUÍ": ("GUATAQUÍ", "69"),
    "OIBA": ("Oiba", "83"),
    "LOS CUROS": ("Los Curos", "85"),
    "EL PICACHO": ("El Picacho", "127"),
}

# (sector EXACTO en red_vial.csv, nodo_origen, nodo_destino, peaje asignado
# o None); la tarifa del peaje se lee de peajes.csv (ver PEAJES_CSV)
TRAMOS = [
    ("Bogotá - Tocancipá", "Bogotá", "Tocancipá", "EL ROBLE"),
    ("Tocancipá - Chocontá", "Tocancipá", "Chocontá", None),
    ("Chocontá - Tunja", "Chocontá", "Tunja", "ALBARRACÍN"),
    ("Tunja - Duitama", "Tunja", "Duitama", "TUTA"),
    ("Barbosa - Tunja", "Barbosa", "Tunja", "ARCABUCO"),
    ("Chiquinquirá - Sáchica", "Chiquinquirá", "Sáchica", None),
    ("Sáchica - Tunja", "Sáchica", "Tunja", "SÁCHICA"),
    ("Bogotá - Cajicá", "Bogotá", "Cajicá", "FUSCA"),
    ("Cajicá - Zipaquirá", "Cajicá", "Zipaquirá", None),
    ("Zipaquirá - Ubaté", "Zipaquirá", "Ubaté", "CASABLANCA"),
    ("Ubaté - Puente Nacional", "Ubaté", "Puente Nacional", "SABOYÁ"),
    ("Madrid - Bogotá (Rio Bogotá)", "Madrid", "Bogotá", "RÍO BOGOTÁ"),
    ("Bogotá (Los Patios) - Guasca", "Bogotá", "Guasca", "LOS PATIOS"),
    ("Bogotá (El Portal) - Villavicencio",
     "Bogotá", "Villavicencio", "NARANJAL"),
    ("Ye de Granada - Paso por el Puente sobre el Río Ocoa",
     "Villavicencio", "Ye de Granada", "OCOA"),
    ("Ye de Granada - Casco Urbano Granada", "Ye de Granada", "Granada", None),
    ("Villavicencio - Paso por el Puente sobre el Río La Balsa -Puerto Lopez",
     "Villavicencio", "Puerto López", "LA LIBERTAD"),
    ("Puerto López - Puerto Gaitán", "Puerto López", "Puerto Gaitán", "YUCAO"),
    ("Villeta - Bogotá", "Bogotá", "Villeta", "SIBERIA"),
    ("Honda - Villeta", "Villeta", "Honda", "BICENTENARIO"),
    ("Mariquita - Honda (Puente Luis Ignacio Andrade)",
     "Honda", "Mariquita", "HONDA"),
    ("Fusagasugá - Silvania - Bogotá (Bosa)",
     "Bogotá", "Fusagasugá", "CHUSACÁ"),
    ("Girardot - Fusagasugá", "Fusagasugá", "Girardot", "CHINAUTA"),
    ("El Espinal - Girardot", "Girardot", "El Espinal", "FLANDES"),
    ("Girardot - Cambao", "Girardot", "Cambao", "GUATAQUÍ"),
    # --- extensión: ciclo real vía Santander (ver docstring) ---
    ("Puente Nacional - San Gil", "Puente Nacional", "San Gil", "OIBA"),
    ("San Gil - Bucaramanga", "San Gil", "Bucaramanga", "LOS CUROS"),
    ("Bucaramanga - Cuestaboba", "Bucaramanga", "Cuestaboba", None),
    ("Cuestaboba - Pamplona", "Cuestaboba", "Pamplona", "EL PICACHO"),
    ("Presidente - Pamplona", "Pamplona", "Presidente", None),
    ("La Palmera - Presidente", "Presidente", "La Palmera", None),
    ("Duitama - La Palmera", "La Palmera", "Duitama", None),
]

# tramos adicionales que se suman a su tramo principal (misma sector, dos
# sub-registros con PR complementario -- ver docstring para la verificación
# de que esto no es duplicación de calzada sino continuación real del tramo)
TRAMO_EXTRA_LONGITUD = {
    ("Ye de Granada - Paso por el Puente sobre el Río Ocoa",
     "Villavicencio", "Ye de Granada"):
    "Paso por el Puente sobre el Río Ocoa - Villavicencio",
}

# Corredor (nombre en siniestralidad.csv) -> lista de aristas (origen, destino)
CORREDOR_A_ARISTAS = {
    "Bogotá - Tunja": [("Bogotá", "Tocancipá"), ("Tocancipá", "Chocontá"),
                       ("Chocontá", "Tunja")],
    "Tunja - Duitama": [("Tunja", "Duitama")],
    "Bogotá - Villavicencio": [("Bogotá", "Villavicencio"),
                               ("Villavicencio", "Ye de Granada")],
    "Granada - Villavicencio": [("Villavicencio", "Ye de Granada"),
                                ("Ye de Granada", "Granada")],
    "Bogotá - Villeta": [("Bogotá", "Villeta")],
    "Villeta-Honda": [("Villeta", "Honda")],
    "Girardot - Bogotá": [("Bogotá", "Fusagasugá"),
                          ("Fusagasugá", "Girardot")],
}


def normaliza(txt):
    return (txt or "").strip()


def carga_csv(nombre):
    with open(DATOS / nombre, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def tarifa_peaje(peajes, nombre):
    """Tarifa de categoría III (COP) del peaje del grafo, desde peajes.csv."""
    if nombre not in PEAJES_CSV:
        raise KeyError(f"Peaje sin correspondencia en PEAJES_CSV: {nombre}")
    nombre_csv, codigo = PEAJES_CSV[nombre]
    filas = [f for f in peajes if f["nombre_peaje"] == nombre_csv
             and f["c_digo_peaje"] == codigo]
    if len(filas) != 1:
        raise ValueError(f"Peaje {nombre}: {len(filas)} filas en peajes.csv "
                         f"para ({nombre_csv}, {codigo}); se esperaba 1")
    return int(filas[0]["categoria_iii"])


def largo_corregido(row, largo_m):
    """Largo del registro (m) tras la regla de doble calzada digitalizada.

    Si 1.7 <= A / B_tot <= 2.3, con A el largo registrado y B_tot el tramo
    entre progresivas, se usa B_tot; en cualquier otro caso se conserva A.
    B_tot = |(PR_final + distancia_final / 1000)
             - (PR_inicial + distancia_inicial / 1000)| km. Requiere las
    columnas de progresivas del red_vial.csv oficial.
    """
    for columna in ("poste_de_referencia_inicial",
                    "poste_de_referencia_final"):
        if columna not in row:
            raise KeyError(f"red_vial.csv sin la columna {columna}; se "
                           "necesita la descarga oficial del 6/10/2026")
    pr_i = float(row["poste_de_referencia_inicial"] or 0)
    pr_f = float(row["poste_de_referencia_final"] or 0)
    d_i = float(row.get("distancia_inicial") or 0)
    d_f = float(row.get("distancia_final") or 0)
    b_tot_m = abs((pr_f + d_f / 1000) - (pr_i + d_i / 1000)) * 1000
    if b_tot_m and REGLA_BANDA[0] <= largo_m / b_tot_m <= REGLA_BANDA[1]:
        return b_tot_m
    return largo_m


def pr_final_km(red_vial, sector):
    """PR final del sector en km (poste + distancia/1000), ruta y tramo.

    Todos los registros del sector deben coincidir; si no, falla.
    """
    valores = {(float(r["poste_de_referencia_final"] or 0)
                + float(r.get("distancia_final") or 0) / 1000,
                r["ruta"], r["codigo_tramo"])
               for r in red_vial if normaliza(r["sector"]) == sector}
    if len(valores) != 1:
        raise ValueError(f"Sector {sector}: {len(valores)} PR finales "
                         "distintos; se esperaba 1")
    return valores.pop()


def pr_inicial_km(red_vial, sector):
    """PR inicial del sector en km (el menor de sus registros)."""
    return min(float(r["poste_de_referencia_inicial"] or 0)
               + float(r.get("distancia_inicial") or 0) / 1000
               for r in red_vial if normaliza(r["sector"]) == sector)


def cargar_postes(tramo):
    """{PR entero: [(lat, lon)]} de los postes de INVÍAS de un tramo."""
    postes = {}
    with open(DATOS / "nuevas" / "postes_referencia_ufg7-is7r.csv",
              encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if (r["codigotramo"] == tramo and r["latitud"]
                    and r["postereferencia"]):
                postes.setdefault(int(r["postereferencia"]), []).append(
                    (float(r["latitud"]), float(r["longitud"])))
    return postes


def distancia_poste_nodo(postes, pr_km, nodo):
    """Km entre el poste del PR (redondeado) y el nodo; None si no hay."""
    candidatos = postes.get(round(pr_km))
    if not candidatos:
        return None
    return min(haversine_km(lat, lon, *nodo) for lat, lon in candidatos)


def medir_progresivas(red_vial, sector, previo, origen, destino,
                      coordenadas, postes):
    """Mediciones de las condiciones (a) a (e) para un sector truncado."""
    pr, ruta, tramo = pr_final_km(red_vial, sector)
    pr_previo, ruta_previo, tramo_previo = pr_final_km(red_vial, previo)
    pr_ini = pr_inicial_km(red_vial, sector)
    largo_km = max(float(r["shape__length"]) for r in red_vial
                   if normaliza(r["sector"]) == sector) / 1000
    return {
        "sector": sector, "sector_anterior": previo,
        "ruta": ruta, "tramo": tramo,
        "ruta_anterior": ruta_previo, "tramo_anterior": tramo_previo,
        "mismo_corredor_y_tramo": (ruta, tramo) == (ruta_previo,
                                                    tramo_previo),
        "pr_final_anterior_km": pr_previo, "pr_inicial_km": pr_ini,
        "pr_final_km": pr,
        "hueco_km": round(pr_ini - pr_previo, 3),
        "extremo_origen_km": distancia_poste_nodo(
            postes, pr_previo, coordenadas[origen]),
        "extremo_destino_km": distancia_poste_nodo(
            postes, pr, coordenadas[destino]),
        "geometria_km": largo_km,
        "tramo_entre_progresivas_km": round(pr - pr_ini, 3),
        "razon_geometria": largo_km / (pr - pr_ini),
        "doble_calzada_verificada": False,
        "por_progresivas_km": round(pr - pr_previo, 3),
        "geodesica_km": haversine_km(*coordenadas[origen],
                                     *coordenadas[destino]),
    }


def evaluar_progresivas(m):
    """Aplica la regla de adopción a las mediciones `m`.

    Devuelve {"a": ..., "e": ..., "adoptar": bool}; cada condición lleva su
    valor medido y si se cumple. Un extremo sin poste no se cumple.
    """
    razon = m["razon_geometria"]
    en_banda = (BANDA_UNO[0] <= razon <= BANDA_UNO[1]
                or (REGLA_BANDA[0] <= razon <= REGLA_BANDA[1]
                    and m["doble_calzada_verificada"]))
    extremos = (m["extremo_origen_km"], m["extremo_destino_km"])
    condiciones = {
        "a": {"nombre": "mismo corredor y tramo",
              "valor": m["mismo_corredor_y_tramo"],
              "cumple": bool(m["mismo_corredor_y_tramo"])},
        "b": {"nombre": "progresivas continuas hasta el nodo",
              "valor": m["hueco_km"],
              "cumple": abs(m["hueco_km"]) <= TOLERANCIA_PR_KM},
        "c": {"nombre": "extremos a menos de 2 km del nodo",
              "valor": list(extremos),
              "cumple": all(x is not None and x < TOPE_EXTREMO_KM
                            for x in extremos)},
        "d": {"nombre": "razón geometría / tramo entre progresivas",
              "valor": razon, "cumple": bool(en_banda)},
        "e": {"nombre": "no menor que la geodésica",
              "valor": [m["por_progresivas_km"], m["geodesica_km"]],
              "cumple": m["por_progresivas_km"] >= m["geodesica_km"]},
    }
    condiciones["adoptar"] = all(c["cumple"] for k, c in condiciones.items())
    return condiciones


def distancia_por_progresivas(red_vial, sector, previo):
    """Diferencia de PR finales (km) si ambos sectores son del mismo tramo."""
    pr, ruta, tramo = pr_final_km(red_vial, sector)
    pr_previo, ruta_previo, tramo_previo = pr_final_km(red_vial, previo)
    if (ruta, tramo) != (ruta_previo, tramo_previo):
        raise ValueError(f"{sector} y {previo} no son del mismo tramo")
    return round(pr - pr_previo, 3)


def main():
    red_vial = carga_csv("red_vial.csv")
    peajes = carga_csv("peajes.csv")
    siniestros = carga_csv("siniestralidad.csv")

    # Para cada sector, se junta TODOS sus registros (puede haber varios por
    # duplicado de calzada o por sub-registro con PR complementario); se
    # decide abajo, arista por arista, si corresponde sumar o tomar el mayor.
    # largo registrado (crudo) y largo con la regla de doble calzada, ambos
    # por registro y en metros
    crudos_por_sector = {}
    corregidos_por_sector = {}
    for row in red_vial:
        sector = normaliza(row["sector"])
        try:
            largo = float(row["shape__length"])
        except (ValueError, KeyError):
            continue
        crudos_por_sector.setdefault(sector, []).append(largo)
        corregidos_por_sector.setdefault(sector, []).append(
            largo_corregido(row, largo))

    # sectores donde, tras inspección manual (ver docstring), se confirmó que
    # hay que SUMAR los registros en vez de tomar el mayor (son PR
    # complementarios de un mismo tramo largo, no duplicados de calzada)
    SECTORES_SUMA = {"San Gil - Bucaramanga"}

    def largo_sector(sector, por_sector):
        valores = por_sector.get(sector)
        if not valores:
            return None
        if sector in SECTORES_SUMA:
            return sum(valores)
        return max(valores)

    coordenadas = cargar_coordenadas()
    riesgo_por_corredor = {}
    for row in siniestros:
        corredor = normaliza(row.get("tramo", ""))
        if not corredor:
            continue
        try:
            giz = float(row.get("gizscore") or 0)
        except ValueError:
            giz = 0
        try:
            fallecidos = float(row.get("fallecidos") or 0)
        except ValueError:
            fallecidos = 0
        d = riesgo_por_corredor.setdefault(
            corredor, {"giz": [], "fallecidos": 0.0, "n": 0})
        d["giz"].append(giz)
        d["fallecidos"] += fallecidos
        d["n"] += 1

    arista_a_riesgo = {}
    for corredor, aristas_cubiertas in CORREDOR_A_ARISTAS.items():
        info = riesgo_por_corredor.get(corredor)
        if not info:
            continue
        giz_prom = sum(info["giz"]) / len(info["giz"]) if info["giz"] else 0.0
        for par in aristas_cubiertas:
            arista_a_riesgo.setdefault(par, []).append(
                (giz_prom, info["fallecidos"], info["n"]))

    nodos = set()
    aristas = []
    sin_longitud = []
    evaluaciones = {}
    for sector, origen, destino, peaje in TRAMOS:
        nodos.add(origen)
        nodos.add(destino)
        largo_m = largo_sector(sector, corregidos_por_sector)
        if largo_m is None:
            sin_longitud.append(sector)
            continue
        crudo_m = largo_sector(sector, crudos_por_sector)
        extra_sector = TRAMO_EXTRA_LONGITUD.get((sector, origen, destino))
        if extra_sector:
            largo_m += largo_sector(extra_sector, corregidos_por_sector) or 0
            crudo_m += largo_sector(extra_sector, crudos_por_sector) or 0
        dist_km = round(largo_m / 1000, 2)
        crudo_km = round(crudo_m / 1000, 2)
        registrada_km = dist_km
        fuente_distancia = "registro"
        por_pr_km = None
        previo = SECTORES_POR_PROGRESIVAS.get((sector, origen, destino))
        if previo:
            medidas = medir_progresivas(
                red_vial, sector, previo, origen, destino, coordenadas,
                cargar_postes(
                    pr_final_km(red_vial, sector)[2]))
            evaluacion = evaluar_progresivas(medidas)
            evaluaciones[sector] = {"mediciones": medidas,
                                    "reglas": evaluacion}
            por_pr_km = round(medidas["por_progresivas_km"], 2)
            fallan = [k for k in "abcde" if not evaluacion[k]["cumple"]]
            print(f"{sector}: progresivas {por_pr_km:.2f} km, geodésica "
                  f"{medidas['geodesica_km']:.2f} km, registrada "
                  f"{dist_km:.2f} km; condiciones que fallan: "
                  f"{', '.join(fallan) or 'ninguna'}")
            if evaluacion["adoptar"]:
                dist_km = por_pr_km
                fuente_distancia = "progresivas"

        if peaje:
            peaje_nombre, peaje_tarifa = peaje, tarifa_peaje(peajes, peaje)
        else:
            peaje_nombre, peaje_tarifa = None, 0

        riesgos = arista_a_riesgo.get((origen, destino), [])
        if riesgos:
            giz_prom = sum(r[0] for r in riesgos) / len(riesgos)
            fallecidos_tot = sum(r[1] for r in riesgos)
            n_puntos = sum(r[2] for r in riesgos)
        else:
            giz_prom, fallecidos_tot, n_puntos = 0.0, 0.0, 0

        aristas.append({
            "origen": origen,
            "destino": destino,
            "distancia_km": dist_km,
            "distancia_cruda_km": crudo_km,
            "distancia_registrada_km": registrada_km,
            "distancia_fuente": fuente_distancia,
            "distancia_progresivas_km": por_pr_km,
            "distancia_truncada": bool(previo and fuente_distancia
                                       == "registro"),
            "peaje_nombre": peaje_nombre,
            "peaje_cop_camion": peaje_tarifa,
            "riesgo_gizscore_prom": round(giz_prom, 3),
            "riesgo_fallecidos_hist": fallecidos_tot,
            "riesgo_puntos_criticos": n_puntos,
        })

    print(f"Nodos: {len(nodos)}")
    print(f"Aristas: {len(aristas)}")
    print("Ciclos independientes (E - V + 1, solo valido si es conexo): "
          f"{len(aristas) - len(nodos) + 1}")
    if sin_longitud:
        print("ADVERTENCIA -- sectores sin longitud encontrada:", sin_longitud)
    con_peaje = sum(1 for a in aristas if a["peaje_cop_camion"] > 0)
    con_riesgo = sum(1 for a in aristas if a["riesgo_puntos_criticos"] > 0)
    print(f"Aristas con peaje: {con_peaje}/{len(aristas)}")
    print(f"Aristas con dato de riesgo: {con_riesgo}/{len(aristas)}")
    print()
    print("Nodos:", sorted(nodos))
    print()
    for a in aristas:
        pj = (f'{a["peaje_nombre"]} ${a["peaje_cop_camion"]}'
              if a["peaje_nombre"] else "sin peaje")
        print(f'{a["origen"]:17s} -> {a["destino"]:17s} | '
              f'{a["distancia_km"]:7.2f} km | {pj:22s} | '
              f'GiZ={a["riesgo_gizscore_prom"]:5.2f} | '
              f'fallecidos={a["riesgo_fallecidos_hist"]:.0f} | '
              f'pts_criticos={a["riesgo_puntos_criticos"]}')

    # sectores críticos de mortalidad (ANSV 2022): solo sensibilidad
    import cruce_mortalidad
    import mapa_geografico
    mortalidad = cruce_mortalidad.calcular(
        aristas, mapa_geografico.cargar_trazado())
    for a, m in zip(aristas, mortalidad):
        a["sectores_mortalidad"] = m["sectores_mortalidad"]
        a["mortalidad_por_100km"] = m["mortalidad_por_100km"]
        a["mortalidad_disponible"] = m["mortalidad_disponible"]

    SALIDA.mkdir(exist_ok=True)
    with open(SALIDA / "aristas_red.json", "w", encoding="utf-8") as f:
        json.dump(aristas, f, ensure_ascii=False, indent=2)
    with open(SALIDA / "nodos_red.json", "w", encoding="utf-8") as f:
        json.dump(sorted(nodos), f, ensure_ascii=False, indent=2)
    with open(SALIDA / "evaluacion_progresivas.json", "w",
              encoding="utf-8") as f:
        json.dump(evaluaciones, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
