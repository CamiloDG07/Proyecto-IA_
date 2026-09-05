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
src/
  build_graph.py         Construccion del grafo corregido (nodos, aristas, exportacion)
  agente.py              Prototipo del agente (modelo PEAS + shortest_path como placeholder)
  pruebas_agente.py      3 pruebas de rutas antes imposibles por fragmentacion
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
estaciones quedan en una sola componente conexa.

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

**4. Notebook con las visualizaciones** (requiere haber corrido `build_graph.py` al
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

El detalle linea por linea de cada decision (umbrales, por que se descartó cierta
coincidencia de texto, etc.) esta documentado en los docstrings de
`src/build_graph.py`.

## Prototipo del agente (modelo PEAS)

Ver el docstring de `src/agente.py`. Para el Corte 1 el agente usa
`networkx.shortest_path` (Dijkstra) como placeholder funcional; en el Corte 2 se
reemplaza por las implementaciones propias de BFS, DFS, UCS, busqueda voraz y A*
del curso.
