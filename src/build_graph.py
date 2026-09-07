"""
Construccion del grafo G = (V, E) de la red troncal de Transmilenio.

Corte 1 - Inteligencia Artificial (SIST5036).

V = estaciones troncales (clave: cod_nodo, identificador unico real del dataset).
E = conexiones entre estaciones: tramos consecutivos dentro de un mismo trazado,
    mas las conexiones de transferencia entre troncales distintas descritas abajo.

--------------------------------------------------------------------------------
Bug corregido respecto al notebook original (diagrama_de_red_a_traves_del_dataset):
--------------------------------------------------------------------------------
El notebook original usaba `nom_est` (el nombre) como clave de G.add_node(). El
dataset tiene un nombre duplicado ("Temporal AV. Jimenez - Inter Electricas",
cod_nodo 9110 en TZ001 y cod_nodo 14003 en TZ015, dos estaciones fisicas
distintas a ~150m una de otra). Como NetworkX indexa nodos por clave, ese
duplicado fusionaba las dos estaciones en un solo nodo y el segundo
G.add_node() sobreescribia los atributos del primero. Ademas, cualquier otra
coincidencia accidental de nombre entre trazados distintos fusionaba
componentes sin que nadie lo pidiera (esto es justamente lo que ocurria entre
TZ001 y TZ015). Aqui se usa `cod_nodo` (unico, verificado sobre las 153 filas)
como clave del grafo; `nom_est` queda solo como atributo.

--------------------------------------------------------------------------------
Problema de fondo corregido: fragmentacion en componentes por id_trazado
--------------------------------------------------------------------------------
El notebook original solo conectaba estaciones consecutivas DENTRO de cada
id_trazado (17 valores distintos con estaciones), sin ordenar explicitamente
por num_est (funcionaba por coincidir con el orden de filas del CSV, pero eso
es fragil). El resultado es un grafo con ~16 componentes desconectadas: nunca
se modelan las transferencias reales ENTRE troncales.

Aqui se agregan tres capas de conexion, en este orden:

  (a) Estaciones de intercambio (tipo_esta == 3): se conectan pares de estas
      estaciones que pertenecen a id_trazado distintos y estan a <= 500 m
      (formula aproximada, ver mas abajo). Con ese umbral aparecen exactamente
      los 3 pares reales de intercambio del dataset (147-405 m) y ningun falso
      positivo (el siguiente par mas cercano esta a mas de 1.3 km):
        Ricaurte-NQS (TZ008) <-> Ricaurte-CL13 (TZ009)
        Temporal AV. Jimenez (TZ001) <-> Temporal AV. Jimenez (TZ015)
        Las Aguas (TZ015) <-> Universidades-CityU (TZ016)

  (b) Cruces de troncal via el dataset de Trazados: cuando dos id_trazado
      (con estaciones) comparten el mismo ori_traz o fin_traz -normalizando
      mayusculas/tildes/espacios, porque el dataset trae inconsistencias como
      "Limite del Distrito" vs "Limite Del Distrito"- se busca el par de
      estaciones mas cercano entre esos dos id_trazado (proximidad geografica,
      no por num_est: se verifico que num_est NO refleja el orden geografico
      dentro de un trazado, asi que no se puede asumir que el primer/ultimo
      valor de num_est sea el extremo real). Se conecta ese par si la distancia
      es <= 3 km. Ese limite excluye un unico falso positivo real del dataset:
      "Limite del Distrito" aparece como texto compartido entre Calle 80 y NQS
      Sur pero corresponde a dos limites administrativos distintos y sin
      relacion geografica (~8.3 km de separacion) -es una coincidencia de
      texto, no un cruce fisico-, y se descarta explicitamente.

  (c) Auto-reparacion de fragmentacion interna de una misma troncal fisica:
      una troncal (nom_tronc) puede estar repartida en varios id_trazado (p.
      ej. "Caracas Sur" = TZ012 + TZ013 + TZ014). Si tras (a) y (b) dos
      fragmentos de la MISMA troncal siguen en componentes distintas, se
      conectan por el par de estaciones mas cercano entre esas componentes
      (sin tope de distancia: son, por definicion, la misma via fisica).

  (d) Casos residuales sin metadato de cruce explicito: Carrera 10 y Carrera 7
      quedan aisladas del resto de la red tras (a)-(c) porque su cruce real
      con el resto de la malla (en el centro de Bogota) no queda registrado
      como coincidencia de texto en ori_traz/fin_traz. Hay evidencia de
      proximidad geografica real y documentada:
        San Victorino (10006, Carrera 10) <-> Temporal AV. Jimenez (14003,
          Eje Ambiental): ~291 m
        Las Nieves (10007, Carrera 10) <-> Calle 19 (9111, Caracas): ~346 m
      Se agregan explicitamente estas dos conexiones.

Con (a)-(d) el grafo completo (153 estaciones) queda en una sola componente
conexa - ver outputs/despues_de_corregir.json para la verificacion.

--------------------------------------------------------------------------------
Bitacora: orden de estaciones dentro de cada trazado (corregido num_est -> geometria)
--------------------------------------------------------------------------------
Hallazgo: ordenar las estaciones de un id_trazado por `num_est` (como se hacia hasta
ahora para las aristas intra_trazado) asume que num_est refleja la posicion real de
la estacion a lo largo de la via. Eso es falso en varios trazados: el dataset de
estaciones no garantiza que num_est sea correlativo con la geografia (numeros de
codigo asignados por fases de construccion, no por orden fisico). Esto producia
aristas "intra_trazado" con saltos absurdos, verificados con los pesos reales del
grafo (ANTES, ordenando por num_est):

    TZ002 (Autopista Norte): Heroes - Colmena Seguros -> Terminal      11.33 km
    TZ010 (NQS Sur):         SENA -> Bosa                               7.83 km
    TZ010 (NQS Sur):         Bosa -> Comuneros                          9.07 km
    TZ018 (Carrera 10):      San Diego -> San Bernardo                  2.70 km

(el promedio real de arista dentro de esos trazados es ~1-2 km; en los 4 casos una
estacion tipo portal/terminal - Terminal, Bosa, San Bernardo - recibio el num_est
mas alto de su trazado como si fuera la ultima parada, cuando geograficamente esta
en otro punto de la linea).

Correccion: en vez de num_est, se usa la geometria real de cada trazado
(`data/Trazado_troncal.geojson`, MultiLineString/LineString por id_trazado) para
proyectar cada estacion sobre la linea (`LineString.project`) y ordenar por esa
posicion real a lo largo de la via. Los trazados con geometria partida en varios
segmentos (MultiLineString) se intenta unificar con `shapely.ops.linemerge`; como
en este dataset ningun segmento comparte coordenadas de extremo exactas, linemerge
nunca logra fusionarlos, asi que se encadenan manualmente por el extremo mas
cercano (permitiendo invertir el sentido de cada segmento) y se registra el hueco
maximo introducido. Si ese hueco supera UMBRAL_HUECO_ENCADENADO_KM (500 m), se
descarta la geometria para ese trazado y se deja el orden por num_est como
fallback explicito (ver `calcular_orden_geometrico`): esto ocurre en TZ009
(Americas) y TZ016 (Calle 26), cuya geometria tiene ramificaciones reales (no son
una sola linea continua) y el encadenado introduce huecos de 2.4 km y 1.3 km
respectivamente -peor que el problema que se intenta resolver-, asi que ahi se deja
el orden original.

DESPUES de la correccion, las 4 aristas de la tabla bajan a un rango normal
(Terminal -> Calle 187: 0.62 km; Bosa -> Portal Sur: 1.32 km, SENA -> Santa Isabel:
1.01 km; San Diego -> Las Nieves: 0.62 km). El grafo sigue en 153 nodos y 1 sola
componente conexa (esta correccion solo reordena, no agrega ni quita estaciones ni
cambia las conexiones entre troncales). TZ009 y TZ016 conservan, sin cambios, la
arista mas larga que ya tenian con num_est (Zona Industrial -> De La Sabana 2.49 km
y Centro Memoria -> Universidades-CityU 2.02 km): es una limitacion conocida y
documentada del dataset, no algo que esta correccion pueda resolver sin inventar
geometria que el dataset no tiene.

--------------------------------------------------------------------------------
Peso de las aristas
--------------------------------------------------------------------------------
El peso (`weight`, en km) es una aproximacion: distancia euclidiana en grados
(lat, lon) * 111 -no es distancia Haversine real-. A la escala de Bogota
(~30 km de extremo a extremo) el error de esta aproximacion frente a Haversine
es de un pequeno porcentaje, y no afecto ningun umbral usado en este script
(se verifico explicitamente contra Haversine real). Se documenta aqui en vez
de cambiarla porque no es necesaria mayor precision para el Corte 1; se podria
reemplazar por Haversine en una fase posterior si se requiere.
"""

import itertools
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point, shape
from shapely.ops import linemerge

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

ESTACIONES_CSV = DATA_DIR / "Estacion_troncalT.csv"
TRAZADOS_CSV = DATA_DIR / "Trazados_Troncales_de_TRANSMILENIO.csv"
# Geometria real de cada trazado (para ordenar estaciones a lo largo de la via,
# ver "Bitacora: orden de estaciones..." en el docstring del modulo). Ya estaba
# en el repo como Trazado_troncal.geojson; hay una copia identica bajo el nombre
# Trazados_Troncales_de_TRANSMILENIO.geojson (mismo contenido, byte a byte) que
# no se usa aqui para no duplicar el dato.
GEOJSON_TRAZADOS = DATA_DIR / "Trazado_troncal.geojson"

UMBRAL_INTERCAMBIO_KM = 0.5
UMBRAL_CRUCE_TRONCAL_KM = 3.0
UMBRAL_HUECO_ENCADENADO_KM = 0.5

# Conexiones residuales (c): no derivables de ori_traz/fin_traz, ver docstring.
CONEXIONES_RESIDUALES = [
    (10006, 14003, "San Victorino <-> Temporal AV. Jimenez (Carrera 10 <-> Eje Ambiental)"),
    (10007, 9111, "Las Nieves <-> Calle 19 (Carrera 10 <-> Caracas)"),
]


def normalizar(texto: str) -> str:
    """minusculas, sin tildes, sin espacios repetidos - para comparar nombres de punto."""
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", texto)


def distancia_aprox_km(lat1, lon1, lat2, lon2) -> float:
    """Aproximacion euclidiana en grados * 111 (ver docstring del modulo)."""
    return float(np.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) * 111.0)


def cargar_datos():
    estaciones = pd.read_csv(ESTACIONES_CSV, encoding="utf-8-sig")
    trazados = pd.read_csv(TRAZADOS_CSV, encoding="utf-8-sig")
    idt_to_tronc = dict(zip(trazados["id_trazado"], trazados["nom_tronc"]))
    estaciones["nom_tronc"] = estaciones["id_trazado"].map(idt_to_tronc)
    return estaciones, trazados


def cargar_geometrias_trazados() -> dict:
    """id_trazado -> geometria shapely (LineString o MultiLineString), desde el geojson."""
    with open(GEOJSON_TRAZADOS, encoding="utf-8") as f:
        geojson = json.load(f)
    return {feat["properties"]["id_trazado"]: shape(feat["geometry"]) for feat in geojson["features"]}


def _encadenar_partes_multilinestring(partes) -> tuple:
    """Une las partes de un MultiLineString en una sola secuencia de coordenadas,
    encadenando siempre la parte cuyo extremo (inicio o fin, permitiendo invertirla)
    quede mas cerca del extremo actual de la cadena. Retorna (coords, hueco_max_km):
    hueco_max_km es la mayor distancia que hubo que "saltar" para pegar dos partes
    que no compartian coordenada exacta (normal en datos SIG reales: ver docstring
    del modulo)."""
    restantes = [list(p.coords) for p in partes]
    cadena = restantes.pop(0)
    hueco_max_km = 0.0
    while restantes:
        inicio, fin = cadena[0], cadena[-1]
        mejor = None  # (hueco_km, indice, extremo_cadena, invertir_parte)
        for i, parte in enumerate(restantes):
            p_inicio, p_fin = parte[0], parte[-1]
            candidatos = [
                (distancia_aprox_km(fin[1], fin[0], p_inicio[1], p_inicio[0]), i, "fin", False),
                (distancia_aprox_km(fin[1], fin[0], p_fin[1], p_fin[0]), i, "fin", True),
                (distancia_aprox_km(inicio[1], inicio[0], p_inicio[1], p_inicio[0]), i, "inicio", True),
                (distancia_aprox_km(inicio[1], inicio[0], p_fin[1], p_fin[0]), i, "inicio", False),
            ]
            for c in candidatos:
                if mejor is None or c[0] < mejor[0]:
                    mejor = c
        hueco_km, idx, extremo, invertir = mejor
        parte = restantes.pop(idx)
        if invertir:
            parte = list(reversed(parte))
        cadena = cadena + parte if extremo == "fin" else parte + cadena
        hueco_max_km = max(hueco_max_km, hueco_km)
    return cadena, hueco_max_km


def calcular_orden_geometrico(estaciones: pd.DataFrame) -> dict:
    """Para cada id_trazado con estaciones, intenta construir una linea unica a
    partir de su geometria real y decide si usarla ("geometria_real") o hacer
    fallback a num_est ("num_est_fallback") cuando el trazado esta partido en
    geometria con huecos grandes al encadenar (ver docstring del modulo).
    Retorna id_trazado -> {"metodo", "linea" (si aplica), "hueco_max_km"}.
    """
    geometrias = cargar_geometrias_trazados()
    info = {}
    for idt in estaciones["id_trazado"].unique():
        geom = geometrias.get(idt)
        if geom is None:
            info[idt] = {"metodo": "num_est_fallback", "motivo": "sin geometria en el dataset de trazados"}
            continue

        if geom.geom_type == "MultiLineString":
            # linemerge fusiona partes que comparten coordenada de extremo exacta;
            # en este dataset ninguna lo hace (ver docstring), pero se intenta primero
            # por si la geometria cambiara en una actualizacion del dataset oficial.
            fusionada = linemerge(geom)
            if fusionada.geom_type == "LineString":
                coords = [(x, y) for x, y, *_ in fusionada.coords]
                info[idt] = {"metodo": "geometria_real", "linea": LineString(coords), "hueco_max_km": 0.0}
                continue
            coords, hueco_max_km = _encadenar_partes_multilinestring(list(geom.geoms))
        else:
            coords = list(geom.coords)
            hueco_max_km = 0.0

        coords = [(x, y) for x, y, *_ in coords]
        if hueco_max_km <= UMBRAL_HUECO_ENCADENADO_KM:
            info[idt] = {"metodo": "geometria_real", "linea": LineString(coords), "hueco_max_km": hueco_max_km}
        else:
            info[idt] = {
                "metodo": "num_est_fallback",
                "hueco_max_km": hueco_max_km,
                "motivo": (
                    f"hueco de {hueco_max_km * 1000:.0f} m al encadenar las partes de la "
                    f"geometria (> {UMBRAL_HUECO_ENCADENADO_KM * 1000:.0f} m): probable "
                    "ramificacion real del trazado, no una sola linea continua"
                ),
            }

    print("  orden de estaciones por trazado (geometria real vs num_est fallback):")
    for idt, datos in sorted(info.items()):
        if datos["metodo"] == "geometria_real":
            print(f"    {idt}: geometria_real (hueco max al encadenar: {datos['hueco_max_km'] * 1000:.0f} m)")
        else:
            print(f"    {idt}: num_est_fallback ({datos['motivo']})")
    return info


def construir_grafo_original_con_bug(estaciones: pd.DataFrame) -> nx.Graph:
    """Reproduce EXACTAMENTE la logica del notebook original (nom_est como clave,
    solo conecta consecutivos dentro de cada id_trazado, sin ordenar por num_est).
    Sirve unicamente para documentar el "antes" (ver generar_reporte_antes_despues)."""
    G = nx.Graph()
    for _, row in estaciones.iterrows():
        G.add_node(
            row["nom_est"],
            pos=(row["longitud"], row["latitud"]),
            codigo=row["num_est"],
            trazado=row["id_trazado"],
            capacidad=row["cap_art"],
        )
    for _, grupo in estaciones.groupby("id_trazado"):
        nombres = grupo["nom_est"].tolist()
        for i in range(len(nombres) - 1):
            s1, s2 = nombres[i], nombres[i + 1]
            lat1, lon1 = estaciones.loc[estaciones["nom_est"] == s1, ["latitud", "longitud"]].values[0]
            lat2, lon2 = estaciones.loc[estaciones["nom_est"] == s2, ["latitud", "longitud"]].values[0]
            dist_km = distancia_aprox_km(lat1, lon1, lat2, lon2)
            G.add_edge(s1, s2, weight=dist_km, distancia=dist_km)
    return G


def agregar_nodos(G: nx.Graph, estaciones: pd.DataFrame, orden_geometrico: dict = None) -> None:
    orden_geometrico = orden_geometrico or {}
    for _, row in estaciones.iterrows():
        datos_orden = orden_geometrico.get(row["id_trazado"])
        dist_en_linea_m = None
        if datos_orden and datos_orden["metodo"] == "geometria_real":
            punto = Point(row["longitud"], row["latitud"])
            dist_en_linea_m = datos_orden["linea"].project(punto) * 111000.0
        G.add_node(
            row["cod_nodo"],
            nom_est=row["nom_est"],
            id_trazado=row["id_trazado"],
            nom_tronc=row["nom_tronc"],
            tipo_esta=int(row["tipo_esta"]),
            num_est=row["num_est"],
            dist_en_linea_m=dist_en_linea_m,
            lat=row["latitud"],
            lon=row["longitud"],
            ub_est=row["ub_est"],
            cap_art=row["cap_art"],
        )


def agregar_aristas_intra_trazado(G: nx.Graph, estaciones: pd.DataFrame, orden_geometrico: dict) -> int:
    """Conecta estaciones consecutivas de cada id_trazado. El orden ya no es
    num_est (ver docstring del modulo: no refleja la posicion geografica real);
    es la proyeccion de cada estacion sobre la geometria real del trazado
    (`dist_en_linea_m`, calculada en agregar_nodos), salvo en los id_trazado
    marcados como "num_est_fallback" en `orden_geometrico`, donde se conserva
    num_est por no haber una linea unica confiable."""
    n_antes = G.number_of_edges()
    for idt, grupo in estaciones.groupby("id_trazado"):
        metodo = orden_geometrico.get(idt, {}).get("metodo", "num_est_fallback")
        if metodo == "geometria_real":
            clave_orden = [G.nodes[cod]["dist_en_linea_m"] for cod in grupo["cod_nodo"]]
            grupo = grupo.assign(_orden=clave_orden).sort_values("_orden")
        else:
            grupo = grupo.sort_values("num_est")
        filas = list(grupo.itertuples())
        for a, b in zip(filas, filas[1:]):
            d = distancia_aprox_km(a.latitud, a.longitud, b.latitud, b.longitud)
            G.add_edge(a.cod_nodo, b.cod_nodo, weight=d, tipo="intra_trazado")
    return G.number_of_edges() - n_antes


def agregar_aristas_intercambio(G: nx.Graph, estaciones: pd.DataFrame) -> int:
    """(a) Estaciones tipo_esta==3 de id_trazado distintos y cercanas (<=500 m)."""
    n_antes = G.number_of_edges()
    intercambio = estaciones[estaciones["tipo_esta"] == 3]
    for a, b in itertools.combinations(intercambio.itertuples(), 2):
        if a.id_trazado == b.id_trazado:
            continue
        d = distancia_aprox_km(a.latitud, a.longitud, b.latitud, b.longitud)
        if d <= UMBRAL_INTERCAMBIO_KM:
            G.add_edge(a.cod_nodo, b.cod_nodo, weight=d, tipo="intercambio")
    return G.number_of_edges() - n_antes


def _puntos_compartidos(estaciones: pd.DataFrame, trazados: pd.DataFrame):
    """id_trazado (con estaciones) agrupados por punto normalizado (ori_traz/fin_traz)."""
    idt_con_datos = set(estaciones["id_trazado"].unique())
    puntos = defaultdict(set)
    for row in trazados.itertuples():
        if row.id_trazado not in idt_con_datos:
            continue
        for valor in (row.ori_traz, row.fin_traz):
            puntos[normalizar(valor)].add(row.id_trazado)
    return puntos


def agregar_aristas_cruce_troncal(G: nx.Graph, estaciones: pd.DataFrame, trazados: pd.DataFrame) -> list:
    """(b) Para cada punto compartido por >=2 id_trazado, conecta el par de
    estaciones geograficamente mas cercano entre ambos, si esta a <= 3 km."""
    n_antes = G.number_of_edges()
    id_stations = {idt: grupo for idt, grupo in estaciones.groupby("id_trazado")}
    puntos = _puntos_compartidos(estaciones, trazados)

    pares_evaluados = set()
    for _, idts in puntos.items():
        idts = sorted(idts)
        for i1, i2 in itertools.combinations(idts, 2):
            pares_evaluados.add((i1, i2))

    descartados = []
    for i1, i2 in sorted(pares_evaluados):
        s1s, s2s = id_stations[i1], id_stations[i2]
        mejor = None
        for a in s1s.itertuples():
            for b in s2s.itertuples():
                d = distancia_aprox_km(a.latitud, a.longitud, b.latitud, b.longitud)
                if mejor is None or d < mejor[0]:
                    mejor = (d, a.cod_nodo, b.cod_nodo, a.nom_est, b.nom_est)
        if mejor is None:
            continue
        d, cod_a, cod_b, nom_a, nom_b = mejor
        if d <= UMBRAL_CRUCE_TRONCAL_KM:
            tipo = "cruce_troncal" if G.nodes[cod_a]["nom_tronc"] != G.nodes[cod_b]["nom_tronc"] else "continuidad_troncal"
            G.add_edge(cod_a, cod_b, weight=d, tipo=tipo)
        else:
            descartados.append(
                {"id_trazado_1": i1, "id_trazado_2": i2, "distancia_km": round(d, 2), "estacion_1": nom_a, "estacion_2": nom_b}
            )
    print(f"  aristas de cruce agregadas: {G.number_of_edges() - n_antes}")
    if descartados:
        print(f"  descartados por superar {UMBRAL_CRUCE_TRONCAL_KM} km (probable coincidencia de texto, no cruce real):")
        for x in descartados:
            print(f"    {x['id_trazado_1']} <-> {x['id_trazado_2']}: {x['distancia_km']} km ({x['estacion_1']} <-> {x['estacion_2']})")
    return descartados


def reparar_fragmentacion_interna(G: nx.Graph, max_iter: int = 20) -> int:
    """(c) Si una misma troncal (nom_tronc) quedo repartida en componentes
    distintas tras (a) y (b), conecta el par de estaciones mas cercano entre
    esas componentes. Itera hasta que ninguna troncal este partida."""
    conexiones_agregadas = 0
    for _ in range(max_iter):
        componentes = list(nx.connected_components(G))
        if len(componentes) <= 1:
            break
        tronc_a_componentes = defaultdict(list)
        for idx, comp in enumerate(componentes):
            for tronc in {G.nodes[n]["nom_tronc"] for n in comp}:
                tronc_a_componentes[tronc].append(idx)

        troncal_partida = next((t for t, idxs in tronc_a_componentes.items() if len(idxs) > 1), None)
        if troncal_partida is None:
            break

        i, j = tronc_a_componentes[troncal_partida][:2]
        comp_i, comp_j = componentes[i], componentes[j]
        mejor = None
        for a in comp_i:
            for b in comp_j:
                d = distancia_aprox_km(G.nodes[a]["lat"], G.nodes[a]["lon"], G.nodes[b]["lat"], G.nodes[b]["lon"])
                if mejor is None or d < mejor[0]:
                    mejor = (d, a, b)
        d, a, b = mejor
        G.add_edge(a, b, weight=d, tipo="continuidad_troncal_auto")
        print(f"  reparacion interna ({troncal_partida}): {G.nodes[a]['nom_est']} <-> {G.nodes[b]['nom_est']} ({round(d*1000,1)} m)")
        conexiones_agregadas += 1
    return conexiones_agregadas


def agregar_conexiones_residuales(G: nx.Graph, estaciones: pd.DataFrame) -> int:
    """(d) Conexiones geograficas documentadas sin metadato de cruce explicito."""
    agregadas = 0
    for cod_a, cod_b, descripcion in CONEXIONES_RESIDUALES:
        fila_a = estaciones.loc[estaciones["cod_nodo"] == cod_a].iloc[0]
        fila_b = estaciones.loc[estaciones["cod_nodo"] == cod_b].iloc[0]
        d = distancia_aprox_km(fila_a.latitud, fila_a.longitud, fila_b.latitud, fila_b.longitud)
        G.add_edge(cod_a, cod_b, weight=d, tipo="residual_geografico", descripcion=descripcion)
        print(f"  conexion residual: {descripcion} ({round(d*1000,1)} m)")
        agregadas += 1
    return agregadas


def construir_grafo_corregido(estaciones: pd.DataFrame, trazados: pd.DataFrame) -> nx.Graph:
    print("0) Orden de estaciones dentro de cada trazado (geometria real vs num_est):")
    orden_geometrico = calcular_orden_geometrico(estaciones)

    G = nx.Graph()
    agregar_nodos(G, estaciones, orden_geometrico)

    n_intra = agregar_aristas_intra_trazado(G, estaciones, orden_geometrico)
    print(f"1) Aristas intra-trazado: {n_intra} | componentes: {nx.number_connected_components(G)}")

    n_intercambio = agregar_aristas_intercambio(G, estaciones)
    print(f"2) Aristas de intercambio (tipo_esta==3): {n_intercambio} | componentes: {nx.number_connected_components(G)}")

    print("3) Cruces de troncal (ori_traz/fin_traz compartido):")
    agregar_aristas_cruce_troncal(G, estaciones, trazados)
    print(f"   componentes: {nx.number_connected_components(G)}")

    print("4) Reparacion de fragmentacion interna de troncales:")
    reparar_fragmentacion_interna(G)
    print(f"   componentes: {nx.number_connected_components(G)}")

    print("5) Conexiones residuales (Carrera 10 / Carrera 7):")
    agregar_conexiones_residuales(G, estaciones)
    print(f"   componentes: {nx.number_connected_components(G)}")

    return G


def resumen_componentes(G: nx.Graph) -> dict:
    componentes = list(nx.connected_components(G))
    resumen = []
    for comp in sorted(componentes, key=len, reverse=True):
        troncales = sorted({G.nodes[n].get("nom_tronc") or G.nodes[n].get("trazado") for n in comp})
        resumen.append({"tamano": len(comp), "troncales_o_trazados": troncales})
    return {
        "num_nodos": G.number_of_nodes(),
        "num_aristas": G.number_of_edges(),
        "num_componentes_conexas": len(componentes),
        "componentes": resumen,
    }


def generar_reporte_antes_despues(estaciones: pd.DataFrame, trazados: pd.DataFrame, G_corregido: nx.Graph) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("\n=== Grafo ANTES de la correccion (logica original del notebook) ===")
    G_antes = construir_grafo_original_con_bug(estaciones)
    resumen_antes = resumen_componentes(G_antes)
    resumen_antes["nota"] = (
        "Construido con la logica original (nom_est como clave de nodo, aristas solo "
        "dentro de cada id_trazado). El numero de nodos es menor que el numero de filas "
        "del dataset porque el nombre duplicado 'Temporal AV. Jimenez - Inter Electricas' "
        "fusiona dos estaciones fisicas distintas (TZ001 y TZ015) en un solo nodo."
    )
    print(json.dumps({k: v for k, v in resumen_antes.items() if k != "componentes"}, ensure_ascii=False, indent=2))
    with open(OUTPUT_DIR / "antes_de_corregir.json", "w", encoding="utf-8") as f:
        json.dump(resumen_antes, f, ensure_ascii=False, indent=2)

    print("\n=== Grafo DESPUES de la correccion ===")
    resumen_despues = resumen_componentes(G_corregido)
    print(json.dumps({k: v for k, v in resumen_despues.items() if k != "componentes"}, ensure_ascii=False, indent=2))
    with open(OUTPUT_DIR / "despues_de_corregir.json", "w", encoding="utf-8") as f:
        json.dump(resumen_despues, f, ensure_ascii=False, indent=2)


def generar_estadisticas(G: nx.Graph, trazados: pd.DataFrame) -> dict:
    grados = dict(G.degree())
    tipo_esta_labels = {1: "Portal", 2: "Intermedia", 3: "Intercambio", 4: "Sencilla"}
    conteo_tipo = defaultdict(int)
    for n in G.nodes:
        conteo_tipo[tipo_esta_labels.get(G.nodes[n]["tipo_esta"], "Desconocido")] += 1

    stats = {
        "num_nodos": G.number_of_nodes(),
        "num_aristas": G.number_of_edges(),
        "num_componentes_conexas": nx.number_connected_components(G),
        "num_troncales_fisicas": int(trazados["nom_tronc"].nunique()),
        "num_trazados": int(trazados["id_trazado"].nunique()),
        "troncales_fisicas": sorted(trazados["nom_tronc"].unique().tolist()),
        "estaciones_por_tipo": dict(conteo_tipo),
        "grado_promedio": round(sum(grados.values()) / len(grados), 3),
        "grado_maximo": max(grados.values()),
        "estacion_grado_maximo": G.nodes[max(grados, key=grados.get)]["nom_est"],
        "densidad": round(nx.density(G), 5),
    }
    with open(OUTPUT_DIR / "estadisticas_grafo.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    return stats


def exportar_grafo(G: nx.Graph) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    G_export = G.copy()
    for _, data in G_export.nodes(data=True):
        data.pop("ub_est", None)  # texto con posibles caracteres no soportados en graphml
        # GraphML no admite None como valor de atributo (lo tiene dist_en_linea_m
        # en los id_trazado con fallback a num_est, ver docstring del modulo);
        # se usa NaN, que sigue siendo un float valido para GraphML.
        if data.get("dist_en_linea_m") is None:
            data["dist_en_linea_m"] = float("nan")
    nx.write_graphml(G_export, OUTPUT_DIR / "grafo_transmilenio.graphml")

    import pickle

    with open(OUTPUT_DIR / "grafo_transmilenio.gpickle", "wb") as f:
        pickle.dump(G, f)


def main():
    estaciones, trazados = cargar_datos()
    print(f"Estaciones cargadas: {len(estaciones)} | id_trazado distintos con estaciones: {estaciones['id_trazado'].nunique()}")

    print("\n=== Construyendo grafo corregido ===")
    G = construir_grafo_corregido(estaciones, trazados)

    print(f"\nVerificacion final -> nx.number_connected_components(G) = {nx.number_connected_components(G)}")
    assert nx.number_connected_components(G) == 1, "El grafo deberia quedar en 1 sola componente conexa"

    generar_reporte_antes_despues(estaciones, trazados, G)
    stats = generar_estadisticas(G, trazados)
    exportar_grafo(G)

    print("\n=== Estadisticas finales ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))

    return G


if __name__ == "__main__":
    main()
