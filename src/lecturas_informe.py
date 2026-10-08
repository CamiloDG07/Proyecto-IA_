"""Bloques «Cómo leerla» de las figuras y tablas de resultados.

Genera outputs/lectura_c1_*.tex (informe del Corte 1) y
outputs/lectura_c2_*.tex (informe del Corte 2). Cada archivo contiene una
llamada \\comoleerla{estructura}{qué se ve}{por qué} que el informe incluye
con \\input dentro del flotante. Las cifras se calculan aquí desde los datos
de outputs/ (nada se escribe a mano en los .tex). En «por qué» solo se afirma
una causa cuando el propio script la mide; si no, el texto empieza con
«Hipótesis:».
"""
import csv
import json
import statistics

import networkx as nx

from build_graph import SALIDA, cargar_grafo, construir_grafo
from exportar_latex import TRAMO_CICLO, costos
from formato_latex import estilizar
from agente import AgenteRutas
from agente_rutas import formatear, recomendar
from mapa_geografico import (DESTINO, ORIGEN, UMBRAL_KM,
                             algoritmos_por_via, cargar_trazado,
                             costos_ruta, unir)

ALGORITMOS = ["BFS", "DFS", "UCS", "Voraz", "A*"]


def leer(nombre):
    with open(SALIDA / nombre, encoding="utf-8") as f:
        return json.load(f)


def miles(valor):
    return f"{valor:,.0f}".replace(",", "\\,")


def pct(valor, decimales=3):
    """Número con `decimales` cifras; evita el cero negativo."""
    if abs(valor) < 5 * 10 ** -(decimales + 1):
        valor = 0.0
    return f"{valor:.{decimales}f}"


def bloque(nombre, estructura, que_se_ve, por_que):
    texto = (f"\\comoleerla{{{estructura}}}\n{{{que_se_ve}}}\n{{{por_que}}}")
    with open(SALIDA / f"lectura_{nombre}.tex", "w", encoding="utf-8") as f:
        f.write(texto + "\n")


def celda(res, origen, criterio, algoritmo, destino=None):
    return next(c for c in res if c["origen"] == origen
                and (destino is None or c["destino"] == destino)
                and c["criterio"] == criterio and c["algoritmo"] == algoritmo)


def grupos_validacion(val):
    """Brechas medias por grupo (red por n y euclidianas n = 20)."""
    red = [r for r in val if r["familia"] == "red de carga"]
    eucl = [r for r in val if r["familia"].startswith("euclidiana n=20")]
    return red, eucl


def media(valores):
    return sum(valores) / len(valores)


# ---------------------------------------------------------------- Corte 1
def lecturas_corte1():
    g = cargar_grafo()
    est = leer("estadisticas_grafo.json")
    ciclo = nx.cycle_basis(g)[0]
    trazado = cargar_trazado()
    lejos = [(max(t["km_extremo_origen"], t["km_extremo_destino"]), k)
             for k, t in trazado.items()
             if max(t["km_extremo_origen"], t["km_extremo_destino"])
             > UMBRAL_KM]
    mayor, arista = max(lejos)
    bloque(
        "c1_mapa",
        "ejes de longitud y latitud; cada línea es el trazado de INVÍAS de "
        "un tramo y cada punto una ciudad; el ciclo va en azul, el resto de "
        "la red en gris y la línea punteada marca un tramo sin trazado en la "
        "fuente.",
        f"la red tiene {est['nodos']} ciudades y {est['aristas']} tramos, "
        f"{est['distancia_total_km']:.2f} km en total; el ciclo, que cierra "
        f"por Santander, pasa por {len(ciclo)} ciudades.",
        f"Medido: en {len(lejos)} de las {est['aristas']} aristas el "
        f"trazado queda a más de {UMBRAL_KM:.0f} km de uno de sus nodos "
        f"(hasta {mayor:.2f} km en {arista.replace('|', ' a ')}) y ahí se "
        "dibuja punteado.")
    pruebas = leer("pruebas_agente.json")["ciclo"]
    por_via = {}
    for criterio in ("distancia", "peaje", "riesgo", "compuesto",
                     "compuesto_sin_riesgo"):
        r = pruebas[criterio]
        via = "Santander" if "Bucaramanga" in r["ruta"] else "Bogotá"
        por_via.setdefault(via, []).append(criterio.replace("_", " "))
    ref = {v: next(pruebas[c.replace(" ", "_")] for c in cs)
           for v, cs in por_via.items()}
    partes = [f"{' y '.join(cs)} eligen {v} "
              f"({ref[v]['distancia_total_km']:.2f} km, "
              f"{miles(ref[v]['peaje_total_cop'])} COP de peaje)"
              for v, cs in por_via.items()]
    dif_peaje = (ref["Bogotá"]["peaje_total_cop"]
                 - ref["Santander"]["peaje_total_cop"])
    bloque(
        "c1_criterios",
        "filas: los cinco criterios; columnas: vía elegida, distancia, "
        "peaje, tiempo y memoria de una corrida del agente.",
        "; ".join(partes) + ".",
        f"Medido: la ruta por Santander cuesta {miles(dif_peaje)} COP menos "
        f"de peaje y sus {pruebas['riesgo']['tramos_sin_dato_riesgo']} "
        "tramos sin dato de riesgo valen 0.")
    ag = AgenteRutas(g)
    corta = ag.calcular_ruta("Duitama", "Puente Nacional",
                             "distancia")["ruta"]
    desvio = ag.calcular_ruta("Duitama", "Puente Nacional", "distancia",
                              tramos_bloqueados=[TRAMO_CICLO])["ruta"]
    c, d = costos(g, corta), costos(g, desvio)
    bloque(
        "c1_rutas",
        "columnas: la ruta corta por Bogotá y el desvío por Santander; "
        "filas: saltos, distancia, peaje, tramos sin riesgo y costos "
        "compuestos.",
        f"el desvío mide {d['km'] - c['km']:.2f} km más y cuesta "
        f"{miles(c['peaje'] - d['peaje'])} COP menos de peaje; el costo "
        f"compuesto es {c['compuesto']:.3f} por Bogotá y "
        f"{d['compuesto']:.3f} por Santander, y sin riesgo "
        f"{c['sin_riesgo']:.3f} y {d['sin_riesgo']:.3f}.",
        f"Medido: la ruta por Bogotá tiene {c['sin_dato']} tramos sin dato "
        f"de riesgo y el desvío {d['sin_dato']}, que valen 0 en el costo "
        "compuesto.")
    with open(SALIDA / "auditoria_aristas.csv", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    marcadas = [r for r in filas if r["anomalia"]]

    def cuenta(texto):
        return sum(1 for r in marcadas if texto in r["anomalia"])

    desde_bogota = [r for r in marcadas if "extremo lejos" in r["anomalia"]
                    and "Bogotá" in (r["origen"], r["destino"])]
    exts = [max(float(r["extremo_a_origen_km"]),
                float(r["extremo_a_destino_km"])) for r in desde_bogota]
    bloque(
        "c1_auditoria",
        "filas: las aristas marcadas por la auditoría; columnas: distancia "
        "por carretera, geodésica, su razón, la mayor separación entre un "
        "extremo del trazado y el nodo, y las marcas A a E.",
        f"{len(marcadas)} de {len(filas)} aristas tienen alguna marca: "
        f"{cuenta('carretera menor')} con carretera menor que la línea "
        f"recta (A), {cuenta('extremo lejos')} con el trazado lejos de un "
        f"nodo (B) y {cuenta('geometría sin camino')} sin camino entre "
        "extremos (E).",
        f"Medido: {len(desde_bogota)} de las aristas con extremo lejos "
        f"salen de Bogotá, con el trazado a entre {min(exts):.2f} y "
        f"{max(exts):.2f} km del nodo.")


def costos_sin_riesgo(variante):
    """Costo compuesto sin riesgo de las dos rutas (Bogotá, Santander)."""
    g = construir_grafo(distancia=variante)
    caminos = list(nx.all_simple_paths(g, "Duitama", "Puente Nacional"))
    por_bogota = next(c for c in caminos if "Bogotá" in c)
    por_santander = next(c for c in caminos if "Bucaramanga" in c)
    return tuple(sum(g[u][v]["peso_sin_riesgo"] for u, v in zip(c, c[1:]))
                 for c in (por_bogota, por_santander))


def texto_corte1_cambio_sin_riesgo():
    (ab, as_), (db, ds) = (costos_sin_riesgo("cruda"),
                           costos_sin_riesgo("corregida"))
    antes = "el desvío por Santander" if as_ < ab else "la ruta por Bogotá"
    despues = "la ruta por Bogotá" if db < ds else "el desvío por Santander"
    with open(SALIDA / "texto_c1_cambio_sin_riesgo.tex", "w",
              encoding="utf-8") as f:
        f.write(
            f"Sin el término de riesgo, con las distancias sin corregir el "
            f"costo compuesto era {ab:.3f} por Bogotá y {as_:.3f} por "
            f"Santander, y ganaba {antes}; con las distancias corregidas es "
            f"{db:.3f} y {ds:.3f}, y gana {despues}.\n")


def lectura_mapa_caso_central():
    """Bloque del mapa del caso central (Corte 2)."""
    g = cargar_grafo()
    agente = AgenteRutas(g)
    corta = agente.calcular_ruta(ORIGEN, DESTINO, "distancia")["ruta"]
    desvio = agente.calcular_ruta(ORIGEN, DESTINO, "peaje")["ruta"]
    km_c, pe_c = costos_ruta(g, corta)
    km_d, pe_d = costos_ruta(g, desvio)
    alg_b, alg_s = algoritmos_por_via()
    bloque(
        "c2_mapa_caso",
        "ejes de longitud y latitud; azul con borde oscuro, la ruta por "
        "Bogotá; naranja grueso, el desvío por Santander; halo claro, el "
        "ciclo; punteado, un tramo sin trazado en la fuente.",
        f"por Bogotá, {km_c:.2f} km y {miles(pe_c)} COP de peaje; por "
        f"Santander, {km_d:.2f} km y {miles(pe_d)} COP; con el criterio "
        f"distancia, {unir(alg_b)} devuelven la primera y {unir(alg_s)} la "
        "segunda.",
        f"Medido: el desvío es {km_d - km_c:.2f} km más largo y tiene "
        f"{miles(pe_c - pe_d)} COP menos de peaje.")


# ---------------------------------------------------------------- Corte 2
def lecturas_corte2():
    g = cargar_grafo()
    res = leer("resultados_corte2.json")["resultados"]
    bar = leer("barrido_pesos.json")
    heur = leer("analisis_heuristica.json")
    val = leer("validacion_agente.json")["instancias"]
    central = {a: celda(res, "Duitama", "distancia", a)
               for a in ALGORITMOS}
    # --- figura de rutas
    por_via = {}
    for a, c in central.items():
        via = "Santander" if "Bucaramanga" in c["ruta"] else "Bogotá"
        por_via.setdefault(via, []).append(a)
    partes = [f"{', '.join(algos)} devuelven la ruta por {v} "
              f"({central[algos[0]]['costo']:.2f} km, "
              f"{central[algos[0]]['saltos']} saltos)"
              for v, algos in por_via.items()]
    primero = sorted(g["Duitama"])[0]
    dfs_ok = central["DFS"]["ruta"][1] == primero
    porque = (f"Medido: BFS minimiza los saltos y el desvío tiene "
              f"{central['BFS']['saltos']} frente a "
              f"{central['UCS']['saltos']}; DFS explora los vecinos en orden "
              f"alfabético y el primero de Duitama es {primero}"
              + (", que abre el desvío." if dfs_ok else "."))
    bloque(
        "c2_rutas",
        "un panel por algoritmo sobre las coordenadas oficiales; el ciclo "
        "va en rosa y la ruta elegida en azul continuo (Bogotá) o naranja "
        "discontinuo (Santander).",
        "; ".join(partes) + ".", porque)
    # --- figura de convergencia
    red, eucl = grupos_validacion(val)
    peor_red = max(100 * abs(r["aco"]["curva_media"][0]
                             - r["referencia"]["costo"])
                   / r["referencia"]["costo"] for r in red)
    ini = media([100 * (r["aco"]["curva_media"][0] - r["referencia"]["costo"])
                 / r["referencia"]["costo"] for r in eucl])
    fin = media([100 * (r["aco"]["curva_media"][-1]
                        - r["referencia"]["costo"])
                 / r["referencia"]["costo"] for r in eucl])
    fin_red = max(100 * abs(r["aco"]["curva_media"][-1]
                            - r["referencia"]["costo"])
                  / r["referencia"]["costo"] for r in red)
    mayores = [r for r in val if "mayor" in r["familia"]]
    sin_red = media([r["aco_sin_2opt"]["brecha_media_pct"] for r in red])
    sin_tal = media([r["aco_sin_2opt"]["brecha_media_pct"] for r in eucl])
    bloque(
        "c2_convergencia",
        "izquierda, la red de carga (media de sus instancias); derecha, las "
        "cinco instancias euclidianas con n = 20 (semillas 1 a 5); eje x, la "
        "iteración; eje y, la brecha de la media de 10 semillas del mejor "
        "global respecto de la referencia.",
        f"en la red la brecha de la iteración 1 es a lo sumo "
        f"{pct(peor_red, 3)}\\,\\% y la final es {pct(fin_red, 3)}\\,\\%; "
        f"en las euclidianas n = 20 la media de las instancias baja de "
        f"{ini:.2f}\\,\\% en la iteración 1 a {pct(fin, 3)}\\,\\% en la "
        "100.",
        f"Medido: sin 2-opt la brecha media final es {pct(sin_red)}\\,\\% en "
        f"la red y {pct(sin_tal)}\\,\\% en las euclidianas n = 20 (con 2-opt, "
        f"{pct(fin, 3)}\\,\\%); en $n = 100$ y $200$ es "
        f"{pct(mayores[0]['aco_sin_2opt']['brecha_media_pct'])}\\,\\% y "
        f"{pct(mayores[1]['aco_sin_2opt']['brecha_media_pct'])}\\,\\% y con "
        "2-opt supera la referencia: el aporte del 2-opt crece con $n$.")
    # --- figura y tabla del barrido
    b0, b1 = bar[0], bar[1]
    d0, d1 = b0["delta_corta_menos_desvio"], b1["delta_corta_menos_desvio"]
    bloque(
        "c2_barrido_figura",
        "dos paneles (red corregida y con cota inferior); cada punto es un "
        "$(w_1, w_2)$ de la malla con $w_3 = 1 - w_1 - w_2$; círculo azul, "
        "gana Bogotá; triángulo naranja, gana Santander; la línea es la "
        "frontera exacta.",
        f"Bogotá gana en {b0['ganan_bogota_compuesto']} de "
        f"{len(b0['puntos'])} puntos en la red corregida y en "
        f"{b1['ganan_bogota_compuesto']} con la cota inferior; la frontera "
        f"corta $w_3=0$ en $w_1 = {b0['w1_umbral_sobre_w3_cero']:.4f}$ y "
        f"${b1['w1_umbral_sobre_w3_cero']:.4f}$.",
        f"Medido: Bogotá es más corta ($\\Delta D = {d0[0]:.4f}$) pero más "
        f"cara en peaje ($\\Delta P = {d0[1]:.4f}$) y en riesgo "
        f"($\\Delta R = {d0[2]:.4f}$); la frontera es el lugar donde esos "
        "tres términos se compensan.")
    bloque(
        "c2_barrido_tabla",
        "filas: medidas del barrido; columnas: la red corregida y la "
        "variante con la distancia de Chocontá a Tunja en su cota inferior.",
        f"con la cota inferior Bogotá gana en {b1['ganan_bogota_compuesto']} "
        f"puntos en lugar de {b0['ganan_bogota_compuesto']} y el umbral "
        f"pasa de {b0['w1_umbral_sobre_w3_cero']:.4f} a "
        f"{b1['w1_umbral_sobre_w3_cero']:.4f}.",
        f"Medido: $\\Delta D$ cambia de {d0[0]:.4f} a {d1[0]:.4f} mientras "
        f"$\\Delta P$ ({d1[1]:.4f}) y $\\Delta R$ ({d1[2]:.4f}) no cambian; "
        "la única arista distinta es Chocontá a Tunja.")
    # --- tabla de heurística
    adm = heur["criterios"]["distancia"]["admisibilidad"]
    pura = heur["geodesica_pura_distancia"]
    todos_cero = all(c["admisibilidad"]["violaciones"] == 0
                     and c["consistencia"]["violaciones"] == 0
                     for c in heur["criterios"].values())
    bloque(
        "c2_heuristica",
        "filas: heurística (distancia, compuesto sin riesgo, compuesto y "
        "geodésica pura con $\\alpha = 1$); columnas: $\\alpha$, violaciones "
        "y margen mínimo de admisibilidad y de consistencia.",
        f"con $\\alpha = {heur['alfa']:.6f}$ no hay violaciones "
        f"({'en las tres heurísticas' if todos_cero else 'revisar'}); con "
        f"$\\alpha = 1$ hay {pura['admisibilidad']['violaciones']} de "
        f"admisibilidad y {pura['consistencia']['violaciones']} de "
        "consistencia.",
        f"Medido: el margen mínimo ({adm['margen_minimo']:.6f}) está en el "
        f"par {adm['par_margen_minimo'][0]} a {adm['par_margen_minimo'][1]},"
        " la arista que fija $\\alpha$.")
    # --- tablas de la comparación de los cinco algoritmos (criterio dist.)
    dist = [c for c in res if c["criterio"] == "distancia"]
    escenarios = sorted({(c["origen"], c["destino"]) for c in dist})
    total = {a: sum(c["nodos_expandidos"] for c in dist
                    if c["algoritmo"] == a) for a in ALGORITMOS}
    a_menos = sum(
        1 for o, d in escenarios
        if celda(res, o, "distancia", "A*", d)["nodos_expandidos"]
        <= celda(res, o, "distancia", "UCS", d)["nodos_expandidos"])
    bloque(
        "c2_t_expandidos",
        f"filas: los {len(escenarios)} escenarios (* cruzan el ciclo); "
        "columnas: los cinco algoritmos; celda: nodos expandidos con el "
        "criterio distancia.",
        "sumados los escenarios, expanden " + ", ".join(
            f"{a} {total[a]}" for a in ALGORITMOS) + f"; A* expande no más "
        f"que UCS en {a_menos} de {len(escenarios)}.",
        "Hipótesis: el voraz expande menos porque ordena solo por $h$ e "
        "ignora el costo acumulado; no se midió.")
    desv = max(c["tiempo_desv_s"] / c["tiempo_media_s"] for c in res)
    bloque(
        "c2_t_tiempo",
        "filas: escenarios; columnas: algoritmos; celda: tiempo medio "
        "$\\pm$ desviación estándar en $\\mu$s de 2000 repeticiones.",
        "en el caso central: " + ", ".join(
            f"{a} {central[a]['tiempo_media_s'] * 1e6:.0f} $\\pm$ "
            f"{central[a]['tiempo_desv_s'] * 1e6:.0f}"
            for a in ALGORITMOS) + ".",
        f"Medido: la desviación llega a {desv:.2f} veces la media, de modo "
        "que las diferencias menores que esa dispersión no son "
        "concluyentes.")
    rango = {a: (min(c["memoria_pico_kib"] for c in dist
                     if c["algoritmo"] == a),
                 max(c["memoria_pico_kib"] for c in dist
                     if c["algoritmo"] == a)) for a in ALGORITMOS}
    bloque(
        "c2_t_memoria",
        "filas: escenarios; columnas: algoritmos; celda: memoria pico en "
        "KiB de una corrida aparte con \\texttt{tracemalloc}.",
        "rango entre escenarios: " + ", ".join(
            f"{a} {rango[a][0]:.1f} a {rango[a][1]:.1f}"
            for a in ALGORITMOS) + ".",
        "Hipótesis: UCS y A* guardan costos acumulados y una cola de "
        "prioridad, y BFS y DFS solo la frontera y los padres; no se midió.")
    bloque(
        "c2_t_costo",
        "filas: escenarios; columnas: algoritmos; celda: costo de la ruta "
        "devuelta en km.",
        f"en el caso central BFS y DFS devuelven {central['BFS']['costo']:.2f}"
        f" km y UCS, voraz y A* {central['UCS']['costo']:.2f} km.",
        f"Medido: BFS minimiza los saltos ({central['BFS']['saltos']} "
        f"frente a {central['UCS']['saltos']}), no los kilómetros.")
    no_opt = {a: [(c["origen"], c["destino"]) for c in dist
                  if c["algoritmo"] == a and not c["optima"]]
              for a in ALGORITMOS}
    unicos = [(o, d) for (o, d) in escenarios
              if next(c for c in dist if c["origen"] == o
                      and c["destino"] == d)["rutas_simples"] == 1]
    misma = all(len({tuple(c["ruta"]) for c in dist
                     if c["origen"] == o and c["destino"] == d}) == 1
                for o, d in unicos)
    ciclo_pares = {(c["origen"], c["destino"]) for c in dist
                   if c["rutas_simples"] > 1}
    todos_en_ciclo = all(p in ciclo_pares for lista in no_opt.values()
                         for p in lista)
    fallan = ", ".join(f"{a} en {len(no_opt[a])}" for a in ALGORITMOS
                       if no_opt[a])
    exactos = [a for a in ALGORITMOS if not no_opt[a]]
    bloque(
        "c2_t_optimalidad",
        "filas: escenarios; columnas: algoritmos; celda: «sí» si el costo "
        "iguala al de UCS o el exceso porcentual.",
        f"no son óptimos {fallan} de {len(escenarios)} escenarios; "
        f"{', '.join(exactos)} son óptimos en todos.",
        f"Medido: todos los casos no óptimos están en pares que cruzan el "
        f"ciclo ({'sí' if todos_en_ciclo else 'no'}) y en los "
        f"{len(unicos)} pares de ruta única los cinco algoritmos devuelven "
        f"la misma ruta ({'sí' if misma else 'no'}).")
    # --- tabla de validación principal
    nz = [f"{'euclidianas' if r in eucl else 'red'}, n = {r['n']}, instancia "
          f"{r['instancia']}" for r in red + eucl
          if r["aco"]["brecha_media_pct"] > 5e-4]
    iguales_red = sum(r["aco"]["semillas_que_igualan_referencia"]
                      for r in red)
    iguales_tal = sum(r["aco"]["semillas_que_igualan_referencia"]
                      for r in eucl)
    brecha_eucl = media([r["aco"]["brecha_media_pct"] for r in eucl])
    bloque(
        "c2_validacion",
        "filas: grupos de instancias (red de carga por n y euclidianas "
        "n = 20); columnas: instancias, brecha media, mayor brecha de la "
        "mejor corrida, semillas que alcanzan la referencia y tiempos "
        "medios.",
        f"en la red el ACO con 2-opt alcanza la referencia con "
        f"{iguales_red} de {10 * len(red)} semillas; en las euclidianas "
        f"n = 20, la brecha media es {pct(brecha_eucl)}"
        f"\\,\\% y {iguales_tal} de {10 * len(eucl)} semillas la alcanzan.",
        "Medido: la brecha media es mayor que cero solo en " + "; ".join(nz)
        + ". Hipótesis: el ACO se estanca en un óptimo local; no se midió.")
    # --- sentencia del cambio de ruta (texto, no flotante) se genera en
    # tablas_corte2.py (texto_cambio_sin_riesgo)


def tex(texto):
    """Escapa los caracteres especiales de LaTeX de un texto."""
    return (str(texto).replace("%", "\\%").replace("_", "\\_")
            .replace("&", "\\&"))


def flecha(ruta):
    return " $\\to$ ".join(tex(c) for c in ruta)


def columna_ejemplo(r, solicitud):
    """Celdas de una columna de la tabla de ejemplos del agente."""
    m = r["recomendada"]
    grupos = {}
    for x in r["metodos"]:
        etiqueta = x["metodo"].split(" por")[0]
        grupos.setdefault(etiqueta, []).append(
            x["criterio"].replace("_", " "))
    metodo = "; ".join(f"{e} ({', '.join(c)})" if len(r["metodos"]) > 1
                       else e for e, c in grupos.items())
    if "k" in m.get("metricas", {}):
        metodo += (f", $k = {m['metricas']['k']} \\le K_{{\\mathrm{{exacto}}}}"
                   f" = {m['metricas']['umbral_k']}$")
    metodo += (f"; $\\alpha = {r['alfa']:.6f}$; "
               f"{r['nodos_expandidos']} nodos expandidos")
    if r["alternativas"]:
        alt = r["alternativas"][0]
        via = ("desvío por Santander" if "Bucaramanga" in alt["ruta"]
               else "otra ruta")
        alternativas = (f"{via}: {alt['km']:.2f} km, "
                        f"{miles(alt['peaje_cop'])} COP; margen "
                        f"{alt['margen']:.3f} ({alt['margen_pct']:.1f}"
                        "\\,\\%)")
    elif r["tipo"] == "origen_destino":
        alternativas = "ninguna (un solo camino)"
    else:
        alternativas = "no aplica (orden exacto de las paradas)"
    lim = r["limitaciones"]
    avisos = []
    if lim["truncada"]:
        avisos.append("Chocontá a Tunja truncada")
    if lim["marcadas"]:
        avisos.append(f"{lim['marcadas']} aristas marcadas por la auditoría")
    if lim["sin_dato"]:
        avisos.append(f"{lim['sin_dato']} de {lim['tramos']} tramos sin "
                      "dato de riesgo")
    if any("otra ruta" in x for x in r["avisos"]):
        avisos.append("riesgo y compuesto prefieren otra ruta")
    ruta = m.get("orden_paradas", m["ruta"])
    tipos = {"origen_destino": "origen a destino",
             "orden_libre_regreso": "orden libre con regreso",
             "orden_libre_sin_regreso": "orden libre sin regreso"}
    return [tex(solicitud), tipos[r["tipo"]], flecha(ruta),
            f"{m['km']:.2f}", miles(m["peaje_cop"]),
            f"{m['riesgo']:.2f} (dato en el {m['cobertura_riesgo_pct']:.0f}"
            "\\,\\%)", metodo, alternativas,
            "; ".join(avisos) if avisos else "ninguna"]


def ejemplo_agente():
    """Tabla de ejemplos del agente autónomo, su texto y su bloque."""
    casos = [("Duitama a Puente Nacional (ciclo)",
              recomendar("Duitama", ["Puente Nacional"])),
             ("Bogotá a Granada (ruta única)",
              recomendar("Bogotá", ["Granada"])),
             ("Duitama; paradas Tunja, Bogotá y Villeta; con regreso",
              recomendar("Duitama", ["Tunja", "Bogotá", "Villeta"], True))]
    columnas = [columna_ejemplo(r, t) for t, r in casos]
    filas = ["Solicitud", "Tipo decidido", "Ruta u orden", "Distancia (km)",
             "Peaje (COP)", "Riesgo", "Método y heurística",
             "Alternativas y margen", "Advertencias"]
    lineas = ["\\begin{tabular}{>{\\raggedright\\arraybackslash}p{2.2cm}"
              + ">{\\raggedright\\arraybackslash}p{3.9cm}" * 3 + "}",
              "\\toprule",
              "\\textbf{Fila} & \\textbf{(a)} & \\textbf{(b)} & "
              "\\textbf{(c)} \\\\",
              "\\midrule"]
    for i, fila in enumerate(filas):
        lineas.append(" & ".join([f"\\textbf{{{fila}}}"]
                                 + [c[i] for c in columnas]) + " \\\\")
        lineas.append("\\addlinespace[2pt]")
    lineas += ["\\bottomrule", "\\end{tabular}"]
    with open(SALIDA / "tabla_agente_ejemplos.tex", "w",
              encoding="utf-8") as f:
        f.write("\n".join(estilizar(lineas)) + "\n")
    ra, rb, rc = (c[1] for c in casos)
    m, alt = ra["recomendada"], ra["alternativas"][0]
    otros = [k for ruta, k in ra["prefiere"].items()
             if ruta == " > ".join(alt["ruta"])][0]
    # umbral de la participación de la distancia, del barrido de pesos, y
    # comprobación contra el propio agente a ambos lados del umbral
    barrido = leer("barrido_pesos.json")
    cota = construir_grafo(reemplazos={("Chocontá", "Tunja"): 56.96})
    umbrales = []
    for b, grafo in ((barrido[0], None), (barrido[1], cota)):
        u = b["w1_umbral_sobre_w3_cero"]
        for delta, via in ((0.005, "Bogotá"), (-0.005, "Bucaramanga")):
            ruta = recomendar("Duitama", ["Puente Nacional"], grafo=grafo,
                              pesos={"distancia": u + delta,
                                     "peaje": 1 - u - delta}
                              )["recomendada"]["ruta"]
            assert via in ruta, (b["variante"], delta)
        igual = recomendar("Duitama", ["Puente Nacional"],
                           grafo=grafo)["recomendada"]["ruta"]
        assert "Bogotá" in igual
        umbrales.append(u)
    u0, u1 = umbrales
    costo = m["costos"]["compuesto_sin_riesgo"]
    preferencias = ", ".join(otros[:-1]) + " y " + otros[-1]
    with open(SALIDA / "texto_ejemplo_agente.tex", "w",
              encoding="utf-8") as f:
        f.write(
            "En (a):\n\\begin{itemize}\n"
            "\\item La recomendación se apoya en la distancia y el peaje "
            f"(costo compuesto sin riesgo {costo:.3f}).\n"
            f"\\item {preferencias.capitalize()}"
            " prefieren el desvío por Santander.\n"
            "\\item El riesgo tiene dato en el "
            f"{m['cobertura_riesgo_pct']:.0f}\\,\\% de los tramos de la "
            f"recomendada y en el {alt['cobertura_riesgo_pct']:.0f}\\,\\% "
            "de los del desvío.\n"
            "\\item La recomendación se mantiene mientras el "
            f"peso de la distancia, $w_d/(w_d+w_p)$, sea mayor que {u0:.4f} "
            f"({u1:.4f} con la cota inferior de Chocontá a Tunja).\n"
            "\\end{itemize}\n")
    mc = rc["recomendada"]["metricas"]
    bloque(
        "c2_ejemplos",
        "columnas, una solicitud cada una; filas, lo que el agente decide y "
        "devuelve (tipo, ruta, medidas, método, alternativas y advertencias).",
        f"(a) recomienda {m['km']:.2f} km con una alternativa a "
        f"{alt['margen']:.3f}; (b) no tiene alternativas; (c) ordena las "
        f"paradas con {rc['recomendada']['metodo']}.",
        f"Medido: (a) tiene {1 + len(ra['alternativas'])} candidatas no "
        f"dominadas y (b) {1 + len(rb['alternativas'])}; en (c) "
        f"$k = {mc['k']}$ no supera $K_{{\\mathrm{{exacto}}}} = "
        f"{mc['umbral_k']}$, por eso el orden es exacto.")


def texto_corte1_caso_referencia():
    """Frase del caso de referencia del Corte 1, leída de outputs/."""
    r = leer("sensibilidad_corte2.json")
    r = r["rutas_optimas_duitama_puente_nacional"]
    bogota = r["base"]["distancia"]["distancia_km"]
    santander = r["base"]["peaje"]["distancia_km"]
    bogota_c = r["crudas"]["distancia"]["distancia_km"]
    santander_c = r["crudas"]["peaje"]["distancia_km"]
    with open(SALIDA / "texto_c1_caso_referencia.tex", "w",
              encoding="utf-8") as f:
        f.write(
            "El caso de referencia es Duitama a Puente Nacional: "
            f"{bogota:.2f} km por Bogotá o {santander:.2f} km por Santander "
            f"(con las distancias sin corregir, {bogota_c:.2f} y "
            f"{santander_c:.2f} km).\n")


def cifras_dinero():
    """Ahorro de peaje y km extra del desvío, y umbrales de COP por km."""
    grafo = cargar_grafo()
    sin_enlace = grafo.copy()
    sin_enlace.remove_edge("Bogotá", "Tocancipá")
    rutas = [nx.shortest_path(h, "Duitama", "Puente Nacional",
                              weight="distancia_km")
             for h in (grafo, sin_enlace)]

    def total(ruta, atributo):
        return sum(grafo[u][v][atributo] or 0
                   for u, v in zip(ruta, ruta[1:]))
    km_b, km_s = (total(r, "distancia_km") for r in rutas)
    peaje_b, peaje_s = (total(r, "peaje_cop_camion") for r in rutas)
    sens = leer("sensibilidad_corte2.json")
    sens = sens["rutas_optimas_duitama_puente_nacional"]
    cota = sens["cota_inferior"]["distancia"]["distancia_km"]
    ahorro = peaje_b - peaje_s
    return {"km_bogota": km_b, "km_desvio": km_s, "ahorro_cop": ahorro,
            "km_extra": km_s - km_b, "cota_bogota": cota,
            "umbral_registrado": ahorro / (km_s - km_b),
            "umbral_cota": ahorro / (km_s - cota)}


def texto_c2_dinero():
    """Frase del barrido de pesos sobre el costo en dinero (outputs/)."""
    d = cifras_dinero()
    with open(SALIDA / "texto_c2_dinero.tex", "w", encoding="utf-8") as f:
        f.write(
            f"Con las distancias registradas, el desvío por Santander ahorra "
            f"{miles(d['ahorro_cop'])} COP de peaje y suma "
            f"{d['km_extra']:.2f} km. Solo es más barato en dinero si el "
            f"costo operativo por km es menor que el ahorro dividido entre "
            f"los km extra, {d['umbral_registrado']:.1f} COP/km; como la "
            f"ruta por Bogotá está subestimada (cota inferior "
            f"{d['cota_bogota']:.2f} km), el umbral real es al menos el "
            f"ahorro dividido entre ({d['km_desvio']:.2f} $-$ "
            f"{d['cota_bogota']:.2f}) km, {d['umbral_cota']:.1f} COP/km. "
            "No hay datos de costo operativo por kilómetro para decidir "
            "cuál ruta es más barata, y esta comparación no incluye tiempo "
            "ni riesgo.\n")


def main():
    lecturas_corte1()
    texto_c2_dinero()
    texto_corte1_cambio_sin_riesgo()
    texto_corte1_caso_referencia()
    lecturas_corte2()
    lectura_mapa_caso_central()
    ejemplo_agente()
    print("Bloques 'Cómo leerla' escritos en", SALIDA)


if __name__ == "__main__":
    main()
