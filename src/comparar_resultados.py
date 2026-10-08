"""Compara los resultados de outputs/ con los de una entrega anterior.

Uso: python src/comparar_resultados.py [referencia_git]

La referencia por defecto es la etiqueta corte2-entrega-6. Se comparan, sin
los tiempos ni la memoria (que dependen de la máquina), los resultados de los
criterios anteriores (distancia, peaje, riesgo, compuesto y compuesto sin
riesgo: rutas, costos, nodos expandidos y generados, optimalidad), la
validación del agente, el barrido de pesos, la sensibilidad de A*, el perfil
topológico y las aristas. Los campos y criterios nuevos no se comparan.
Termina con código 1 si hay una diferencia.
"""
import csv
import io
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CRITERIOS_ANTERIORES = ("distancia", "peaje", "riesgo", "compuesto",
                        "compuesto_sin_riesgo")
IGNORAR = ("tiempo", "precalculo", "memoria", "fecha", "maquina", "sesion",
           "limite", "variante")  # variante: solo el rótulo
diferencias = []


def de_git(ref, ruta):
    r = subprocess.run(["git", "show", f"{ref}:{ruta}"], cwd=RAIZ,
                       capture_output=True)
    if r.returncode:
        raise FileNotFoundError(f"{ref}:{ruta}")
    return r.stdout.decode("utf-8")


def ignorado(clave):
    return any(x in str(clave) for x in IGNORAR)


def comparar(a, b, ruta, nuevo_ok=True):
    """Compara `a` (entrega anterior) con `b` (vigente) recursivamente."""
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if ignorado(k):
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


def cargar(ref, nombre):
    return json.loads(de_git(ref, f"outputs/{nombre}")), json.loads(
        (RAIZ / "outputs" / nombre).read_text(encoding="utf-8"))


def main(ref):
    cuenta = {}

    # resultados de los escenarios con los criterios anteriores
    a, b = cargar(ref, "resultados_corte2.json")
    clave = ("origen", "destino", "criterio", "algoritmo")
    vigente = {tuple(r[k] for k in clave): r for r in b["resultados"]}
    n = 0
    for r in a["resultados"]:
        if r["criterio"] not in CRITERIOS_ANTERIORES:
            continue
        comparar(r, vigente[tuple(r[k] for k in clave)],
                 "resultados/" + "|".join(str(r[k]) for k in clave))
        n += 1
    cuenta["celdas de escenarios (criterios anteriores)"] = n
    comparar(a["alfa"], b["alfa"], "resultados/alfa")

    for nombre in ("validacion_agente.json", "perfil_topologico.json",
                   "verificacion_estructura.json", "analisis_heuristica.json"):
        a, b = cargar(ref, nombre)
        if nombre == "analisis_heuristica.json":
            b = dict(b, criterios={k: v for k, v in b["criterios"].items()
                                   if k in a["criterios"]})
        comparar(a, b, nombre)
        cuenta[nombre] = 1

    # barrido de pesos: sin la variante de la entrega anterior que cambió
    a, b = cargar(ref, "barrido_pesos.json")
    comparar(a[0], b[0], "barrido_pesos/base")
    comparar(a[2], b[2], "barrido_pesos/crudas")
    comparar(a[1], b[1], "barrido_pesos/cota_inferior")
    cuenta["barrido_pesos.json (base, cota inferior y crudas)"] = 3

    a, b = cargar(ref, "sensibilidad_corte2.json")
    for k in ("alfa_base", "alfa_ref", "por_escenario", "todos_los_pares"):
        comparar(a[k], b[k], f"sensibilidad_corte2/{k}")
    cuenta["sensibilidad_corte2.json"] = 4

    a, b = cargar(ref, "aristas_red.json")
    comparar(a, b, "aristas_red")
    cuenta["aristas_red.json (campos de la entrega anterior)"] = len(a)

    filas = list(csv.DictReader(io.StringIO(
        de_git(ref, "outputs/auditoria_aristas.csv"))))
    with open(RAIZ / "outputs" / "auditoria_aristas.csv",
              encoding="utf-8") as f:
        actuales = list(csv.DictReader(f))
    comparar(filas, actuales, "auditoria_aristas")
    cuenta["auditoria_aristas.csv"] = len(filas)

    for nombre, n in cuenta.items():
        print(f"  comparado: {nombre}: {n}")
    if diferencias:
        print(f"\n{len(diferencias)} diferencias frente a {ref}:")
        for d in diferencias[:60]:
            print("  -", d)
        sys.exit(1)
    print(f"\nSin diferencias frente a {ref} (salvo tiempos y memoria).")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "corte2-entrega-6")
