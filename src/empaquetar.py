"""Arma el zip de la entrega con los archivos versionados del repositorio.

Uso:
    python src/empaquetar.py [DESTINO.zip]

Incluye solo lo versionado (nada de .git ni venv, que no lo están) y excluye
el material del dominio anterior (_archivo_transmilenio), las muestras del
estilo de tablas (outputs/muestras_formato) y los documentos de terceros
(PDF, Word y Excel fuera de outputs, como los de la CREG y la UPME, cuyas URL
y SHA-256 están en data/carga/FUENTES_NUEVAS.md). Los PDF de los informes en
la raíz y en outputs sí se incluyen. El contenido de cada archivo es el del
árbol de trabajo, que debe coincidir con el último commit.
"""
import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PREFIJO = "ProyectoIA"
DESTINO = RAIZ.parent / "Proyecto_IA_Corte2.zip"
TERCEROS = (".docx", ".xlsx", ".doc", ".xls")


def excluido(ruta):
    partes = ruta.split("/")
    if "_archivo_transmilenio" in partes:
        return True
    if ruta.startswith("outputs/muestras_formato"):
        return True
    if ruta.lower().endswith(TERCEROS):
        return True
    return ruta.lower().endswith(".pdf") and partes[0] == "data"


def archivos():
    salida = subprocess.run(["git", "ls-files"], cwd=RAIZ, check=True,
                            capture_output=True, encoding="utf-8").stdout
    return [r for r in salida.splitlines() if r and not excluido(r)]


def main(argumentos):
    destino = Path(argumentos[0]) if argumentos else DESTINO
    sucio = subprocess.run(["git", "status", "--porcelain"], cwd=RAIZ,
                           capture_output=True, encoding="utf-8").stdout
    if sucio.strip():
        print("Aviso: el árbol de trabajo tiene cambios sin confirmar; el "
              "zip contiene el árbol de trabajo, no el último commit.")
    lista = archivos()
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for ruta in lista:
            z.write(RAIZ / ruta, f"{PREFIJO}/{ruta}")
    print(f"{len(lista)} archivos en {destino} "
          f"({destino.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
