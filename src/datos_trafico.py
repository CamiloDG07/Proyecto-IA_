"""Depuración del tránsito vehicular de los peajes de la ANI.

Fuente: ANI, Tráfico Vehicular (datos.gov.co, conjunto 8yi9-t44c, licencia
CC BY-SA 4.0), descargado el 16 de noviembre de 2026 ordenado por el
identificador interno de fila. Cada fila es el tránsito de un mes en un
peaje y una categoría de tarifa.

Pasos de la depuración (cada uno deja su conteo en
outputs/datos/depuracion_trafico.json):

 1. Se comprueba el SHA-256 del archivo y que cada fila cubra un mes
    calendario completo.
 2. Se asigna un grupo vehicular a cada código de categoría. La fuente no
    trae diccionario: el grupo sale del número romano del código (I,
    livianos; II, buses; III en adelante, carga), que es la clasificación
    de categorías de peaje que ya usa el proyecto (categoría III, camión
    de dos ejes). El código UNICA (tarifa única) cuenta en el total sin
    grupo. Los códigos sin número romano (EC, ER, EG, EA y POLCA) no
    tienen clase vehicular identificable y se excluyen.
 3. Se agrega a una fila por peaje y mes.
 4. Se quitan los meses sin tránsito y los meses anómalos (tránsito diario
    menor que la fracción UMBRAL_ANOMALO de la mediana del peaje: aperturas,
    cierres o registros parciales) y los meses parciales de borde (meses
    sin mes válido antes o después, es decir, el inicio o el final de la
    serie o de una interrupción, con tránsito diario menor que la fracción
    UMBRAL_PARCIAL de la mediana del peaje).
 5. Se agregan los rezagos del tránsito diario (1, 2, 3, 12 y 13 meses) y
    la composición del mes anterior; solo quedan en el conjunto de
    modelado las filas con todos los rezagos.

Escribe outputs/datos/trafico_peaje_mes.csv (una fila por peaje y mes, con
el indicador `modelable`) y outputs/datos/depuracion_trafico.json.
"""
import hashlib
import json
import re

import numpy as np
import pandas as pd

from rutas import CARGA, SALIDA

ARCHIVO = CARGA / "nuevas" / "trafico_vehicular_ani_8yi9-t44c.csv"
SHA256 = "c9a4dc7a7fc6da90bb2c21ebefbc99353cb80b7493c8eb87df7de5a74b5fb362"
SIN_CLASE = ("EC", "ER", "EG", "EA", "POLCA")
ROMANO = re.compile(r"^(?:E\d?-|EXC)?(IX|VIII|VII|VI|IV|V|III|II|I)")
GRUPOS = ("livianos", "buses", "carga", "unica")
UMBRAL_ANOMALO = 0.10
UMBRAL_PARCIAL = 0.50
REZAGOS = (1, 2, 3, 12, 13)
SALIDA_CSV = "trafico_peaje_mes.csv"
SALIDA_JSON = "depuracion_trafico.json"


def grupo_de(codigo):
    """Grupo vehicular de un código de categoría (None si no tiene)."""
    if codigo == "UNICA":
        return "unica"
    if codigo in SIN_CLASE:
        return None
    hallado = ROMANO.match(codigo)
    if not hallado:
        return None
    romano = hallado.group(1)
    if romano == "I":
        return "livianos"
    return "buses" if romano == "II" else "carga"


def leer_crudo(ruta=ARCHIVO):
    """Lee el archivo de la ANI y comprueba su huella."""
    huella = hashlib.sha256(ruta.read_bytes()).hexdigest()
    if huella != SHA256:
        raise ValueError(f"El archivo {ruta.name} no coincide con la "
                         f"descarga documentada (SHA-256 {huella})")
    return pd.read_csv(ruta, parse_dates=["desde", "hasta"])


def rezago(tabla, columna, meses):
    """Valor de `columna` del mismo peaje `meses` meses antes (NaN si ese
    mes no está en la tabla depurada)."""
    serie = tabla.set_index(["id_peaje", "indice_mes"])[columna]
    claves = pd.MultiIndex.from_arrays(
        [tabla["id_peaje"], tabla["indice_mes"] - meses])
    return serie.reindex(claves).to_numpy()


def agregar_rezagos(tabla):
    """Agrega los rezagos y el indicador `modelable`."""
    tabla = tabla.sort_values(["id_peaje", "indice_mes"]).reset_index(
        drop=True)
    for meses in REZAGOS:
        tabla[f"transito_diario_rezago_{meses}"] = rezago(
            tabla, "transito_diario", meses)
    tabla["participacion_carga_rezago_1"] = rezago(
        tabla, "participacion_carga", 1)
    columnas = [f"transito_diario_rezago_{m}" for m in REZAGOS]
    columnas.append("participacion_carga_rezago_1")
    tabla["modelable"] = tabla[columnas].notna().all(axis=1)
    return tabla


def depurar(crudo):
    """Devuelve la tabla por peaje y mes y el registro de la depuración."""
    registro = {"filas_crudas": int(len(crudo)),
                "peajes_crudos": int(crudo["idpeaje"].nunique()),
                "categorias_crudas": int(crudo["categoriatarifa"].nunique()),
                "primer_mes": crudo["desde"].min().strftime("%Y-%m"),
                "ultimo_mes": crudo["desde"].max().strftime("%Y-%m")}
    fin_de_mes = crudo["desde"] + pd.offsets.MonthEnd(0)
    completos = (crudo["desde"].dt.day == 1) & (crudo["hasta"] == fin_de_mes)
    registro["filas_que_no_cubren_un_mes"] = int((~completos).sum())
    registro["valores_faltantes"] = int(crudo.isna().sum().sum())
    registro["filas_duplicadas"] = int(crudo.duplicated(
        ["idpeaje", "categoriatarifa", "desde"]).sum())
    crudo = crudo[completos].copy()

    crudo["grupo"] = crudo["categoriatarifa"].map(grupo_de)
    total = crudo["cantidadtrafico"].sum()
    excluidas = crudo[crudo["grupo"].isna()]
    registro["filas_sin_clase_vehicular"] = int(len(excluidas))
    registro["transito_sin_clase_pct"] = round(float(
        100 * excluidas["cantidadtrafico"].sum() / total), 4)
    registro["codigos_sin_clase"] = sorted(
        excluidas["categoriatarifa"].unique())
    crudo = crudo[crudo["grupo"].notna()]
    registro["transito_por_grupo_pct"] = {
        g: round(float(100 * crudo.loc[crudo["grupo"] == g,
                                       "cantidadtrafico"].sum()
                       / crudo["cantidadtrafico"].sum()), 2)
        for g in GRUPOS}

    claves = ["idpeaje", "peaje", "desde"]
    tabla = crudo.pivot_table(index=claves, columns="grupo",
                              values="cantidadtrafico", aggfunc="sum",
                              fill_value=0).reset_index()
    for g in GRUPOS:
        if g not in tabla:
            tabla[g] = 0
    otros = crudo.groupby(claves).agg(
        evasores=("cantidadevasores", "sum"),
        exentos=("cantidadexentos787", "sum")).reset_index()
    tarifa = (crudo[crudo["categoriatarifa"] == "I"]
              .groupby(claves)["valortarifa"].max()
              .rename("tarifa_categoria_i_cop").reset_index())
    tabla = tabla.merge(otros, on=claves).merge(tarifa, on=claves,
                                                how="left")
    tabla = tabla.rename(columns={"idpeaje": "id_peaje", "desde": "mes"})
    tabla.columns.name = None
    tabla["transito_mes"] = tabla[list(GRUPOS)].sum(axis=1)
    registro["filas_peaje_mes"] = int(len(tabla))

    sin_transito = tabla["transito_mes"] == 0
    registro["meses_sin_transito"] = int(sin_transito.sum())
    tabla = tabla[~sin_transito].copy()
    tabla["dias_mes"] = tabla["mes"].dt.days_in_month
    tabla["transito_diario"] = tabla["transito_mes"] / tabla["dias_mes"]
    mediana = tabla.groupby("id_peaje")["transito_diario"].transform(
        "median")
    anomalo = tabla["transito_diario"] < UMBRAL_ANOMALO * mediana
    registro["umbral_anomalo"] = UMBRAL_ANOMALO
    registro["meses_anomalos"] = int(anomalo.sum())
    tabla = tabla[~anomalo].copy()

    tabla["indice_mes"] = (tabla["mes"].dt.year * 12
                           + tabla["mes"].dt.month)
    tabla = tabla.sort_values(["id_peaje", "indice_mes"])
    por_peaje = tabla.groupby("id_peaje")["indice_mes"]
    borde = ((por_peaje.diff() != 1) | (por_peaje.diff(-1) != -1))
    mediana = tabla.groupby("id_peaje")["transito_diario"].transform(
        "median")
    parcial = borde & (tabla["transito_diario"] < UMBRAL_PARCIAL * mediana)
    registro["umbral_parcial"] = UMBRAL_PARCIAL
    registro["meses_parciales_de_borde"] = int(parcial.sum())
    tabla = tabla[~parcial].copy()

    tabla["participacion_carga"] = tabla["carga"] / tabla["transito_mes"]
    tabla["participacion_buses"] = tabla["buses"] / tabla["transito_mes"]
    tabla["tasa_evasion"] = tabla["evasores"] / tabla["transito_mes"]
    tabla["anio"] = tabla["mes"].dt.year
    tabla["mes_del_anio"] = tabla["mes"].dt.month
    tabla = agregar_rezagos(tabla)
    registro["filas_depuradas"] = int(len(tabla))
    registro["peajes_depurados"] = int(tabla["id_peaje"].nunique())
    registro["filas_modelables"] = int(tabla["modelable"].sum())
    registro["peajes_modelables"] = int(
        tabla.loc[tabla["modelable"], "id_peaje"].nunique())
    registro["rezagos_meses"] = list(REZAGOS)
    return tabla, registro


def cargar_depurado():
    """Lee la tabla depurada ya escrita."""
    tabla = pd.read_csv(SALIDA / SALIDA_CSV, parse_dates=["mes"])
    return tabla


def main():
    tabla, registro = depurar(leer_crudo())
    registro["sha256"] = SHA256
    registro["archivo"] = ARCHIVO.name
    salida = tabla.copy()
    salida["mes"] = salida["mes"].dt.strftime("%Y-%m-%d")
    reales = salida.select_dtypes("float").columns
    salida[reales] = salida[reales].round(6)
    salida.to_csv(SALIDA / SALIDA_CSV, index=False, lineterminator="\n")
    with open(SALIDA / SALIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(registro, f, ensure_ascii=False, indent=1)
    for clave, valor in registro.items():
        print(f"{clave}: {valor}")
    print(f"Tránsito diario: mediana {np.median(tabla.transito_diario):.0f}"
          f", máximo {tabla.transito_diario.max():.0f} vehículos por día")


if __name__ == "__main__":
    main()
