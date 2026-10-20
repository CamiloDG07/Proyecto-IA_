"""Compara los resultados de outputs/ con los de una entrega anterior.

Uso: python pruebas/comparar_resultados.py [referencia_git]

La referencia por defecto es la etiqueta corte2-entrega-8, anterior al piso
geodésico. Se comparan, sin los tiempos ni la memoria (que dependen de la
máquina), los resultados de los escenarios de los pares cuya ruta no contiene
ninguna arista con piso (outputs/datos/aristas_piso_geodesico.csv): rutas y
costos idénticos en los cinco algoritmos; nodos expandidos y generados de BFS,
DFS y UCS idénticos cuando ninguno de los nodos de la ruta toca una arista
con piso (si alguno la toca, la búsqueda la explora y el orden de
expansión puede cambiar; esas diferencias se listan como explicadas); en A*,
nodos expandidos menores o iguales (la heurística es más informativa con alfa
= 1). También se comparan el perfil topológico y los campos de las aristas sin
piso. Termina con código 1 si hay una diferencia inesperada.
"""
import sys
from pathlib import Path
if True:  # carpetas de código en el path
    sys.path[:0] = [str(Path(__file__).resolve().parents[1] / c)
                    for c in ("src", "experimentos", "informe", "pruebas")]
from rutas import RAIZ, SALIDA
import csv
import json
import subprocess
import sys
from pathlib import Path

IGNORAR = ("tiempo", "precalculo", "memoria", "fecha", "maquina", "sesion",
           "limite")
diferencias = []


def de_git(ref, ruta):
    r = subprocess.run(["git", "show", f"{ref}:{ruta}"], cwd=RAIZ,
                       capture_output=True)
    if r.returncode:
        raise FileNotFoundError(f"{ref}:{ruta}")
    return r.stdout.decode("utf-8")


def cargar(ref, nombre):
    return json.loads(de_git(ref, f"outputs/{nombre}")), json.loads(
        (SALIDA / nombre).read_text(encoding="utf-8"))


def comparar(a, b, ruta):
    """Compara `a` (entrega anterior) con `b` (vigente) recursivamente."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if any(x in k for x in IGNORAR):
                continue
            if k not in b:
                diferencias.append(f"{ruta}/{k}: falta en la versión vigente")
                continue
            comparar(a[k], b[k], f"{ruta}/{k}")
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diferencias.append(f"{ruta}: {len(a)} elementos contra {len(b)}")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            comparar(x, y, f"{ruta}[{i}]")
    elif isinstance(a, float) and isinstance(b, (int, float)):
        if abs(a - b) > 1e-9 * max(1.0, abs(a)):
            diferencias.append(f"{ruta}: {a} contra {b}")
    elif a != b:
        diferencias.append(f"{ruta}: {a!r} contra {b!r}")


def aristas_con_piso():
    with open(SALIDA / "aristas_piso_geodesico.csv", encoding="utf-8") as f:
        return {frozenset((r["origen"], r["destino"]))
                for r in csv.DictReader(f)}


def libre(ruta, pisos):
    return not any(frozenset(p) in pisos for p in zip(ruta, ruta[1:]))


def vecindad_libre(ruta, pisos):
    """Ningún nodo de la ruta tiene una arista con piso incidente."""
    nodos = {n for par in pisos for n in par}
    return not any(n in nodos for n in ruta)


def main(ref):
    pisos = aristas_con_piso()
    cuenta = {}
    a, b = cargar(ref, "resultados_corte2.json")
    clave = ("origen", "destino", "criterio", "algoritmo")
    vigente = {tuple(r[k] for k in clave): r for r in b["resultados"]}
    antes = {tuple(r[k] for k in clave): r for r in a["resultados"]}
    pares = {k[:3] for k in antes}
    libres = {p for p in pares if libre(antes[p + ("UCS",)]["ruta"], pisos)}
    cuenta["pares-criterio con ruta óptima sin piso"] = len(libres)
    cuenta["pares-criterio con ruta óptima con piso (no comparables)"] = (
        len(pares) - len(libres))
    iguales = menores = explicadas = 0
    for p in sorted(libres):
        for alg in ("BFS", "DFS", "UCS", "Voraz", "A*"):
            x, y = antes[p + (alg,)], vigente[p + (alg,)]
            if not libre(x["ruta"], pisos):
                continue
            nombre = "resultados/" + "|".join(p + (alg,))
            comparar({"ruta": x["ruta"], "costo": x["costo"]},
                     {"ruta": y["ruta"], "costo": y["costo"]}, nombre)
            if alg in ("BFS", "DFS", "UCS"):
                if (x["nodos_expandidos"], x["nodos_generados"]) != (
                        y["nodos_expandidos"], y["nodos_generados"]):
                    if vecindad_libre(x["ruta"], pisos):
                        diferencias.append(
                            f"{nombre}: nodos {x['nodos_expandidos']}, "
                            f"{x['nodos_generados']} contra "
                            f"{y['nodos_expandidos']}, "
                            f"{y['nodos_generados']} sin arista con piso "
                            "en la ruta ni en sus nodos")
                    else:
                        explicadas += 1
                        print(f"  explicada: {nombre}: expandidos "
                              f"{x['nodos_expandidos']} a "
                              f"{y['nodos_expandidos']}, generados "
                              f"{x['nodos_generados']} a "
                              f"{y['nodos_generados']} (la ruta pasa por un "
                              "nodo con arista con piso)")
                else:
                    iguales += 1
            elif alg == "A*":
                if y["nodos_expandidos"] > x["nodos_expandidos"]:
                    diferencias.append(
                        f"{nombre}: A* expande más nodos que antes "
                        f"({x['nodos_expandidos']} a "
                        f"{y['nodos_expandidos']})")
                menores += y["nodos_expandidos"] < x["nodos_expandidos"]
    cuenta["celdas BFS, DFS y UCS con ruta, costo y nodos idénticos"] = (
        iguales)
    cuenta["celdas con nodos distintos explicados por un nodo con piso"] = (
        explicadas)
    cuenta["celdas de A* con menos nodos que antes"] = menores

    a, b = cargar(ref, "perfil_topologico.json")
    comparar(a, b, "perfil_topologico")
    cuenta["perfil_topologico.json"] = 1

    a, b = cargar(ref, "aristas_red.json")
    nuevo = {(r["origen"], r["destino"]): r for r in b}
    sin_piso = 0
    for r in a:
        par = (r["origen"], r["destino"])
        if frozenset(par) in pisos:
            continue
        comparar(r, nuevo[par], f"aristas_red/{par[0]}-{par[1]}")
        sin_piso += 1
    cuenta["aristas sin piso (campos de la entrega anterior)"] = sin_piso

    for nombre, n in cuenta.items():
        print(f"  comparado: {nombre}: {n}")
    if diferencias:
        print(f"\n{len(diferencias)} diferencias frente a {ref}:")
        for d in diferencias[:60]:
            print("  -", d)
        sys.exit(1)
    print(f"\nSin diferencias frente a {ref} en los pares sin piso "
          "(salvo tiempos y memoria).")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "corte2-entrega-8")
