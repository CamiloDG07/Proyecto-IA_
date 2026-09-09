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
PROCESSED_DIR = DATA_DIR / "processed"

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

# Modelo de tiempo por arista (ver "Bitacora: tiempo aproximado de viaje..." arriba).
VELOCIDAD_CRUCERO_KMH = 25.0
VELOCIDAD_CAMINATA_KMH = 4.5
TIEMPO_ESPERA_TRANSBORDO_MIN = 3.0

TIPOS_VIAJE_CONTINUO = {"intra_trazado", "continuidad_troncal", "continuidad_troncal_auto"}
TIPOS_TRANSBORDO_A_PIE = {"intercambio", "residual_geografico"}
TIPOS_CRUCE_TRONCAL = {"cruce_troncal"}

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


def calcular_tiempo_min(tipo: str, distancia_km: float) -> float:
    """Tiempo aproximado de viaje/transbordo para una arista, segun su tipo
    (ver "Bitacora: tiempo aproximado de viaje..." en el docstring del modulo)."""
    if tipo in TIPOS_VIAJE_CONTINUO:
        return (distancia_km / VELOCIDAD_CRUCERO_KMH) * 60.0
    if tipo in TIPOS_TRANSBORDO_A_PIE:
        return (distancia_km / VELOCIDAD_CAMINATA_KMH) * 60.0 + TIEMPO_ESPERA_TRANSBORDO_MIN
    if tipo in TIPOS_CRUCE_TRONCAL:
        return (distancia_km / VELOCIDAD_CRUCERO_KMH) * 60.0 + TIEMPO_ESPERA_TRANSBORDO_MIN
    raise ValueError(f"tipo de arista desconocido, no se puede clasificar para tiempo_min: {tipo!r}")


def agregar_tiempos_viaje(G: nx.Graph) -> None:
    """(6) Calcula `tiempo_min` para cada arista ya construida, segun su `tipo`."""
    for _, _, data in G.edges(data=True):
        data["tiempo_min"] = calcular_tiempo_min(data["tipo"], data["weight"])


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

    print("6) Tiempo aproximado de viaje por arista (tiempo_min, segun tipo):")
    agregar_tiempos_viaje(G)
    tiempos_por_tipo = defaultdict(list)
    for _, _, data in G.edges(data=True):
        tiempos_por_tipo[data["tipo"]].append(data["tiempo_min"])
    for tipo, tiempos in sorted(tiempos_por_tipo.items()):
        print(f"   {tipo}: {len(tiempos)} aristas, tiempo promedio {sum(tiempos) / len(tiempos):.2f} min")

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


def _orden_en_trazado(G: nx.Graph) -> dict:
    """cod_nodo -> posicion (1..n) dentro de su id_trazado, con el mismo criterio
    de orden que agregar_aristas_intra_trazado (dist_en_linea_m si esta disponible,
    num_est en los id_trazado con fallback)."""
    orden = {}
    por_trazado = defaultdict(list)
    for cod, data in G.nodes(data=True):
        por_trazado[data["id_trazado"]].append(cod)
    for _, cods in por_trazado.items():
        usa_geometria = all(G.nodes[c]["dist_en_linea_m"] is not None for c in cods)
        clave = (lambda c: G.nodes[c]["dist_en_linea_m"]) if usa_geometria else (lambda c: G.nodes[c]["num_est"])
        for i, cod in enumerate(sorted(cods, key=clave), start=1):
            orden[cod] = i
    return orden


def construir_datasets_consolidados(G: nx.Graph) -> tuple:
    """Arma los dos DataFrames del dataset consolidado (ver "Bitacora: dataset
    consolidado" en el docstring del modulo): nodos_final (153 filas, con el
    orden ya corregido de la Parte 1 explicito en `orden_en_trazado`) y
    aristas_final (158 filas, con distancia_km y tiempo_min ya calculados).
    Estos dos archivos reconstruyen el grafo completo sin volver a leer los
    GeoJSON ni recalcular nada."""
    orden = _orden_en_trazado(G)
    filas_nodos = []
    for cod, data in G.nodes(data=True):
        filas_nodos.append(
            {
                "cod_nodo": cod,
                "nom_est": data["nom_est"],
                "id_trazado": data["id_trazado"],
                "nom_tronc": data["nom_tronc"],
                "tipo_esta": data["tipo_esta"],
                "latitud": data["lat"],
                "longitud": data["lon"],
                "orden_en_trazado": orden[cod],
            }
        )
    df_nodos = pd.DataFrame(filas_nodos).sort_values(["id_trazado", "orden_en_trazado"]).reset_index(drop=True)

    filas_aristas = []
    for u, v, data in G.edges(data=True):
        filas_aristas.append(
            {
                "origen": u,
                "destino": v,
                "tipo": data["tipo"],
                "distancia_km": round(data["weight"], 5),
                "tiempo_min": round(data["tiempo_min"], 3),
            }
        )
    df_aristas = pd.DataFrame(filas_aristas)

    return df_nodos, df_aristas


def guardar_datasets_consolidados(G: nx.Graph) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df_nodos, df_aristas = construir_datasets_consolidados(G)
    df_nodos.to_csv(PROCESSED_DIR / "nodos_final.csv", index=False, encoding="utf-8-sig")
    df_aristas.to_csv(PROCESSED_DIR / "aristas_final.csv", index=False, encoding="utf-8-sig")
    print(f"  {PROCESSED_DIR / 'nodos_final.csv'} ({len(df_nodos)} filas)")
    print(f"  {PROCESSED_DIR / 'aristas_final.csv'} ({len(df_aristas)} filas)")


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

    print("\n=== Dataset consolidado (data/processed/) ===")
    guardar_datasets_consolidados(G)

    print("\n=== Estadisticas finales ===")
    print(json.dumps(stats, ensure_ascii=False, indent=2))

    return G


if __name__ == "__main__":
    main()
