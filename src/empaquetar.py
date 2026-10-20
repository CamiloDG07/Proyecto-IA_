"""Arma el zip de la entrega con los archivos versionados del repositorio.

Uso:
    python src/empaquetar.py [DESTINO.zip]
    python src/empaquetar.py --entregable [DESTINO.zip]

Modo completo (por defecto): incluye lo versionado y excluye el material del
dominio anterior (_archivo_transmilenio), las muestras del estilo de tablas
(muestras_formato) y los documentos de terceros (PDF, Word y Excel fuera de
outputs, como los de la CREG y la UPME, cuyas URL y SHA-256 están en
data/carga/FUENTES_NUEVAS.md).

Modo --entregable: el paquete ejecutable mínimo que se entrega con el informe
del Corte 2. Solo el código que corre sin el repositorio (sin .git, sin los
fuentes .tex y sin red_vial.csv), los resultados, tablas, lecturas y figuras
que ese código lee, los datos livianos de data/carga, la configuración de
costos y la documentación. No incluye los informes (.tex ni .pdf), las
auditorías de una sola vez ni las bitácoras.

El contenido de cada archivo es el del árbol de trabajo, que debe coincidir
con el último commit.
"""
from rutas import RAIZ
import subprocess
import sys
import zipfile
from pathlib import Path

PREFIJO = "ProyectoIA"
DESTINO = RAIZ.parent / "Proyecto_IA_Corte2.zip"
TERCEROS = (".docx", ".xlsx", ".doc", ".xls")
# modo --entregable
CARPETAS_CODIGO = ("src/", "experimentos/", "informe/", "pruebas/")
SIN_REPOSITORIO = {
    # necesitan el historial de git o los fuentes .tex del informe
    "src/empaquetar.py", "pruebas/comparar_resultados.py",
    "pruebas/verificar_cifras.py", "informe/candidatos_tablas.py",
    "informe/cifras_movidas.py", "informe/guia_comandos.py"}
DATOS_LIVIANOS = {
    "data/carga/coordenadas_nodos.csv", "data/carga/peajes.csv",
    "data/carga/siniestralidad.csv",
    "data/carga/mgn2020_departamentos_dane.json",
    "data/carga/VERIFICACION.md", "data/carga/FUENTES_NUEVAS.md",
    "data/carga/nuevas/sectores_criticos_mortalidad_2022_ybqk-8s42.csv"}
RAIZ_ENTREGABLE = {"config_costos.json", "requirements.txt", "README.md",
                   "EJECUTAR.md", "GUIA_DE_COMANDOS.md",
                   "guion_demostracion.md"}


def excluido(ruta):
    partes = ruta.split("/")
    if "_archivo_transmilenio" in partes:
        return True
    if "muestras_formato" in partes:
        return True
    if ruta.lower().endswith(TERCEROS):
        return True
    return ruta.lower().endswith(".pdf") and partes[0] == "data"


def en_entregable(ruta):
    """Regla del paquete mínimo (ver el modo --entregable)."""
    if excluido(ruta) or ruta in SIN_REPOSITORIO:
        return False
    if ruta.startswith(CARPETAS_CODIGO):
        return ruta.endswith(".py")
    if ruta.startswith(("outputs/datos/", "outputs/tablas/",
                        "outputs/lecturas/", "outputs/figuras/")):
        return True
    if ruta.startswith("outputs/reportes/"):
        nombre = ruta.rsplit("/", 1)[-1]
        return nombre.startswith(("LICENCIA", "condiciones"))
    return ruta in DATOS_LIVIANOS or ruta in RAIZ_ENTREGABLE


def archivos(entregable=False):
    salida = subprocess.run(["git", "ls-files"], cwd=RAIZ, check=True,
                            capture_output=True, encoding="utf-8").stdout
    regla = en_entregable if entregable else (lambda r: not excluido(r))
    return [r for r in salida.splitlines() if r and regla(r)]


def main(argumentos):
    entregable = "--entregable" in argumentos
    argumentos = [a for a in argumentos if a != "--entregable"]
    destino = Path(argumentos[0]) if argumentos else DESTINO
    sucio = subprocess.run(["git", "status", "--porcelain"], cwd=RAIZ,
                           capture_output=True, encoding="utf-8").stdout
    if sucio.strip():
        print("Aviso: el árbol de trabajo tiene cambios sin confirmar; el "
              "zip contiene el árbol de trabajo, no el último commit.")
    lista = archivos(entregable)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for ruta in lista:
            z.write(RAIZ / ruta, f"{PREFIJO}/{ruta}")
    print(f"{len(lista)} archivos en {destino} "
          f"({destino.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
