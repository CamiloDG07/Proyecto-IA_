# Sistema inteligente de planificacion de rutas - Transmilenio

Proyecto integrador de Inteligencia Artificial (SIST5036, Universidad Sergio Arboleda).
Corte 1: **Agente inteligente y formulacion**. Modela la red troncal de Transmilenio
(Bogota) como un grafo `G = (V, E)` y construye un prototipo de agente que calcula
rutas origen-destino sobre esa red.

Este repositorio cubre la parte tecnica del Corte 1: dataset, codigo del grafo,
prototipo del agente y pruebas. El documento de formulacion, el modelo PEAS redactado
y la presentacion del avance se elaboran aparte, a partir de las estadisticas e
imagenes generadas en `outputs/`.

## Estructura del repositorio

```
README.md
requirements.txt
data/                    Datasets originales (CSV, GeoJSON) tal como se recibieron
data/processed/          Dataset consolidado (nodos_final.csv, aristas_final.csv) -
                         fuente canonica del proyecto de aqui en adelante, generada
                         por build_graph.py
src/
  build_graph.py         Construccion del grafo corregido (nodos, aristas, tiempos,
                         exportacion) y del dataset consolidado
  agente.py              Prototipo del agente (modelo PEAS + shortest_path como placeholder)
  pruebas_agente.py      3 pruebas de rutas antes imposibles por fragmentacion
  visualizar_ruta.py     Dibuja una ruta resaltada sobre la red completa (3 casos -> PNG)
  visualizar_red.py      Diagrama de la red completa, con y sin pesos de arista
notebooks/
  diagrama_de_red.ipynb  Notebook corregido: construccion, antes/despues, visualizacion, demo del agente
outputs/                 Imagenes .png y estadisticas .json generadas por el codigo
```

## Como preparar el entorno

Requiere Python 3.10+.

```bash
python -m venv venv

# activar el entorno
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
```

## Como correr cada script

Todo se ejecuta desde la raiz del repositorio (con el entorno activado).

**1. Construir el grafo corregido** (genera todo lo que hay en `outputs/`: el grafo
exportado en `.graphml` y `.gpickle`, las estadisticas, y el reporte antes/despues de
la correccion de conectividad):

```bash
python src/build_graph.py
```

Al final imprime `nx.number_connected_components(G) = 1`, confirmando que las 153
estaciones quedan en una sola componente conexa, y guarda el dataset consolidado en
`data/processed/nodos_final.csv` / `data/processed/aristas_final.csv` (ver seccion
"Dataset consolidado" mas abajo).

**2. Probar el prototipo del agente** con un par origen-destino de ejemplo:

```bash
python src/agente.py
```

**3. Correr las pruebas del agente** (3 rutas que antes de la correccion eran
imposibles por estar en troncales/componentes distintas; guarda el resultado en
`outputs/pruebas_agente.json`):

```bash
python src/pruebas_agente.py
```

**4. Generar las visualizaciones de ruta resaltada** (una imagen por cada uno de los
3 casos de prueba, guardadas en `outputs/`):

```bash
python src/visualizar_ruta.py
```

**5. Generar el diagrama de la red con los pesos de arista** (requiere haber corrido
`build_graph.py` antes, para tener `outputs/grafo_transmilenio.gpickle`):

```bash
python src/visualizar_red.py
```

Genera `outputs/red_transmilenio_corregida.png` (vista general, sin etiquetas),
`outputs/grafo_con_pesos.png` (vista general con `distancia_km`/`tiempo_min` sobre
cada arista) y `outputs/grafo_con_pesos_zoom_comuneros.png` (zoom a una zona de
cruces, para que las etiquetas se vean con claridad sin abrir el PNG a resolucion
completa).

**6. Notebook con las visualizaciones** (requiere haber corrido `build_graph.py` al
menos una vez, o simplemente ejecutar todas las celdas del notebook, que reconstruye
el grafo):

```bash
jupyter notebook notebooks/diagrama_de_red.ipynb
```

## Resumen del grafo (Corte 1)

| | Antes de corregir | Despues de corregir |
|---|---|---|
| Nodos | 152 (bug: nombre duplicado fusiona 2 estaciones) | 153 |
| Aristas | 136 | 158 |
| Componentes conexas | 16 | **1** |

Ver `outputs/antes_de_corregir.json`, `outputs/despues_de_corregir.json` y
`outputs/estadisticas_grafo.json` para el detalle completo, y
`outputs/red_transmilenio_antes_bug.png` / `outputs/red_transmilenio_corregida.png`
para la comparacion visual.

### Que se corrigio y por que (resumen)

1. **Clave de nodo**: el notebook original usaba `nom_est` (nombre) en vez de
   `cod_nodo` (identificador unico real). Un nombre duplicado en el dataset
   fusionaba dos estaciones fisicas distintas en un solo nodo.
2. **Fragmentacion por troncal**: solo se conectaban estaciones consecutivas dentro
   de cada `id_trazado`, nunca las transferencias reales entre troncales. Se agregaron
   3 capas de conexion (estaciones de intercambio, cruces derivados del dataset de
   Trazados, y 2 conexiones residuales documentadas por proximidad geografica) mas
   una reparacion automatica de troncales repartidas en varios `id_trazado`.
3. **Orden de estaciones dentro de cada trazado**: se ordenaba por `num_est`, que no
   siempre refleja la posicion geografica real (4 aristas con saltos de 2.7 a 11.3 km
   en TZ002, TZ010 y TZ018). Ahora se usa la geometria real de cada trazado
   (`data/Trazado_troncal.geojson`, proyectando cada estacion sobre la linea) para
   ordenar; los dos trazados cuya geometria tiene ramificaciones reales (TZ009,
   TZ016) conservan `num_est` como fallback documentado. El numero de nodos/aristas
   y la componente conexa no cambian (solo se reordena qué estacion se conecta con
   cuál); las rutas del agente que pasan por esos trazados ahora dan una distancia
   total ligeramente menor, ya no inflada por los saltos falsos.
4. **Tiempo de viaje por arista** (`tiempo_min`): ademas de la distancia, cada arista
   tiene un tiempo aproximado, con un modelo de velocidad distinto segun el tipo de
   arista (viaje continuo sobre el mismo corredor, transbordo a pie, o transbordo
   entre troncales por un cruce fisico). Los supuestos de velocidad y la
   clasificacion completa estan documentados en el docstring de `src/build_graph.py`.

El detalle linea por linea de cada decision (umbrales, por que se descartó cierta
coincidencia de texto, etc.) esta documentado en los docstrings de
`src/build_graph.py`.

## Dataset consolidado

`src/build_graph.py` genera, ademas del grafo, dos CSV en `data/processed/` que son
la fuente de datos canonica del proyecto de aqui en adelante (Corte 2 y 3 pueden
partir de aqui en vez de reconstruir el grafo desde los CSV/GeoJSON crudos cada vez):

- `nodos_final.csv` (153 filas): `cod_nodo, nom_est, id_trazado, nom_tronc, tipo_esta,
  latitud, longitud, orden_en_trazado` -este ultimo explicita el orden ya corregido
  con la geometria real (o el fallback a `num_est`, segun el trazado)-.
- `aristas_final.csv` (158 filas): `origen, destino, tipo, distancia_km, tiempo_min`.

Estos dos archivos reconstruyen el grafo completo por si solos, sin volver a leer los
GeoJSON ni recalcular nada. Los datasets originales (`Estacion_troncalT.csv`, los
GeoJSON) se conservan sin modificar como fuente cruda/de auditoria.

## Prototipo del agente (modelo PEAS)

Ver el docstring de `src/agente.py`. Para el Corte 1 el agente usa
`networkx.shortest_path` (Dijkstra) como placeholder funcional; en el Corte 2 se
reemplaza por las implementaciones propias de BFS, DFS, UCS, busqueda voraz y A*
del curso.

## Rendimiento del agente

`AgenteRutas.calcular_ruta()` reporta, ademas de la ruta: la distancia total
(`distancia_total_km`), el tiempo de viaje estimado (`tiempo_viaje_min`, suma de
`tiempo_min` de cada arista de la ruta - ver "Dataset consolidado" arriba para el
modelo de velocidad), y el tiempo/memoria que tarda el algoritmo en calcularla
(`tiempo_calculo_ms`, `memoria_pico_kb`, medidos con `time.perf_counter()` y
`tracemalloc` de la libreria estandar, sin contar la carga del grafo). Resultado
medido para los 3 casos de prueba (`outputs/pruebas_agente.json`):

| Ruta | Estaciones | Transferencias | Distancia | Tiempo de viaje | Tiempo de calculo | Memoria pico |
|---|---|---|---|---|---|---|
| Portal Suba -> Portal Tunal | 40 | 2 | 25.77 km | 67.9 min | 4.26 ms | 50.86 KB |
| Portal Norte -> Portal Usme | 43 | 2 | 28.16 km | 73.6 min | 1.00 ms | 11.48 KB |
| Museo Nacional -> Portal Americas | 22 | 5 | 15.93 km | 61.4 min | 0.68 ms | 8.78 KB |

`tiempo_viaje_min` es cuanto dura el viaje (segun el modelo de velocidad); no
confundir con `tiempo_calculo_ms`, que es cuanto tarda Dijkstra en encontrar la
ruta. Estos ultimos corresponden al placeholder de Dijkstra (`networkx.shortest_path`)
sobre un grafo de 153 nodos / 158 aristas; sirven como linea base para comparar
contra BFS/DFS/UCS/voraz/A* en el Corte 2. Varian ligeramente entre corridas (son del
orden de milisegundos, sensibles al estado de cache del interprete), por lo que no
hay que esperar cifras identicas al volver a correr `python src/pruebas_agente.py`
-`distancia_total_km`, `tiempo_viaje_min` y el numero de estaciones/transferencias sí
deben ser estables, porque no dependen del reloj de la maquina-.

`src/visualizar_ruta.py` genera, para cada uno de estos 3 casos, una imagen con la
ruta resaltada (linea roja) sobre la red completa (gris claro de fondo), marcando las
estaciones de transferencia en azul y origen/destino en verde:

- `outputs/ruta_portal_suba_portal_tunal.png`
- `outputs/ruta_portal_norte_portal_usme.png`
- `outputs/ruta_museo_nacional_portal_americas.png`

## Diagrama de la red con pesos de arista

`src/visualizar_red.py` genera tres imagenes (ver paso 5 de "Como correr cada
script"): la vista general sin etiquetas (`red_transmilenio_corregida.png`), la
vista general con `distancia_km`/`tiempo_min` sobre cada arista
(`grafo_con_pesos.png` - con 158 aristas sobre el mapa completo de Bogota, las
etiquetas de las 136 aristas `intra_trazado` se ven pequeñas al ajustar la imagen a
la pantalla, pero son legibles al abrir el PNG a resolucion completa o hacer zoom en
un visor de imagenes; las 22 aristas de transferencia llevan etiqueta grande y
coloreada por tipo para que se identifiquen sin necesidad de zoom), y un zoom a la
zona de cruces alrededor de Comuneros/Ricaurte (`grafo_con_pesos_zoom_comuneros.png`)
con todas las etiquetas de esa zona ya legibles sin esfuerzo.
