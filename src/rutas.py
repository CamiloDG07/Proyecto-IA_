"""Rutas del proyecto: un solo lugar donde se define dónde vive cada archivo.

La raíz, los datos de entrada y las carpetas de salida por tipo:

    outputs/datos      JSON, CSV, grafo persistido, trazados y evaluaciones
    outputs/tablas     tabla_*.tex
    outputs/lecturas   lectura_*.tex y texto_*.tex
    outputs/figuras    figuras, mapas y diagramas (png y pdf)
    outputs/reportes   bitácoras, licencias, condiciones de medición y
                       listas de candidatos

`SALIDA / "nombre.ext"` devuelve la ruta según el tipo del archivo, de modo
que el código no escribe cadenas con carpetas. `tipo` es la regla única de
clasificación (la usa también el script que reubicó los archivos).
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATA = RAIZ / "data"
CARGA = DATA / "carga"
RAIZ_SALIDA = RAIZ / "outputs"
DATOS = RAIZ_SALIDA / "datos"
TABLAS = RAIZ_SALIDA / "tablas"
LECTURAS = RAIZ_SALIDA / "lecturas"
FIGURAS = RAIZ_SALIDA / "figuras"
REPORTES = RAIZ_SALIDA / "reportes"
CARPETAS = {"datos": DATOS, "tablas": TABLAS, "lecturas": LECTURAS,
            "figuras": FIGURAS, "reportes": REPORTES}
CAPAS = ("src", "experimentos", "informe", "pruebas")
REPORTES_CSV = ("candidatos_", "cifras_movidas", "mapa_archivos")


def tipo(nombre):
    """Tipo de un archivo de salida según su nombre (o patrón)."""
    n = str(nombre).lower()
    ext = n.rsplit(".", 1)[-1] if "." in n else ""
    if ext == "tex":
        if n.startswith(("lectura_", "texto_")):
            return "lecturas"
        return "tablas"
    if ext in ("png", "pdf", "svg"):
        return "figuras"
    if ext in ("md", "txt") or n.startswith(REPORTES_CSV):
        return "reportes"
    return "datos"


def ruta_salida(nombre):
    """Ruta de un archivo de salida dado solo su nombre."""
    return CARPETAS[tipo(nombre)] / nombre


def resolver(relativa):
    """Ruta absoluta de una ruta relativa a la raíz; 'outputs/x.ext' se
    busca en la carpeta de su tipo."""
    partes = Path(str(relativa).replace("\\", "/")).parts
    if len(partes) == 2 and partes[0] == "outputs" and "." in partes[1]:
        return ruta_salida(partes[1])
    return RAIZ.joinpath(*partes)


class _Salida(Path):
    """La carpeta outputs: `SALIDA / "archivo.ext"` apunta a su subcarpeta."""

    def __truediv__(self, clave):
        if (self == RAIZ_SALIDA and isinstance(clave, str)
                and "/" not in clave and "\\" not in clave and "." in clave):
            return ruta_salida(clave)
        return super().__truediv__(clave)

    def glob(self, patron, **opciones):
        if self == RAIZ_SALIDA and "/" not in patron and "." in patron:
            return CARPETAS[tipo(patron)].glob(patron, **opciones)
        return super().glob(patron, **opciones)


SALIDA = _Salida(RAIZ_SALIDA)
