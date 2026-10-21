"""Pruebas de la API del visualizador (visualizador/servidor.py).

La aplicación se llama directamente por la interfaz ASGI, con un llamador
mínimo propio: no abre puertos y no necesita dependencias de prueba. Se
comprueban los valores conocidos del informe en el caso central (370.54 km
por Bogotá y 654.25 km por Santander, A* con distancia y 14 expandidos), los
errores con mensaje en español, el despachador (Held-Karp con k <= 19 y ACO
si no), la coherencia de las métricas con las aristas de la ruta y que cada
respuesta coincide con la salida directa de los módulos del proyecto.

La última prueba levanta el servidor en un puerto libre, pide `/`,
`/api/red` y una búsqueda con urllib, y lo apaga.
"""
import sys
from pathlib import Path
if True:  # carpetas de código en el path
    sys.path[:0] = [str(Path(__file__).resolve().parents[1] / c)
                    for c in ("src", "experimentos", "informe", "pruebas",
                              "visualizador")]
import asyncio
import json
import socket
import subprocess
import tomllib
import time
import urllib.parse
import urllib.request

import servidor
from agente import CRITERIOS
from busquedas import a_estrella, bfs, dfs, ucs, voraz
from despachador import Despachador, Solicitud
from heuristica import Heuristica

RAIZ = Path(__file__).resolve().parents[1]
CENTRAL = {"origen": "Duitama", "destino": "Puente Nacional"}
EPS = 1e-6


def verificar(condicion, mensaje):
    if not condicion:
        raise AssertionError(mensaje)


async def _llamar(metodo, ruta, consulta="", cuerpo=None, cabeceras=None):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else b""
    alcance = {
        "type": "http", "method": metodo, "path": ruta,
        "raw_path": ruta.encode(), "query_string": consulta.encode(),
        "headers": [(b"content-type", b"application/json")],
        "server": ("prueba", 80), "scheme": "http", "http_version": "1.1",
        "client": ("cliente", 1), "root_path": ""}
    entregado = False

    async def recibir():
        nonlocal entregado
        if not entregado:
            entregado = True
            return {"type": "http.request", "body": datos,
                    "more_body": False}
        await asyncio.sleep(3600)

    salida = {"cuerpo": b"", "estado": None}

    async def enviar(mensaje):
        if mensaje["type"] == "http.response.start":
            salida["estado"] = mensaje["status"]
            if cabeceras is not None:
                cabeceras.update({k.decode(): v.decode()
                                  for k, v in mensaje["headers"]})
        elif mensaje["type"] == "http.response.body":
            salida["cuerpo"] += mensaje.get("body", b"")

    await servidor.app(alcance, recibir, enviar)
    return salida["estado"], salida["cuerpo"]


def pedir(metodo, ruta, consulta="", cuerpo=None):
    """(estado, JSON) de una llamada a la API."""
    estado, datos = asyncio.run(_llamar(metodo, ruta, consulta, cuerpo))
    return estado, json.loads(datos)


def get(ruta, **parametros):
    estado, datos = pedir("GET", ruta, urllib.parse.urlencode(parametros))
    return estado, datos


def ok(ruta, **parametros):
    estado, datos = get(ruta, **parametros)
    verificar(estado == 200, f"{ruta} {parametros}: estado {estado}: "
              f"{datos}")
    return datos


def despachar(**cuerpo):
    return pedir("POST", "/api/despachador", cuerpo=cuerpo)


def prueba_red():
    print("GET /api/red")
    r = ok("/api/red")
    verificar(len(r["nodos"]) == 32 and len(r["aristas"]) == 32,
              "la red tiene 32 nodos y 32 aristas")
    verificar(list(r["criterios"]) == list(CRITERIOS), "nueve criterios")
    limitados = {c for c, d in r["criterios"].items() if d["limitado"]}
    verificar(limitados == {"compuesto", "riesgo", "compuesto_total",
                            "compuesto_mortalidad"}, "criterios limitados")
    verificar(r["criterios"]["distancia"]["factor_heuristica"] == 1.0
              and r["criterios"]["peaje"]["factor_heuristica"] == 0.0,
              "factor de la heurística por criterio")
    verificar(r["alfa"] == 1.0, "alfa = 1 con el piso geodésico")
    velocidad = r["config"]["velocidad_promedio_kmh"]
    verificar(velocidad["valor"] == 50
              and velocidad["estado"] == "supuesto del equipo"
              and (velocidad["minimo"], velocidad["maximo"]) == (20, 90),
              "velocidad supuesta de 50 km/h, rotulada como supuesto")
    arista = next(a for a in r["aristas"]
                  if {a["u"], a["v"]} == {"Bogotá", "Cajicá"})
    verificar(arista["peaje_nombre"] == "FUSCA" and arista["riesgo"] is None
              and not arista["piso"] and len(arista["costos"]) == 9,
              "atributos de una arista")
    ids = [e["id"] for e in r["ejemplos"]]
    verificar(ids == ["central", "cinco", "diecinueve", "veinte"],
              "casos de ejemplo")
    ej = {e["id"]: e for e in r["ejemplos"]}
    verificar(ej["cinco"]["paradas"] == ["Tunja", "Villeta", "Girardot",
                                         "Duitama", "Zipaquirá"],
              "las 5 paradas son las de guion_demostracion.md")
    verificar(len(ej["diecinueve"]["paradas"]) == 19
              and len(ej["veinte"]["paradas"]) == 20
              and "Bogotá" not in ej["veinte"]["paradas"]
              and ej["veinte"]["paradas"][:19] == ej["diecinueve"]["paradas"],
              "instancias de demostración de 19 y 20 paradas")


def prueba_coordenadas():
    print("GET /api/red: coordenadas de los 32 nodos dentro de Colombia")
    nodos = {n["nombre"]: n for n in ok("/api/red")["nodos"]}
    verificar(len(nodos) == 32, "32 nodos con coordenadas")
    for n in nodos.values():
        verificar(isinstance(n["latitud"], float)
                  and isinstance(n["longitud"], float)
                  and -4.3 <= n["latitud"] <= 13.5
                  and -79.1 <= n["longitud"] <= -66.8,
                  f"{n['nombre']} fuera de Colombia: {n}")
    bogota = nodos["Bogotá"]
    verificar(nodos["Duitama"]["latitud"] > bogota["latitud"]
              and nodos["Duitama"]["longitud"] > bogota["longitud"],
              "Duitama al noreste de Bogotá")
    pn, barbosa = nodos["Puente Nacional"], nodos["Barbosa"]
    verificar(pn["latitud"] > bogota["latitud"]
              and abs(pn["latitud"] - barbosa["latitud"]) < 0.4
              and abs(pn["longitud"] - barbosa["longitud"]) < 0.4,
              "Puente Nacional al norte de Bogotá y cerca de Barbosa")
    verificar(nodos["Villavicencio"]["latitud"] < bogota["latitud"]
              and nodos["Villavicencio"]["longitud"] > bogota["longitud"],
              "Villavicencio al sureste de Bogotá")


def prueba_despliegue():
    print("Despliegue: pyproject.toml, requirements.txt y .vercelignore")
    if not (RAIZ / "pyproject.toml").exists():
        return  # el paquete del entregable no lleva los archivos de Vercel
    with open(RAIZ / "pyproject.toml", "rb") as f:
        proyecto = tomllib.load(f)
    verificar("project" in proyecto, "falta la tabla [project] que uv exige")
    verificar(proyecto["tool"]["vercel"]["entrypoint"]
              == "visualizador.servidor:app", "entrypoint de Vercel")
    pedidos = proyecto["project"]["dependencies"]
    with open(RAIZ / "requirements.txt", encoding="utf-8") as f:
        requisitos = [x.strip() for x in f if x.strip()]
    for dependencia in pedidos:
        verificar(dependencia in requisitos,
                  f"{dependencia} no está igual en requirements.txt")
    nombres = {d.split("=")[0].strip().lower() for d in pedidos}
    verificar({"fastapi", "networkx", "numpy"} <= nombres
              and not nombres & {"scipy", "matplotlib", "pycodestyle"},
              "solo las dependencias que el servidor importa")
    version = (RAIZ / ".python-version").read_text().strip()
    verificar(proyecto["project"]["requires-python"] == f">={version}",
              "requires-python coherente con .python-version")
    ignorados = [x.strip() for x in (RAIZ / ".vercelignore").read_text(
        encoding="utf-8").splitlines() if x.strip()
        and not x.startswith("#")]
    for necesario in ("pyproject.toml", "vercel.json", "src", "visualizador",
                      "outputs/datos", "config_costos.json",
                      "data/carga/coordenadas_nodos.csv"):
        verificar(necesario not in ignorados, f"{necesario} está excluido")
    codigo = subprocess.run(
        [sys.executable, "-B", "-c",
         "import sys; sys.path[:0] = ['visualizador']; import servidor; "
         "raise SystemExit(any(m in sys.modules for m in "
         "('scipy', 'matplotlib', 'pycodestyle')))"],
        cwd=RAIZ).returncode
    verificar(codigo == 0, "el servidor importa scipy, matplotlib o "
              "pycodestyle")


def prueba_salud_y_limites():
    print("GET /api/salud y límites de la entrada")
    estado, r = get("/api/salud")
    verificar(estado == 200 and r == {"estado": "ok"}, "/api/salud")
    nombres = sorted(servidor.GRAFO)
    libres = [n for n in nombres if n != "Bogotá"]
    estado, r = despachar(tipo="d", origen="Bogotá", paradas=libres[:21])
    verificar(estado == 422 and "máximo 20 paradas" in r["detail"],
              "21 paradas libres se rechazan con 422 en español")
    estado, r = despachar(tipo="c", origen="Bogotá", destino="Tunja",
                          obligatorias=libres[:21])
    verificar(estado == 422 and "máximo 20 paradas" in r["detail"],
              "21 obligatorias se rechazan")
    aristas = [list(par) for par in servidor.GRAFO.edges()]
    estado, r = despachar(tipo="a", origen="Bogotá", destino="Tunja",
                          bloqueados=aristas * 3)
    verificar(estado == 422 and "aristas bloqueadas" in r["detail"],
              "demasiados bloqueos se rechazan")
    grande = json.dumps({"tipo": "d", "origen": "Bogotá",
                         "paradas": ["x" * 100] * 1000}).encode()
    verificar(len(grande) > servidor.MAX_CUERPO, "cuerpo de prueba grande")
    alcance = {"type": "http", "method": "POST",
               "path": "/api/despachador", "raw_path": b"",
               "query_string": b"", "server": ("prueba", 80),
               "scheme": "http", "http_version": "1.1",
               "client": ("c", 1), "root_path": "",
               "headers": [(b"content-type", b"application/json"),
                           (b"content-length", str(len(grande)).encode())]}
    salida = {}

    async def llamar():
        enviado = False

        async def recibir():
            nonlocal enviado
            if not enviado:
                enviado = True
                return {"type": "http.request", "body": grande,
                        "more_body": False}
            await asyncio.sleep(3600)

        async def enviar(mensaje):
            if mensaje["type"] == "http.response.start":
                salida["estado"] = mensaje["status"]
            elif mensaje["type"] == "http.response.body":
                salida["cuerpo"] = salida.get("cuerpo", b"") + mensaje.get(
                    "body", b"")
        await servidor.app(alcance, recibir, enviar)

    asyncio.run(llamar())
    verificar(salida["estado"] == 413 and "demasiado grande"
              in json.loads(salida["cuerpo"])["detail"],
              "cuerpo de más de 64 KiB: 413")
    estado, r = despachar(tipo="d", origen="Bogotá", paradas=libres[:20])
    verificar(estado == 200 and r["k"] == 20, "20 paradas siguen válidas")


def prueba_solo_lectura():
    print("El servidor no escribe en disco (sistema de archivos de solo "
          "lectura)")
    import builtins
    original = builtins.open
    escrituras = []

    def vigilado(archivo, modo="r", *args, **kwargs):
        if any(c in str(modo) for c in "wax+"):
            escrituras.append(str(archivo))
            raise PermissionError(f"solo lectura: {archivo}")
        return original(archivo, modo, *args, **kwargs)

    builtins.open = vigilado
    try:
        ok("/api/salud")
        ok("/api/red")
        ok("/api/busqueda", **CENTRAL, criterio="distancia",
           algoritmo="astar")
        ok("/api/comparar", **CENTRAL, criterio="peaje")
        ok("/api/criterios", **CENTRAL)
        estado, d = despachar(tipo="d", origen="Bogotá",
                              paradas=["Tunja", "Villeta", "Girardot"])
        verificar(estado == 200, f"despachador: {d}")
        for ruta in ("/", "/static/app.js", "/docs"):
            estado, _ = asyncio.run(_llamar("GET", ruta))
            verificar(estado == 200, ruta)
    finally:
        builtins.open = original
    verificar(not escrituras, f"intentó escribir: {escrituras}")


def prueba_busqueda():
    print("GET /api/busqueda: caso central")
    b = ok("/api/busqueda", **CENTRAL, criterio="distancia",
           algoritmo="astar")
    verificar(round(b["costo"], 2) == 370.54, "370.54 km por Bogotá")
    verificar("Bogotá" in b["ruta"] and "Bucaramanga" not in b["ruta"],
              "ruta por Bogotá")
    verificar(b["expandidos"] == 14, "A* con distancia expande 14 nodos")
    verificar((b["generados"], b["frontera_max"], b["reexpansiones"])
              == (19, 7, 0), "generados, frontera máxima y reexpansiones")
    verificar(b["optimo"] is True, "A* es óptimo")
    m = b["metricas"]
    verificar(round(m["distancia_km"], 2) == 370.54 and m["saltos"] == 8
              and m["peaje_cop"] == 170800 and m["tramos_con_piso"] == 4
              and m["tramos_sin_riesgo"] == 4
              and round(m["costo_operativo_cop"]) == 599510
              and len(m["peajes"]) == 6, "métricas de la ruta")
    verificar(m["intermedias"] == b["ruta"][1:-1], "ciudades intermedias")
    verificar(b["tiempo"]["repeticiones"] == 200
              and b["tiempo"]["media_ms"] > 0
              and b["tiempo"]["equipo"]["procesador"]
              and b["tiempo"]["fecha"], "tiempo de cómputo de 200 corridas")
    verificar(len(b["pasos"]) == b["expandidos"] + 2
              and b["pasos"][-1]["resultado"] == "meta", "pasos de la traza")
    verificar(len(b["h"]) == 32 and b["h"]["Puente Nacional"] == 0,
              "tabla h(n)")
    verificar(b["heuristica"]["formula"].startswith("h(n) = α")
              and not b["heuristica"]["avisos"], "heurística de distancia")
    verificar(b["comando"] == 'python src\\demostracion.py Duitama '
              '"Puente Nacional" distancia', "comando equivalente")
    print("  coincide con busquedas.py en los cinco algoritmos")
    grafo, coordenadas = servidor.GRAFO, servidor.COORDENADAS
    funciones = {"bfs": bfs, "dfs": dfs, "ucs": ucs, "voraz": voraz,
                 "astar": a_estrella}
    for criterio, atributo in CRITERIOS.items():
        h = Heuristica(grafo, coordenadas, criterio, servidor.ALFA)
        for algoritmo, funcion in funciones.items():
            args = (grafo, "Duitama", "Puente Nacional", atributo)
            if algoritmo in ("voraz", "astar"):
                args += (h,)
            esperado = funcion(*args)
            r = servidor.ejecutar(algoritmo, "Duitama", "Puente Nacional",
                                  criterio)
            verificar(r["ruta"] == esperado["ruta"]
                      and r["costo"] == esperado["costo"]
                      and r["nodos_expandidos"]
                      == esperado["nodos_expandidos"],
                      f"{algoritmo} {criterio}")
    b2 = ok("/api/busqueda", **CENTRAL, criterio="peaje", algoritmo="astar")
    verificar(round(b2["metricas"]["distancia_km"], 2) == 654.25
              and "Bucaramanga" in b2["ruta"], "654.25 km por Santander")
    verificar(b2["heuristica"]["h_cero"]
              and "UCS" in b2["heuristica"]["avisos"][0],
              "h = 0 advierte que A* equivale a UCS")
    b3 = ok("/api/busqueda", **CENTRAL, criterio="compuesto",
            algoritmo="voraz")
    verificar(b3["heuristica"]["limitada"] and any(
        "limitado" in a for a in b3["heuristica"]["avisos"]),
        "criterio limitado advertido")
    b4 = ok("/api/busqueda", **CENTRAL, criterio="distancia",
            algoritmo="bfs")
    verificar(round(b4["metricas"]["distancia_km"], 2) == 654.25
              and b4["optimo"] is False, "BFS no es óptimo en este par")


def prueba_metricas_coherentes():
    print("Las métricas son la suma de las aristas de la ruta")
    for algoritmo in ("bfs", "astar"):
        b = ok("/api/busqueda", origen="Bucaramanga", destino="Bogotá",
               criterio="compuesto_total", algoritmo=algoritmo)
        m = b["metricas"]
        verificar(abs(m["distancia_km"] - sum(
            servidor.GRAFO[u][v]["distancia_km"]
            for u, v in zip(b["ruta"], b["ruta"][1:]))) < EPS, "distancia")
        verificar(abs(m["costo_operativo_cop"] - m["peaje_cop"]
                      - m["costo_variable_cop"]) < 1e-3,
                  "costo operativo = peajes + costo variable")
        verificar(m["tramos_con_riesgo"] + m["tramos_sin_riesgo"]
                  == m["saltos"], "tramos con y sin dato de riesgo")


def prueba_comparar():
    print("GET /api/comparar")
    c = ok("/api/comparar", **CENTRAL, criterio="distancia")
    filas = {f["algoritmo"]: f for f in c["algoritmos"]}
    verificar(list(filas) == ["bfs", "dfs", "ucs", "voraz", "astar"],
              "cinco algoritmos")
    verificar([filas[a]["optimo"] for a in filas]
              == [False, False, True, True, True], "optimalidad")
    verificar(round(filas["ucs"]["costo"], 2) == 370.54
              and filas["astar"]["expandidos"] == 14
              and filas["bfs"]["expandidos"] == 25
              and filas["voraz"]["expandidos"] == 12,
              "expandidos y costos del informe")
    for f in filas.values():
        verificar(f["metricas"]["ruta"] == f["ruta"], "métricas por ruta")


def prueba_criterios():
    print("GET /api/criterios: el compromiso entre criterios")
    c = ok("/api/criterios", **CENTRAL, algoritmo="astar")
    filas = {f["criterio"]: f for f in c["criterios"]}
    verificar(list(filas) == list(CRITERIOS), "nueve criterios")
    for criterio in ("distancia", "compuesto_sin_riesgo", "costo_operativo",
                     "compuesto_total_sin_riesgo", "compuesto_mortalidad"):
        verificar(filas[criterio]["via"] == "Bogotá"
                  and round(filas[criterio]["metricas"]["distancia_km"], 2)
                  == 370.54, f"{criterio} por Bogotá")
    for criterio in ("peaje", "riesgo", "compuesto", "compuesto_total"):
        verificar(filas[criterio]["via"] == "Santander"
                  and round(filas[criterio]["metricas"]["distancia_km"], 2)
                  == 654.25, f"{criterio} por Santander")
    verificar(filas["peaje"]["metricas"]["peaje_cop"] == 100200
              and filas["distancia"]["metricas"]["peaje_cop"] == 170800,
              "peajes de los dos corredores")


def prueba_errores():
    print("Errores con código HTTP y mensaje en español")
    estado, r = get("/api/busqueda", origen="Atlantis", destino="Bogotá")
    verificar(estado == 404 and r["detail"] == "Nodo desconocido: Atlantis",
              "nodo desconocido")
    estado, r = get("/api/busqueda", origen="Bogotá", destino="Bogotá")
    verificar(estado == 400 and "distintos" in r["detail"],
              "origen igual a destino")
    estado, r = get("/api/comparar", origen="Bogotá", destino="Tunja",
                    criterio="velocidad")
    verificar(estado == 400 and r["detail"] == "Criterio desconocido: "
              "velocidad", "criterio desconocido")
    estado, r = get("/api/busqueda", origen="Bogotá", destino="Tunja",
                    algoritmo="dijkstra")
    verificar(estado == 400 and "Algoritmo desconocido" in r["detail"],
              "algoritmo desconocido")
    estado, r = get("/api/criterios", origen="Bogotá")
    verificar(estado == 422 and "destino" in r["detail"]
              and "Solicitud inválida" in r["detail"],
              "falta un parámetro")
    estado, r = despachar(tipo="z", origen="Bogotá")
    verificar(estado == 400 and "Tipo de problema desconocido" in r["detail"],
              "tipo desconocido")
    estado, r = despachar(tipo="a", origen="Bogotá")
    verificar(estado == 400 and "requiere destino" in r["detail"],
              "tipo a sin destino")
    estado, r = despachar(tipo="a", origen="Bogotá", destino="Bogotá")
    verificar(estado == 400 and "distintos" in r["detail"],
              "despachador con origen igual a destino")
    estado, r = despachar(tipo="d", origen="Bogotá", paradas=["Nunca"])
    verificar(estado == 404 and "Nodo desconocido" in r["detail"],
              "parada desconocida")
    estado, r = despachar(tipo="a", origen="Bogotá", destino="Tunja",
                          bloqueados=[["Bogotá", "Duitama"]])
    verificar(estado == 400 and "no existe en la red" in r["detail"],
              "arista inexistente")
    estado, r = despachar(tipo="a", origen="Duitama",
                          destino="Puente Nacional",
                          bloqueados=[["Tunja", "Chocontá"],
                                      ["Bucaramanga", "San Gil"]])
    verificar(estado == 400 and "Sin ruta" in r["detail"],
              "bloqueos que desconectan")
    estado, r = despachar(tipo="d", origen="Bogotá", paradas=[])
    verificar(estado == 400, "orden libre sin paradas")


def solicitud_directa(tipo, origen, destino=None, paradas=(),
                      obligatorias=(), bloqueados=(), criterio="distancia"):
    d = Despachador(servidor.GRAFO, servidor.COORDENADAS)
    return d.resolver(Solicitud(
        tipo, origen, destino, tuple(paradas), criterio,
        {"obligatorias": list(obligatorias),
         "bloqueados": [tuple(b) for b in bloqueados]}))


def prueba_despachador():
    print("POST /api/despachador")
    estado, a = despachar(tipo="a", **{"origen": "Duitama",
                                       "destino": "Puente Nacional"})
    verificar(estado == 200 and a["metodo"] == "A* por tramo"
              and round(a["costo"], 2) == 370.54, "tipo a")
    verificar(a["regreso"] is None and a["k"] is None, "sin regreso")
    paradas = ["Tunja", "Villeta", "Girardot", "Duitama", "Zipaquirá"]
    estado, d = despachar(tipo="d", origen="Bogotá", paradas=paradas)
    esperado = solicitud_directa("d", "Bogotá", paradas=paradas)
    verificar(estado == 200 and d["metodo"] == "Held-Karp" and d["k"] == 5
              and d["umbral_k"] == 19, "cinco paradas con Held-Karp")
    verificar(d["orden_paradas"] == esperado["orden_paradas"]
              and abs(d["costo"] - esperado["costo"]) < EPS,
              "coincide con el despachador directo")
    verificar(d["orden_paradas"][0] == d["orden_paradas"][-1] == "Bogotá"
              and sorted(d["orden_paradas"][1:-1]) == sorted(paradas),
              "visita todas las paradas y regresa")
    verificar(d["comando"] == 'python src\\demostracion.py despachador d '
              'Bogotá --paradas "Tunja,Villeta,Girardot,Duitama,Zipaquirá" '
              '--criterio distancia', "comando equivalente")
    verificar(d["aco"] is None and "no viable" not in d["motivo"],
              "sin curva de ACO con Held-Karp")
    nodos = d["matriz"]["nodos"]
    matriz = d["matriz"]["costos"]
    verificar(nodos == ["Bogotá", *paradas] and all(
        matriz[i][i] == 0 for i in range(6)), "matriz de costos")
    verificar(all(abs(matriz[i][j] - matriz[j][i]) < EPS
                  for i in range(6) for j in range(6)), "matriz simétrica")
    for t in d["tramos"]:
        verificar(abs(matriz[nodos.index(t["desde"])]
                      [nodos.index(t["hasta"])] - t["costo"]) < EPS,
                  "cada tramo coincide con la matriz")
        verificar(t["metricas"]["ruta"] == t["ruta"], "métricas del tramo")
    verificar(abs(d["metricas"]["distancia_km"] - sum(
        t["metricas"]["distancia_km"] for t in d["tramos"])) < EPS
        and d["metricas"]["ruta"] == d["ruta"],
        "las métricas de la ruta completa suman las de los tramos")
    print("  tipo c con una obligatoria y un tramo bloqueado")
    estado, c = despachar(tipo="c", origen="Duitama",
                          destino="Puente Nacional", obligatorias=["Tunja"],
                          bloqueados=[["Tunja", "Chocontá"]])
    esperado = solicitud_directa("c", "Duitama", "Puente Nacional",
                                 obligatorias=["Tunja"],
                                 bloqueados=[("Tunja", "Chocontá")])
    verificar(estado == 200 and c["ruta"] == esperado["ruta"]
              and abs(c["costo"] - esperado["costo"]) < EPS
              and ("Tunja", "Chocontá") not in zip(c["ruta"], c["ruta"][1:]),
              "tipo c con bloqueo")
    print("  ida y vuelta con un tramo bloqueado solo en el regreso")
    estado, v = despachar(tipo="a", origen="Duitama",
                          destino="Puente Nacional", ida_vuelta=True,
                          bloqueados_regreso=[["Tunja", "Chocontá"]])
    verificar(estado == 200 and v["regreso"] is not None
              and v["regreso"]["origen"] == "Puente Nacional"
              and v["ruta"][1:] != v["regreso"]["ruta"][::-1][1:],
              "el regreso difiere de la ida invertida")
    estado, e = despachar(tipo="e", origen="Bogotá",
                          paradas=["Tunja", "Villeta"])
    verificar(estado == 200 and e["metodo"] == "Held-Karp"
              and e["orden_paradas"][-1] != "Bogotá", "tipo e sin regreso")


def prueba_umbral_y_aco():
    print("Held-Karp con k = 19 y ACO con k = 20 (instancias de demostración)")
    ej = {e["id"]: e for e in ok("/api/red")["ejemplos"]}
    estado, d19 = despachar(tipo="d", origen="Bogotá",
                            paradas=ej["diecinueve"]["paradas"])
    verificar(estado == 200 and d19["k"] == 19
              and d19["metodo"] == "Held-Karp", "k = 19 usa Held-Karp")
    print("  k = 19: Held-Karp, el límite del método exacto")
    estado, d20 = despachar(tipo="d", origen="Bogotá",
                            paradas=ej["veinte"]["paradas"])
    verificar(estado == 200 and d20["k"] == 20
              and d20["metodo"].startswith("ACO"), "k = 20 usa ACO")
    verificar(d20["aco"] and len(d20["aco"]["curva"]) == 100
              and d20["aco"]["costo_medio"] >= d20["costo"] - EPS,
              "curva de convergencia de las semillas")
    verificar(sorted(d20["orden_paradas"][1:-1])
              == sorted(ej["veinte"]["paradas"]), "visita las 20 paradas")


def servidor_sin_cache():
    """Las respuestas no de API llevan Cache-Control: no-cache."""
    cabeceras = {}
    asyncio.run(_llamar("GET", "/static/estilos.css", cabeceras=cabeceras))
    return cabeceras.get("cache-control") == "no-cache"


def prueba_estaticos():
    print("Interfaz y documentación de la API")
    verificar(servidor_sin_cache(), "la interfaz se revalida siempre")
    for ruta, texto in (("/", b"Rutas de carga"), ("/docs", b"swagger"),
                        ("/static/app.js", b"use strict"),
                        ("/static/estilos.css", b"--c-ambar"),
                        ("/static/vendor/leaflet/leaflet.js", b"Leaflet"),
                        ("/static/vendor/leaflet/LICENSE", b"BSD"),
                        ("/static/vendor/fuentes/LICENCIA-fraunces.txt",
                         b"Open Font License")):
        estado, cuerpo = asyncio.run(_llamar("GET", ruta))
        verificar(estado == 200 and texto in cuerpo,
                  f"{ruta}: estado {estado}")
    for ruta, tipo in (("/static/app.js", "text/javascript"),
                       ("/static/estilos.css", "text/css"),
                       ("/static/vendor/fuentes/"
                        "ibm-plex-mono-latin-400-normal.woff2", "font/woff2"),
                       ("/static/vendor/leaflet/leaflet.css", "text/css")):
        cabeceras = {}
        asyncio.run(_llamar("GET", ruta, cabeceras=cabeceras))
        verificar(cabeceras.get("content-type", "").startswith(tipo),
                  f"{ruta}: tipo {cabeceras.get('content-type')}")
    for archivo in ("fraunces-latin-600-normal.woff2",
                    "public-sans-latin-400-normal.woff2",
                    "ibm-plex-mono-latin-400-normal.woff2"):
        verificar((RAIZ / "visualizador" / "static" / "vendor" / "fuentes"
                   / archivo).exists(), f"fuente local {archivo}")


def puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def prueba_arranque():
    print("Arranque del servidor en un puerto libre")
    puerto = puerto_libre()
    base = f"http://127.0.0.1:{puerto}"
    proceso = subprocess.Popen(
        [sys.executable, "-B", str(RAIZ / "visualizador" / "servidor.py"),
         "--sin-navegador", "--puerto", str(puerto)],
        cwd=RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for _ in range(120):
            try:
                with urllib.request.urlopen(base + "/api/red",
                                            timeout=2) as r:
                    red = json.load(r)
                break
            except OSError:
                if proceso.poll() is not None:
                    raise AssertionError("el servidor se detuvo: "
                                         + proceso.stderr.read().decode())
                time.sleep(0.5)
        else:
            raise AssertionError("el servidor no respondió en 60 s")
        verificar(len(red["nodos"]) == 32, "/api/red")
        with urllib.request.urlopen(base + "/", timeout=5) as r:
            verificar(r.status == 200 and b"Rutas de carga" in r.read(),
                      "/")
        consulta = urllib.parse.urlencode(
            {**CENTRAL, "criterio": "distancia", "algoritmo": "astar"})
        with urllib.request.urlopen(f"{base}/api/busqueda?{consulta}",
                                    timeout=10) as r:
            busqueda = json.load(r)
        verificar(round(busqueda["costo"], 2) == 370.54
                  and busqueda["expandidos"] == 14, "/api/busqueda")
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()
    print("  / , /api/red y /api/busqueda responden en un puerto libre")


def main():
    prueba_red()
    prueba_coordenadas()
    prueba_despliegue()
    prueba_salud_y_limites()
    prueba_solo_lectura()
    prueba_busqueda()
    prueba_metricas_coherentes()
    prueba_comparar()
    prueba_criterios()
    prueba_errores()
    prueba_despachador()
    prueba_umbral_y_aco()
    prueba_estaticos()
    prueba_arranque()
    print("Pruebas del visualizador: todas pasan")


if __name__ == "__main__":
    main()
