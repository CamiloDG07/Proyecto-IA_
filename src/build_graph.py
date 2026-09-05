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

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

ESTACIONES_CSV = DATA_DIR / "Estacion_troncalT.csv"
TRAZADOS_CSV = DATA_DIR / "Trazados_Troncales_de_TRANSMILENIO.csv"

UMBRAL_INTERCAMBIO_KM = 0.5
UMBRAL_CRUCE_TRONCAL_KM = 3.0

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


def agregar_nodos(G: nx.Graph, estaciones: pd.DataFrame) -> None:
    for _, row in estaciones.iterrows():
        G.add_node(
            row["cod_nodo"],
            nom_est=row["nom_est"],
            id_trazado=row["id_trazado"],
            nom_tronc=row["nom_tronc"],
            tipo_esta=int(row["tipo_esta"]),
            num_est=row["num_est"],
            lat=row["latitud"],
            lon=row["longitud"],
            ub_est=row["ub_est"],
            cap_art=row["cap_art"],
        )


def agregar_aristas_intra_trazado(G: nx.Graph, estaciones: pd.DataFrame) -> int:
    """Conecta estaciones consecutivas de cada id_trazado, ordenadas explicitamente
    por num_est (no se asume el orden de filas del CSV)."""
    n_antes = G.number_of_edges()
    for _, grupo in estaciones.groupby("id_trazado"):
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
    G = nx.Graph()
    agregar_nodos(G, estaciones)

    n_intra = agregar_aristas_intra_trazado(G, estaciones)
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
