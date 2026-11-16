"""Experimentos del Corte 3: regresión, clasificación y agrupamiento.

Uso:
    python experimentos/experimentos_corte3.py

Lee outputs/datos/trafico_peaje_mes.csv (si no existe, lo genera con
src/datos_trafico.py) y escribe en outputs/datos/:

    resultados_corte3.json     métricas de todos los modelos y referencias
    predicciones_prueba.csv    real y predicho por peaje y mes de la prueba
    agrupamiento_peajes.csv    perfil y grupo de cada peaje
    pronostico_red.json        tránsito, nivel y tiempo por tramo de la red
                               y por mes (prueba y los 12 meses siguientes)
    tiempo_tramo_mes.csv       tiempo BPR de cada tramo con peaje en la ANI
                               en cada mes observado

El pronóstico de la red lo usan el agente predictivo y el visualizador, que
no necesitan scikit-learn: solo leen pronostico_red.json.
"""
import sys
from pathlib import Path
if True:  # carpetas de código en el path
    sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "src")]
import json

import numpy as np
import pandas as pd

import aprendizaje as ap
import datos_trafico
import modelo_tiempo as mt
from build_graph import construir_grafo
from rutas import SALIDA


def cargar_tabla():
    if not (SALIDA / datos_trafico.SALIDA_CSV).exists():
        datos_trafico.main()
    return datos_trafico.cargar_depurado()


def texto_mes(fecha):
    return fecha.strftime("%Y-%m")


def reajustar(nombre, hiperparametros, tabla, clasificador=False,
              cortes=None):
    """Ajusta el modelo elegido con todas las filas modelables."""
    catalogo = ap.CLASIFICADORES if clasificador else ap.REGRESORES
    clase, rejilla = catalogo[nombre]
    parametros = next(p for p in rejilla
                      if ap.texto_parametros(p) == hiperparametros)
    datos = tabla[tabla["modelable"]]
    if clasificador:
        objetivo = ap.clase_de(datos["transito_diario"], cortes)
    else:
        objetivo = np.log(datos["transito_diario"])
    return clase(**parametros).fit(ap.matriz(datos), objetivo)


def entrada_mes(transito, observado, origen, clase, tramo, config):
    razon = mt.saturacion(transito, tramo["doble_calzada"], config)
    return {
        "transito_usado": round(transito, 1),
        "transito_observado": (None if observado is None
                               else round(observado, 1)),
        "origen_dato": origen, "clase": ap.CLASES[int(clase)],
        "saturacion": round(razon, 4),
        "tiempo_min": round(mt.tiempo_min(
            tramo["distancia_km"], transito, tramo["doble_calzada"],
            config), 3),
    }


def pronostico_red(tabla, cortes, regresor_prueba, clasificador_prueba,
                   regresor_final, clasificador_final):
    """Tránsito, nivel y tiempo de cada tramo de la red por mes."""
    config = mt.cargar_config()
    ultimo = tabla["mes"].max()
    inicio_futuro = ultimo + pd.DateOffset(months=1)
    meses_prueba = pd.date_range(ap.INICIO_PRUEBA, ultimo, freq="MS")
    meses_futuros = pd.date_range(inicio_futuro, periods=ap.HORIZONTE,
                                  freq="MS")
    peajes = {mt.normalizar(n): int(i) for i, n in
              tabla[["id_peaje", "peaje"]].drop_duplicates().itertuples(
                  index=False)}
    grafo = construir_grafo()
    tramos = []
    for tramo in mt.tramos_con_peaje(peajes, config):
        u, v = tramo["origen"], tramo["destino"]
        tramo["distancia_km"] = round(grafo[u][v]["distancia_km"], 6)
        tramo["tiempo_libre_min"] = round(mt.tiempo_libre_min(
            tramo["distancia_km"], config), 3)
        tramo["capacidad_veh_h"] = mt.capacidad(tramo["doble_calzada"],
                                                config)
        tramo["meses"] = {}
        if tramo["id_peaje"] is None:
            tramo["estado"] = "sin_dato"
            tramo["ultimo_mes"] = None
            tramos.append(tramo)
            continue
        serie_peaje = tabla[tabla["id_peaje"] == tramo["id_peaje"]]
        serie = serie_peaje.set_index("mes")
        tramo["ultimo_mes"] = texto_mes(serie.index.max())
        vigente = serie.index.max() == ultimo
        tramo["estado"] = "vigente" if vigente else "historico"
        if not vigente:
            # serie terminada: valor del mismo mes en su último año
            ultimos = serie.tail(12)
            por_mes = ultimos.groupby("mes_del_anio")[
                "transito_diario"].mean()
            for mes in list(meses_prueba) + list(meses_futuros):
                if mes.month not in por_mes:
                    continue
                valor = float(por_mes[mes.month])
                observado = (float(serie.loc[mes, "transito_diario"])
                             if mes in serie.index else None)
                tramo["meses"][texto_mes(mes)] = entrada_mes(
                    valor, observado, "historico",
                    ap.clase_de([valor], cortes)[0], tramo, config)
            tramos.append(tramo)
            continue
        en_prueba = serie[(serie.index >= ap.INICIO_PRUEBA)
                          & serie["modelable"]]
        if len(en_prueba):
            x = ap.matriz(en_prueba)
            valores = np.exp(regresor_prueba.predict(x))
            clases = clasificador_prueba.predict(x)
            for mes, valor, clase in zip(en_prueba.index, valores, clases):
                tramo["meses"][texto_mes(mes)] = entrada_mes(
                    float(valor),
                    float(en_prueba.loc[mes, "transito_diario"]),
                    "prueba", clase, tramo, config)
        pasos = ap.pronosticar(
            regresor_final, serie["transito_diario"],
            float(serie["participacion_carga"].iloc[-1]), inicio_futuro)
        for mes, valor, fila in pasos:
            clase = clasificador_final.predict(
                ap.matriz(pd.DataFrame([fila])))[0]
            tramo["meses"][texto_mes(mes)] = entrada_mes(
                valor, None, "pronostico", clase, tramo, config)
        tramos.append(tramo)
    return {
        "descripcion": "Tránsito diario, nivel de tránsito y tiempo BPR "
                       "de cada tramo de la red por mes. origen_dato: "
                       "«prueba» (predicción a un mes con rezagos "
                       "observados), «pronostico» (recursivo, modelo "
                       "final) o «historico» (serie terminada: mismo mes "
                       "de su último año).",
        "meses_prueba": [texto_mes(m) for m in meses_prueba],
        "meses_pronostico": [texto_mes(m) for m in meses_futuros],
        "cortes_clase": [round(c, 1) for c in cortes],
        "clases": list(ap.CLASES), "config_tiempo": config,
        "tramos": tramos,
    }


def tiempo_por_tramo(tabla, pronostico):
    """Tiempo BPR de cada tramo con peaje en la ANI y mes observado."""
    config = pronostico["config_tiempo"]
    filas = []
    for tramo in pronostico["tramos"]:
        if tramo["id_peaje"] is None:
            continue
        serie = tabla[tabla["id_peaje"] == tramo["id_peaje"]]
        for fila in serie.itertuples():
            razon = mt.saturacion(fila.transito_diario,
                                  tramo["doble_calzada"], config)
            filas.append({
                "origen": tramo["origen"], "destino": tramo["destino"],
                "peaje": tramo["peaje"], "mes": texto_mes(fila.mes),
                "distancia_km": tramo["distancia_km"],
                "doble_calzada": tramo["doble_calzada"],
                "transito_diario": round(fila.transito_diario, 1),
                "saturacion": round(razon, 4),
                "factor_bpr": round(mt.factor_bpr(razon, config), 6),
                "tiempo_libre_min": tramo["tiempo_libre_min"],
                "tiempo_min": round(mt.tiempo_min(
                    tramo["distancia_km"], fila.transito_diario,
                    tramo["doble_calzada"], config), 3)})
    return pd.DataFrame(filas)


def evaluar_tiempo(pronostico, tiempos):
    """Error del tiempo estimado en la prueba y rango del factor BPR."""
    config = pronostico["config_tiempo"]
    errores, relativos = [], []
    for tramo in pronostico["tramos"]:
        for dato in tramo["meses"].values():
            if dato["origen_dato"] != "prueba":
                continue
            real = mt.tiempo_min(tramo["distancia_km"],
                                 dato["transito_observado"],
                                 tramo["doble_calzada"], config)
            errores.append(abs(dato["tiempo_min"] - real))
            relativos.append(abs(dato["tiempo_min"] - real) / real)
    mayor = tiempos.loc[tiempos["factor_bpr"].idxmax()]
    return {
        "casos_prueba": len(errores),
        "mae_min": float(np.mean(errores)),
        "error_maximo_min": float(np.max(errores)),
        "error_porcentual_medio": float(100 * np.mean(relativos)),
        "filas_tramo_mes": int(len(tiempos)),
        "saturacion_mediana": float(tiempos["saturacion"].median()),
        "saturacion_maxima": float(tiempos["saturacion"].max()),
        "factor_bpr_mediano": float(tiempos["factor_bpr"].median()),
        "factor_bpr_maximo": float(mayor["factor_bpr"]),
        "tramo_factor_maximo": f"{mayor['origen']} - {mayor['destino']}",
        "mes_factor_maximo": mayor["mes"],
        "demora_maxima_min": float(
            (tiempos["tiempo_min"] - tiempos["tiempo_libre_min"]).max()),
    }


def main():
    tabla = cargar_tabla()
    entrenamiento, validacion, prueba = ap.particion(tabla)
    cortes = ap.cortes_de_clase(tabla)
    res_reg, modelos_reg, pred_reg = ap.entrenar_regresion(tabla)
    mejor_reg = ap.mejor_modelo(res_reg)
    res_cla, modelos_cla, pred_cla = ap.entrenar_clasificacion(
        tabla, cortes, pred_reg[mejor_reg])
    mejor_cla = ap.mejor_clasificador(res_cla)
    perfil, res_grupos = ap.agrupar(ap.perfil_peajes(tabla))

    regresor_final = reajustar(
        mejor_reg, res_reg[mejor_reg]["hiperparametros"], tabla)
    clasificador_final = reajustar(
        mejor_cla, res_cla[mejor_cla]["hiperparametros"], tabla,
        clasificador=True, cortes=cortes)
    pronostico = pronostico_red(
        tabla, cortes, modelos_reg[mejor_reg], modelos_cla[mejor_cla],
        regresor_final, clasificador_final)
    tiempos = tiempo_por_tramo(tabla, pronostico)

    def rango(parte):
        return {"filas": int(len(parte)),
                "peajes": int(parte["id_peaje"].nunique()),
                "desde": texto_mes(parte["mes"].min()),
                "hasta": texto_mes(parte["mes"].max())}

    clases_desarrollo = ap.clase_de(
        pd.concat([entrenamiento, validacion])["transito_diario"], cortes)
    resultados = {
        "semilla": ap.SEMILLA,
        "particion": {"entrenamiento": rango(entrenamiento),
                      "validacion": rango(validacion),
                      "prueba": rango(prueba)},
        "predictores": ap.PREDICTORES,
        "regresion": {
            "objetivo": "logaritmo natural del tránsito diario",
            "mejor": mejor_reg, "modelos": res_reg,
            "importancias": ap.importancias(modelos_reg[mejor_reg], prueba),
            "error_por_horizonte": ap.error_por_horizonte(
                modelos_reg[mejor_reg], tabla),
        },
        "clasificacion": {
            "cortes": cortes, "clases": list(ap.CLASES),
            "mejor": mejor_cla, "modelos": res_cla,
            "casos_por_clase_desarrollo": {
                c: int((clases_desarrollo == i).sum())
                for i, c in enumerate(ap.CLASES)},
        },
        "agrupamiento": res_grupos,
        "tiempo": evaluar_tiempo(pronostico, tiempos),
        "red": {
            estado: sum(1 for t in pronostico["tramos"]
                        if t["estado"] == estado)
            for estado in ("vigente", "historico", "sin_dato")},
    }
    resultados["red"]["doble_calzada"] = sum(
        1 for t in pronostico["tramos"] if t["doble_calzada"])

    salida = prueba[["id_peaje", "peaje", "mes", "transito_diario"]].copy()
    salida["mes"] = salida["mes"].dt.strftime("%Y-%m")
    for nombre, valores in pred_reg.items():
        salida[f"transito_{nombre}"] = np.round(valores, 1)
    salida["clase_real"] = [ap.CLASES[i] for i in ap.clase_de(
        prueba["transito_diario"], cortes)]
    for nombre, valores in pred_cla.items():
        salida[f"clase_{nombre}"] = [ap.CLASES[int(i)] for i in valores]
    salida["transito_diario"] = salida["transito_diario"].round(1)
    salida.to_csv(SALIDA / "predicciones_prueba.csv", index=False,
                  lineterminator="\n")
    reales = perfil.select_dtypes("float").columns
    perfil[reales] = perfil[reales].round(6)
    perfil.to_csv(SALIDA / "agrupamiento_peajes.csv", index=False,
                  lineterminator="\n")
    tiempos.to_csv(SALIDA / "tiempo_tramo_mes.csv", index=False,
                   lineterminator="\n")
    for nombre, datos in (("resultados_corte3.json", resultados),
                          ("pronostico_red.json", pronostico)):
        with open(SALIDA / nombre, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)

    print("Regresión (prueba):")
    for nombre, r in res_reg.items():
        p = r["prueba"]
        print(f"  {nombre:42s} MAE {p['mae']:7.1f}  RMSE {p['rmse']:7.1f}"
              f"  R2 {p['r2']:.4f}  EPM {p['error_porcentual_mediano']:.2f}")
    print(f"  mejor en validación: {mejor_reg}")
    print("Clasificación (prueba):")
    for nombre, r in res_cla.items():
        p = r["prueba"]
        print(f"  {nombre:42s} exactitud {p['exactitud']:.4f}"
              f"  F1 macro {p['f1_macro']:.4f}")
    print(f"  mejor en validación: {mejor_cla}; cortes {cortes}")
    print(f"Agrupamiento: k = {res_grupos['k']} con "
          f"{res_grupos['peajes']} peajes")
    print("Tiempo:", resultados["tiempo"])
    print("Red:", resultados["red"])


if __name__ == "__main__":
    main()
