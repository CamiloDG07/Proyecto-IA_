"""Pruebas del costo monetario y de los criterios nuevos.

  - config_costos.json: cada insumo trae fuente, fecha o unidad y un estado
    permitido; el costo variable sale de los insumos.
  - costo_operativo, compuesto_total, compuesto_total_sin_riesgo y
    compuesto_mortalidad coinciden con el mínimo entre TODOS los caminos
    simples (enumerados aparte) en al menos 20 pares con y sin ciclo, con y
    sin tramos bloqueados.
  - Regla del criterio por defecto: costo_operativo solo con todos los
    insumos verificados; con un supuesto del equipo, el compuesto sin riesgo.
  - Las heurísticas de los criterios nuevos son admisibles y consistentes.
  - El umbral exacto en COP por km coincide con la enumeración y con la
    inversión de la recomendación a ambos lados.
  - Las opciones del usuario anulan la configuración y se rotulan.
"""
import json
import subprocess
import sys
from pathlib import Path

import networkx as nx

from agente import CRITERIOS
from agente_rutas import formatear, main, recomendar
from build_graph import CONFIG_COSTOS, cargar_costos, construir_grafo
from despachador import Despachador, Solicitud
from heuristica import (Heuristica, alfa_minimo, cargar_coordenadas,
                        verificar_admisibilidad, verificar_consistencia)
from umbral_costo import rutas_del_par, umbral_exacto

NUEVOS = ("costo_operativo", "compuesto_total", "compuesto_total_sin_riesgo",
          "compuesto_mortalidad")
ESTADOS = {"verificada", "supuesto del equipo"}
RAIZ = Path(__file__).resolve().parent.parent
grafo = construir_grafo()


def ok(condicion, mensaje):
    if not condicion:
        print(f"  FALLA: {mensaje}")
        sys.exit(1)
    print(f"  ok: {mensaje}")


def pares():
    """Pares con ciclo (dos rutas) y sin ciclo, en total más de 20."""
    nodos = sorted(grafo)
    salida = [("Duitama", "Puente Nacional"), ("Bucaramanga", "Bogotá"),
              ("Tunja", "Ubaté"), ("Barbosa", "Zipaquirá"),
              ("Pamplona", "Zipaquirá"), ("Cajicá", "Duitama"),
              ("Bogotá", "San Gil"), ("Chiquinquirá", "Pamplona")]
    for i in range(0, len(nodos), 2):
        a, b = nodos[i], nodos[(i * 7 + 5) % len(nodos)]
        if a != b and (a, b) not in salida:
            salida.append((a, b))
    return salida


def minimo_enumerado(origen, destino, atributo, bloqueados=()):
    vista = nx.restricted_view(grafo, [], list(bloqueados))
    costos = [sum(grafo[u][v][atributo] for u, v in zip(c, c[1:]))
              for c in nx.all_simple_paths(vista, origen, destino)]
    return min(costos), len(costos)


def prueba_config():
    print("config_costos.json")
    with open(CONFIG_COSTOS, encoding="utf-8") as f:
        c = json.load(f)
    for nombre, i in c["insumos"].items():
        ok(i["estado"] in ESTADOS and i["unidad"] and i["fuente"]
           and "valor" in i, f"{nombre}: valor, unidad, fuente y estado "
           f"({i['estado']})")
    ok(c["pesos_compuesto_total"]["estado"] in ESTADOS,
       "los pesos del compuesto total llevan estado")
    costos = cargar_costos()
    esperado = (c["insumos"]["precio_galon_acpm_cop"]["valor"]
                * c["insumos"]["consumo_litros_por_100km"]["valor"] / 100
                / c["insumos"]["litros_por_galon"]["valor"]
                + c["insumos"]["otros_costos_variables_cop_por_km"]["valor"])
    ok(abs(costos["costo_variable_cop_km"] - esperado) < 1e-9,
       f"costo variable por km = precio * litros por km / litros por galón "
       f"+ otros = {esperado:.2f} COP/km")
    ok(all(abs(d["costo_variable_cop"] - d["distancia_km"]
               * costos["costo_variable_cop_km"]) < 1e-6
           and abs(d["costo_operativo_cop"] - d["peaje_cop_camion"]
                   - d["costo_variable_cop"]) < 1e-6
           for _, _, d in grafo.edges(data=True)),
       "las 32 aristas: costo variable = km * costo por km y operativo = "
       "peaje + variable")
    ok(not costos["verificados"],
       "con otros costos por km como supuesto, no todos los insumos están "
       "verificados")


def prueba_minimos():
    print("Mínimos contra la enumeración de caminos simples")
    lista = pares()
    ok(len(lista) >= 20, f"{len(lista)} pares de prueba")
    con_ciclo = sin_ciclo = bloqueados_n = 0
    for criterio in NUEVOS:
        atributo = CRITERIOS[criterio]
        for origen, destino in lista:
            r = recomendar(origen, destino, grafo=grafo, criterio=criterio)
            esperado, n = minimo_enumerado(origen, destino, atributo)
            obtenido = r["recomendada"]["costos"][criterio]
            if abs(obtenido - esperado) > 1e-9 * max(1.0, abs(esperado)):
                ok(False, f"{criterio}: {origen} a {destino}: {obtenido} "
                   f"contra {esperado}")
            if criterio == NUEVOS[0]:
                con_ciclo += n > 1
                sin_ciclo += n == 1
        # con tramos bloqueados (solo tiene sentido en pares con ciclo)
        for origen, destino in lista:
            rutas = rutas_del_par(grafo, origen, destino)
            if len(rutas) < 2:
                continue
            tramos = [frozenset(t) for t in zip(rutas[1]["ruta"],
                                                rutas[1]["ruta"][1:])]
            u, v = next(t for t in zip(rutas[0]["ruta"],
                                       rutas[0]["ruta"][1:])
                        if frozenset(t) not in tramos)
            esperado, _ = minimo_enumerado(origen, destino, atributo,
                                           [(u, v)])
            d = Despachador(grafo, cargar_coordenadas())
            s = d.resolver(Solicitud("a", origen, destino, criterio=criterio,
                                     restricciones={"bloqueados": [(u, v)]}))
            if abs(s["costo"] - esperado) > 1e-9 * max(1.0, abs(esperado)):
                ok(False, f"{criterio} bloqueando {u}-{v}: {s['costo']} "
                   f"contra {esperado}")
            if criterio == NUEVOS[0]:
                bloqueados_n += 1
    ok(con_ciclo >= 5 and sin_ciclo >= 4,
       f"los cuatro criterios nuevos coinciden con el mínimo de los "
       f"caminos simples: {len(lista)} pares ({con_ciclo} con ciclo, "
       f"{sin_ciclo} sin ciclo) y {bloqueados_n} con un tramo bloqueado")


def prueba_defecto():
    print("Regla del criterio por defecto")
    r = recomendar("Duitama", "Puente Nacional", grafo=grafo)
    ok(r["criterio_por_defecto"] == "compuesto_sin_riesgo"
       and "Bogotá" in r["recomendada"]["ruta"],
       "con un supuesto del equipo, el criterio por defecto sigue siendo el "
       "compuesto sin riesgo")
    texto = formatear(r)
    ok("supuesto del equipo" in texto and "Advertencia" in texto,
       "la salida marca el supuesto y lo advierte")
    costos = cargar_costos()
    costos["estados"]["otros costos por km"] = "verificada"
    costos["verificados"] = True
    verificado = construir_grafo(costos=costos)
    r = recomendar("Duitama", "Puente Nacional", grafo=verificado)
    ok(r["criterio_por_defecto"] == "costo_operativo"
       and r["criterio_efectivo"] == "costo_operativo",
       "con todos los insumos verificados, el criterio por defecto es el "
       "costo operativo")
    esperado, _ = minimo_enumerado("Duitama", "Puente Nacional",
                                   "costo_operativo_cop")
    ok(abs(r["recomendada"]["costo_operativo_cop"] - esperado) < 1e-6,
       "el costo operativo recomendado es el mínimo de los caminos simples")
    ok("operativo" in formatear(r).split("Regla:")[1][:80],
       "la regla impresa dice costo operativo")


def prueba_heuristicas():
    print("Heurísticas de los criterios nuevos")
    coord = cargar_coordenadas()
    alfa = alfa_minimo(grafo, coord)
    for criterio in NUEVOS:
        h = Heuristica(grafo, coord, criterio, alfa)
        a = verificar_admisibilidad(grafo, h, criterio)
        c = verificar_consistencia(grafo, h, criterio)
        ok(a["violaciones"] == 0 and c["violaciones"] == 0
           and a["margen_minimo"] >= -1e-12,
           f"{criterio}: admisible y consistente (margen mínimo "
           f"{a['margen_minimo']:.6f}, "
           f"{'limitada' if h.limitada else 'no limitada'})")


def prueba_umbral():
    print("Umbral exacto del costo variable por km")
    u = umbral_exacto(grafo, "Duitama", "Puente Nacional")
    rutas = rutas_del_par(grafo, "Duitama", "Puente Nacional")
    ok(len(rutas) == 2, "el caso central tiene dos rutas simples")
    a, b = sorted(rutas, key=lambda r: r["km"])
    esperado = (a["peaje_cop"] - b["peaje_cop"]) / (b["km"] - a["km"])
    ok(abs(u["cop_por_km"] - esperado) < 1e-9,
       f"umbral = (peaje A - peaje B) / (km B - km A) = {esperado:.3f} "
       "COP/km")
    for factor, via in ((1.001, "Bogotá"), (0.999, "Santander")):
        c = u["cop_por_km"] * factor
        costos = cargar_costos(precio_galon=c, rendimiento=1.0, otros_km=0.0)
        g = construir_grafo(costos=costos)
        r = recomendar("Duitama", "Puente Nacional", grafo=g,
                       criterio="costo_operativo")
        enumerado = min(
            rutas_del_par(g, "Duitama", "Puente Nacional"),
            key=lambda x: x["peaje_cop"] + c * x["km"])
        ok(r["recomendada"]["ruta"] == enumerado["ruta"]
           and (via == "Bogotá") == ("Bogotá" in r["recomendada"]["ruta"]),
           f"con {factor} veces el umbral la recomendación es la ruta por "
           f"{via}")
    ok(umbral_exacto(grafo, "Bogotá", "Granada") is None,
       "un par de ruta única no tiene umbral")


def prueba_opciones():
    print("Opciones del usuario")
    costos = cargar_costos(precio_galon=12000, rendimiento=10, otros_km=50)
    ok(costos["estados"] == {"precio del galón": "dado por el usuario",
                             "rendimiento": "dado por el usuario",
                             "otros costos por km": "dado por el usuario"}
       and abs(costos["costo_variable_cop_km"] - 1250) < 1e-9,
       "las opciones anulan la configuración y se rotulan «dado por el "
       "usuario» (12 000 / 10 + 50 = 1 250 COP/km)")
    r = recomendar("Duitama", "Puente Nacional", costos=costos)
    texto = formatear(r)
    ok("dado por el usuario" in texto and "1 250.0 COP por km" in texto,
       "la salida rotula los insumos dados por el usuario")
    ok(r["criterio_por_defecto"] == "compuesto_sin_riesgo",
       "lo dado por el usuario no es «verificada»: el criterio por defecto "
       "no cambia")
    w = {"distancia": 0.1, "peaje": 0.2, "riesgo": 0.3, "costo_variable": 0.4}
    g = construir_grafo(costos=cargar_costos(pesos_total=w))
    ok(g.graph["pesos_total"] == w, "--pesos anula los pesos del compuesto "
       "total")
    for argumentos, mensaje in (
            (["Duitama", "Tunja", "--precio-galon", "abc"], "número"),
            (["Duitama", "Tunja", "--rendimiento", "0"], "mayor que 0"),
            (["Duitama", "Tunja", "--pesos", "0.5,0.5"], "cuatro números"),
            (["Duitama", "Tunja", "--pesos", "0.5,0.5,0.5,0.5"], "sumen 1"),
            (["Duitama", "Tunja", "--costo-otros-km", "-3"], "negativo")):
        salida = subprocess.run(
            [sys.executable, str(RAIZ / "src" / "agente_rutas.py"),
             *argumentos], capture_output=True, text=True,
            encoding="utf-8")
        ok(salida.returncode == 1 and mensaje in salida.stdout,
           f"{' '.join(argumentos[2:])}: error claro")
    ok(main(["Duitama", "Tunja", "--precio-galon", "12000"]) == 0,
       "main acepta --precio-galon")


def main_pruebas():
    prueba_config()
    prueba_minimos()
    prueba_defecto()
    prueba_heuristicas()
    prueba_umbral()
    prueba_opciones()
    r = subprocess.run([sys.executable, "-m", "pycodestyle", __file__],
                       capture_output=True, text=True)
    ok(r.returncode == 0, "pycodestyle limpio" + r.stdout)
    print("Todas las pruebas de costos pasaron.")


if __name__ == "__main__":
    main_pruebas()
