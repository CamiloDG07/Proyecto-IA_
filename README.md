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
| `data/carga/_descarga_previa/` | Descarga anterior (esquema reducido), conservada con su hash; **no es la fuente oficial vigente** |
| `data/carga/mgn2020_departamentos_dane.json` | Límites departamentales del DANE (MGN 2020), fondo de los mapas |
| `data/_archivo_transmilenio/`, `src/_archivo_transmilenio/`, `outputs/_archivo_transmilenio/` | Material del dominio anterior (TransMilenio) |
| `src/` | Código fuente |
| `outputs/` | JSON del grafo, grafo persistido, figuras y tablas |
| `formulacion_corte1.tex` | Informe del Corte 1 |
| `informe_corte2.tex`, `guion_demostracion.md` | Informe del Corte 2 y guion de la demostración |

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

`data/carga/_descarga_previa/` contiene la descarga anterior de los datos,
con un esquema reducido (por ejemplo, su `red_vial.csv` pesa unos 91 KB y no
trae la geometría ni las progresivas). Se conserva solo como evidencia, con
sus hashes en la sección «Descarga previa» de `VERIFICACION.md`; **no es la
fuente oficial vigente**. La fuente oficial vigente es la descarga del 6 de
octubre de 2026 indicada arriba.

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
python src/heuristica.py         # alfa y verificación de h
python src/pruebas_busquedas.py  # BFS, DFS, UCS, voraz y A*
python src/auditar_aristas.py    # auditoría geométrica (requiere red_vial.csv)
python src/auditar_distancias.py # distancias por registro (requiere red_vial.csv)
python src/exportar_latex.py     # tablas del informe

python src/experimentos_corte2.py  # escenarios, barrido y sensibilidad
python src/tablas_corte2.py       # tablas del informe del Corte 2
python src/visualizar_rutas.py    # figuras de rutas y barrido
python src/demostracion.py Duitama "Puente Nacional" distancia
python src/pruebas_despachador.py  # agente multifuncional
python src/pruebas_orden_libre.py  # Held-Karp, 2-opt y ACO
python src/medir_umbral.py         # umbral de Held-Karp (varios minutos)
python src/verificar_estructura.py  # formula unicíclica contra Held-Karp
python src/validacion_agente.py    # validacion del agente (varios minutos)
python src/tablas_agente.py        # tablas y figura del agente

python src/agente_rutas.py Bogotá Granada         # agente autónomo
python src/agente_rutas.py Duitama "Puente Nacional" --regreso
python src/agente_rutas.py Duitama "Puente Nacional" --regreso --bloquear-regreso "Tunja-Chocontá"
python src/agente_rutas.py Duitama "Puente Nacional" --criterio peaje
python src/pruebas_agente_rutas.py   # pruebas del agente autónomo
python src/pruebas_criterio.py       # pruebas de --criterio
python src/perfil_topologico.py      # perfil topológico de los 496 pares
python src/pruebas_perfil_topologico.py
python src/mapa_geografico.py        # mapas (desde outputs/trazado_aristas.json)
python src/pruebas_mapa.py
python src/lecturas_informe.py       # bloques «Cómo leerla» y tabla de ejemplos
python src/figuras_informe.py      # figuras de los informes (PNG y PDF en outputs/)
python src/pruebas_figuras.py

pdflatex formulacion_corte1.tex  # dos pasadas
pdflatex formulacion_corte1.tex
pdflatex informe_corte2.tex      # dos pasadas
pdflatex informe_corte2.tex
```

Estilo del código: `pycodestyle src/*.py` (PEP 8, máximo 79 caracteres).
