"""
Pruebas del prototipo del agente (Corte 1).

Corre 3 pares origen-destino que, ANTES de la correccion de conectividad
(ver src/build_graph.py), habrian sido IMPOSIBLES de resolver porque las
estaciones quedaban en componentes desconectadas del grafo original (una por
id_trazado, sin conexiones entre troncales):

  1. Portal Suba (Suba) -> Portal Tunal (Caracas Sur)
     Antes: Suba (comp. de 14 nodos) y Caracas Sur (repartida en comps. de
     3/12/2 nodos) eran componentes distintas.
  2. Portal Norte (Autopista Norte) -> Portal Usme (Caracas Sur)
     Antes: Autopista Norte (comp. de 17 nodos) y Caracas Sur eran
     componentes distintas.
  3. Museo Nacional (Carrera 7) -> Portal Americas (Americas)
     Antes: Carrera 7 era una componente de un solo nodo (aislada por
     completo) y Americas era otra componente de 17 nodos.

Para cada par se imprime y guarda: la ruta completa, el numero de estaciones,
el numero de transferencias de troncal, el costo total, y el tiempo de
calculo ("tiempo_calculo_ms") y memoria pico ("memoria_pico_kb") que reporta
AgenteRutas.calcular_ruta(). Esto demuestra que la conexion entre troncales
funciona de extremo a extremo (no solo que nx.number_connected_components(G)
reporte 1) y deja una primera medida de rendimiento del placeholder de
busqueda (Dijkstra via networkx) para comparar en el Corte 2 contra BFS/DFS/
UCS/voraz/A*.
"""

import json
from pathlib import Path

from agente import AgenteRutas

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"

CASOS_DE_PRUEBA = [
    {
        "descripcion": "Portal Suba (Suba) -> Portal Tunal (Caracas Sur)",
        "origen": 3000,  # Portal Suba
        "destino": 8000,  # Portal Tunal
    },
    {
        "descripcion": "Portal Norte (Autopista Norte) -> Portal Usme (Caracas Sur)",
        "origen": 2000,  # Portal Norte - Unicervantes
        "destino": 9000,  # Portal Usme
    },
    {
        "descripcion": "Museo Nacional (Carrera 7) -> Portal Americas (Americas)",
        "origen": 10009,  # Museo Nacional
        "destino": 5000,  # Portal Americas
    },
]


def main():
    agente = AgenteRutas.desde_pickle()
    resultados = []

    for caso in CASOS_DE_PRUEBA:
        print("=" * 70)
        print(caso["descripcion"])
        print("=" * 70)
        resultado = agente.imprimir_ruta(caso["origen"], caso["destino"])
        assert resultado["exito"], f"La ruta deberia existir tras la correccion: {caso}"
        assert resultado["num_transferencias"] >= 1, "Se esperaba al menos una transferencia de troncal"
        resultados.append({"caso": caso["descripcion"], **resultado})
        print()

    with open(OUTPUT_DIR / "pruebas_agente.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print(f"Guardado en {OUTPUT_DIR / 'pruebas_agente.json'}")
    print("\nTodas las pruebas pasaron: las 3 rutas, imposibles antes de la correccion, se resuelven correctamente.")

    imprimir_tabla_tiempos(resultados)


def imprimir_tabla_tiempos(resultados: list) -> None:
    """Tabla resumen: ruta, tiempo de calculo, num_estaciones, num_transferencias."""
    encabezado = f"{'Ruta':<45} {'Tiempo (ms)':>12} {'Estaciones':>11} {'Transferencias':>15}"
    print("\n" + encabezado)
    print("-" * len(encabezado))
    for r in resultados:
        ruta_txt = f"{r['origen']} -> {r['destino']}"
        print(
            f"{ruta_txt:<45} {r['tiempo_calculo_ms']:>12.3f} "
            f"{r['num_estaciones']:>11} {r['num_transferencias']:>15}"
        )


if __name__ == "__main__":
    main()
