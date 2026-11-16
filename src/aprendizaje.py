"""Modelos de aprendizaje automático sobre el tránsito de los peajes.

Unidad de análisis: un peaje en un mes (tabla depurada de datos_trafico.py).

Regresión. Predice el tránsito diario del mes siguiente (objetivo: su
logaritmo natural) con lo que se conoce al cierre del mes anterior: los
rezagos de 1, 2, 3, 12 y 13 meses, la participación de la carga del mes
anterior, los días del mes y el mes del año. El tiempo de recorrido de un
tramo se obtiene después con la función BPR (modelo_tiempo.py).

Clasificación. Predice el nivel de tránsito del mes (bajo, medio o alto),
que es el indicador de congestión del proyecto. Los cortes son los terciles
del tránsito diario en el conjunto de entrenamiento y quedan fijos.

Agrupamiento. Agrupa los peajes por su perfil (volumen, composición y
estacionalidad) con K-medias y con agrupamiento jerárquico.

Partición temporal, sin barajar: entrenamiento hasta mayo de 2024,
validación de junio de 2024 a mayo de 2025 (elige los hiperparámetros) y
prueba de junio de 2025 a mayo de 2026 (se usa una sola vez). El modelo que
se evalúa en la prueba se ajusta con entrenamiento más validación.
"""
import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import (HistGradientBoostingRegressor,
                              RandomForestClassifier, RandomForestRegressor)
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (accuracy_score, adjusted_rand_score,
                             confusion_matrix, f1_score,
                             mean_absolute_error, mean_squared_error,
                             precision_recall_fscore_support, r2_score,
                             silhouette_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from datos_trafico import REZAGOS

SEMILLA = 42
INICIO_VALIDACION = pd.Timestamp("2024-06-01")
INICIO_PRUEBA = pd.Timestamp("2025-06-01")
HORIZONTE = 12
CLASES = ("bajo", "medio", "alto")
PREDICTORES = ([f"log_rezago_{m}" for m in REZAGOS]
               + ["participacion_carga_rezago_1", "dias_mes"]
               + [f"mes_{m}" for m in range(1, 13)])
ANIO_EXCLUIDO_PERFIL = 2020
MESES_MINIMOS_PERFIL = 24
RANGO_K = range(2, 9)
# El índice de diciembre y enero y el crecimiento anual se calculan y se
# guardan como descripción, pero no entran al agrupamiento: el primero
# repite la amplitud estacional y el segundo lo dominan las series cortas.
VARIABLES_PERFIL = ("log10_transito_diario", "participacion_carga",
                    "participacion_buses", "amplitud_estacional")

REGRESORES = {
    "Regresión lineal": (LinearRegression, [{}]),
    "Árbol de decisión": (DecisionTreeRegressor, [
        {"max_depth": p, "min_samples_leaf": h, "random_state": SEMILLA}
        for p in (4, 6, 8, 12, None) for h in (5, 20)]),
    "Bosque aleatorio": (RandomForestRegressor, [
        {"n_estimators": 300, "min_samples_leaf": h, "max_features": c,
         "random_state": SEMILLA, "n_jobs": -1}
        for h in (1, 3, 5) for c in (1.0, 0.5)]),
    "Potenciación del gradiente": (HistGradientBoostingRegressor, [
        {"learning_rate": t, "max_iter": n, "random_state": SEMILLA}
        for t in (0.05, 0.1) for n in (200, 400)]),
}


def _logistica(**parametros):
    return make_pipeline(StandardScaler(),
                         LogisticRegression(max_iter=5000, **parametros))


CLASIFICADORES = {
    "Regresión logística": (_logistica, [{"C": c} for c in (0.1, 1, 10)]),
    "Árbol de decisión": (DecisionTreeClassifier, [
        {"max_depth": p, "min_samples_leaf": h, "random_state": SEMILLA}
        for p in (4, 6, 8, 12, None) for h in (5, 20)]),
    "Bosque aleatorio": (RandomForestClassifier, [
        {"n_estimators": 300, "min_samples_leaf": h,
         "random_state": SEMILLA, "n_jobs": -1} for h in (1, 3, 5)]),
}


# ------------------------------------------------------------- datos
def matriz(tabla):
    """Matriz de predictores de las filas de `tabla`."""
    x = pd.DataFrame(index=tabla.index)
    for meses in REZAGOS:
        x[f"log_rezago_{meses}"] = np.log(
            tabla[f"transito_diario_rezago_{meses}"])
    x["participacion_carga_rezago_1"] = tabla["participacion_carga_rezago_1"]
    x["dias_mes"] = tabla["dias_mes"]
    for mes in range(1, 13):
        x[f"mes_{mes}"] = (tabla["mes_del_anio"] == mes).astype(int)
    return x[PREDICTORES]


def particion(tabla):
    """Entrenamiento, validación y prueba de las filas modelables."""
    tabla = tabla[tabla["modelable"]]
    entrenamiento = tabla[tabla["mes"] < INICIO_VALIDACION]
    validacion = tabla[(tabla["mes"] >= INICIO_VALIDACION)
                       & (tabla["mes"] < INICIO_PRUEBA)]
    prueba = tabla[tabla["mes"] >= INICIO_PRUEBA]
    return entrenamiento, validacion, prueba


def texto_parametros(parametros):
    """Hiperparámetros sin la semilla ni los hilos, para las tablas."""
    return {c: v for c, v in parametros.items()
            if c not in ("random_state", "n_jobs")}


# --------------------------------------------------------- regresión
def metricas_regresion(real, predicho):
    real, predicho = np.asarray(real), np.asarray(predicho)
    relativo = np.abs(predicho - real) / real
    return {
        "mae": float(mean_absolute_error(real, predicho)),
        "rmse": float(mean_squared_error(real, predicho) ** 0.5),
        "r2": float(r2_score(real, predicho)),
        "error_porcentual_mediano": float(100 * np.median(relativo)),
        "error_porcentual_medio": float(100 * np.mean(relativo)),
    }


def referencias_regresion(tabla):
    """Predicciones de las dos referencias sin aprendizaje."""
    return {"Persistencia (mes anterior)":
            tabla["transito_diario_rezago_1"].to_numpy(),
            "Estacional (mismo mes del año anterior)":
            tabla["transito_diario_rezago_12"].to_numpy()}


def entrenar_regresion(tabla):
    """Selecciona, ajusta y evalúa los regresores.

    Devuelve (resultados, modelos, predicciones): `resultados` tiene una
    entrada por modelo y por referencia con las métricas de validación y de
    prueba; `modelos` son los ajustados con entrenamiento más validación;
    `predicciones` son las de la prueba.
    """
    entrenamiento, validacion, prueba = particion(tabla)
    desarrollo = pd.concat([entrenamiento, validacion])
    resultados, modelos, predicciones = {}, {}, {}
    for nombre, valores in referencias_regresion(prueba).items():
        en_validacion = referencias_regresion(validacion)[nombre]
        resultados[nombre] = {
            "tipo": "referencia", "hiperparametros": {},
            "validacion": metricas_regresion(validacion["transito_diario"],
                                             en_validacion),
            "prueba": metricas_regresion(prueba["transito_diario"],
                                         valores)}
        predicciones[nombre] = valores
    for nombre, (clase, rejilla) in REGRESORES.items():
        ensayos = []
        for parametros in rejilla:
            modelo = clase(**parametros).fit(
                matriz(entrenamiento),
                np.log(entrenamiento["transito_diario"]))
            estimado = np.exp(modelo.predict(matriz(validacion)))
            ensayos.append((metricas_regresion(
                validacion["transito_diario"], estimado), parametros))
        en_validacion, mejor = min(ensayos, key=lambda e: e[0]["mae"])
        modelo = clase(**mejor).fit(matriz(desarrollo),
                                    np.log(desarrollo["transito_diario"]))
        estimado = np.exp(modelo.predict(matriz(prueba)))
        resultados[nombre] = {
            "tipo": "modelo", "hiperparametros": texto_parametros(mejor),
            "combinaciones_probadas": len(rejilla),
            "validacion": en_validacion,
            "prueba": metricas_regresion(prueba["transito_diario"],
                                         estimado)}
        modelos[nombre] = modelo
        predicciones[nombre] = estimado
    return resultados, modelos, predicciones


def mejor_modelo(resultados):
    """Nombre del modelo (no referencia) con menor MAE en validación."""
    candidatos = {n: r for n, r in resultados.items()
                  if r["tipo"] == "modelo"}
    return min(candidatos,
               key=lambda n: candidatos[n]["validacion"]["mae"])


def importancias(modelo, tabla, repeticiones=10):
    """Importancia por permutación en `tabla`; los doce indicadores del
    mes se suman en una sola variable."""
    x = matriz(tabla)
    res = permutation_importance(
        modelo, x, np.log(tabla["transito_diario"]),
        n_repeats=repeticiones, random_state=SEMILLA,
        scoring="neg_mean_absolute_error")
    suma = {}
    for columna, valor in zip(x.columns, res.importances_mean):
        clave = "mes_del_anio" if columna.startswith("mes_") else columna
        suma[clave] = suma.get(clave, 0.0) + float(valor)
    return dict(sorted(suma.items(), key=lambda par: -par[1]))


# ------------------------------------------------------ pronóstico
def _fila_futura(historia, mes, carga):
    """Predictores de `mes` a partir de la serie `historia` (por mes)."""
    fila = {"mes_del_anio": mes.month, "dias_mes": mes.days_in_month,
            "participacion_carga_rezago_1": carga}
    for meses in REZAGOS:
        previo = mes - pd.DateOffset(months=meses)
        if previo not in historia or not historia[previo] > 0:
            return None
        fila[f"transito_diario_rezago_{meses}"] = historia[previo]
    return fila


def pronosticar(modelo, serie, carga, inicio, pasos=HORIZONTE):
    """Pronóstico recursivo de `pasos` meses desde `inicio`.

    serie: tránsito diario observado por mes (pd.Series con índice de
    fechas) hasta el mes anterior a `inicio`. Cada paso usa como rezagos
    los valores observados y, cuando ya no los hay, los pronosticados. La
    participación de la carga se deja en su último valor observado.
    Devuelve una lista de (mes, valor, fila de predictores); se corta si
    falta algún rezago.
    """
    historia = {m: v for m, v in serie.items() if m < inicio}
    salida = []
    for paso in range(pasos):
        mes = inicio + pd.DateOffset(months=paso)
        fila = _fila_futura(historia, mes, carga)
        if fila is None:
            break
        x = matriz(pd.DataFrame([fila]))
        valor = float(np.exp(modelo.predict(x))[0])
        historia[mes] = valor
        salida.append((mes, valor, fila))
    return salida


def error_por_horizonte(modelo, tabla):
    """Error del pronóstico recursivo de 12 meses lanzado al final de la
    validación, por horizonte, frente a las dos referencias (que solo usan
    datos anteriores al inicio de la prueba)."""
    filas = []
    for id_peaje, grupo in tabla.groupby("id_peaje"):
        serie = grupo.set_index("mes")["transito_diario"]
        previos = grupo[grupo["mes"] < INICIO_PRUEBA]
        if previos.empty:
            continue
        ultimo = previos.iloc[-1]
        if ultimo["mes"] != INICIO_PRUEBA - pd.DateOffset(months=1):
            continue
        pasos = pronosticar(modelo, serie, ultimo["participacion_carga"],
                            INICIO_PRUEBA)
        for horizonte, (mes, valor, _) in enumerate(pasos, start=1):
            if mes not in serie:
                continue
            anterior = mes - pd.DateOffset(months=12)
            if anterior not in serie:
                continue
            filas.append({"id_peaje": id_peaje, "horizonte": horizonte,
                          "real": serie[mes], "modelo": valor,
                          "persistencia": ultimo["transito_diario"],
                          "estacional": serie[anterior]})
    filas = pd.DataFrame(filas)
    resumen = []
    for horizonte, grupo in filas.groupby("horizonte"):
        entrada = {"horizonte": int(horizonte), "peajes": int(len(grupo))}
        for metodo in ("modelo", "persistencia", "estacional"):
            relativo = np.abs(grupo[metodo] - grupo["real"]) / grupo["real"]
            entrada[metodo] = float(100 * np.median(relativo))
        resumen.append(entrada)
    return resumen


# ----------------------------------------------------- clasificación
def cortes_de_clase(tabla):
    """Terciles del tránsito diario en el entrenamiento (cortes fijos)."""
    entrenamiento = particion(tabla)[0]
    return [float(q) for q in
            entrenamiento["transito_diario"].quantile([1 / 3, 2 / 3])]


def clase_de(transito_diario, cortes):
    """Índice de clase (0 bajo, 1 medio, 2 alto) de cada valor."""
    return np.digitize(np.asarray(transito_diario, dtype=float), cortes)


def metricas_clasificacion(real, predicho):
    precision, exhaustividad, f1, soporte = precision_recall_fscore_support(
        real, predicho, labels=[0, 1, 2], zero_division=0)
    return {
        "exactitud": float(accuracy_score(real, predicho)),
        "f1_macro": float(f1_score(real, predicho, average="macro")),
        "por_clase": {CLASES[i]: {"precision": float(precision[i]),
                                  "exhaustividad": float(exhaustividad[i]),
                                  "f1": float(f1[i]),
                                  "casos": int(soporte[i])}
                      for i in range(3)},
        "matriz_confusion": confusion_matrix(
            real, predicho, labels=[0, 1, 2]).tolist(),
    }


def entrenar_clasificacion(tabla, cortes, regresion_prueba=None):
    """Selecciona, ajusta y evalúa los clasificadores.

    regresion_prueba: predicciones de tránsito del mejor regresor en la
    prueba; si se dan, se agrega la fila «clase a partir de la regresión».
    """
    entrenamiento, validacion, prueba = particion(tabla)
    desarrollo = pd.concat([entrenamiento, validacion])

    def y(parte):
        return clase_de(parte["transito_diario"], cortes)

    resultados, modelos, predicciones = {}, {}, {}
    referencia = "Persistencia (clase del mes anterior)"
    resultados[referencia] = {
        "tipo": "referencia", "hiperparametros": {},
        "validacion": metricas_clasificacion(y(validacion), clase_de(
            validacion["transito_diario_rezago_1"], cortes)),
        "prueba": metricas_clasificacion(y(prueba), clase_de(
            prueba["transito_diario_rezago_1"], cortes))}
    predicciones[referencia] = clase_de(
        prueba["transito_diario_rezago_1"], cortes)
    for nombre, (clase, rejilla) in CLASIFICADORES.items():
        ensayos = []
        for parametros in rejilla:
            modelo = clase(**parametros).fit(matriz(entrenamiento),
                                             y(entrenamiento))
            ensayos.append((metricas_clasificacion(
                y(validacion), modelo.predict(matriz(validacion))),
                parametros))
        en_validacion, mejor = max(ensayos,
                                   key=lambda e: e[0]["f1_macro"])
        modelo = clase(**mejor).fit(matriz(desarrollo), y(desarrollo))
        estimado = modelo.predict(matriz(prueba))
        resultados[nombre] = {
            "tipo": "modelo", "hiperparametros": texto_parametros(mejor),
            "combinaciones_probadas": len(rejilla),
            "validacion": en_validacion,
            "prueba": metricas_clasificacion(y(prueba), estimado)}
        modelos[nombre] = modelo
        predicciones[nombre] = estimado
    if regresion_prueba is not None:
        nombre = "Clase a partir de la regresión"
        estimado = clase_de(regresion_prueba, cortes)
        resultados[nombre] = {
            "tipo": "derivado", "hiperparametros": {},
            "prueba": metricas_clasificacion(y(prueba), estimado)}
        predicciones[nombre] = estimado
    return resultados, modelos, predicciones


def mejor_clasificador(resultados):
    candidatos = {n: r for n, r in resultados.items()
                  if r["tipo"] == "modelo"}
    return max(candidatos,
               key=lambda n: candidatos[n]["validacion"]["f1_macro"])


# ------------------------------------------------------ agrupamiento
def perfil_peajes(tabla):
    """Una fila por peaje con las variables del agrupamiento.

    Entran los peajes con al menos MESES_MINIMOS_PERFIL meses depurados y
    dos años calendario completos, sin contar ANIO_EXCLUIDO_PERFIL (la
    caída de 2020 deforma la estacionalidad y la tendencia).
    """
    filas = []
    for (id_peaje, peaje), grupo in tabla.groupby(["id_peaje", "peaje"]):
        util = grupo[grupo["anio"] != ANIO_EXCLUIDO_PERFIL]
        por_anio = util.groupby("anio")["transito_diario"]
        completos = [a for a, n in por_anio.count().items() if n == 12]
        if len(grupo) < MESES_MINIMOS_PERFIL or len(completos) < 2:
            continue
        base = util[util["anio"].isin(completos)]
        indice = (base["transito_diario"]
                  / base.groupby("anio")["transito_diario"]
                  .transform("mean"))
        estacional = indice.groupby(base["mes_del_anio"]).mean()
        tiempo = (util["indice_mes"] - util["indice_mes"].min()) / 12
        pendiente = np.polyfit(tiempo, np.log(util["transito_diario"]),
                               1)[0]
        filas.append({
            "id_peaje": id_peaje, "peaje": peaje,
            "meses": int(len(grupo)),
            "transito_diario_medio": util["transito_diario"].mean(),
            "log10_transito_diario": np.log10(
                util["transito_diario"].mean()),
            "participacion_carga": util["carga"].sum()
            / util["transito_mes"].sum(),
            "participacion_buses": util["buses"].sum()
            / util["transito_mes"].sum(),
            "amplitud_estacional": estacional.max() - estacional.min(),
            "indice_dic_ene": (estacional[12] + estacional[1]) / 2,
            "crecimiento_anual": float(np.exp(pendiente) - 1),
        })
    return pd.DataFrame(filas)


def agrupar(perfil):
    """K-medias y jerárquico (Ward) sobre el perfil estandarizado.

    k se elige con la mayor silueta de K-medias en RANGO_K. Devuelve el
    perfil con las etiquetas y las dos componentes principales, y un
    resumen con la curva de silueta e inercia, la comparación entre los
    dos métodos y la matriz de enlace del dendrograma.
    """
    x = StandardScaler().fit_transform(perfil[list(VARIABLES_PERFIL)])
    curva = []
    for k in RANGO_K:
        km = KMeans(n_clusters=k, n_init=20, random_state=SEMILLA).fit(x)
        ward = AgglomerativeClustering(n_clusters=k, linkage="ward").fit(x)
        curva.append({
            "k": k, "inercia": float(km.inertia_),
            "silueta_k_medias": float(silhouette_score(x, km.labels_)),
            "silueta_jerarquico": float(silhouette_score(x, ward.labels_)),
        })
    k = max(curva, key=lambda c: c["silueta_k_medias"])["k"]
    km = KMeans(n_clusters=k, n_init=20, random_state=SEMILLA).fit(x)
    ward = AgglomerativeClustering(n_clusters=k, linkage="ward").fit(x)
    # grupos numerados de mayor a menor tránsito medio
    orden = (perfil.assign(g=km.labels_).groupby("g")
             ["transito_diario_medio"].mean()
             .sort_values(ascending=False).index)
    nuevo = {viejo: i + 1 for i, viejo in enumerate(orden)}
    pca = PCA(n_components=2, random_state=SEMILLA).fit(x)
    plano = pca.transform(x)
    salida = perfil.copy()
    salida["grupo_k_medias"] = [nuevo[e] for e in km.labels_]
    salida["grupo_jerarquico"] = ward.labels_ + 1
    salida["componente_1"] = plano[:, 0]
    salida["componente_2"] = plano[:, 1]
    resumen = {
        "peajes": int(len(perfil)), "variables": list(VARIABLES_PERFIL),
        "k": int(k), "curva": curva,
        "indice_rand_ajustado": float(adjusted_rand_score(
            km.labels_, ward.labels_)),
        "varianza_explicada_plano": [float(v) for v in
                                     pca.explained_variance_ratio_],
        "cargas_componentes": {
            v: [float(pca.components_[0][i]), float(pca.components_[1][i])]
            for i, v in enumerate(VARIABLES_PERFIL)},
        "enlace_ward": linkage(x, method="ward").tolist(),
    }
    return salida, resumen
