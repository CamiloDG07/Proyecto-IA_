"""Agente de rutas para carga interurbana.

Modelo PEAS:

| Componente  | Definición                                                    |
|-------------|---------------------------------------------------------------|
| Performance | Minimizar el costo compuesto (distancia, peaje, riesgo) y     |
|             | responder en tiempo útil                                      |
| Environment | Red vial interurbana de 33 nodos y 33 aristas, estática,      |
|             | determinista, discreta, totalmente observable                 |
| Actuators   | Elegir el siguiente tramo de carretera                        |
| Sensors     | Posición actual (ciudad) y estado de los tramos disponibles   |
|             | (grafo persistido)                                            |
"""
import time
import tracemalloc

import networkx as nx

from build_graph import cargar_grafo

# criterio -> atributo de arista que se minimiza
CRITERIOS = {
    "distancia": "distancia_km",
    "peaje": "peaje_cop_camion",
    "riesgo": "riesgo_gizscore_prom",
    "compuesto": "peso_multicriterio",
    "compuesto_sin_riesgo": "peso_sin_riesgo",
}


class AgenteRutas:
    """Agente que elige la ruta de menor costo entre dos ciudades."""

    def __init__(self, grafo=None):
        self.grafo = grafo if grafo is not None else cargar_grafo()

    def calcular_ruta(self, origen, destino, criterio="compuesto",
                      tramos_bloqueados=None):
        """Ruta de menor costo según el criterio, con tiempo y memoria.

        tramos_bloqueados: pares (u, v) de tramos no disponibles.
        """
        if criterio not in CRITERIOS:
            raise ValueError(f"Criterio desconocido: {criterio}")
        for nodo in (origen, destino):
            if nodo not in self.grafo:
                raise ValueError(f"Ciudad fuera de la red: {nodo}")
        vista = nx.restricted_view(self.grafo, [], tramos_bloqueados or [])
        atributo = CRITERIOS[criterio]

        tracemalloc.start()
        inicio = time.perf_counter()
        try:
            ruta = nx.shortest_path(vista, origen, destino, weight=atributo)
        except nx.NetworkXNoPath:
            raise ValueError(f"Sin ruta de {origen} a {destino}") from None
        finally:
            tiempo = time.perf_counter() - inicio
            _, pico = tracemalloc.get_traced_memory()
            tracemalloc.stop()

        resultado = self.resumen_ruta(ruta)
        resultado.update({
            "origen": origen,
            "destino": destino,
            "criterio": criterio,
            "costo": sum(self.grafo[u][v][atributo]
                         for u, v in zip(ruta, ruta[1:])),
            "tiempo_s": tiempo,
            "memoria_pico_kb": pico / 1024,
        })
        return resultado

    def resumen_ruta(self, ruta):
        """Totales de cada criterio a lo largo de una ruta."""
        tramos = [self.grafo[u][v] for u, v in zip(ruta, ruta[1:])]
        return {
            "ruta": list(ruta),
            "saltos": len(tramos),
            "distancia_total_km": round(
                sum(t["distancia_km"] for t in tramos), 2),
            "peaje_total_cop": sum(t["peaje_cop_camion"] for t in tramos),
            "riesgo_total_gizscore": round(
                sum(t["riesgo_gizscore_prom"] for t in tramos), 3),
            "tramos_sin_dato_riesgo": sum(
                not t["riesgo_disponible"] for t in tramos),
        }


def main():
    agente = AgenteRutas()
    for criterio in CRITERIOS:
        r = agente.calcular_ruta("Duitama", "Puente Nacional", criterio)
        print(f"{criterio:21s} {r['distancia_total_km']:7.2f} km "
              f"{r['peaje_total_cop']:7d} COP  {' > '.join(r['ruta'])}")


if __name__ == "__main__":
    main()
