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
