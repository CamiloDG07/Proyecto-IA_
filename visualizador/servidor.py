"""Servidor del visualizador web de la búsqueda y del despachador.

Uso:
    python visualizador/servidor.py [--puerto 8000] [--sin-navegador]

Levanta la API y la interfaz en http://127.0.0.1:8000 (la documentación
interactiva de la API queda en /docs). Funciona sin conexión a internet: el
mapa de Leaflet, las fuentes y los estilos están en static/vendor/. El fondo
de OpenStreetMap solo se descarga si hay conexión; la interfaz tiene un
interruptor «sin fondo».

El servidor no reimplementa ninguna lógica del proyecto: las búsquedas con
traza vienen de src/trazas.py (probado contra src/busquedas.py), las cifras
de tiempo de cómputo de busquedas.medir y el despachador, Held-Karp y el ACO
de sus módulos. Aquí solo se calculan las métricas de una ruta sumando los
atributos de sus aristas.

Endpoints:
    GET  /api/red          nodos, aristas, criterios, configuración y ejemplos
    GET  /api/busqueda     traza de un algoritmo y métricas de la ruta
    GET  /api/comparar     los cinco algoritmos para un origen y un destino
    GET  /api/criterios    la ruta bajo cada uno de los nueve criterios
    POST /api/despachador  ruta con varias paradas, método y matriz
"""
import sys
from pathlib import Path
if True:  # carpetas de código en el path
    sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "src")]
import argparse
import json
import os
import platform
import threading
import webbrowser
from datetime import date

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agente import CRITERIOS
from build_graph import cargar_grafo
from busquedas import a_estrella, bfs, dfs, medir, ucs, voraz
from demostracion import REPETICIONES
from despachador import (CRITERIOS_CON_HEURISTICA, TIPOS, Despachador,
                         Solicitud, cargar_umbral)
from heuristica import Heuristica, alfa_minimo, cargar_coordenadas
from matriz_costos import MatrizCostos
from trazas import ALGORITMOS as TRAZAS

CARPETA = Path(__file__).resolve().parent
ESTATICOS = CARPETA / "static"
NOMBRES = {"bfs": "BFS", "dfs": "DFS", "ucs": "UCS", "voraz": "Voraz",
           "astar": "A*"}
BASE = {"bfs": bfs, "dfs": dfs, "ucs": ucs, "voraz": voraz,
        "astar": a_estrella}
CON_HEURISTICA = ("voraz", "astar")
DESCRIPCION_CRITERIOS = {
    "distancia": "Menor distancia en km del modelo (con piso geodésico).",
    "peaje": "Menor suma de peajes (COP, categoría III).",
    "riesgo": "Menor suma del puntaje GiZScore; solo los tramos con dato.",
    "compuesto": "Distancia, peaje y riesgo normalizados con pesos iguales; "
                 "el riesgo faltante vale 0.",
    "compuesto_sin_riesgo": "Distancia y peaje normalizados, sin riesgo.",
    "costo_operativo": "Peaje más costo variable (combustible), en COP.",
    "compuesto_total": "Distancia, peaje, riesgo y costo variable con cuatro "
                       "pesos iguales; el riesgo faltante vale 0.",
    "compuesto_total_sin_riesgo": "Compuesto total sin el término de "
                                  "riesgo.",
    "compuesto_mortalidad": "Sensibilidad: mortalidad por 100 km de la ANSV "
                            "en lugar del GiZScore.",
}
FORMULAS = {
    "distancia": "h(n) = α · d_geo(n, meta)",
    "compuesto_sin_riesgo": "h(n) = α · w1/(w1 + w2) · d_geo(n, meta) / d_max",
    "compuesto": "h(n) = α · w1 · d_geo(n, meta) / d_max",
    "compuesto_mortalidad": "h(n) = α · w1 · d_geo(n, meta) / d_max",
    "costo_operativo": "h(n) = α · c_km · d_geo(n, meta)",
    "compuesto_total_sin_riesgo": "h(n) = α · (w1 + w4)/(w1 + w2 + w4) · "
                                  "d_geo(n, meta) / d_max",
    "compuesto_total": "h(n) = α · (w1 + w4) · d_geo(n, meta) / d_max",
    "peaje": "h(n) = 0",
    "riesgo": "h(n) = 0",
}
MENSAJE_CERO = ("h = 0: el criterio no tiene información geométrica, así que "
                "A* equivale a costo uniforme (UCS) y la búsqueda voraz no "
                "tiene guía.")
MENSAJE_LIMITADO = ("Criterio «limitado»: h solo incluye el término de "
                    "distancia; los demás términos, no negativos, quedan "
                    "fuera. Sigue siendo admisible, pero informa menos.")

GRAFO = cargar_grafo()
COORDENADAS = cargar_coordenadas()
ALFA = alfa_minimo(GRAFO, COORDENADAS)
HEURISTICAS = {c: Heuristica(GRAFO, COORDENADAS, c, ALFA)
               for c in CRITERIOS}
with open(CARPETA / "config_visualizador.json", encoding="utf-8") as _f:
    CONFIG = json.load(_f)


def _procesador():
    """Nombre del procesador; en Windows, el del registro."""
    try:
        import winreg
        with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as clave:
            return winreg.QueryValueEx(clave, "ProcessorNameString")[0].strip()
    except (ImportError, OSError):
        return platform.processor() or platform.machine()


EQUIPO = {"procesador": _procesador(), "nucleos_logicos": os.cpu_count(),
          "sistema": platform.platform(), "python": platform.python_version()}


# ---- utilidades ----------------------------------------------------------
def error(codigo, mensaje):
    return HTTPException(status_code=codigo, detail=mensaje)


def validar_nodos(*nodos):
    for nodo in nodos:
        if nodo not in GRAFO:
            raise error(404, f"Nodo desconocido: {nodo}")


def validar_criterio(criterio):
    if criterio not in CRITERIOS:
        raise error(400, f"Criterio desconocido: {criterio}")


def validar_algoritmo(algoritmo):
    if algoritmo not in NOMBRES:
        raise error(400, f"Algoritmo desconocido: {algoritmo}")


def validar_par(origen, destino):
    validar_nodos(origen, destino)
    if origen == destino:
        raise error(400, "El origen y el destino deben ser distintos.")


def entre_comillas(texto):
    return f'"{texto}"' if " " in texto else texto


def buscar(algoritmo, origen, destino, criterio):
    """Ejecuta la búsqueda de busquedas.py; devuelve (función, args, h)."""
    atributo = CRITERIOS[criterio]
    h = HEURISTICAS[criterio]
    args = (GRAFO, origen, destino, atributo)
    if algoritmo in CON_HEURISTICA:
        args += (h,)
    return BASE[algoritmo], args, h


def ejecutar(algoritmo, origen, destino, criterio):
    funcion, args, _ = buscar(algoritmo, origen, destino, criterio)
    try:
        return funcion(*args)
    except ValueError as problema:
        raise error(409, str(problema)) from None


def es_optimo(resultado, origen, destino, criterio):
    optimo = ucs(GRAFO, origen, destino, CRITERIOS[criterio])["costo"]
    return resultado["costo"] <= optimo + 1e-9 * max(1.0, abs(optimo))


# ---- métricas de una ruta (todas sobre las aristas de la ruta) -----------
def metricas_ruta(ruta):
    """Distancia, peajes, costo operativo, riesgo y saltos de una ruta."""
    tramos = []
    for u, v in zip(ruta, ruta[1:]):
        d = GRAFO[u][v]
        tramos.append({
            "desde": u, "hasta": v,
            "distancia_km": d["distancia_km"],
            "distancia_oficial_km": d["distancia_oficial_km"],
            "piso": bool(d["distancia_piso_aplicado"]),
            "peaje_cop": d["peaje_cop_camion"],
            "peaje_nombre": d["peaje_nombre"],
            "costo_variable_cop": d["costo_variable_cop"],
            "costo_operativo_cop": d["costo_operativo_cop"],
            "riesgo": (d["riesgo_gizscore_prom"]
                       if d["riesgo_disponible"] else None)})
    con_riesgo = [t["riesgo"] for t in tramos if t["riesgo"] is not None]
    return {
        "ruta": list(ruta),
        "saltos": len(tramos),
        "intermedias": list(ruta[1:-1]),
        "distancia_km": sum(t["distancia_km"] for t in tramos),
        "tramos_con_piso": sum(t["piso"] for t in tramos),
        "peaje_cop": sum(t["peaje_cop"] for t in tramos),
        "peajes": [t["peaje_nombre"] for t in tramos if t["peaje_cop"] > 0],
        "costo_variable_cop": sum(t["costo_variable_cop"] for t in tramos),
        "costo_operativo_cop": sum(t["costo_operativo_cop"]
                                   for t in tramos),
        "riesgo_gizscore": sum(con_riesgo),
        "tramos_con_riesgo": len(con_riesgo),
        "tramos_sin_riesgo": len(tramos) - len(con_riesgo),
        "tramos": tramos}


def info_heuristica(criterio):
    h = HEURISTICAS[criterio]
    cero = h.factor == 0.0
    avisos = []
    if cero:
        avisos.append(MENSAJE_CERO)
    if h.limitada and not cero:
        avisos.append(MENSAJE_LIMITADO)
    return {"formula": FORMULAS[criterio], "alfa": h.alfa,
            "factor": h.factor, "limitada": h.limitada, "h_cero": cero,
            "avisos": avisos}


def comando_busqueda(origen, destino, criterio):
    return (f"python src\\demostracion.py {entre_comillas(origen)} "
            f"{entre_comillas(destino)} {criterio}")


def comando_despachador(tipo, origen, destino, paradas, obligatorias,
                        bloqueados, criterio):
    partes = [f"python src\\demostracion.py despachador {tipo} "
              f"{entre_comillas(origen)}"]
    if destino:
        partes.append(f"--destino {entre_comillas(destino)}")
    if paradas:
        partes.append(f'--paradas "{",".join(paradas)}"')
    if obligatorias:
        partes.append(f'--obligatorias "{",".join(obligatorias)}"')
    if bloqueados:
        partes.append('--bloqueados "'
                      + ";".join("/".join(b) for b in bloqueados) + '"')
    partes.append(f"--criterio {criterio}")
    return " ".join(partes)


# ---- ejemplos de la sustentación ------------------------------------------
def ejemplos():
    """Casos de la guía de demostración.

    El caso central y las cinco paradas salen de guion_demostracion.md. El
    proyecto no tiene una instancia de 19 o 20 paradas sobre la red real
    (el umbral se midió con instancias euclidianas); aquí son, desde Bogotá,
    las primeras 19 y 20 ciudades restantes en orden alfabético.
    """
    otras = [n for n in sorted(GRAFO) if n != "Bogotá"]
    return [
        {"id": "central", "titulo": "Caso central", "modo": "ruta",
         "detalle": "Duitama a Puente Nacional, A*, distancia",
         "origen": "Duitama", "destino": "Puente Nacional",
         "criterio": "distancia", "algoritmo": "astar"},
        {"id": "cinco", "titulo": "5 paradas", "modo": "despachador",
         "detalle": "Tipo d desde Bogotá: Held-Karp",
         "tipo": "d", "origen": "Bogotá", "criterio": "distancia",
         "paradas": ["Tunja", "Villeta", "Girardot", "Duitama",
                     "Zipaquirá"]},
        {"id": "diecinueve", "titulo": "19 paradas", "modo": "despachador",
         "detalle": "Límite de Held-Karp (K = 19)", "tipo": "d",
         "origen": "Bogotá", "criterio": "distancia",
         "paradas": otras[:19]},
        {"id": "veinte", "titulo": "20 paradas", "modo": "despachador",
         "detalle": "Sobre el umbral: ACO con 2-opt", "tipo": "d",
         "origen": "Bogotá", "criterio": "distancia",
         "paradas": otras[:20]},
    ]


# ---- aplicación ----------------------------------------------------------
app = FastAPI(title="Visualizador de rutas de carga",
              description="Búsqueda y despachador sobre la red de carga de "
                          "32 nodos y 32 aristas.")


@app.exception_handler(RequestValidationError)
async def validacion(_peticion: Request, excepcion: RequestValidationError):
    campos = ", ".join(".".join(str(x) for x in e["loc"][1:])
                       for e in excepcion.errors()) or "cuerpo"
    return JSONResponse(
        status_code=422,
        content={"detail": f"Solicitud inválida: revise {campos}."})


@app.get("/api/red")
def api_red():
    nodos = [{"nombre": n, "latitud": COORDENADAS[n][0],
              "longitud": COORDENADAS[n][1]} for n in sorted(GRAFO)]
    aristas = []
    for u, v, d in GRAFO.edges(data=True):
        aristas.append({
            "u": u, "v": v,
            "distancia_km": d["distancia_km"],
            "distancia_oficial_km": d["distancia_oficial_km"],
            "piso": bool(d["distancia_piso_aplicado"]),
            "peaje_cop": d["peaje_cop_camion"],
            "peaje_nombre": d["peaje_nombre"],
            "riesgo": (d["riesgo_gizscore_prom"]
                       if d["riesgo_disponible"] else None),
            "costos": {c: d[a] for c, a in CRITERIOS.items()}})
    criterios = {c: {"atributo": a, "descripcion": DESCRIPCION_CRITERIOS[c],
                     "factor_heuristica": HEURISTICAS[c].factor,
                     "limitado": HEURISTICAS[c].limitada}
                 for c, a in CRITERIOS.items()}
    costos = GRAFO.graph["costos"]
    return {
        "nodos": nodos, "aristas": aristas, "criterios": criterios,
        "algoritmos": NOMBRES, "alfa": ALFA,
        "costos": {"precio_galon_cop": costos["precio_galon_cop"],
                   "costo_variable_cop_km": costos["costo_variable_cop_km"],
                   "estados": costos["estados"]},
        "tipos": TIPOS, "config": CONFIG, "equipo": EQUIPO,
        "repeticiones": REPETICIONES, "ejemplos": ejemplos()}


@app.get("/api/busqueda")
def api_busqueda(origen: str, destino: str, criterio: str = "distancia",
                 algoritmo: str = "astar"):
    validar_par(origen, destino)
    validar_criterio(criterio)
    validar_algoritmo(algoritmo)
    funcion, args, h = buscar(algoritmo, origen, destino, criterio)
    traza = TRAZAS[algoritmo]
    try:
        resultado = traza(GRAFO, origen, destino, CRITERIOS[criterio], h)
        tiempo = medir(funcion, REPETICIONES, *args)
    except ValueError as problema:
        raise error(409, str(problema)) from None
    return {
        "origen": origen, "destino": destino, "criterio": criterio,
        "algoritmo": algoritmo, "nombre_algoritmo": NOMBRES[algoritmo],
        "atributo": CRITERIOS[criterio],
        "ruta": resultado["ruta"], "costo": resultado["costo"],
        "saltos": resultado["saltos"],
        "expandidos": resultado["nodos_expandidos"],
        "generados": resultado["nodos_generados"],
        "frontera_max": resultado["frontera_max"],
        "reexpansiones": resultado["reexpansiones"],
        "optimo": es_optimo(resultado, origen, destino, criterio),
        "entradas": resultado["entradas"], "pasos": resultado["pasos"],
        "h": resultado["h"],
        "heuristica": info_heuristica(criterio),
        "metricas": metricas_ruta(resultado["ruta"]),
        "tiempo": {"media_ms": tiempo["tiempo_media_s"] * 1e3,
                   "desviacion_ms": tiempo["tiempo_desv_s"] * 1e3,
                   "repeticiones": tiempo["repeticiones"],
                   "memoria_pico_kib": tiempo["memoria_pico_kib"],
                   "fecha": date.today().isoformat(), "equipo": EQUIPO},
        "comando": comando_busqueda(origen, destino, criterio)}


@app.get("/api/comparar")
def api_comparar(origen: str, destino: str, criterio: str = "distancia"):
    validar_par(origen, destino)
    validar_criterio(criterio)
    filas = []
    for algoritmo in NOMBRES:
        r = ejecutar(algoritmo, origen, destino, criterio)
        filas.append({
            "algoritmo": algoritmo, "nombre": NOMBRES[algoritmo],
            "ruta": r["ruta"], "costo": r["costo"], "saltos": r["saltos"],
            "expandidos": r["nodos_expandidos"],
            "generados": r["nodos_generados"],
            "frontera_max": r["frontera_max"],
            "reexpansiones": r["reexpansiones"],
            "optimo": es_optimo(r, origen, destino, criterio),
            "metricas": metricas_ruta(r["ruta"])})
    return {"origen": origen, "destino": destino, "criterio": criterio,
            "heuristica": info_heuristica(criterio), "algoritmos": filas,
            "comando": comando_busqueda(origen, destino, criterio)}


@app.get("/api/criterios")
def api_criterios(origen: str, destino: str, algoritmo: str = "astar"):
    validar_par(origen, destino)
    validar_algoritmo(algoritmo)
    filas = []
    for criterio in CRITERIOS:
        r = ejecutar(algoritmo, origen, destino, criterio)
        via = None
        if "Bucaramanga" in r["ruta"]:
            via = "Santander"
        elif "Bogotá" in r["ruta"]:
            via = "Bogotá"
        filas.append({
            "criterio": criterio, "ruta": r["ruta"], "costo": r["costo"],
            "expandidos": r["nodos_expandidos"],
            "limitado": HEURISTICAS[criterio].limitada, "via": via,
            "metricas": metricas_ruta(r["ruta"])})
    return {"origen": origen, "destino": destino, "algoritmo": algoritmo,
            "nombre_algoritmo": NOMBRES[algoritmo], "criterios": filas,
            "comando": comando_busqueda(origen, destino, "distancia")}


class PeticionDespachador(BaseModel):
    """Cuerpo de POST /api/despachador (como Despachador y Solicitud)."""

    tipo: str
    origen: str
    destino: str | None = None
    paradas: list[str] = Field(default_factory=list)
    obligatorias: list[str] = Field(default_factory=list)
    bloqueados: list[list[str]] = Field(default_factory=list)
    criterio: str = "distancia"
    ida_vuelta: bool = False
    bloqueados_regreso: list[list[str]] | None = None


def nodos_de_matriz(tipo, origen, destino, paradas, obligatorias):
    """Paradas de las que el despachador arma la matriz de costos."""
    if tipo == "a":
        return [origen, destino]
    if tipo == "b":
        return [origen, *paradas, destino]
    if tipo == "c":
        return [origen, *obligatorias, destino]
    return [origen, *paradas]


def resolver(tipo, origen, destino, paradas, obligatorias, bloqueados,
             criterio):
    """Una solicitud al Despachador, con métricas, matriz y comando."""
    bloqueos = []
    for tramo in bloqueados:
        if len(tramo) != 2 or not GRAFO.has_edge(*tramo):
            raise error(400, f"El tramo {'/'.join(tramo)} no existe en la "
                             "red.")
        bloqueos.append(tuple(tramo))
    if tipo in ("a", "b", "c"):
        if not destino:
            raise error(400, f"El tipo {tipo} requiere destino.")
        validar_par(origen, destino)
    validar_nodos(origen, *paradas, *obligatorias)
    if destino:
        validar_nodos(destino)
    solicitud = Solicitud(
        tipo, origen, destino, tuple(paradas), criterio,
        {"obligatorias": list(obligatorias), "bloqueados": bloqueos})
    try:
        salida = Despachador(GRAFO, COORDENADAS).resolver(solicitud)
        nodos = nodos_de_matriz(tipo, origen, destino, paradas,
                                obligatorias)
        heuristica = (HEURISTICAS[criterio]
                      if criterio in CRITERIOS_CON_HEURISTICA else None)
        matriz = MatrizCostos(GRAFO, nodos, CRITERIOS[criterio], bloqueos,
                              heuristica)
    except FileNotFoundError as problema:
        raise error(500, f"Falta un archivo del proyecto: {problema}") \
            from None
    except ValueError as problema:
        raise error(400, str(problema)) from None
    for tramo in salida["tramos"]:
        tramo["metricas"] = metricas_ruta(tramo["ruta"])
    metricas = salida["metricas"]
    umbral = metricas.get("umbral_k")
    if umbral is None:
        umbral = cargar_umbral()
    aco = None
    if "curva_media_aco" in metricas:
        aco = {"curva": metricas["curva_media_aco"],
               "costo_medio": metricas["costo_medio_aco"],
               "costo_peor": metricas["costo_peor_aco"],
               "desviacion": metricas["desviacion_aco"]}
    return {
        "tipo": tipo, "nombre_tipo": salida["tipo"], "criterio": criterio,
        "origen": origen, "destino": destino,
        "ruta": salida["ruta"], "orden_paradas": salida["orden_paradas"],
        "costo": salida["costo"], "metodo": salida["metodo"],
        "motivo": salida["motivo"], "k": metricas.get("k"),
        "umbral_k": umbral,
        "paradas": {"libres": len(paradas), "obligatorias":
                    len(obligatorias)},
        "tramos": salida["tramos"], "metricas_despachador": metricas,
        "metricas": metricas_ruta(salida["ruta"]),
        "matriz": {"nodos": nodos, "costos": matriz.costo.tolist()},
        "aco": aco,
        "comando": comando_despachador(tipo, origen, destino, paradas,
                                       obligatorias, bloqueados, criterio)}


@app.post("/api/despachador")
def api_despachador(p: PeticionDespachador):
    if p.tipo not in TIPOS:
        raise error(400, f"Tipo de problema desconocido: {p.tipo}")
    validar_criterio(p.criterio)
    # cada tipo usa solo los campos que su definición contempla
    paradas = p.paradas if p.tipo in ("b", "d", "e") else []
    obligatorias = p.obligatorias if p.tipo == "c" else []
    destino = p.destino if p.tipo in ("a", "b", "c") else None
    ida = resolver(p.tipo, p.origen, destino, paradas, obligatorias,
                   p.bloqueados, p.criterio)
    respuesta = dict(ida, regreso=None)
    if p.ida_vuelta and p.tipo in ("a", "b", "c"):
        bloqueos = (p.bloqueados if p.bloqueados_regreso is None
                    else p.bloqueados_regreso)
        respuesta["regreso"] = resolver(
            p.tipo, destino, p.origen, paradas[::-1], obligatorias[::-1],
            bloqueos, p.criterio)
    return respuesta


@app.get("/", include_in_schema=False)
def inicio():
    return FileResponse(ESTATICOS / "index.html")


app.mount("/static", StaticFiles(directory=ESTATICOS), name="static")


def main(argumentos):
    lector = argparse.ArgumentParser(prog="servidor.py")
    lector.add_argument("--puerto", type=int, default=8000)
    lector.add_argument("--sin-navegador", action="store_true")
    a = lector.parse_args(argumentos)
    direccion = f"http://127.0.0.1:{a.puerto}"
    if not a.sin_navegador:
        threading.Timer(1.5, webbrowser.open, args=(direccion,)).start()
    print(f"Visualizador en {direccion} (Ctrl+C para detener)")
    uvicorn.run(app, host="127.0.0.1", port=a.puerto, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
