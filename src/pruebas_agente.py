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
el numero de transferencias de troncal, la distancia total ("distancia_total_km"),
el tiempo de viaje estimado ("tiempo_viaje_min", suma de tiempo_min de cada
arista de la ruta - ver build_graph.py), y el tiempo de calculo
("tiempo_calculo_ms") y memoria pico ("memoria_pico_kb") que reporta
AgenteRutas.calcular_ruta(). tiempo_viaje_min es cuanto dura el viaje;
tiempo_calculo_ms es cuanto tarda el algoritmo en calcular la ruta - no
confundirlos. Esto demuestra que la conexion entre troncales funciona de
extremo a extremo (no solo que nx.number_connected_components(G) reporte 1) y
deja una primera medida de rendimiento del placeholder de busqueda (Dijkstra
via networkx) para comparar en el Corte 2 contra BFS/DFS/UCS/voraz/A*.

Valores esperados (con el orden de estaciones ya corregido con la geometria
real del trazado, ver "Bitacora: orden de estaciones..." en build_graph.py):
    Portal Suba -> Portal Tunal:          40 estaciones, 2 transf., 25.77 km, ~67.8 min
    Portal Norte -> Portal Usme:          43 estaciones, 2 transf., 28.16 km, ~73.5 min
    Museo Nacional -> Portal Americas:    22 estaciones, 5 transf., 15.93 km, ~61.5 min
Si Portal Norte -> Portal Usme da 44 estaciones (en vez de 43) o 30.13 km (en
vez de 28.16 km), el grafo cargado no tiene el orden corregido de la Parte 1
(revisar que se corrio build_graph.py despues de esa correccion).
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
        "num_estaciones_esperado": 40,
    },
    {
        "descripcion": "Portal Norte (Autopista Norte) -> Portal Usme (Caracas Sur)",
        "origen": 2000,  # Portal Norte - Unicervantes
        "destino": 9000,  # Portal Usme
        "num_estaciones_esperado": 43,
    },
    {
        "descripcion": "Museo Nacional (Carrera 7) -> Portal Americas (Americas)",
        "origen": 10009,  # Museo Nacional
        "destino": 5000,  # Portal Americas
        "num_estaciones_esperado": 22,
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
        assert resultado["num_estaciones"] == caso["num_estaciones_esperado"], (
            f"num_estaciones={resultado['num_estaciones']}, se esperaba "
            f"{caso['num_estaciones_esperado']}: el grafo cargado no parece tener "
            "el orden corregido de la Parte 1 (geometria real en vez de num_est)."
        )
        resultados.append({"caso": caso["descripcion"], **resultado})
        print()

    with open(OUTPUT_DIR / "pruebas_agente.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print(f"Guardado en {OUTPUT_DIR / 'pruebas_agente.json'}")
    print("\nTodas las pruebas pasaron: las 3 rutas, imposibles antes de la correccion, se resuelven correctamente.")

    imprimir_tabla_tiempos(resultados)


def imprimir_tabla_tiempos(resultados: list) -> None:
    """Tabla resumen: ruta, estaciones, transferencias, distancia, tiempo de viaje, tiempo de calculo."""
    encabezado = (
        f"{'Ruta':<45} {'Estaciones':>10} {'Transfer.':>9} "
        f"{'Distancia':>10} {'T. viaje':>9} {'T. calculo':>11}"
    )
    print("\n" + encabezado)
    print("-" * len(encabezado))
    for r in resultados:
        ruta_txt = f"{r['origen']} -> {r['destino']}"
        print(
            f"{ruta_txt:<45} {r['num_estaciones']:>10} {r['num_transferencias']:>9} "
            f"{r['distancia_total_km']:>8.2f}km {r['tiempo_viaje_min']:>7.1f}' "
            f"{r['tiempo_calculo_ms']:>9.3f}ms"
        )


if __name__ == "__main__":
    main()
