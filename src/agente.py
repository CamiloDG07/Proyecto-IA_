import pickle
import time
import tracemalloc
from pathlib import Path

import networkx as nx

BASE_DIR = Path(__file__).resolve().parent.parent
GRAFO_PICKLE = BASE_DIR / "outputs" / "grafo_transmilenio.gpickle"

# BETA (Corte 1): numero de "ruta facil" asociado a cada troncal, para poder
# mostrar en las pruebas del agente que ruta debe tomar el usuario en cada
# tramo del camino calculado -- no son los codigos reales de servicio de
# TransMilenio (eso, con datos GTFS reales, queda documentado como trabajo
# futuro); es una simplificacion didactica para esta entrega.
RUTA_FACIL_POR_TRONCAL = {
    "Americas": 5,
    "Autopista Norte": 8,
    "Avenida Ciudad de Cali": 9,
    "Calle 26": 26,
    "Calle 80": 80,
    "Caracas": 1,
    "Caracas Sur": 2,
    "Carrera 10": 10,
    "Carrera 7": 7,
    "Eje Ambiental": 11,
    "NQS Central": 3,
    "NQS Sur": 4,
    "Suba": 6,
}


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
        """Calcula la ruta de menor costo (distancia, `weight`) entre origen y
        destino.

        origen/destino: nombre de estacion (str) o cod_nodo (int).
        Retorna un dict con la lista de estaciones, la distancia total
        ("distancia_total_km"), el tiempo de viaje estimado sumando
        `tiempo_min` a lo largo de la ruta ("tiempo_viaje_min" -distinto de
        cuanto tarda el algoritmo en calcularla-), las transferencias de
        troncal detectadas, y el tiempo de calculo ("tiempo_calculo_ms") y
        memoria pico usada por el calculo ("memoria_pico_kb", medida con
        tracemalloc, modulo estandar de Python). Estas dos ultimas metricas se
        miden solo alrededor del calculo de la ruta (Dijkstra vía
        nx.shortest_path), no de la carga del grafo ni de la resolucion de
        nombres a cod_nodo.
        """
        cod_origen = self.resolver_nodo(origen)
        cod_destino = self.resolver_nodo(destino)

        tracemalloc.start()
        t_inicio = time.perf_counter()
        try:
            camino = nx.shortest_path(self.G, cod_origen, cod_destino, weight="weight")
        except nx.NetworkXNoPath:
            t_fin = time.perf_counter()
            _, pico_bytes = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            return {
                "exito": False,
                "mensaje": f"No existe ruta entre {origen} y {destino}.",
                "tiempo_calculo_ms": (t_fin - t_inicio) * 1000,
                "memoria_pico_kb": pico_bytes / 1024,
            }
        t_fin = time.perf_counter()
        _, pico_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        tiempo_calculo_ms = (t_fin - t_inicio) * 1000
        memoria_pico_kb = pico_bytes / 1024

        # Distancia total = suma de pesos a lo largo del camino ya encontrado, en
        # vez de una segunda llamada a nx.shortest_path_length (que repetiria todo
        # el calculo de Dijkstra y falsearia el tiempo medido arriba). tiempo_viaje
        # se suma de la misma forma sobre tiempo_min (ver build_graph.py).
        aristas_ruta = list(zip(camino, camino[1:]))
        distancia_total = sum(self.G[u][v]["weight"] for u, v in aristas_ruta)
        tiempo_viaje_min = sum(self.G[u][v]["tiempo_min"] for u, v in aristas_ruta)

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

        rutas_tomadas = self._agrupar_en_rutas_faciles(estaciones)

        return {
            "exito": True,
            "origen": estaciones[0]["nom_est"],
            "destino": estaciones[-1]["nom_est"],
            "num_estaciones": len(estaciones),
            "num_transferencias": len(transferencias),
            "distancia_total_km": round(distancia_total, 3),
            "tiempo_viaje_min": round(tiempo_viaje_min, 2),
            "tiempo_calculo_ms": tiempo_calculo_ms,
            "memoria_pico_kb": memoria_pico_kb,
            "ruta": estaciones,
            "transferencias": transferencias,
            "rutas_tomadas": rutas_tomadas,
        }

    @staticmethod
    def _agrupar_en_rutas_faciles(estaciones: list) -> list:
        """BETA: colapsa la secuencia estacion-a-estacion en tramos por troncal,
        cada uno con el numero de "ruta facil" (RUTA_FACIL_POR_TRONCAL) que el
        usuario tomaria en ese tramo. P.ej. en vez de listar las 40 estaciones
        una por una, devuelve algo como "Ruta 8 (Autopista Norte): Portal Norte
        -> San Martin", "Ruta 1 (Caracas): San Martin -> Tercer Milenio", etc.
        """
        tramos = []
        actual = {
            "ruta_facil": RUTA_FACIL_POR_TRONCAL.get(estaciones[0]["nom_tronc"]),
            "troncal": estaciones[0]["nom_tronc"],
            "desde": estaciones[0]["nom_est"],
            "hasta": estaciones[0]["nom_est"],
        }
        for est in estaciones[1:]:
            if est["nom_tronc"] == actual["troncal"]:
                actual["hasta"] = est["nom_est"]
            else:
                tramos.append(actual)
                actual = {
                    "ruta_facil": RUTA_FACIL_POR_TRONCAL.get(est["nom_tronc"]),
                    "troncal": est["nom_tronc"],
                    "desde": est["nom_est"],
                    "hasta": est["nom_est"],
                }
        tramos.append(actual)
        return tramos

    def imprimir_ruta(self, origen, destino) -> dict:
        resultado = self.calcular_ruta(origen, destino)
        if not resultado["exito"]:
            print(resultado["mensaje"])
            return resultado

        print(f"Ruta: {resultado['origen']} -> {resultado['destino']}")
        print(f"  Estaciones: {resultado['num_estaciones']} | Transferencias: {resultado['num_transferencias']} "
              f"| Distancia: {resultado['distancia_total_km']} km "
              f"| Tiempo de viaje: {resultado['tiempo_viaje_min']:.1f} min "
              f"| Tiempo de calculo: {resultado['tiempo_calculo_ms']:.3f} ms "
              f"| Memoria pico: {resultado['memoria_pico_kb']:.2f} KB")
        for i, est in enumerate(resultado["ruta"]):
            marca = " <-- transferencia" if i > 0 and est["nom_tronc"] != resultado["ruta"][i - 1]["nom_tronc"] else ""
            print(f"  {i+1:2d}. {est['nom_est']} ({est['nom_tronc']}){marca}")

        print("  Rutas tomadas (beta, numero simplificado por troncal):")
        for tramo in resultado["rutas_tomadas"]:
            if tramo["desde"] == tramo["hasta"]:
                print(f"    Ruta {tramo['ruta_facil']} ({tramo['troncal']}): solo transbordo en {tramo['desde']}")
            else:
                print(f"    Ruta {tramo['ruta_facil']} ({tramo['troncal']}): {tramo['desde']} -> {tramo['hasta']}")
        return resultado


if __name__ == "__main__":
    agente = AgenteRutas.desde_pickle()
    agente.imprimir_ruta("Portal Suba", "Portal Tunal")
