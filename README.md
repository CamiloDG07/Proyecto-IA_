# Proyecto Integrador de Inteligencia Artificial: ruta de carga interurbana

> **Paquete entregable.** Si recibió este proyecto como el paquete del Corte 2, empiece por `GUIA_DE_COMANDOS.md`: allí están los comandos probados con su salida. Este documento describe el repositorio completo, que además incluye los fuentes LaTeX de los informes, el historial de git y el verificador de cifras.


Universidad Sergio Arboleda, Inteligencia Artificial (SIST5036).
Autores: Juan David Andradé Gómez, Mario Jiménez López y Camilo Andrés Díaz
García.

Un camión de carga de categoría III (dos ejes) se desplaza entre 32 ciudades
de Colombia. Cada tramo tiene distancia (km), peaje (COP) y riesgo de
siniestralidad (GiZScore). El agente elige la ruta de menor costo según un
criterio: `distancia`, `peaje`, `riesgo`, `compuesto`, `compuesto_sin_riesgo`,
`costo_operativo` (peaje más combustible), `compuesto_total`,
`compuesto_total_sin_riesgo` o `compuesto_mortalidad` (esta última, de
sensibilidad). El grafo tiene 32 nodos, 32 aristas y un único ciclo (desvío
por Santander).

Piso geodésico: una carretera no puede ser más corta que la línea recta entre
sus nodos. En 8 aristas la distancia oficial es menor que la recta (sector
truncado, entrada urbana a Bogotá o coordenada del nodo en el centro del
municipio); la distancia del modelo es `max(oficial, geodésica)` y la oficial se
conserva (`distancia_oficial_km`, `distancia_piso_km`; ver `src/piso_geodesico.py`
y `outputs/datos/aristas_piso_geodesico.csv`). El piso es una cota inferior, no una
medida. Con él, `h = geodésica` es admisible y consistente en toda la red con
alfa = 1; la variante «sin piso» (distancias oficiales) es una sensibilidad.

El costo en pesos usa los insumos de `config_costos.json`, cada uno con su
fuente y su estado: precio del galón de ACPM (CREG) y consumo del camión de
dos ejes (UPME) están verificados; «otros costos por km» vale 0 y es un
supuesto del equipo, no un dato. Por eso el criterio por defecto sigue siendo
`compuesto_sin_riesgo` y el costo en pesos es un piso.

## Estructura

| Ruta | Contenido |
|---|---|
| `data/carga/` | Datos oficiales (INVÍAS y ANSV), `VERIFICACION.md` y `FUENTES_NUEVAS.md` (fuentes evaluadas el 8 de octubre de 2026, con su decisión) |
| `data/carga/nuevas/` | Archivos de las fuentes nuevas con licencia CC BY-SA 4.0 (mortalidad ANSV y postes de INVÍAS); los documentos de la CREG y de la UPME no se redistribuyen: sus URL, fechas y SHA-256 están en `FUENTES_NUEVAS.md` |
| `config_costos.json` | Insumos del costo monetario, con fuente y estado |
| `data/carga/_descarga_previa/` | Descarga anterior (esquema reducido), conservada con su hash; **no es la fuente oficial vigente** |
| `data/carga/mgn2020_departamentos_dane.json` | Límites departamentales del DANE (MGN 2020), fondo de los mapas |
| `data/_archivo_transmilenio/`, `src/_archivo_transmilenio/`, `outputs/_archivo_transmilenio/` | Material del dominio anterior (TransMilenio) |
| `src/`, `experimentos/`, `informe/`, `pruebas/` | Código (ver el mapa de carpetas) |
| `visualizador/` | Aplicación web local (FastAPI y Leaflet) que muestra la búsqueda y el despachador sobre la red |
| `outputs/` | Resultados por tipo: `datos/`, `tablas/`, `lecturas/`, `figuras/` y `reportes/` |
| `formulacion_corte1.tex` | Informe del Corte 1 |
| `informe_corte2.tex`, `guion_demostracion.md` | Informe del Corte 2 y guion de la demostración |

## Mapa de carpetas

Cada línea indica qué contiene la carpeta y de qué tipo es. Para ejecutar el
proyecto paso a paso, ver `EJECUTAR.md`.

| Carpeta | Contenido | Tipo |
|---|---|---|
| (raíz) | `README.md`, `EJECUTAR.md`, `requirements.txt`, `config_costos.json`, los dos informes (`.tex` y `.pdf`) y el guion de la demostración | documentación e informe |
| `data/` | Datos de entrada | datos |
| `data/carga/` | Datos oficiales de la red (INVÍAS, ANSV, DANE), coordenadas, `VERIFICACION.md` y `FUENTES_NUEVAS.md`; `red_vial.csv` no está versionado | datos |
| `data/carga/nuevas/` | Mortalidad ANSV y postes de INVÍAS (CC BY-SA 4.0) | datos |
| `data/carga/_descarga_previa/` | Descarga anterior, conservada como evidencia | datos |
| `data/_archivo_transmilenio/` | Material del dominio anterior (TransMilenio) | datos (archivo) |
| `src/` | Núcleo que se ejecuta para resolver rutas y construir la red: construcción de la red y del grafo, búsquedas, heurística, piso geodésico, costos, agente, despachador, Held-Karp, ACO y demostración; `rutas.py` define las rutas de entrada y de salida; `mapa_geografico.py` (trazado que usa la construcción de la red), `diagrama_red.py` (que aquel importa) y `empaquetar.py` quedan aquí por ambiguos | ejecución |
| `src/_archivo_transmilenio/` | Código del dominio anterior | archivo |
| `experimentos/` | Corridas que producen resultados: experimentos del Corte 2, validación del agente, umbral de Held-Karp, perfil topológico, auditorías de aristas y de distancias, verificación de estructura | medición |
| `informe/` | Código que arma las tablas, las lecturas, las figuras, los diagramas y el estilo de los informes | informe |
| `visualizador/` | Servidor y interfaz web local (`servidor.py`, `static/` con Leaflet y las fuentes con sus licencias) | ejecución |
| `pruebas/` | Pruebas (`pruebas_*.py`), `verificar_cifras.py` y `comparar_resultados.py` | pruebas |
| `outputs/` | Resultados guardados, ordenados por tipo en las subcarpetas siguientes | resultados e informe |
| `outputs/datos/` | JSON, CSV, grafo persistido, trazados y evaluaciones | resultados |
| `outputs/tablas/` | `tabla_*.tex` que incluyen los informes | informe |
| `outputs/lecturas/` | `lectura_*.tex` («Cómo leerla») y `texto_*.tex` | informe |
| `outputs/figuras/` | Figuras, mapas y diagramas (PNG y PDF) y `muestras_formato/` | informe |
| `outputs/reportes/` | Bitácoras, licencias, condiciones de medición, listas de candidatos, `mapa_archivos.csv` y `reemplazos_rutas.csv` | documentación |
| `outputs/_archivo_transmilenio/` | Resultados del dominio anterior | archivo |
| `notebooks/`, `data/notebooks/` | Carpetas locales sin archivos versionados | (vacías) |
| `venv/` | Entorno virtual local, no versionado | local |

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

No hace falta ese archivo para usar el grafo: `outputs/datos/aristas_red.json`,
`outputs/datos/nodos_red.json` y `outputs/datos/grafo_carga.gpickle` están versionados.
Si el pickle no se puede leer (otra versión de Python o networkx),
`build_graph.py` reconstruye el grafo desde los JSON.

## Reproducción

La guía completa, con los comandos probados, los tiempos y el orden de la
regeneración, está en `EJECUTAR.md`. Resumen:

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

python src/construir_red.py      # requiere data/carga/red_vial.csv
python src/build_graph.py        # grafo y estadísticas
python src/agente.py             # demostración del agente
python pruebas/pruebas_agente.py     # pruebas
python src/diagrama_red.py       # figura de la red
python src/heuristica.py         # alfa y verificación de h
python pruebas/pruebas_busquedas.py  # BFS, DFS, UCS, voraz y A*
python experimentos/auditar_aristas.py    # auditoría geométrica (requiere red_vial.csv)
python experimentos/auditar_distancias.py # distancias por registro (requiere red_vial.csv)
python informe/exportar_latex.py     # tablas del informe

python experimentos/experimentos_corte2.py  # escenarios, barrido y sensibilidad (esta, fuera del informe)
python informe/tablas_corte2.py       # tablas del informe del Corte 2
python informe/visualizar_rutas.py    # figuras de rutas y barrido (barrido_pesos_base.png va en el informe)
python src/demostracion.py Duitama "Puente Nacional" distancia
python pruebas/pruebas_despachador.py  # agente multifuncional
python pruebas/pruebas_orden_libre.py  # Held-Karp, 2-opt y ACO
python experimentos/medir_umbral.py         # umbral de Held-Karp (varios minutos)
python experimentos/verificar_estructura.py  # formula unicíclica contra Held-Karp
python experimentos/validacion_agente.py    # validacion del agente (varios minutos)
python informe/tablas_agente.py        # tablas y figura del agente

python src/agente_rutas.py Bogotá Granada         # agente autónomo
python src/agente_rutas.py Duitama "Puente Nacional" --regreso
python src/agente_rutas.py Duitama "Puente Nacional" --regreso --bloquear-regreso "Tunja-Chocontá"
python src/agente_rutas.py Duitama "Puente Nacional" --criterio peaje
python src/agente_rutas.py Duitama "Puente Nacional" --criterio costo_operativo
python src/agente_rutas.py Duitama "Puente Nacional" --precio-galon 14000 --rendimiento 8 --costo-otros-km 500
python pruebas/pruebas_agente_rutas.py   # pruebas del agente autónomo
python pruebas/pruebas_costos.py         # costo monetario, umbral y heurísticas nuevas
python pruebas/pruebas_progresivas.py    # regla de adopción de distancias por progresivas
python src/piso_geodesico.py         # aristas con piso geodésico (tras auditar_aristas.py)
python pruebas/pruebas_piso.py           # invariante geodésico, admisibilidad y consistencia
python pruebas/comparar_resultados.py    # identidad con corte2-entrega-8 en los pares sin piso
python src/cruce_mortalidad.py       # cruce de la mortalidad ANSV (lo llama construir_red.py)
python pruebas/verificar_cifras.py       # contrasta las cifras de los informes y del guion con los datos
python pruebas/pruebas_criterio.py       # pruebas de --criterio
python experimentos/perfil_topologico.py      # perfil topológico de los 496 pares
python pruebas/pruebas_perfil_topologico.py
python src/mapa_geografico.py        # mapas (desde outputs/datos/trazado_aristas.json)
python pruebas/pruebas_mapa.py
python informe/lecturas_informe.py       # bloques «Cómo leerla» y tabla de ejemplos
python informe/tablas_resumen.py         # tablas de resumen que reemplazan párrafos con varias cifras (tabla_r_*.tex)
python pruebas/pruebas_tablas_resumen.py # sus cifras contra outputs/ y el máximo de 6 columnas
python pruebas/pruebas_tabla_heuristica.py # la tabla de criterios de la heurística contra el código y el grafo
python informe/candidatos_tablas.py      # párrafos con cifras comparables (outputs/reportes/candidatos_tablas.csv)
python informe/cifras_movidas.py         # cifras antes y después contra master (outputs/reportes/cifras_movidas.csv)
python informe/figuras_informe.py      # figuras de los informes (PNG y PDF en outputs/)
python pruebas/pruebas_figuras.py
python informe/formato_latex.py outputs/tablas/tabla_*.tex  # estilo único de tablas (cuadrícula, encabezado gris)
python pruebas/pruebas_formato.py

pdflatex formulacion_corte1.tex  # tres pasadas
pdflatex formulacion_corte1.tex
pdflatex formulacion_corte1.tex
pdflatex informe_corte2.tex      # tres pasadas
pdflatex informe_corte2.tex
pdflatex informe_corte2.tex
```

Estilo del código: `python -m pycodestyle --max-line-length=79 --exclude=_archivo_transmilenio src experimentos informe pruebas` (PEP 8).

## Visualizador web

Aplicación local que dibuja, sobre la red real de 32 nodos y 32 aristas, cómo trabajan los cinco algoritmos y el despachador. Necesita dos dependencias más, `fastapi` y `uvicorn` (versiones fijadas en `requirements.txt`), y se instala con el resto:

```
pip install -r requirements.txt
python visualizador/servidor.py
```

Abre `http://127.0.0.1:8000` (la documentación de la API queda en `/docs`) y funciona sin conexión: Leaflet, las fuentes y los estilos están en `visualizador/static/vendor/`; el fondo de OpenStreetMap solo se descarga si hay conexión y tiene un interruptor «sin fondo». Ofrece el mapa con el estado de cada nodo, la animación paso a paso de la búsqueda con su árbol, la construcción de la ruta tramo por tramo con las métricas acumuladas, la comparación de los cinco algoritmos y de los nueve criterios, y el despachador con paradas elegidas en el mapa (orden de visita, matriz de costos y curva del ACO). Las búsquedas y los costos los calculan los módulos del proyecto (`src/trazas.py` repite la lógica de `busquedas.py` y se prueba contra ella en 44 640 casos); el navegador solo dibuja.

Límite: el proyecto no tiene datos de tiempo de viaje. La aplicación muestra un «tiempo estimado» igual a la distancia dividida por una velocidad supuesta (50 km/h, supuesto del equipo, editable de 20 a 90 km/h y rotulado como estimación); no es un criterio de búsqueda y no entra a ningún costo ni resultado. Las instancias de 19 y 20 paradas son de demostración, no casos de las pruebas del informe.

## Despliegue en Vercel

El visualizador se puede publicar en Vercel directamente desde este repositorio, sin cambiar la lógica ni los resultados. Los archivos de despliegue están en la raíz: `pyproject.toml` (`[project]` con las dependencias mínimas del servidor, `fastapi`, `networkx` y `numpy`, que Vercel instala con uv; y `[tool.vercel]` con `entrypoint = "visualizador.servidor:app"`), `vercel.json` (`maxDuration` de 60 s para la función), `.vercelignore` (deja fuera del paquete lo que la función no lee: informe, experimentos, pruebas, figuras, tablas, lecturas, archivo de TransMilenio y datos pesados) y `.python-version` (3.14, la versión con que se probó). `requirements.txt` sigue siendo el de uso local y de la guía (una prueba comprueba que las dependencias de `pyproject.toml` están en él con la misma versión). Pasos, en el panel de Vercel:

1. Add New > Project, importar `CamiloDG07/Proyecto-IA_` y elegir la rama `master` como rama de producción.
2. Framework Preset: FastAPI (Vercel lo detecta solo). No hay variables de entorno ni comando de compilación.
3. Deploy. Al terminar, abrir `https://<proyecto>.vercel.app/api/salud` (debe responder `{"estado":"ok"}`), luego `/` y pulsar «Caso central» (370.54 km por Bogotá con A*, 14 expandidos).

Límites: el sistema de archivos de la función es de solo lectura y el servidor no escribe en disco. Para que un despliegue público no se use mal, el despachador acepta como máximo 20 paradas libres u obligatorias (422 con mensaje en español si se excede) y el cuerpo de una solicitud no pasa de 64 KiB. Si una solicitud agota el tiempo (el peor caso medido es de unos 3.5 s en un portátil con Intel Core i7-8750H; en la plataforma puede ser más lento), subir `maxDuration` en `vercel.json` o pedir menos paradas.

## Licencias y atribución

Los datos de INVÍAS (Red Vial, Peajes, Postes de Referencia), de la ANSV
(sectores críticos de siniestralidad y de mortalidad 2022) y del DANE
(DIVIPOLA) provienen del portal de datos abiertos datos.gov.co y se usan bajo
la licencia Creative Commons Atribución-CompartirIgual 4.0 Internacional
(CC BY-SA 4.0, https://creativecommons.org/licenses/by-sa/4.0/deed.es). Los
datos derivados que contiene este repositorio (`outputs/datos/aristas_red.json`,
`outputs/datos/nodos_red.json`, `outputs/datos/trazado_aristas.json`,
`outputs/datos/riesgo_mortalidad_aristas.json`, las auditorías y las tablas que salen
de ellos) fueron cruzados, corregidos y transformados por el equipo y se
comparten bajo la misma licencia, con atribución a INVÍAS, la ANSV y el DANE.

El precio del combustible (CREG) y el consumo (UPME) son datos públicos de
documentos que no declaran licencia de redistribución: no se incluyen los
archivos, solo el valor con su cita en `config_costos.json`. La tabla completa
(entidad, URL, fecha y licencia de cada fuente) está en
`data/carga/FUENTES_NUEVAS.md`.
