"""Pruebas de la regla de adopción de distancias por progresivas.

La regla (construir_red.evaluar_progresivas) adopta la diferencia de
progresivas como base solo si se cumplen las cinco condiciones. Se prueba
con un caso sintético que las cumple, con un caso que falla cada condición
por separado y con el caso real de Chocontá a Tunja.
"""
import json
import sys
from pathlib import Path

from construir_red import SALIDA, evaluar_progresivas

fallas = []


def ok(condicion, mensaje):
    print(("  ok: " if condicion else "  FALLA: ") + mensaje)
    if not condicion:
        fallas.append(mensaje)


SINTETICO = {
    "mismo_corredor_y_tramo": True,
    "hueco_km": 0.0,
    "extremo_origen_km": 0.4,
    "extremo_destino_km": 1.2,
    "razon_geometria": 1.02,
    "doble_calzada_verificada": False,
    "por_progresivas_km": 30.0,
    "geodesica_km": 28.0,
}


def con(**cambios):
    return evaluar_progresivas(dict(SINTETICO, **cambios))


def main():
    print("Caso sintético que cumple las cinco condiciones")
    r = con()
    ok(r["adoptar"], "se adopta la distancia por progresivas")
    ok(all(r[k]["cumple"] for k in "abcde"), "cumple (a) a (e)")

    print("Cada condición, por separado, impide adoptar")
    for clave, cambios, texto in (
            ("a", {"mismo_corredor_y_tramo": False}, "otro corredor o tramo"),
            ("b", {"hueco_km": 49.1}, "hueco de 49.1 km"),
            ("b", {"hueco_km": -3.0}, "solape de 3 km"),
            ("c", {"extremo_destino_km": 11.0}, "extremo a 11 km del nodo"),
            ("c", {"extremo_origen_km": None}, "extremo sin poste"),
            ("d", {"razon_geometria": 1.486}, "razón 1.486"),
            ("e", {"por_progresivas_km": 27.0}, "menor que la geodésica")):
        r = con(**cambios)
        ok(not r["adoptar"] and not r[clave]["cumple"]
           and all(r[k]["cumple"] for k in "abcde" if k != clave),
           f"({clave}) {texto}: no se adopta y solo falla esa condición")

    print("Banda de doble calzada")
    ok(not con(razon_geometria=2.0)["adoptar"],
       "razón 2.0 sin verificar la doble calzada: no se adopta")
    ok(con(razon_geometria=2.0, doble_calzada_verificada=True)["adoptar"],
       "razón 2.0 con doble calzada verificada: se adopta")
    ok(con(razon_geometria=0.85)["adoptar"] and con(
        razon_geometria=1.15)["adoptar"], "los límites 0.85 y 1.15 se aceptan")
    ok(not con(razon_geometria=1.5, doble_calzada_verificada=True)["adoptar"],
       "razón 1.5 (entre las bandas): no se adopta")

    print("Caso real: Chocontá a Tunja (outputs/evaluacion_progresivas.json)")
    with open(SALIDA / "evaluacion_progresivas.json", encoding="utf-8") as f:
        real = json.load(f)["Chocontá - Tunja"]
    m, reglas = real["mediciones"], real["reglas"]
    r = evaluar_progresivas(m)
    ok(r["adoptar"] == reglas["adoptar"] and not r["adoptar"],
       "la regla no adopta los 61.0 km")
    ok([k for k in "abcde" if not r[k]["cumple"]] == ["b", "c", "d"],
       "incumple (b), (c) y (d)")
    ok(r["a"]["cumple"] and r["e"]["cumple"], "cumple (a) y (e)")
    ok(abs(m["hueco_km"] - 49.096) < 1e-3, "hueco de 49.1 km")
    ok(10 < m["extremo_destino_km"] < 12, "el PR 120 queda a unos 11 km de "
       "Tunja")
    ok(abs(m["razon_geometria"] - 1.486) < 5e-3, "razón de la geometría 1.486")
    ok(round(m["por_progresivas_km"], 2) == 61.0, "diferencia de PR 61.0 km")
    with open(SALIDA / "aristas_red.json", encoding="utf-8") as f:
        arista = next(a for a in json.load(f)
                      if (a["origen"], a["destino"]) == ("Chocontá", "Tunja"))
    ok(arista["distancia_km"] == 17.69 and arista["distancia_truncada"]
       and arista["distancia_fuente"] == "registro",
       "la base de la arista es 17.69 km, marcada truncada")
    ok(arista["distancia_progresivas_km"] == 61.0,
       "los 61.0 km quedan solo como dato de sensibilidad")

    if fallas:
        print(f"\n{len(fallas)} pruebas fallaron")
        sys.exit(1)
    print("\nTodas las pruebas de la regla de progresivas pasaron.")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
