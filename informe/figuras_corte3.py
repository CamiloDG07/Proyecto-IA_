"""Figuras del informe del Corte 3, desde los datos guardados en outputs/.

Uso:
    python informe/figuras_corte3.py

No entrena ningún modelo: lee la tabla depurada y los resultados que escribe
experimentos/experimentos_corte3.py. Escribe outputs/figuras/c3_*.{png,pdf}
al ancho de texto de los informes; la letra mínima es de 7 puntos.
"""
import sys
from pathlib import Path
if True:  # carpetas de código en el path
    sys.path[:0] = [str(Path(__file__).resolve().parents[1] / c)
                    for c in ("src", "experimentos", "informe", "pruebas")]
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from scipy.cluster.hierarchy import dendrogram  # noqa: E402

import agente_predictivo  # noqa: E402
import mapa_geografico as mg  # noqa: E402
from build_graph import construir_grafo  # noqa: E402
from modelo_tiempo import normalizar  # noqa: E402
from rutas import SALIDA  # noqa: E402

ANCHO = mg.ANCHO_IN
FUENTE = mg.FUENTE
TINTA, TINTA_2 = mg.TINTA, mg.TINTA_2
AZUL, NARANJA = mg.AZUL, mg.NARANJA
VERDE, AMARILLO, MORADO = "#1baf7a", "#eda100", "#7a5cc9"
GRIS = mg.GRIS_VIA
COLOR_NIVEL = {"bajo": VERDE, "medio": AMARILLO, "alto": NARANJA}
COLOR_GRUPO = [AZUL, NARANJA, VERDE, AMARILLO, MORADO, GRIS, TINTA,
               "#c0504d"]
COLOR_ESTADO = {"vigente": AZUL, "historico": AMARILLO, "sin_dato": GRIS}
ROTULO_ESTADO = {"vigente": "Serie vigente (hasta mayo de 2026)",
                 "historico": "Serie terminada",
                 "sin_dato": "Sin peaje en la fuente"}
MES_EJEMPLO = "2026-12"
CASO = ("Duitama", "Puente Nacional")
ABREVIADO = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep",
             "oct", "nov", "dic"]

plt.rcParams.update({
    "font.size": FUENTE, "axes.titlesize": FUENTE + 1,
    "axes.labelsize": FUENTE, "xtick.labelsize": FUENTE,
    "ytick.labelsize": FUENTE, "legend.fontsize": FUENTE,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": TINTA_2, "axes.labelcolor": TINTA,
    "xtick.color": TINTA_2, "ytick.color": TINTA_2,
    "axes.facecolor": mg.SUPERFICIE, "figure.facecolor": mg.SUPERFICIE,
    "axes.grid": True, "grid.color": "#e4e2dc", "grid.linewidth": 0.6,
})


def leer_json(nombre):
    with open(SALIDA / nombre, encoding="utf-8") as f:
        return json.load(f)


def cargar():
    tabla = pd.read_csv(SALIDA / "trafico_peaje_mes.csv",
                        parse_dates=["mes"])
    return {"tabla": tabla,
            "resultados": leer_json("resultados_corte3.json"),
            "pronostico": leer_json("pronostico_red.json"),
            "prueba": pd.read_csv(SALIDA / "predicciones_prueba.csv"),
            "grupos": pd.read_csv(SALIDA / "agrupamiento_peajes.csv"),
            "tiempos": pd.read_csv(SALIDA / "tiempo_tramo_mes.csv")}


def miles(valor):
    return f"{valor:,.0f}".replace(",", " ")


def guardar(fig, nombre):
    fig.savefig(SALIDA / f"{nombre}.png", dpi=200)
    fig.savefig(SALIDA / f"{nombre}.pdf")
    plt.close(fig)


def corto(nombre):
    return nombre.split(" (")[0]


# ------------------------------------------------- análisis exploratorio
def fig_serie(d):
    tabla = d["tabla"]
    por_mes = tabla.groupby("mes").agg(
        transito=("transito_diario", "sum"), peajes=("id_peaje", "nunique"))
    fig, (a, b) = plt.subplots(2, 1, figsize=(ANCHO, 4.2), sharex=True,
                               height_ratios=[2, 1])
    a.plot(por_mes.index, por_mes["transito"] / 1000, color=AZUL, lw=1.4)
    a.set_ylabel("Tránsito diario, suma de\nlos peajes (miles de veh)")
    minimo = por_mes["transito"].idxmin()
    a.annotate(f"{minimo:%Y-%m}", (minimo, por_mes["transito"].min() / 1000),
               xytext=(8, 2), textcoords="offset points", fontsize=FUENTE,
               color=TINTA)
    b.step(por_mes.index, por_mes["peajes"], color=TINTA_2, lw=1.2,
           where="mid")
    b.set_ylabel("Peajes que\nreportan")
    b.set_xlabel("Mes")
    fig.tight_layout()
    return fig


def fig_distribucion(d):
    tabla = d["tabla"]
    cortes = d["resultados"]["clasificacion"]["cortes"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(ANCHO, 2.9))
    limites = np.logspace(np.log10(tabla["transito_diario"].min()),
                          np.log10(tabla["transito_diario"].max()), 45)
    a.hist(tabla["transito_diario"], bins=limites, color=AZUL, alpha=0.85)
    a.set_xscale("log")
    for corte in cortes:
        a.axvline(corte, color=NARANJA, lw=1.2, ls="--")
    a.set_xlabel("Tránsito diario del peaje en el mes (veh/día)")
    a.set_ylabel("Filas peaje-mes")
    a.set_title("(a) Distribución y cortes de nivel")
    util = tabla[tabla["anio"] != 2020].copy()
    completos = util.groupby(["id_peaje", "anio"])["mes"].transform("count")
    util = util[completos == 12]
    util["indice"] = util["transito_diario"] / util.groupby(
        ["id_peaje", "anio"])["transito_diario"].transform("mean")
    cajas = [util.loc[util["mes_del_anio"] == m, "indice"]
             for m in range(1, 13)]
    b.boxplot(cajas, showfliers=False, widths=0.6,
              medianprops=dict(color=NARANJA, lw=1.4),
              boxprops=dict(color=TINTA_2), whiskerprops=dict(color=TINTA_2),
              capprops=dict(color=TINTA_2))
    b.axhline(1, color=TINTA_2, lw=0.8)
    b.set_xticks(range(1, 13), ABREVIADO)
    b.set_ylabel("Tránsito del mes / media del año")
    b.set_title("(b) Estacionalidad")
    fig.tight_layout()
    return fig


def fig_composicion(d):
    tabla = d["tabla"]
    anual = tabla.groupby("anio")[["livianos", "buses", "carga",
                                   "unica"]].sum()
    partes = 100 * anual.div(anual.sum(axis=1), axis=0)
    fig, (a, b) = plt.subplots(1, 2, figsize=(ANCHO, 2.9))
    base = np.zeros(len(partes))
    for columna, nombre, color in (
            ("livianos", "Livianos (I)", AZUL), ("buses", "Buses (II)",
                                                 AMARILLO),
            ("carga", "Carga (III o más)", NARANJA),
            ("unica", "Tarifa única", GRIS)):
        a.bar(partes.index, partes[columna], bottom=base, color=color,
              label=nombre, width=0.8)
        base += partes[columna].to_numpy()
    a.set_ylabel("Participación en el tránsito (%)")
    a.set_xlabel("Año")
    a.set_title("(a) Composición por año")
    a.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=2,
             frameon=False)
    por_peaje = tabla.groupby("id_peaje").apply(
        lambda g: 100 * g["carga"].sum() / g["transito_mes"].sum(),
        include_groups=False)
    b.hist(por_peaje, bins=25, color=NARANJA, alpha=0.85)
    b.axvline(por_peaje.median(), color=TINTA, lw=1.2, ls="--")
    b.set_xlabel("Participación de la carga en el peaje (%)")
    b.set_ylabel("Peajes")
    b.set_title("(b) Carga por peaje")
    fig.tight_layout()
    return fig


def fig_correlacion(d):
    tabla = d["tabla"][d["tabla"]["modelable"]]
    columnas = {"transito_diario": "Tránsito diario",
                "transito_diario_rezago_1": "Rezago 1",
                "transito_diario_rezago_12": "Rezago 12",
                "participacion_carga": "Part. carga",
                "participacion_buses": "Part. buses",
                "tasa_evasion": "Tasa de evasión",
                "tarifa_categoria_i_cop": "Tarifa cat. I"}
    datos = tabla[list(columnas)].copy()
    for c in ("transito_diario", "transito_diario_rezago_1",
              "transito_diario_rezago_12"):
        datos[c] = np.log(datos[c])
    matriz = datos.corr(method="spearman").to_numpy()
    fig, ax = plt.subplots(figsize=(ANCHO * 0.72, ANCHO * 0.6))
    imagen = ax.imshow(matriz, cmap="RdBu_r", vmin=-1, vmax=1)
    nombres = list(columnas.values())
    ax.set_xticks(range(len(nombres)), nombres, rotation=40, ha="right")
    ax.set_yticks(range(len(nombres)), nombres)
    ax.grid(False)
    for i in range(len(nombres)):
        for j in range(len(nombres)):
            ax.text(j, i, f"{matriz[i, j]:.2f}", ha="center", va="center",
                    fontsize=FUENTE,
                    color="white" if abs(matriz[i, j]) > 0.6 else TINTA)
    barra = fig.colorbar(imagen, ax=ax, shrink=0.8)
    barra.set_label("Correlación de Spearman")
    fig.tight_layout()
    return fig


def _tramos_con_serie(d):
    return [t for t in d["pronostico"]["tramos"] if t["id_peaje"]]


def fig_series_red(d):
    tabla = d["tabla"]
    tramos = _tramos_con_serie(d)
    columnas = 3
    filas = int(np.ceil(len(tramos) / columnas))
    fig, ejes = plt.subplots(filas, columnas, figsize=(ANCHO, 1.05 * filas),
                             sharex=True)
    for ax, t in zip(ejes.flat, tramos):
        serie = tabla[tabla["id_peaje"] == t["id_peaje"]]
        ax.plot(serie["mes"], serie["transito_diario"] / 1000,
                color=COLOR_ESTADO[t["estado"]], lw=0.9)
        ax.set_title(t["peaje"].title(), fontsize=FUENTE, pad=2)
        ax.set_ylim(bottom=0)
        ax.tick_params(axis="x", labelrotation=45)
    for ax in list(ejes.flat)[len(tramos):]:
        ax.axis("off")
    fig.supylabel("Tránsito diario (miles de veh/día)", fontsize=FUENTE)
    fig.legend(handles=[Line2D([0], [0], color=COLOR_ESTADO[e], lw=1.4,
                               label=ROTULO_ESTADO[e])
                        for e in ("vigente", "historico")],
               loc="upper center", ncol=2, frameon=False)
    fig.tight_layout(h_pad=0.4, w_pad=0.6, rect=(0, 0, 1, 0.97))
    return fig


def _mapa(grafo, color_de, ancho_de, casco=lambda u, v: False):
    trazado = mg.cargar_trazado()
    lon, lat = (-75.25, -71.75), (3.35, 7.65)
    fig, ax = mg.crear_figura(lon, lat, relleno_alto=0.25)
    ax.grid(False)
    mg.preparar_eje(ax, lon, lat)
    mg.rotular_departamentos(ax, lon, lat)
    coord = mg.dibujar_aristas(ax, grafo, trazado, color_de, ancho_de,
                               lambda u, v: 3, casco)
    ax.scatter([coord[n][1] for n in grafo], [coord[n][0] for n in grafo],
               s=16, color=mg.SUPERFICIE, edgecolors=TINTA, lw=0.9, zorder=5)
    mg.rotular_nodos(ax, fig, coord, list(grafo))
    mg.barra_escala(ax, lat, -72.95, 5.15)
    return fig, ax


def fig_mapa_cobertura(d):
    grafo = construir_grafo()
    info = {frozenset((t["origen"], t["destino"])): t
            for t in d["pronostico"]["tramos"]}

    def dato(u, v):
        return info[frozenset((u, v))]

    fig, ax = _mapa(
        grafo, lambda u, v: COLOR_ESTADO[dato(u, v)["estado"]],
        lambda u, v: 3.0 if dato(u, v)["doble_calzada"] else 1.5)
    entradas = [Line2D([0], [0], color=COLOR_ESTADO[e], lw=2,
                       label=ROTULO_ESTADO[e])
                for e in ("vigente", "historico", "sin_dato")]
    entradas += [Line2D([0], [0], color=TINTA_2, lw=3,
                        label="Doble calzada"),
                 Line2D([0], [0], color=TINTA_2, lw=1.5,
                        label="Calzada sencilla")]
    mg.leyenda(ax, entradas, "upper left")
    fig.text(0.01, 0.006, "Fuentes: ANI (tránsito); INVÍAS (trazado); "
             "DANE (límites y nodos).", fontsize=FUENTE, color=TINTA_2,
             ha="left", va="bottom")
    return fig


# ----------------------------------------------------------- modelos
def fig_regresion(d):
    r = d["resultados"]["regresion"]
    prueba = d["prueba"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(ANCHO, 3.0),
                               width_ratios=[1.15, 1])
    nombres = list(r["modelos"])
    valores = [r["modelos"][n]["prueba"]["mae"] for n in nombres]
    colores = [NARANJA if n == r["mejor"] else
               (GRIS if r["modelos"][n]["tipo"] == "referencia" else AZUL)
               for n in nombres]
    posiciones = np.arange(len(nombres))[::-1]
    a.barh(posiciones, valores, color=colores)
    a.set_yticks(posiciones, [corto(n) for n in nombres])
    for y, v in zip(posiciones, valores):
        a.text(v + 6, y, f"{v:.0f}", va="center", fontsize=FUENTE)
    a.set_xlabel("MAE en la prueba (veh/día)")
    a.set_xlim(0, max(valores) * 1.14)
    a.set_title("(a) Error por método")
    a.grid(axis="y", visible=False)
    real = prueba["transito_diario"]
    estimado = prueba[f"transito_{r['mejor']}"]
    b.scatter(real, estimado, s=4, color=AZUL, alpha=0.35, lw=0)
    limites = [real.min() * 0.8, real.max() * 1.2]
    b.plot(limites, limites, color=TINTA, lw=0.8)
    b.set_xscale("log")
    b.set_yscale("log")
    b.set_xlabel("Tránsito real (veh/día)")
    b.set_ylabel("Tránsito predicho (veh/día)")
    b.set_title(f"(b) {r['mejor']}")
    fig.tight_layout()
    return fig


ROTULO_VARIABLE = {
    "log_rezago_1": "Tránsito del mes anterior",
    "log_rezago_2": "Tránsito de hace 2 meses",
    "log_rezago_3": "Tránsito de hace 3 meses",
    "log_rezago_12": "Tránsito de hace 12 meses",
    "log_rezago_13": "Tránsito de hace 13 meses",
    "mes_del_anio": "Mes del año", "dias_mes": "Días del mes",
    "participacion_carga_rezago_1": "Participación de la carga"}


def fig_horizonte(d):
    r = d["resultados"]["regresion"]
    curva = pd.DataFrame(r["error_por_horizonte"])
    fig, (a, b) = plt.subplots(1, 2, figsize=(ANCHO, 2.9))
    for columna, nombre, color, estilo, marca in (
            ("persistencia", "Persistencia", GRIS, "--", "s"),
            ("estacional", "Estacional", VERDE, ":", "^"),
            ("modelo", "Modelo recursivo", NARANJA, "-", "o")):
        a.plot(curva["horizonte"], curva[columna], color=color, ls=estilo,
               marker=marca, ms=3, lw=1.4, label=nombre)
    a.set_xticks(range(1, 13))
    a.set_ylim(0, 1.45 * curva[["persistencia", "estacional",
                                "modelo"]].to_numpy().max())
    a.set_xlabel("Horizonte del pronóstico (meses)")
    a.set_ylabel("Error porcentual mediano (%)")
    a.set_title("(a) Pronóstico recursivo de 12 meses")
    a.legend(framealpha=0.95)
    nombres = list(r["importancias"])[::-1]
    b.barh([ROTULO_VARIABLE[n] for n in nombres],
           [r["importancias"][n] for n in nombres], color=AZUL)
    b.set_xscale("log")
    b.set_xlabel("Aumento del MAE al permutar (log)")
    b.set_title("(b) Importancia por permutación")
    b.grid(axis="y", visible=False)
    fig.tight_layout()
    return fig


def fig_clasificacion(d):
    c = d["resultados"]["clasificacion"]
    fig, (a, b) = plt.subplots(1, 2, figsize=(ANCHO, 2.9),
                               width_ratios=[1.2, 1])
    nombres = list(c["modelos"])
    valores = [100 * c["modelos"][n]["prueba"]["exactitud"]
               for n in nombres]
    colores = [NARANJA if n == c["mejor"] else
               (AZUL if c["modelos"][n]["tipo"] == "modelo" else GRIS)
               for n in nombres]
    posiciones = np.arange(len(nombres))[::-1]
    a.barh(posiciones, valores, color=colores)
    a.set_yticks(posiciones, [corto(n) for n in nombres])
    for y, v in zip(posiciones, valores):
        a.text(v + 0.1, y, f"{v:.1f}", va="center", fontsize=FUENTE)
    a.set_xlim(min(valores) - 3, max(valores) + 1.5)
    a.set_xlabel("Exactitud en la prueba (%)")
    a.set_title("(a) Exactitud por método")
    a.grid(axis="y", visible=False)
    matriz = np.array(c["modelos"][c["mejor"]]["prueba"]["matriz_confusion"])
    b.imshow(matriz, cmap="Blues")
    b.grid(False)
    b.set_xticks(range(3), c["clases"])
    b.set_yticks(range(3), c["clases"])
    b.set_xlabel("Nivel predicho")
    b.set_ylabel("Nivel real")
    for i in range(3):
        for j in range(3):
            b.text(j, i, str(matriz[i, j]), ha="center", va="center",
                   fontsize=FUENTE + 1,
                   color="white" if matriz[i, j] > matriz.max() / 2
                   else TINTA)
    b.set_title(f"(b) {c['mejor']}")
    fig.tight_layout()
    return fig


def fig_silueta(d):
    a_ = d["resultados"]["agrupamiento"]
    curva = pd.DataFrame(a_["curva"])
    fig, (a, b) = plt.subplots(1, 2, figsize=(ANCHO, 2.7))
    a.plot(curva["k"], curva["silueta_k_medias"], color=AZUL, marker="o",
           ms=3.5, label="K-medias")
    a.plot(curva["k"], curva["silueta_jerarquico"], color=NARANJA,
           marker="s", ms=3.5, ls="--", label="Jerárquico (Ward)")
    a.axvline(a_["k"], color=TINTA_2, lw=0.8, ls=":")
    a.set_ylim(bottom=0)
    a.set_xlabel("Número de grupos (k)")
    a.set_ylabel("Coeficiente de silueta")
    a.set_title("(a) Silueta")
    a.legend(framealpha=0.95)
    b.plot(curva["k"], curva["inercia"], color=AZUL, marker="o", ms=3.5)
    b.axvline(a_["k"], color=TINTA_2, lw=0.8, ls=":")
    b.set_xlabel("Número de grupos (k)")
    b.set_ylabel("Inercia de K-medias")
    b.set_title("(b) Codo")
    fig.tight_layout()
    return fig


def fig_grupos(d):
    grupos = d["grupos"]
    resumen = d["resultados"]["agrupamiento"]
    de_red = {normalizar(t["peaje"]) for t in _tramos_con_serie(d)}
    es_red = grupos["peaje"].map(normalizar).isin(de_red)
    fig, (a, b) = plt.subplots(1, 2, figsize=(ANCHO, 3.2))
    for g in sorted(grupos["grupo_k_medias"].unique()):
        parte = grupos[grupos["grupo_k_medias"] == g]
        a.scatter(parte["componente_1"], parte["componente_2"], s=14,
                  color=COLOR_GRUPO[g - 1], alpha=0.75, lw=0,
                  label=f"Grupo {g} ({len(parte)})")
    a.scatter(grupos.loc[es_red, "componente_1"],
              grupos.loc[es_red, "componente_2"], s=34, facecolors="none",
              edgecolors=TINTA, lw=0.9, label="Peaje de la red")
    varianza = resumen["varianza_explicada_plano"]
    a.set_xlabel(f"Componente 1 ({100 * varianza[0]:.0f} % de la varianza)")
    a.set_ylabel(f"Componente 2 ({100 * varianza[1]:.0f} %)")
    a.set_title("(a) K-medias en el plano principal")
    a.legend(framealpha=0.95, loc="best")
    enlace = np.array(resumen["enlace_ward"])
    corte = (enlace[-resumen["k"], 2] + enlace[-resumen["k"] + 1, 2]) / 2
    dendrogram(enlace, ax=b, no_labels=True, color_threshold=corte,
               above_threshold_color=TINTA_2)
    b.axhline(corte, color=NARANJA, lw=1, ls="--")
    b.set_ylabel("Distancia de enlace (Ward)")
    b.set_xlabel(f"Peajes ({resumen['peajes']})")
    b.set_title(f"(b) Dendrograma, corte en k = {resumen['k']}")
    b.grid(False)
    fig.tight_layout()
    return fig


# -------------------------------------------------------- integración
def fig_saturacion(d):
    tiempos = d["tiempos"].copy()
    tiempos["tramo"] = tiempos["origen"] + " - " + tiempos["destino"]
    orden = tiempos.groupby("tramo")["saturacion"].median().sort_values()
    doble = tiempos.groupby("tramo")["doble_calzada"].first()
    fig, ax = plt.subplots(figsize=(ANCHO, 4.3))
    cajas = ax.boxplot([tiempos.loc[tiempos["tramo"] == t, "saturacion"]
                        for t in orden.index], orientation="horizontal",
                       widths=0.6,
                       patch_artist=True, showfliers=True,
                       flierprops=dict(marker=".", ms=2, mec=TINTA_2),
                       medianprops=dict(color=TINTA, lw=1.1))
    for caja, tramo in zip(cajas["boxes"], orden.index):
        caja.set(facecolor=AZUL if doble[tramo] else AMARILLO, alpha=0.8,
                 edgecolor=TINTA_2)
    ax.set_yticks(range(1, len(orden) + 1), orden.index)
    ax.axvline(1, color=NARANJA, lw=1.2, ls="--")
    ax.set_xlim(0, 1.05)
    ax.set_xlabel("Saturación en la hora pico (volumen / capacidad), "
                  "todos los meses observados")
    ax.grid(axis="y", visible=False)
    ax.legend(handles=[
        plt.Rectangle((0, 0), 1, 1, fc=AZUL, alpha=0.8,
                      label="Doble calzada"),
        plt.Rectangle((0, 0), 1, 1, fc=AMARILLO, alpha=0.8,
                      label="Calzada sencilla"),
        Line2D([0], [0], color=NARANJA, ls="--", label="Capacidad")],
        loc="lower right", framealpha=0.95)
    fig.tight_layout()
    return fig


def fig_pronostico_red(d):
    tabla = d["tabla"]
    tramos = [t for t in _tramos_con_serie(d) if t["estado"] == "vigente"]
    inicio = pd.Timestamp("2024-01-01")
    columnas = 3
    filas = int(np.ceil(len(tramos) / columnas))
    fig, ejes = plt.subplots(filas, columnas, figsize=(ANCHO, 1.2 * filas),
                             sharex=True)
    for ax, t in zip(ejes.flat, tramos):
        serie = tabla[(tabla["id_peaje"] == t["id_peaje"])
                      & (tabla["mes"] >= inicio)]
        ax.plot(serie["mes"], serie["transito_diario"] / 1000, color=TINTA,
                lw=0.9)
        for origen, color in (("prueba", AZUL), ("pronostico", NARANJA)):
            puntos = [(pd.Timestamp(m + "-01"), v["transito_usado"] / 1000)
                      for m, v in t["meses"].items()
                      if v["origen_dato"] == origen]
            if puntos:
                x, y = zip(*sorted(puntos))
                ax.plot(x, y, color=color, lw=1.1,
                        ls="--" if origen == "pronostico" else "-",
                        marker="." if origen == "prueba" else None, ms=3)
        ax.set_title(t["peaje"].title(), fontsize=FUENTE, pad=2)
        ax.tick_params(axis="x", labelrotation=45)
    for ax in list(ejes.flat)[len(tramos):]:
        ax.axis("off")
    fig.supylabel("Tránsito diario (miles de veh/día)", fontsize=FUENTE)
    entradas = [
        Line2D([0], [0], color=TINTA, lw=1, label="Observado"),
        Line2D([0], [0], color=AZUL, lw=1.1, marker=".",
               label="Predicción a un mes (prueba)"),
        Line2D([0], [0], color=NARANJA, lw=1.1, ls="--",
               label="Pronóstico recursivo")]
    fig.legend(handles=entradas, loc="lower right", frameon=False)
    fig.tight_layout(h_pad=0.4, w_pad=0.6)
    return fig


def fig_mapa_nivel(d):
    red = agente_predictivo.grafo_del_mes(MES_EJEMPLO, d["pronostico"])
    recomendacion = agente_predictivo.recomendar(*CASO, MES_EJEMPLO,
                                                 d["pronostico"])
    ruta = recomendacion["elegida"]["ruta"]
    en_ruta = {frozenset(par) for par in zip(ruta, ruta[1:])}

    def color(u, v):
        return COLOR_NIVEL.get(red[u][v]["nivel_transito"], GRIS)

    fig, ax = _mapa(
        red, color,
        lambda u, v: 4.6 if frozenset((u, v)) in en_ruta else 1.5)
    entradas = [Line2D([0], [0], color=COLOR_NIVEL[n], lw=2.2,
                       label=f"Tránsito {n}") for n in COLOR_NIVEL]
    entradas += [Line2D([0], [0], color=GRIS, lw=2.2,
                        label="Sin dato de tránsito"),
                 Line2D([0], [0], color=TINTA_2, lw=4.6,
                        label=f"Trazo grueso: ruta de {CASO[0]} a "
                              f"{CASO[1]}")]
    mg.leyenda(ax, entradas, "upper left")
    fig.text(0.01, 0.006, "Fuentes: ANI (tránsito); INVÍAS (trazado); "
             "DANE (límites y nodos).", fontsize=FUENTE, color=TINTA_2,
             ha="left", va="bottom")
    return fig


FIGURAS = {
    "c3_serie": fig_serie, "c3_distribucion": fig_distribucion,
    "c3_composicion": fig_composicion, "c3_correlacion": fig_correlacion,
    "c3_series_red": fig_series_red, "c3_mapa_cobertura": fig_mapa_cobertura,
    "c3_regresion": fig_regresion, "c3_horizonte": fig_horizonte,
    "c3_clasificacion": fig_clasificacion, "c3_silueta": fig_silueta,
    "c3_grupos": fig_grupos, "c3_saturacion": fig_saturacion,
    "c3_pronostico_red": fig_pronostico_red, "c3_mapa_nivel": fig_mapa_nivel,
}


def main():
    datos = cargar()
    for nombre, funcion in FIGURAS.items():
        guardar(funcion(datos), nombre)
        print("  figura", nombre)
    print("Figuras del Corte 3 escritas en", SALIDA / "c3_x.pdf")


if __name__ == "__main__":
    main()
