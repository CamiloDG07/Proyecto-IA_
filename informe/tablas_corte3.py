"""Tablas, bloques «Cómo leerla» y cifras del informe del Corte 3.

Uso:
    python informe/tablas_corte3.py

Lee los resultados guardados en outputs/datos/ y escribe:

    outputs/tablas/tabla_c3_*.tex      tablas con el estilo único
    outputs/lecturas/lectura_c3_*.tex  bloques «Cómo leerla»
    outputs/lecturas/texto_c3_cifras.tex
        una orden de LaTeX por cada cifra que el informe cita en el texto,
        de modo que ninguna cifra del informe se escribe a mano.
"""
import sys
from pathlib import Path
if True:  # carpetas de código en el path
    sys.path[:0] = [str(Path(__file__).resolve().parents[1] / c)
                    for c in ("src", "experimentos", "informe", "pruebas")]
import json

import pandas as pd

import agente_predictivo
from figuras_corte3 import CASO, MES_EJEMPLO, ROTULO_VARIABLE
from formato_latex import tabla
from modelo_tiempo import normalizar
from rutas import RAIZ, SALIDA

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
ESTADO = {"vigente": "vigente", "historico": "terminada",
          "sin_dato": "sin dato"}


def leer_json(nombre, carpeta=None):
    with open((carpeta or SALIDA) / nombre, encoding="utf-8") as f:
        return json.load(f)


def miles(valor, decimales=0):
    """Número con espacio fino de LaTeX como separador de miles."""
    return f"{valor:,.{decimales}f}".replace(",", "\\,")


def mes_largo(clave):
    anio, mes = clave.split("-")
    return f"{MESES[int(mes) - 1]} de {anio}"


def horas(minutos):
    h, m = divmod(int(minutos + 0.5), 60)
    return f"{h} h {m:02d} min"


def escribir(nombre, lineas):
    texto = lineas if isinstance(lineas, str) else "\n".join(lineas)
    (SALIDA / nombre).write_text(texto + "\n", encoding="utf-8")


def lectura(nombre, estructura, que_se_ve, por_que):
    escribir(f"lectura_c3_{nombre}.tex",
             "\\comoleerla{" + estructura + "}\n{" + que_se_ve + "}\n{"
             + por_que + "}")


def cargar():
    return {
        "depuracion": leer_json("depuracion_trafico.json"),
        "resultados": leer_json("resultados_corte3.json"),
        "pronostico": leer_json("pronostico_red.json"),
        "config": leer_json("config_tiempo.json", RAIZ)["insumos"],
        "tabla": pd.read_csv(SALIDA / "trafico_peaje_mes.csv",
                             parse_dates=["mes"]),
        "grupos": pd.read_csv(SALIDA / "agrupamiento_peajes.csv"),
        "tiempos": pd.read_csv(SALIDA / "tiempo_tramo_mes.csv"),
    }


# ------------------------------------------------------------ tablas
def tabla_depuracion(d):
    p = d["depuracion"]
    filas = [
        ("Filas del archivo (peaje, mes y categoría)", p["filas_crudas"]),
        ("Filas con código sin clase vehicular (excluidas)",
         p["filas_sin_clase_vehicular"]),
        ("Filas tras agregar por peaje y mes", p["filas_peaje_mes"]),
        ("Meses sin tránsito (excluidos)", p["meses_sin_transito"]),
        ("Meses anómalos (excluidos)", p["meses_anomalos"]),
        ("Meses parciales de borde (excluidos)",
         p["meses_parciales_de_borde"]),
        ("Filas del conjunto depurado", p["filas_depuradas"]),
        ("Filas con todos los rezagos (modelables)", p["filas_modelables"]),
    ]
    escribir("tabla_c3_depuracion.tex", tabla(
        "lr", ["Paso & Filas \\\\"],
        [f"{texto} & {miles(n)} \\\\" for texto, n in filas]))


def tabla_particion(d):
    p = d["resultados"]["particion"]
    nombres = {"entrenamiento": "Entrenamiento", "validacion": "Validación",
               "prueba": "Prueba"}
    escribir("tabla_c3_particion.tex", tabla(
        "llrr", ["Conjunto & Periodo & Filas & Peajes \\\\"],
        [f"{nombres[c]} & {p[c]['desde']} a {p[c]['hasta']} & "
         f"{miles(p[c]['filas'])} & {p[c]['peajes']} \\\\"
         for c in nombres]))


def texto_hiper(h):
    nombres = {"max_depth": "profundidad máxima",
               "min_samples_leaf": "mínimo por hoja",
               "n_estimators": "árboles", "max_features": "variables",
               "learning_rate": "tasa de aprendizaje",
               "max_iter": "iteraciones", "C": "$C$"}
    if not h:
        return "sin hiperparámetros"
    partes = []
    for clave, valor in h.items():
        if clave == "max_features":
            valor = f"{100 * valor:.0f}\\,\\% por división"
        elif valor is None:
            valor = "sin límite"
        partes.append(f"{nombres[clave]} {valor}")
    return ", ".join(partes)


def tabla_regresion(d):
    r = d["resultados"]["regresion"]
    cuerpo, hiper = [], []
    for nombre, m in r["modelos"].items():
        p = m["prueba"]
        rotulo = nombre + (" (elegido)" if nombre == r["mejor"] else "")
        cuerpo.append(
            f"{rotulo} & {miles(m['validacion']['mae'], 1)} & "
            f"{miles(p['mae'], 1)} & {miles(p['rmse'], 1)} & "
            f"{p['r2']:.4f} & {p['error_porcentual_mediano']:.2f} \\\\")
        if m["tipo"] == "modelo":
            hiper.append(f"{nombre} & {m['combinaciones_probadas']} & "
                         f"{texto_hiper(m['hiperparametros'])} \\\\")
    escribir("tabla_c3_regresion.tex", tabla(
        ">{\\raggedright\\arraybackslash}p{4.6cm}rrrrr",
        ["Método & MAE val. & MAE & RMSE & $R^2$ & EPM (\\%) \\\\"],
        cuerpo))
    escribir("tabla_c3_hiper_regresion.tex", tabla(
        "lr>{\\raggedright\\arraybackslash}p{7.2cm}",
        ["Modelo & Combinaciones & Hiperparámetros elegidos \\\\"], hiper))


def tabla_clasificacion(d):
    c = d["resultados"]["clasificacion"]
    cuerpo, hiper = [], []
    for nombre, m in c["modelos"].items():
        p = m["prueba"]
        rotulo = nombre + (" (elegido)" if nombre == c["mejor"] else "")
        validacion = (f"{100 * m['validacion']['f1_macro']:.2f}"
                      if "validacion" in m else "no aplica")
        cuerpo.append(f"{rotulo} & {validacion} & "
                      f"{100 * p['exactitud']:.2f} & "
                      f"{100 * p['f1_macro']:.2f} \\\\")
        if m["tipo"] == "modelo":
            hiper.append(f"{nombre} & {m['combinaciones_probadas']} & "
                         f"{texto_hiper(m['hiperparametros'])} \\\\")
    escribir("tabla_c3_clasificacion.tex", tabla(
        ">{\\raggedright\\arraybackslash}p{6.2cm}rrr",
        ["Método & F1 macro val. (\\%) & Exactitud (\\%) & "
         "F1 macro (\\%) \\\\"], cuerpo))
    escribir("tabla_c3_hiper_clasificacion.tex", tabla(
        "lr>{\\raggedright\\arraybackslash}p{7.2cm}",
        ["Modelo & Combinaciones & Hiperparámetros elegidos \\\\"], hiper))
    por_clase = c["modelos"][c["mejor"]]["prueba"]["por_clase"]
    escribir("tabla_c3_por_clase.tex", tabla(
        "lrrrr",
        ["Nivel & Precisión (\\%) & Exhaustividad (\\%) & F1 (\\%) & "
         "Casos \\\\"],
        [f"{nivel.capitalize()} & {100 * v['precision']:.2f} & "
         f"{100 * v['exhaustividad']:.2f} & {100 * v['f1']:.2f} & "
         f"{v['casos']} \\\\" for nivel, v in por_clase.items()]))


def peajes_de_red(d):
    return {normalizar(t["peaje"]) for t in d["pronostico"]["tramos"]
            if t["id_peaje"]}


def perfil_grupos(d):
    """Media de cada variable y peajes de la red por grupo de K-medias."""
    grupos = d["grupos"]
    de_red = peajes_de_red(d)
    filas = []
    for g, parte in grupos.groupby("grupo_k_medias"):
        en_red = [p.title() for p in parte["peaje"]
                  if normalizar(p) in de_red]
        filas.append({
            "grupo": int(g), "peajes": len(parte),
            "transito": parte["transito_diario_medio"].mean(),
            "carga": 100 * parte["participacion_carga"].mean(),
            "buses": 100 * parte["participacion_buses"].mean(),
            "amplitud": parte["amplitud_estacional"].mean(),
            "en_red": en_red})
    return filas


def tabla_grupos(d):
    filas = perfil_grupos(d)
    escribir("tabla_c3_grupos.tex", tabla(
        "lrrrrr",
        ["Grupo & Peajes & Tránsito (veh/día) & Carga (\\%) & "
         "Buses (\\%) & Amplitud \\\\"],
        [f"Grupo {f['grupo']} & {f['peajes']} & {miles(f['transito'])} & "
         f"{f['carga']:.1f} & {f['buses']:.1f} & {f['amplitud']:.2f} \\\\"
         for f in filas]))
    escribir("tabla_c3_grupos_red.tex", tabla(
        "lr>{\\raggedright\\arraybackslash}p{9.4cm}",
        ["Grupo & En la red & Peajes de la red \\\\"],
        [f"Grupo {f['grupo']} & {len(f['en_red'])} & "
         f"{', '.join(f['en_red']) or 'ninguno'} \\\\" for f in filas]))


def tabla_supuestos(d):
    c = d["config"]
    filas = [
        ("Velocidad libre", f"{c['velocidad_libre_kmh']['valor']} km/h",
         "velocidad_libre_kmh"),
        ("$\\alpha$ de la función BPR", f"{c['bpr_alfa']['valor']}",
         "bpr_alfa"),
        ("$\\beta$ de la función BPR", f"{c['bpr_beta']['valor']}",
         "bpr_beta"),
        ("Factor de hora pico", f"{c['factor_hora_pico']['valor']:.2f}",
         "factor_hora_pico"),
        ("Capacidad, calzada sencilla",
         f"{miles(c['capacidad_calzada_sencilla_veh_h']['valor'])} veh/h",
         "capacidad_calzada_sencilla_veh_h"),
        ("Capacidad, doble calzada",
         f"{miles(c['capacidad_doble_calzada_veh_h']['valor'])} veh/h",
         "capacidad_doble_calzada_veh_h"),
        ("Banda de doble calzada",
         "{} a {}".format(*c["banda_doble_calzada"]["valor"]),
         "banda_doble_calzada"),
    ]
    escribir("tabla_c3_supuestos.tex", tabla(
        "lrl", ["Insumo & Valor & Estado \\\\"],
        [f"{texto} & {valor} & {c[clave]['estado']} \\\\"
         for texto, valor, clave in filas]))


def tabla_red(d):
    cuerpo = []
    for t in d["pronostico"]["tramos"]:
        if not t["peaje"]:
            continue
        dato = t["meses"].get(MES_EJEMPLO)
        serie = ESTADO[t["estado"]]
        if t["estado"] == "historico":
            serie += f" ({t['ultimo_mes']})"
        calzada = "doble" if t["doble_calzada"] else "sencilla"
        if dato:
            transito = miles(dato["transito_usado"])
            nivel = f"{dato['clase']} ({dato['saturacion']:.2f})"
        else:
            transito = nivel = "sin dato"
        cuerpo.append(f"{t['origen']} - {t['destino']} & "
                      f"{t['peaje'].title()} & {serie} & {calzada} & "
                      f"{transito} & {nivel} \\\\")
    escribir("tabla_c3_red.tex", tabla(
        ">{\\raggedright\\arraybackslash}p{3.5cm}"
        ">{\\raggedright\\arraybackslash}p{2.0cm}"
        ">{\\raggedright\\arraybackslash}p{2.5cm}lr"
        ">{\\raggedright\\arraybackslash}p{2.1cm}",
        ["Tramo & Peaje & Serie & Calzada & Veh/día & Nivel ($v/c$) \\\\"],
        cuerpo))


def caso_por_mes(d):
    return {mes: agente_predictivo.recomendar(*CASO, mes, d["pronostico"])
            for mes in d["pronostico"]["meses_pronostico"]}


def tabla_caso(d, casos):
    r = casos[MES_EJEMPLO]
    filas = [("Recomendada (por Bogotá)", r["elegida"])]
    filas += [("Alternativa (por Santander)", a) for a in r["alternativas"]]
    escribir("tabla_c3_caso.tex", tabla(
        "lrrrrr",
        ["Ruta & km & Tiempo & Demora (min) & En alto & Sin dato \\\\"],
        [f"{nombre} & {x['distancia_km']:.2f} & {horas(x['tiempo_min'])} & "
         f"{x['demora_min']:.2f} & {x['tramos_por_nivel']['alto']} & "
         f"{x['tramos_por_nivel']['sin dato']} \\\\" for nombre, x in filas]))
    escribir("tabla_c3_caso_meses.tex", tabla(
        "lrrrrr",
        ["Mes & Tiempo (min) & Demora (min) & Alto & Medio & Bajo \\\\"],
        [f"{mes_largo(mes).capitalize()} & {x['elegida']['tiempo_min']:.1f}"
         f" & {x['elegida']['demora_min']:.2f} & "
         f"{x['elegida']['tramos_por_nivel']['alto']} & "
         f"{x['elegida']['tramos_por_nivel']['medio']} & "
         f"{x['elegida']['tramos_por_nivel']['bajo']} \\\\"
         for mes, x in casos.items()]))


def tabla_tiempo(d):
    t = d["resultados"]["tiempo"]
    filas = [
        ("Filas tramo-mes con tránsito observado",
         miles(t["filas_tramo_mes"])),
        ("Saturación mediana", f"{t['saturacion_mediana']:.2f}"),
        ("Saturación máxima", f"{t['saturacion_maxima']:.2f}"),
        ("Factor BPR máximo", f"{t['factor_bpr_maximo']:.4f}"),
        ("Mayor demora de un tramo en un mes (min)",
         f"{t['demora_maxima_min']:.2f}"),
        ("Casos tramo-mes en la prueba", str(t["casos_prueba"])),
        ("Error absoluto medio del tiempo en la prueba (min)",
         f"{t['mae_min']:.3f}"),
        ("Error máximo del tiempo en la prueba (min)",
         f"{t['error_maximo_min']:.2f}"),
    ]
    escribir("tabla_c3_tiempo.tex", tabla(
        "lr", ["Medida & Valor \\\\"],
        [f"{texto} & {valor} \\\\" for texto, valor in filas]))


# ----------------------------------------------------------- cifras
def cifras(d, casos):
    """Diccionario {orden de LaTeX: texto} con las cifras del informe."""
    p, r = d["depuracion"], d["resultados"]
    tabla_, reg, cla = d["tabla"], r["regresion"], r["clasificacion"]
    agr, tie, red = r["agrupamiento"], r["tiempo"], r["red"]
    modelos = reg["modelos"]
    mejor = modelos[reg["mejor"]]["prueba"]
    persistencia = modelos["Persistencia (mes anterior)"]["prueba"]
    estacional = modelos[
        "Estacional (mismo mes del año anterior)"]["prueba"]
    por_mes = tabla_.groupby("mes")["transito_diario"].sum()
    minimo = por_mes.idxmin()
    previo = minimo - pd.DateOffset(years=1)
    curva = pd.DataFrame(reg["error_por_horizonte"])
    gana = int((curva["modelo"] < curva[["persistencia", "estacional"]]
                .min(axis=1)).sum())
    k = next(c for c in agr["curva"] if c["k"] == agr["k"])
    mejor_cla = cla["modelos"][cla["mejor"]]["prueba"]
    pers_cla = cla["modelos"][
        "Persistencia (clase del mes anterior)"]["prueba"]
    derivada = cla["modelos"]["Clase a partir de la regresión"]["prueba"]
    matriz = mejor_cla["matriz_confusion"]
    caso = casos[MES_EJEMPLO]
    elegida, otra = caso["elegida"], caso["alternativas"][0]
    demoras = [x["elegida"]["demora_min"] for x in casos.values()]
    importancias = list(reg["importancias"].items())
    perfil = perfil_grupos(d)
    mayor = max(perfil, key=lambda f: f["transito"])
    estacional_g = max(perfil, key=lambda f: f["amplitud"])
    con_peaje = sum(1 for t in d["pronostico"]["tramos"] if t["peaje"])
    return {
        "FilasCrudas": miles(p["filas_crudas"]),
        "PeajesCrudos": str(p["peajes_crudos"]),
        "Categorias": str(p["categorias_crudas"]),
        "PrimerMes": mes_largo(p["primer_mes"]),
        "UltimoMes": mes_largo(p["ultimo_mes"]),
        "FilasSinClase": miles(p["filas_sin_clase_vehicular"]),
        "TransitoSinClase": f"{p['transito_sin_clase_pct']:.2f}",
        "PctLivianos": f"{p['transito_por_grupo_pct']['livianos']:.1f}",
        "PctBuses": f"{p['transito_por_grupo_pct']['buses']:.1f}",
        "PctCarga": f"{p['transito_por_grupo_pct']['carga']:.1f}",
        "PctUnica": f"{p['transito_por_grupo_pct']['unica']:.1f}",
        "FilasPeajeMes": miles(p["filas_peaje_mes"]),
        "MesesSinTransito": str(p["meses_sin_transito"]),
        "MesesAnomalos": str(p["meses_anomalos"]),
        "MesesParciales": str(p["meses_parciales_de_borde"]),
        "UmbralAnomalo": f"{100 * p['umbral_anomalo']:.0f}",
        "UmbralParcial": f"{100 * p['umbral_parcial']:.0f}",
        "FilasDepuradas": miles(p["filas_depuradas"]),
        "FilasModelables": miles(p["filas_modelables"]),
        "PeajesModelables": str(p["peajes_modelables"]),
        "TransitoMediano": miles(tabla_["transito_diario"].median()),
        "TransitoMaximo": miles(tabla_["transito_diario"].max()),
        "MesMinimo": mes_largo(minimo.strftime("%Y-%m")),
        "CaidaMinimo": f"{100 * (1 - por_mes[minimo] / por_mes[previo]):.0f}",
        "CorteBajo": miles(cla["cortes"][0]),
        "CorteAlto": miles(cla["cortes"][1]),
        "FilasEntrenamiento": miles(r["particion"]["entrenamiento"]["filas"]),
        "FilasValidacion": miles(r["particion"]["validacion"]["filas"]),
        "FilasPrueba": miles(r["particion"]["prueba"]["filas"]),
        "PeajesPrueba": str(r["particion"]["prueba"]["peajes"]),
        "MejorRegresor": reg["mejor"],
        "MaeMejor": miles(mejor["mae"], 1),
        "RmseMejor": miles(mejor["rmse"], 1),
        "RdosMejor": f"{mejor['r2']:.4f}",
        "EpmMejor": f"{mejor['error_porcentual_mediano']:.2f}",
        "MaePersistencia": miles(persistencia["mae"], 1),
        "MaeEstacional": miles(estacional["mae"], 1),
        "EpmPersistencia":
            f"{persistencia['error_porcentual_mediano']:.2f}",
        "MejoraMae": f"{100 * (1 - mejor['mae'] / persistencia['mae']):.0f}",
        "MaeLineal": miles(modelos["Regresión lineal"]["prueba"]["mae"], 1),
        "MaeArbol": miles(modelos["Árbol de decisión"]["prueba"]["mae"], 1),
        "PrimeraVariable": ROTULO_VARIABLE[importancias[0][0]].lower(),
        "PrimeraImportancia": f"{importancias[0][1]:.3f}",
        "SegundaVariable": ROTULO_VARIABLE[importancias[1][0]].lower(),
        "SegundaImportancia": f"{importancias[1][1]:.3f}",
        "HorizonteUno": f"{curva['modelo'].iloc[0]:.1f}",
        "HorizonteDoce": f"{curva['modelo'].iloc[-1]:.1f}",
        "HorizonteMaximo": f"{curva['modelo'].max():.1f}",
        "HorizontesGana": str(gana),
        "EstacionalDoce": f"{curva['estacional'].iloc[-1]:.1f}",
        "PersistenciaMaxima": f"{curva['persistencia'].max():.1f}",
        "MejorClasificador": cla["mejor"],
        "ExactitudMejor": f"{100 * mejor_cla['exactitud']:.2f}",
        "FunoMejor": f"{100 * mejor_cla['f1_macro']:.2f}",
        "ExactitudPersistencia": f"{100 * pers_cla['exactitud']:.2f}",
        "ExactitudDerivada": f"{100 * derivada['exactitud']:.2f}",
        "ErroresClasificacion": str(sum(map(sum, matriz)) - sum(
            matriz[i][i] for i in range(3))),
        "ErroresExtremos": str(matriz[0][2] + matriz[2][0]),
        "PeajesAgrupados": str(agr["peajes"]),
        "KGrupos": str(agr["k"]),
        "SiluetaKmedias": f"{k['silueta_k_medias']:.3f}",
        "SiluetaJerarquico": f"{k['silueta_jerarquico']:.3f}",
        "RandAjustado": f"{agr['indice_rand_ajustado']:.2f}",
        "VarianzaPlano":
            f"{100 * sum(agr['varianza_explicada_plano']):.0f}",
        "GrupoMayor": str(mayor["grupo"]),
        "GrupoMayorTransito": miles(mayor["transito"]),
        "GrupoMayorEnRed": str(len(mayor["en_red"])),
        "GrupoEstacional": str(estacional_g["grupo"]),
        "GrupoEstacionalAmplitud": f"{estacional_g['amplitud']:.2f}",
        "TramosVigentes": str(red["vigente"]),
        "TramosHistoricos": str(red["historico"]),
        "TramosSinDato": str(red["sin_dato"]),
        "TramosConPeaje": str(con_peaje),
        "TramosConSerie": str(red["vigente"] + red["historico"]),
        "TramosDobleCalzada": str(red["doble_calzada"]),
        "FilasTramoMes": miles(tie["filas_tramo_mes"]),
        "SaturacionMediana": f"{tie['saturacion_mediana']:.2f}",
        "SaturacionMaxima": f"{tie['saturacion_maxima']:.2f}",
        "FactorMaximo": f"{tie['factor_bpr_maximo']:.4f}",
        "DemoraMaxima": f"{tie['demora_maxima_min']:.2f}",
        "TramoDemoraMaxima": tie["tramo_factor_maximo"],
        "MesDemoraMaxima": mes_largo(tie["mes_factor_maximo"]),
        "CasosTiempo": str(tie["casos_prueba"]),
        "MaeTiempo": f"{tie['mae_min']:.3f}",
        "ErrorMaximoTiempo": f"{tie['error_maximo_min']:.2f}",
        "MesEjemplo": mes_largo(MES_EJEMPLO),
        "CasoKm": f"{elegida['distancia_km']:.2f}",
        "CasoTiempo": horas(elegida["tiempo_min"]),
        "CasoLibre": horas(elegida["tiempo_libre_min"]),
        "CasoDemora": f"{elegida['demora_min']:.2f}",
        "CasoAlto": str(elegida["tramos_por_nivel"]["alto"]),
        "CasoSinDato": str(elegida["tramos_por_nivel"]["sin dato"]),
        "CasoTramos": str(elegida["saltos"]),
        "CasoExpandidos": str(caso["nodos_expandidos"]),
        "CasoReexpansiones": str(caso["reexpansiones"]),
        "AlternativaKm": f"{otra['distancia_km']:.2f}",
        "AlternativaTiempo": horas(otra["tiempo_min"]),
        "AlternativaAlto": str(otra["tramos_por_nivel"]["alto"]),
        "AlternativaMas":
            f"{otra['tiempo_min'] - elegida['tiempo_min']:.0f}",
        "DemoraMinimaCaso": f"{min(demoras):.2f}",
        "DemoraMaximaCaso": f"{max(demoras):.2f}",
        "VelocidadLibre": str(d["config"]["velocidad_libre_kmh"]["valor"]),
    }


def escribir_cifras(valores):
    lineas = ["% Generado por informe/tablas_corte3.py: no editar a mano."]
    lineas += [f"\\newcommand{{\\ct{nombre}}}{{{valor}}}"
               for nombre, valor in valores.items()]
    escribir("texto_c3_cifras.tex", lineas)


# ---------------------------------------------------------- lecturas
def lecturas(d, c):
    lectura(
        "serie",
        "arriba, la suma del tránsito diario de todos los peajes que "
        "reportan en cada mes; abajo, cuántos peajes reportan.",
        f"el mínimo está en {c['MesMinimo']}, un {c['CaidaMinimo']}\\,\\% "
        "por debajo del mismo mes del año anterior; el número de peajes "
        "cambia con los años.",
        "la suma mezcla el tránsito con la entrada y la salida de peajes "
        "de la fuente, por eso los modelos trabajan por peaje y no con el "
        "total.")
    lectura(
        "distribucion",
        "(a) histograma del tránsito diario de las "
        f"{c['FilasDepuradas']} filas peaje-mes, en escala logarítmica, "
        "con los dos cortes de nivel; (b) tránsito de cada mes dividido "
        "por la media de su año, por mes calendario.",
        f"los cortes están en {c['CorteBajo']} y {c['CorteAlto']} "
        "vehículos por día; diciembre y enero quedan por encima de 1 y "
        "febrero y mayo por debajo.",
        "los cortes son los terciles del entrenamiento; la estacionalidad "
        "justifica usar el mes del año y el rezago de 12 meses como "
        "predictores.")
    lectura(
        "composicion",
        "(a) participación de cada grupo vehicular en el tránsito de cada "
        "año; (b) histograma de la participación de la carga por peaje.",
        f"en todo el periodo los livianos son el {c['PctLivianos']}\\,\\%, "
        f"los buses el {c['PctBuses']}\\,\\% y la carga el "
        f"{c['PctCarga']}\\,\\%; entre peajes la carga varía mucho más que "
        "entre años.",
        "la composición distingue corredores y por eso entra al "
        "agrupamiento; como cambia poco de un mes a otro, pesa poco en la "
        "regresión.")
    lectura(
        "correlacion",
        "correlación de Spearman entre las variables de las filas "
        "modelables; el tránsito y sus rezagos van en logaritmo.",
        "el tránsito del mes se parece mucho al del mes anterior y al de "
        "12 meses antes; la participación de la carga se relaciona de "
        "forma negativa con el tránsito.",
        "esa persistencia explica que las referencias sin aprendizaje ya "
        "sean buenas y que el modelo deba medirse contra ellas.")
    lectura(
        "series_red",
        f"una gráfica por cada uno de los {c['TramosConSerie']} peajes de "
        "la red que están en la fuente; el color indica si la serie llega "
        "al último mes.",
        f"{c['TramosVigentes']} series llegan a {c['UltimoMes']} y "
        f"{c['TramosHistoricos']} terminan antes; todas muestran la caída "
        "de 2020.",
        "solo las series vigentes permiten pronosticar; en las terminadas "
        "el agente usa el mismo mes de su último año y lo rotula como "
        "histórico.")
    lectura(
        "mapa_cobertura",
        "red de 32 tramos sobre el trazado de INVÍAS; el color es el "
        "estado de la serie de tránsito y el grosor, el tipo de calzada.",
        f"{c['TramosVigentes']} tramos tienen serie vigente, "
        f"{c['TramosHistoricos']} serie terminada y {c['TramosSinDato']} "
        f"no tienen dato; {c['TramosDobleCalzada']} son de doble calzada.",
        "el desvío por Santander no tiene ningún tramo con serie "
        "vigente: su tiempo estimado es, en su mayor parte, el tiempo "
        "libre.")
    lectura(
        "regresion",
        "(a) error absoluto medio en la prueba de las dos referencias "
        "(gris) y de los cuatro modelos; (b) tránsito real contra "
        "predicho del modelo elegido, en escala logarítmica.",
        f"el {c['MejorRegresor'].lower()} tiene el menor error, "
        f"{c['MaeMejor']} vehículos por día, un {c['MejoraMae']}\\,\\% "
        f"menos que la persistencia ({c['MaePersistencia']}); los puntos "
        "siguen la diagonal en todo el rango.",
        "el modelo combina el nivel reciente con la estacionalidad, algo "
        "que ninguna de las dos referencias hace por separado.")
    lectura(
        "horizonte",
        "(a) error porcentual mediano del pronóstico recursivo lanzado al "
        "inicio de la prueba, por horizonte, frente a las dos "
        "referencias; (b) aumento del error al permutar cada variable.",
        f"el error del modelo pasa de {c['HorizonteUno']}\\,\\% a un mes a "
        f"{c['HorizonteDoce']}\\,\\% a doce; es el menor de los tres en "
        f"{c['HorizontesGana']} de los 12 horizontes. La variable que más "
        f"pesa es el {c['PrimeraVariable']}.",
        "al encadenar predicciones el error se acumula, y a varios meses "
        "la referencia estacional alcanza al modelo; por eso el "
        "pronóstico de la red se rotula como tal.")
    lectura(
        "clasificacion",
        "(a) exactitud en la prueba de la referencia, los tres "
        "clasificadores y la clase derivada de la regresión; (b) matriz "
        "de confusión del clasificador elegido.",
        f"el {c['MejorClasificador'].lower()} acierta el "
        f"{c['ExactitudMejor']}\\,\\% frente al "
        f"{c['ExactitudPersistencia']}\\,\\% de la persistencia; de sus "
        f"{c['ErroresClasificacion']} errores, {c['ErroresExtremos']} "
        "confunden bajo con alto.",
        "los errores caen entre niveles vecinos, en peajes cuyo tránsito "
        "está cerca de un corte.")
    lectura(
        "silueta",
        "(a) coeficiente de silueta de K-medias y del jerárquico para "
        "cada número de grupos; (b) inercia de K-medias.",
        f"la mayor silueta de K-medias está en k = {c['KGrupos']} "
        f"({c['SiluetaKmedias']}); la curva es casi plana y la inercia no "
        "tiene un codo marcado.",
        "una silueta cercana a 0.27 indica grupos que se tocan: los "
        "peajes forman un continuo y los grupos son una división útil, "
        "no clases separadas.")
    lectura(
        "grupos",
        f"(a) los {c['PeajesAgrupados']} peajes en el plano de las dos "
        "componentes principales, con el grupo de K-medias; el borde "
        "negro marca los peajes de la red; (b) dendrograma del "
        "agrupamiento jerárquico con el corte.",
        f"el plano recoge el {c['VarianzaPlano']}\\,\\% de la varianza; "
        f"los dos métodos coinciden con un índice de Rand ajustado de "
        f"{c['RandAjustado']}.",
        "que dos métodos distintos lleguen a grupos parecidos respalda la "
        "división, aunque la silueta sea baja.")
    lectura(
        "saturacion",
        "saturación en la hora pico de cada tramo de la red con peaje en "
        "la fuente, en todos sus meses observados "
        f"({c['FilasTramoMes']} filas); la línea punteada es la "
        "capacidad.",
        f"la mediana es {c['SaturacionMediana']} y el máximo "
        f"{c['SaturacionMaxima']}, en {c['TramoDemoraMaxima']}; ningún "
        "tramo llega a la capacidad.",
        "con promedios mensuales el volumen queda lejos de la capacidad y "
        "el término de congestión de la función BPR casi no pesa.")
    lectura(
        "pronostico_red",
        f"los {c['TramosVigentes']} peajes de la red con serie vigente "
        "desde 2024: observado, predicción a un mes en la prueba y "
        "pronóstico recursivo de los 12 meses siguientes.",
        "la predicción a un mes sigue los picos de diciembre y enero; el "
        "pronóstico repite esa forma hacia adelante.",
        "el pronóstico hereda la estacionalidad del rezago de 12 meses; "
        "no anticipa cierres ni cambios de operación como los que "
        "cortaron algunas series.")
    lectura(
        "mapa_nivel",
        f"nivel de tránsito previsto de cada tramo en {c['MesEjemplo']} y, "
        f"en trazo grueso, la ruta de menor tiempo estimado de {CASO[0]} "
        f"a {CASO[1]}.",
        f"la ruta mide {c['CasoKm']} km y tarda {c['CasoTiempo']}; "
        f"{c['CasoAlto']} de sus {c['CasoTramos']} tramos tienen tránsito "
        f"alto y {c['CasoSinDato']} no tienen dato.",
        f"la alternativa evita los tramos en alto pero tarda "
        f"{c['AlternativaMas']} minutos más: la distancia decide la ruta "
        "y el nivel de tránsito informa del estado esperado del "
        "recorrido.")
    lectura(
        "t_regresion",
        "una fila por método; MAE val. es el error absoluto medio en la "
        "validación, las demás columnas son de la prueba; EPM es el error "
        "porcentual mediano.",
        "los cuatro modelos superan a las dos referencias en MAE en la "
        f"prueba; el {c['MejorRegresor'].lower()} es el mejor en "
        f"validación y en prueba, con $R^2 = {c['RdosMejor']}$.",
        "el $R^2$ es alto incluso en las referencias porque el tránsito "
        "difiere mucho entre peajes; la comparación útil es el MAE.")
    lectura(
        "t_caso_meses",
        f"la ruta recomendada de {CASO[0]} a {CASO[1]} en cada mes del "
        "pronóstico: tiempo, demora y número de tramos por nivel.",
        f"la demora va de {c['DemoraMinimaCaso']} a "
        f"{c['DemoraMaximaCaso']} minutos; la ruta es la misma los 12 "
        "meses.",
        "lo que cambia de un mes a otro es el nivel de algunos tramos, no "
        "la decisión.")


def main():
    d = cargar()
    casos = caso_por_mes(d)
    for funcion in (tabla_depuracion, tabla_particion, tabla_regresion,
                    tabla_clasificacion, tabla_grupos, tabla_supuestos,
                    tabla_red, tabla_tiempo):
        funcion(d)
    tabla_caso(d, casos)
    valores = cifras(d, casos)
    escribir_cifras(valores)
    lecturas(d, valores)
    print(f"Tablas, lecturas y {len(valores)} cifras del Corte 3 escritas.")
    return valores


if __name__ == "__main__":
    main()
