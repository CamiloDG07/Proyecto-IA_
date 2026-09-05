"""
Prototipo de agente inteligente para planificacion de rutas - Corte 1.

Modelo PEAS
-----------
Performance (medida de desempeno):
    Minimizar la distancia/costo total de recorrido entre origen y destino;
    generar unicamente rutas validas que respeten la continuidad de las
    troncales (solo se avanza por conexiones que existen en el grafo).

Environment (entorno):
    La red de Transmilenio representada como el grafo de NetworkX construido
    en build_graph.py (153 estaciones, 1 sola componente conexa tras la
    correccion del Corte 1).

Actuators (actuadores):
    - Calcular y trazar la ruta optima entre dos estaciones.
    - Recomendar las estaciones de transferencia (cambios de troncal) que
      forman parte de esa ruta.
    - Generar la visualizacion del trayecto sobre el grafo.

Sensors (sensores):
    - Lectura de las coordenadas (lat/lon) de cada estacion.
    - Lectura de id_trazado / nom_tronc / cod_nodo para validar que una
      transicion entre estaciones es una adyacencia real del grafo.
    - Parametros de entrada del usuario: estacion origen y estacion destino
      (por nombre o por cod_nodo).

Nota importante (alcance de Fase 1 vs Fase 2)
----------------------------------------------
Este prototipo usa networkx.shortest_path (Dijkstra, ya incluido en NetworkX)
como placeholder funcional para el Corte 1: el objetivo de esta fase es
demostrar que el agente PERCIBE el grafo, VALIDA una consulta origen-destino
y ACTUA calculando+mostrando una ruta, no todavia comparar algoritmos de
busqueda. En el Corte 2 este placeholder se reemplaza por las implementaciones
propias de BFS, DFS, UCS, busqueda voraz y A* (con su respectivo analisis de
admisibilidad y consistencia de la heuristica), que es donde corresponde segun
el alcance de la asignatura.
"""

import pickle
from pathlib import Path

import networkx as nx

BASE_DIR = Path(__file__).resolve().parent.parent
GRAFO_PICKLE = BASE_DIR / "outputs" / "grafo_transmilenio.gpickle"


class AgenteRutas:
    """Agente que percibe el grafo de la red y calcula rutas origen-destino."""

    def __init__(self, G: nx.Graph):
        self.G = G
        self._nombre_a_codigos = {}
        for cod, data in G.nodes(data=True):
            self._nombre_a_codigos.setdefault(data["nom_est"].strip().lower(), []).append(cod)

    @classmethod
    def desde_pickle(cls, ruta: Path = GRAFO_PICKLE) -> "AgenteRutas":
        with open(ruta, "rb") as f:
            G = pickle.load(f)
        return cls(G)

    def resolver_nodo(self, estacion) -> int:
        """Acepta cod_nodo (int) o nombre de estacion (str) y devuelve el cod_nodo."""
        if isinstance(estacion, int) or (isinstance(estacion, str) and estacion.isdigit()):
            cod = int(estacion)
            if cod not in self.G.nodes:
                raise ValueError(f"No existe ninguna estacion con cod_nodo={cod}")
            return cod

        candidatos = self._nombre_a_codigos.get(str(estacion).strip().lower())
        if not candidatos:
            raise ValueError(f"No existe ninguna estacion con nombre '{estacion}'")
        if len(candidatos) > 1:
            nombres = [(c, self.G.nodes[c]["id_trazado"]) for c in candidatos]
            raise ValueError(
                f"El nombre '{estacion}' es ambiguo, corresponde a varias estaciones "
                f"(cod_nodo, id_trazado): {nombres}. Use el cod_nodo para desambiguar."
            )
        return candidatos[0]

    def calcular_ruta(self, origen, destino) -> dict:
        """Calcula la ruta de menor costo entre origen y destino.

        origen/destino: nombre de estacion (str) o cod_nodo (int).
        Retorna un dict con la lista de estaciones, el costo total y las
        transferencias de troncal detectadas a lo largo de la ruta.
        """
        cod_origen = self.resolver_nodo(origen)
        cod_destino = self.resolver_nodo(destino)

        try:
            camino = nx.shortest_path(self.G, cod_origen, cod_destino, weight="weight")
        except nx.NetworkXNoPath:
            return {"exito": False, "mensaje": f"No existe ruta entre {origen} y {destino}."}

        costo_total = nx.shortest_path_length(self.G, cod_origen, cod_destino, weight="weight")

        estaciones = [
            {"cod_nodo": c, "nom_est": self.G.nodes[c]["nom_est"], "nom_tronc": self.G.nodes[c]["nom_tronc"]}
            for c in camino
        ]

        transferencias = []
        for anterior, actual in zip(estaciones, estaciones[1:]):
            if anterior["nom_tronc"] != actual["nom_tronc"]:
                transferencias.append(
                    {
                        "en_estacion": anterior["nom_est"],
                        "de_troncal": anterior["nom_tronc"],
                        "a_troncal": actual["nom_tronc"],
                    }
                )

        return {
            "exito": True,
            "origen": estaciones[0]["nom_est"],
            "destino": estaciones[-1]["nom_est"],
            "num_estaciones": len(estaciones),
            "num_transferencias": len(transferencias),
            "costo_total_km": round(costo_total, 3),
            "ruta": estaciones,
            "transferencias": transferencias,
        }

    def imprimir_ruta(self, origen, destino) -> dict:
        resultado = self.calcular_ruta(origen, destino)
        if not resultado["exito"]:
            print(resultado["mensaje"])
            return resultado

        print(f"Ruta: {resultado['origen']} -> {resultado['destino']}")
        print(f"  Estaciones: {resultado['num_estaciones']} | Transferencias: {resultado['num_transferencias']} "
              f"| Costo total: {resultado['costo_total_km']} km")
        for i, est in enumerate(resultado["ruta"]):
            marca = " <-- transferencia" if i > 0 and est["nom_tronc"] != resultado["ruta"][i - 1]["nom_tronc"] else ""
            print(f"  {i+1:2d}. {est['nom_est']} ({est['nom_tronc']}){marca}")
        return resultado


if __name__ == "__main__":
    agente = AgenteRutas.desde_pickle()
    agente.imprimir_ruta("Portal Suba", "Portal Tunal")
