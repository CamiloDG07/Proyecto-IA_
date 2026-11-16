"""Pruebas del Corte 3: datos, modelos, tiempo, agente predictivo y API.

Uso:
    python pruebas/pruebas_corte3.py

No entrena modelos: comprueba la depuración, las funciones puras y la
coherencia de los resultados guardados por
experimentos/experimentos_corte3.py (las métricas se recalculan desde
predicciones_prueba.csv). El agente predictivo se prueba en todos los meses
del pronóstico y la API se llama por la interfaz ASGI, sin abrir puertos.
"""
import sys
from pathlib import Path
if True:  # carpetas de código en el path
    sys.path[:0] = [str(Path(__file__).resolve().parents[1] / c)
                    for c in ("src", "experimentos", "informe", "pruebas",
                              "visualizador")]
import json
import re
import subprocess

import networkx as nx
import numpy as np
import pandas as pd

import agente_predictivo as ag
import aprendizaje as ap
import datos_trafico as dt
import modelo_tiempo as mt
from rutas import RAIZ, SALIDA

CENTRAL = ("Duitama", "Puente Nacional")
ARCHIVOS = ["src/datos_trafico.py", "src/modelo_tiempo.py",
            "src/aprendizaje.py", "src/agente_predictivo.py",
            "experimentos/experimentos_corte3.py",
            "informe/figuras_corte3.py", "informe/tablas_corte3.py",
            "pruebas/pruebas_corte3.py", "visualizador/servidor.py"]


def ok(mensaje):
    print(f"  ok: {mensaje}")


def verificar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)
    ok(mensaje)


def leer_json(nombre):
    with open(SALIDA / nombre, encoding="utf-8") as f:
        return json.load(f)


def prueba_depuracion():
    print("Depuración del tránsito de la ANI")
    casos = {"I": "livianos", "IE": "livianos", "IE10": "livianos",
             "IEEE": "livianos", "II": "buses", "IIE1": "buses",
             "IIA": "buses", "III": "carga", "IV": "carga", "VIIE": "carga",
             "E1-III": "carga", "E2-I": "livianos", "EXCII": "buses",
             "IX": "carga", "UNICA": "unica", "EG": None, "ER": None,
             "EA": None, "EC": None, "POLCA": None}
    verificar(all(dt.grupo_de(c) == g for c, g in casos.items()),
              f"grupo vehicular de {len(casos)} códigos de categoría")
    registro = leer_json(dt.SALIDA_JSON)
    tabla = dt.cargar_depurado()
    verificar(registro["sha256"] == dt.SHA256,
              "la depuración salió del archivo documentado")
    verificar(registro["filas_peaje_mes"] - registro["meses_sin_transito"]
              - registro["meses_anomalos"]
              - registro["meses_parciales_de_borde"]
              == registro["filas_depuradas"] == len(tabla),
              "los pasos de la depuración suman las filas depuradas")
    verificar(not tabla.duplicated(["id_peaje", "mes"]).any()
              and (tabla["transito_diario"] > 0).all(),
              "una fila por peaje y mes, con tránsito positivo")
    suma = tabla[list(dt.GRUPOS)].sum(axis=1)
    verificar((suma == tabla["transito_mes"]).all(),
              "el tránsito del mes es la suma de sus grupos")
    muestra = tabla[tabla["modelable"]].sample(300, random_state=1)
    indice = tabla.set_index(["id_peaje", "indice_mes"])["transito_diario"]
    for meses in dt.REZAGOS:
        previo = indice.reindex(pd.MultiIndex.from_arrays(
            [muestra["id_peaje"], muestra["indice_mes"] - meses]))
        verificar(np.allclose(previo.to_numpy(), muestra[
            f"transito_diario_rezago_{meses}"]),
            f"el rezago {meses} es el tránsito de {meses} mes(es) antes")
    return tabla


def prueba_particion(tabla):
    print("Partición temporal y predictores")
    entrenamiento, validacion, prueba = ap.particion(tabla)
    verificar(entrenamiento["mes"].max() < validacion["mes"].min()
              and validacion["mes"].max() < prueba["mes"].min(),
              "entrenamiento, validación y prueba no se cruzan en el tiempo")
    r = leer_json("resultados_corte3.json")
    verificar([r["particion"][c]["filas"] for c in (
        "entrenamiento", "validacion", "prueba")] == [
        len(entrenamiento), len(validacion), len(prueba)],
        "las filas de la partición coinciden con las guardadas")
    x = ap.matriz(prueba)
    verificar(list(x.columns) == ap.PREDICTORES and not x.isna().any().any()
              and (x[[f"mes_{m}" for m in range(1, 13)]].sum(axis=1)
                   == 1).all(),
              "la matriz de predictores está completa")
    verificar(not any("transito_diario" == c or c == "transito_mes"
                      for c in x.columns),
              "ningún predictor es el tránsito del mes que se predice")
    cortes = ap.cortes_de_clase(tabla)
    verificar(np.allclose(cortes, r["clasificacion"]["cortes"])
              and list(ap.clase_de([cortes[0] - 1, cortes[0], cortes[1]],
                                   cortes)) == [0, 1, 2],
              "los cortes de nivel son los terciles del entrenamiento")
    return r


def prueba_resultados(r):
    print("Resultados guardados de los modelos")
    pred = pd.read_csv(SALIDA / "predicciones_prueba.csv")
    reg = r["regresion"]
    for nombre, m in reg["modelos"].items():
        mae = np.abs(pred[f"transito_{nombre}"]
                     - pred["transito_diario"]).mean()
        verificar(abs(mae - m["prueba"]["mae"]) < 0.06,
                  f"MAE de «{nombre}» recalculado desde las predicciones")
    referencias = [m["prueba"]["mae"] for m in reg["modelos"].values()
                   if m["tipo"] == "referencia"]
    modelos = {n: m["prueba"]["mae"] for n, m in reg["modelos"].items()
               if m["tipo"] == "modelo"}
    verificar(max(modelos.values()) < min(referencias),
              "los cuatro regresores superan a las dos referencias")
    verificar(min(modelos, key=modelos.get) == reg["mejor"],
              "el regresor elegido en validación es también el mejor en "
              "la prueba")
    cla = r["clasificacion"]
    for nombre, m in cla["modelos"].items():
        exactitud = (pred[f"clase_{nombre}"] == pred["clase_real"]).mean()
        verificar(abs(exactitud - m["prueba"]["exactitud"]) < 1e-9,
                  f"exactitud de «{nombre}» recalculada")
    mejor = cla["modelos"][cla["mejor"]]["prueba"]
    verificar(mejor["exactitud"] > cla["modelos"][
        "Persistencia (clase del mes anterior)"]["prueba"]["exactitud"],
        "el clasificador elegido supera a la persistencia")
    agr = r["agrupamiento"]
    grupos = pd.read_csv(SALIDA / "agrupamiento_peajes.csv")
    verificar(len(grupos) == agr["peajes"]
              and grupos["grupo_k_medias"].nunique() == agr["k"]
              and grupos["grupo_jerarquico"].nunique() == agr["k"],
              f"{agr['peajes']} peajes en {agr['k']} grupos con los dos "
              "métodos")
    medias = grupos.groupby("grupo_k_medias")[
        "transito_diario_medio"].mean()
    verificar(medias.is_monotonic_decreasing,
              "los grupos van numerados de mayor a menor tránsito")


def prueba_tiempo():
    print("Función BPR y pronóstico de la red")
    config = mt.cargar_config()
    verificar(mt.tiempo_min(50, None, False, config) == 60.0
              and mt.factor_bpr(0, config) == 1.0,
              "sin tránsito el tiempo es el libre (50 km a 50 km/h, 60 min)")
    capacidad = mt.capacidad(False, config)
    lleno = capacidad / config["factor_hora_pico"]
    verificar(abs(mt.tiempo_min(50, lleno, False, config) - 69.0) < 1e-9,
              "a capacidad el tiempo crece un 15 % (alfa de la BPR)")
    tiempos = [mt.tiempo_min(50, t, True, config)
               for t in (0, 5000, 20000, 60000)]
    verificar(tiempos == sorted(tiempos) and tiempos[0] >= 60.0,
              "el tiempo no baja al subir el tránsito")
    p = ag.cargar_pronostico()
    verificar(len(p["tramos"]) == 32 and len(p["meses_pronostico"]) == 12,
              "32 tramos y 12 meses de pronóstico")
    estados = [t["estado"] for t in p["tramos"]]
    r = leer_json("resultados_corte3.json")["red"]
    verificar(all(estados.count(e) == r[e] for e in (
        "vigente", "historico", "sin_dato")),
        "tramos vigentes, terminados y sin dato como en los resultados")
    for t in p["tramos"]:
        if t["estado"] == "vigente":
            assert all(m in t["meses"] for m in p["meses_pronostico"]), t
        for dato in t["meses"].values():
            esperado = mt.tiempo_min(t["distancia_km"],
                                     dato["transito_usado"],
                                     t["doble_calzada"], config)
            assert abs(esperado - dato["tiempo_min"]) < 0.01, t
            assert dato["clase"] == ap.CLASES[int(ap.clase_de(
                [dato["transito_usado"]], p["cortes_clase"])[0])] \
                or dato["origen_dato"] != "historico", t
    ok("cada tiempo guardado sale de la BPR con su tránsito; los tramos "
       "vigentes tienen los 12 meses")
    return p


def prueba_agente(p):
    print("Agente predictivo")
    violaciones, distintos = 0, 0
    for mes in ag.meses_disponibles(p):
        red = ag.grafo_del_mes(mes, p)
        h = ag.HeuristicaTiempo(red.graph["velocidad_libre_kmh"])
        v = ag.verificar_heuristica(red, h)
        violaciones += v["admisibilidad"] + v["consistencia"]
        if mes in (p["meses_pronostico"][0], p["meses_pronostico"][6]):
            costos = dict(nx.all_pairs_dijkstra_path_length(
                red, weight="tiempo_min"))
            for u in red:
                for w in red:
                    if u == w:
                        continue
                    res = ag.a_estrella(red, u, w, "tiempo_min", h)
                    distintos += (abs(res["costo"] - costos[u][w]) > 1e-6
                                  or res["reexpansiones"] > 0)
    verificar(violaciones == 0,
              "la heurística de tiempo es admisible y consistente en los "
              f"{len(ag.meses_disponibles(p))} meses")
    verificar(distintos == 0,
              "A* da el tiempo mínimo en los 992 pares de dos meses, sin "
              "reexpansiones")
    r = ag.recomendar(*CENTRAL, p["meses_pronostico"][6], p)
    verificar(abs(r["elegida"]["distancia_km"] - 370.54) < 0.005
              and abs(r["alternativas"][0]["distancia_km"] - 654.25) < 0.005,
              "caso central: 370.54 km por Bogotá y 654.25 km de "
              "alternativa")
    e = r["elegida"]
    verificar(sum(e["tramos_por_nivel"].values()) == e["saltos"]
              and e["tiempo_min"] >= e["tiempo_libre_min"]
              and abs(sum(d["tiempo_min"] for d in e["detalle"])
                      - e["tiempo_min"]) < 0.5,
              "los totales de la ruta salen de sus tramos")
    try:
        ag.recomendar("Bogotá", "Bogotá", p["meses_pronostico"][0], p)
        raise AssertionError("debió rechazar origen igual a destino")
    except ValueError:
        ok("rechaza origen igual a destino y meses fuera del pronóstico")
    try:
        ag.grafo_del_mes("2030-01", p)
        raise AssertionError("debió rechazar el mes")
    except ValueError:
        pass


def prueba_api(p):
    print("API de aprendizaje automático del visualizador")
    from pruebas_visualizador import get, ok as pedir_ok
    resumen = pedir_ok("/api/aprendizaje/resumen")
    verificar(resumen["meses_pronostico"] == p["meses_pronostico"]
              and "enlace_ward" not in resumen["agrupamiento"]
              and len(resumen["grupos"]) == resumen["agrupamiento"]["peajes"],
              "/api/aprendizaje/resumen entrega métricas, meses y grupos")
    mes = p["meses_pronostico"][6]
    red = pedir_ok("/api/aprendizaje/red", mes=mes)
    verificar(len(red["tramos"]) == 32 and len(red["nodos"]) == 32
              and red["es_pronostico"],
              "/api/aprendizaje/red entrega los 32 tramos del mes")
    ruta = pedir_ok("/api/aprendizaje/ruta", origen=CENTRAL[0],
                    destino=CENTRAL[1], mes=mes)
    directa = ag.recomendar(*CENTRAL, mes, p)
    verificar(ruta["elegida"] == directa["elegida"],
              "/api/aprendizaje/ruta coincide con el agente predictivo")
    estado, cuerpo = get("/api/aprendizaje/red", mes="2030-01")
    verificar(estado == 422 and "Mes fuera" in cuerpo["detail"],
              "mes desconocido: 422 con mensaje en español")
    estado, _ = get("/api/aprendizaje/ruta", origen="Narnia",
                    destino="Bogotá", mes=mes)
    verificar(estado == 404, "nodo desconocido: 404")
    codigo = subprocess.run(
        [sys.executable, "-B", "-c",
         "import sys; sys.path[:0] = ['visualizador']; import servidor; "
         "raise SystemExit(any(m in sys.modules for m in "
         "('sklearn', 'pandas', 'scipy', 'matplotlib')))"],
        cwd=RAIZ).returncode
    verificar(codigo == 0,
              "el servidor no importa scikit-learn, pandas ni matplotlib")


def prueba_informe():
    print("Cifras del informe")
    ruta = RAIZ / "informe_corte3.tex"
    if not ruta.exists():
        return  # el paquete puede no llevar los fuentes del informe
    definidas = set(re.findall(
        r"\\newcommand\{\\(ct[A-Za-z]+)\}",
        (SALIDA / "texto_c3_cifras.tex").read_text(encoding="utf-8")))
    texto = ruta.read_text(encoding="utf-8")
    usadas = set(re.findall(r"\\(ct[A-Z][A-Za-z]+)", texto))
    verificar(usadas and usadas <= definidas,
              f"las {len(usadas)} cifras que cita el informe están "
              "definidas por informe/tablas_corte3.py")
    for nombre in re.findall(r"\\input\{(outputs/[^}]+)\}", texto):
        assert (RAIZ / nombre).exists(), nombre
    for nombre in re.findall(r"includegraphics\[[^\]]*\]\{([^}]+)\}", texto):
        assert any((RAIZ / c / nombre).exists()
                   for c in ("data", "outputs/figuras")), nombre
    ok("existen todas las tablas, lecturas y figuras que incluye")


def prueba_estilo():
    print("Estilo del código")
    r = subprocess.run([sys.executable, "-m", "pycodestyle",
                        "--max-line-length=79", *ARCHIVOS], cwd=RAIZ,
                       capture_output=True, text=True)
    verificar(r.returncode == 0, "pycodestyle limpio" + r.stdout)


def main():
    tabla = prueba_depuracion()
    resultados = prueba_particion(tabla)
    prueba_resultados(resultados)
    pronostico = prueba_tiempo()
    prueba_agente(pronostico)
    prueba_api(pronostico)
    prueba_informe()
    prueba_estilo()
    print("Todas las pruebas del Corte 3 pasaron.")


if __name__ == "__main__":
    main()
