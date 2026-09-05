"""
Construccion del grafo G = (V, E) de la red troncal de Transmilenio.

Corte 1 - Inteligencia Artificial (SIST5036).

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

Esta version todavia NO agrega las conexiones entre troncales (eso se agrega
en el siguiente commit): solo corrige la clave del nodo y ordena
explicitamente por num_est antes de conectar consecutivos dentro de cada
id_trazado. Por lo tanto el grafo sigue fragmentado (~17 componentes, una por
id_trazado), pero ya no fusiona estaciones distintas por accidente.

--------------------------------------------------------------------------------
Peso de las aristas
--------------------------------------------------------------------------------
El peso (`weight`, en km) es una aproximacion: distancia euclidiana en grados
(lat, lon) * 111 -no es distancia Haversine real-. A la escala de Bogota
(~30 km de extremo a extremo) el error de esta aproximacion frente a Haversine
es minimo. Se documenta aqui en vez de cambiarla porque no es necesaria mayor
precision para el Corte 1.
"""

from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

ESTACIONES_CSV = DATA_DIR / "Estacion_troncalT.csv"
TRAZADOS_CSV = DATA_DIR / "Trazados_Troncales_de_TRANSMILENIO.csv"


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
    """Reproduce EXACTAMENTE la logica del notebook original (nom_est como
    clave, solo conecta consecutivos dentro de cada id_trazado). Sirve para
    documentar el "antes" y comparar contra la version corregida."""
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
    """Conecta estaciones consecutivas de cada id_trazado, ordenadas
    explicitamente por num_est (no se asume el orden de filas del CSV)."""
    n_antes = G.number_of_edges()
    for _, grupo in estaciones.groupby("id_trazado"):
        grupo = grupo.sort_values("num_est")
        filas = list(grupo.itertuples())
        for a, b in zip(filas, filas[1:]):
            d = distancia_aprox_km(a.latitud, a.longitud, b.latitud, b.longitud)
            G.add_edge(a.cod_nodo, b.cod_nodo, weight=d, tipo="intra_trazado")
    return G.number_of_edges() - n_antes


def main():
    estaciones, trazados = cargar_datos()
    print(f"Estaciones cargadas: {len(estaciones)} | id_trazado distintos: {estaciones['id_trazado'].nunique()}")

    G = nx.Graph()
    agregar_nodos(G, estaciones)
    agregar_aristas_intra_trazado(G, estaciones)

    print(f"Nodos: {G.number_of_nodes()} | Aristas: {G.number_of_edges()}")
    print(f"Componentes conexas: {nx.number_connected_components(G)} (aun fragmentado por troncal, sin conectar)")
    return G


if __name__ == "__main__":
    main()
