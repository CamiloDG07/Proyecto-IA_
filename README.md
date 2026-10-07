# Proyecto Integrador de Inteligencia Artificial: ruta de carga interurbana

Universidad Sergio Arboleda, Inteligencia Artificial (SIST5036).
Autores: Juan David Andradé Gómez, Mario Jiménez López y Camilo Andrés Díaz
García.

Un camión de carga de categoría III (dos ejes) se desplaza entre 32 ciudades
de Colombia. Cada tramo tiene distancia (km), peaje (COP) y riesgo de
siniestralidad (GiZScore). El agente elige la ruta de menor costo según un
criterio: `distancia`, `peaje`, `riesgo`, `compuesto` o
`compuesto_sin_riesgo`. El grafo tiene 32 nodos, 32 aristas y un único ciclo
(desvío por Santander).

## Estructura

| Ruta | Contenido |
|---|---|
| `data/carga/` | Datos oficiales (INVÍAS y ANSV) y `VERIFICACION.md` |
| `data/carga/_descarga_previa/` | Descarga anterior, conservada con su hash |
| `data/_archivo_transmilenio/`, `src/_archivo_transmilenio/`, `outputs/_archivo_transmilenio/` | Material del dominio anterior (TransMilenio) |
| `src/` | Código fuente |
| `outputs/` | JSON del grafo, grafo persistido, figuras y tablas |
| `formulacion_corte1.tex` | Informe del Corte 1 |

## Datos

Versión de los datos: descarga oficial del 6 de octubre de 2026 (API Socrata
de datos.gov.co). El detalle de filas, hashes y diferencias está en
`data/carga/VERIFICACION.md`.

`peajes.csv` y `siniestralidad.csv` están en el repositorio. **`red_vial.csv`
(238 MB) no está en el repositorio** porque supera el límite de GitHub. Para
reproducir el grafo desde cero, descargarlo en `data/carga/`:

```
curl -L -o data/carga/red_vial.csv "https://www.datos.gov.co/resource/ie7y-asdn.csv?$limit=50000"
```

y comprobar su SHA-256:

```
42667E510D8C504A690ADC53B7718ED1EF1C568070B7F48CDD5002FBD76CB549
```

Si la fuente cambió, el hash no coincidirá; en ese caso, ver las diferencias
documentadas en `VERIFICACION.md`.

No hace falta ese archivo para usar el grafo: `outputs/aristas_red.json`,
`outputs/nodos_red.json` y `outputs/grafo_carga.gpickle` están versionados.
Si el pickle no se puede leer (otra versión de Python o networkx),
`build_graph.py` reconstruye el grafo desde los JSON.

## Reproducción

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

python src/construir_red.py      # requiere data/carga/red_vial.csv
python src/build_graph.py        # grafo y estadísticas
python src/agente.py             # demostración del agente
python src/pruebas_agente.py     # pruebas
python src/diagrama_red.py       # figura de la red
python src/exportar_latex.py     # tablas del informe

pdflatex formulacion_corte1.tex  # dos pasadas
pdflatex formulacion_corte1.tex
```

Estilo del código: `pycodestyle src/*.py` (PEP 8, máximo 79 caracteres).
