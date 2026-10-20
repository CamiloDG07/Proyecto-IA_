"""Ejecuta todas las suites de pruebas y resume el resultado.

Uso:
    python pruebas/ejecutar_pruebas.py [--detalle]

Corre cada pruebas/pruebas_*.py en su propio proceso, con la codificación
UTF-8, e imprime una línea por suite (resultado y duración). Algunas suites
regeneran archivos de outputs/ (por ejemplo pruebas_agente.py reescribe los
tiempos de pruebas_agente.json); para no cambiar los resultados guardados,
se toma una copia de outputs/ antes y se restaura al terminar. Termina con
código 0 solo si todas las suites pasan.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "outputs"


def instantanea():
    return {p: p.read_bytes() for p in SALIDA.rglob("*") if p.is_file()}


def restaurar(antes):
    """Devuelve outputs/ al estado de `antes`; informa lo que cambió."""
    cambiados = []
    ahora = [p for p in SALIDA.rglob("*") if p.is_file()]
    for p in ahora:
        if p not in antes:
            p.unlink()
            cambiados.append(p)
        elif p.read_bytes() != antes[p]:
            p.write_bytes(antes[p])
            cambiados.append(p)
    for p, datos in antes.items():
        if not p.exists():
            p.write_bytes(datos)
            cambiados.append(p)
    return cambiados


def main(argumentos):
    detalle = "--detalle" in argumentos
    suites = sorted((RAIZ / "pruebas").glob("pruebas_*.py"))
    antes = instantanea()
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    fallan = []
    for suite in suites:
        t0 = time.time()
        r = subprocess.run([sys.executable, "-B", str(suite)], cwd=RAIZ,
                           capture_output=True, encoding="utf-8",
                           env=entorno)
        estado = "OK   " if r.returncode == 0 else "FALLA"
        print(f"{estado} {suite.name} ({time.time() - t0:.0f} s)")
        if r.returncode != 0:
            fallan.append(suite.name)
            print(r.stdout[-800:], r.stderr[-800:])
        elif detalle:
            print(r.stdout)
    cambiados = restaurar(antes)
    if cambiados:
        nombres = ", ".join(sorted(p.name for p in cambiados))
        print(f"Se restauraron archivos de outputs/ que las pruebas "
              f"reescriben: {nombres}")
    print(f"{len(suites) - len(fallan)} de {len(suites)} suites pasan")
    return 1 if fallan else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
