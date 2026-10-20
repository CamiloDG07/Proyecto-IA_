# Cómo ejecutar el proyecto

> **Paquete entregable.** Si recibió este proyecto como el paquete del Corte 2, empiece por `GUIA_DE_COMANDOS.md`: allí están los comandos probados con su salida. Este documento describe el repositorio completo, que además incluye los fuentes LaTeX de los informes, el historial de git y el verificador de cifras.


Proyecto integrador de inteligencia artificial (Universidad Sergio Arboleda):
enrutamiento de carga interurbana sobre una red fija de 32 nodos, 32 aristas y
un ciclo. Todos los comandos de este documento se probaron desde un clon limpio
del repositorio, con un entorno virtual nuevo, y terminaron con código 0, salvo
los que se indican como no probados (los que exigen el archivo `red_vial.csv`,
que no está versionado, y las mediciones largas).

Dónde está cada cosa: `src/` (núcleo que se ejecuta: red, búsquedas, agente,
despachador), `experimentos/` (corridas que miden), `informe/` (tablas,
lecturas y figuras de los informes), `pruebas/` (pruebas, verificador y
comparador) y `outputs/` (resultados por tipo: `datos/`, `tablas/`,
`lecturas/`, `figuras/` y `reportes/`). Todos los scripts se pueden ejecutar
desde cualquier directorio; los comandos de este documento se dan desde la
raíz del repositorio. `src/rutas.py` define las rutas.

## 1. Requisitos

- Python 3.14 (probado con 3.14.3). Cualquier Python 3.10 o posterior debería
  servir, pero solo se probó 3.14.
- Dependencias de terceros (las que importa el código, en `requirements.txt`):
  `numpy`, `scipy`, `networkx`, `matplotlib` y `pycodestyle` (esta solo para
  las pruebas de estilo). Probado con numpy 2.5, scipy 1.18, networkx 3.7 y
  matplotlib 3.11.
- Para compilar los informes: una distribución de LaTeX con `pdflatex` y los
  paquetes que cargan `formulacion_corte1.tex` e `informe_corte2.tex`
  (por ejemplo, MiKTeX o TeX Live completos).
- No hace falta ningún archivo grande para usar el agente: el grafo
  (`outputs/datos/aristas_red.json`, `outputs/datos/nodos_red.json`,
  `outputs/datos/grafo_carga.gpickle`) está versionado.

## 2. Entorno virtual (PowerShell)

```powershell
cd ProyectoIA
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Si PowerShell bloquea la activación, ejecutar antes
`Set-ExecutionPolicy -Scope Process Bypass`. En lo que sigue, `python` es el del
entorno virtual. Para que la consola muestre bien los acentos, usar
`$env:PYTHONIOENCODING = "utf-8"`. Los comandos se ejecutan desde la raíz del
repositorio.

## 3. Demostración del agente

Agente autónomo (el usuario da solo origen y destino; el agente decide el tipo
de problema, el criterio, el algoritmo y la heurística):

```powershell
python src/agente_rutas.py Duitama "Puente Nacional"
python src/agente_rutas.py Bogotá Granada
python src/agente_rutas.py Duitama Tunja Bogotá Villeta --regreso
python src/agente_rutas.py Duitama "Puente Nacional" --regreso
python src/agente_rutas.py Duitama "Puente Nacional" --regreso --bloquear-regreso "Tunja-Chocontá"
python src/agente_rutas.py Duitama "Puente Nacional" --criterio peaje
python src/agente_rutas.py Duitama "Puente Nacional" --criterio costo_operativo
python src/agente_rutas.py Duitama "Puente Nacional" --precio-galon 14000 --rendimiento 8 --costo-otros-km 500
```

- Con varios destinos, o con `--regreso`, ordena las paradas con el
  despachador (Held-Karp exacto hasta K = 19 paradas libres; ACO con 2-opt
  después).
- `--bloquear-regreso` bloquea una arista solo en el viaje de vuelta.
- `--criterio` acepta `distancia`, `peaje`, `riesgo`, `compuesto`,
  `compuesto_sin_riesgo`, `costo_operativo`, `compuesto_total`,
  `compuesto_total_sin_riesgo` y `compuesto_mortalidad`.

Los cinco algoritmos sobre un par, y el despachador:

```powershell
python src/demostracion.py Duitama "Puente Nacional" distancia
python src/demostracion.py Duitama "Puente Nacional" compuesto_sin_riesgo
python src/demostracion.py Bucaramanga Bogotá distancia
python src/demostracion.py Bogotá Granada distancia
python src/demostracion.py Mariquita Granada distancia
python src/demostracion.py despachador a Duitama --destino "Puente Nacional"
python src/demostracion.py despachador d Bogotá --paradas "Tunja,Villeta,Girardot,Duitama,Zipaquirá"
python src/demostracion.py despachador c Duitama --destino "Puente Nacional" --obligatorias Tunja --bloqueados "Tunja/Chocontá"
```

Otras demostraciones breves: `python src/build_graph.py` (estadísticas del
grafo), `python src/agente.py` (agente del Corte 1) y
`python src/heuristica.py` (α y verificación de la heurística). El guion de
la presentación, con la salida esperada, está en `guion_demostracion.md`.

## 4. Pruebas, verificador y comparador

Cada suite imprime el resultado y termina con código 0 si pasa:

```powershell
python pruebas/pruebas_agente.py
python pruebas/pruebas_agente_rutas.py
python pruebas/pruebas_busquedas.py
python pruebas/pruebas_costos.py
python pruebas/pruebas_criterio.py
python pruebas/pruebas_despachador.py
python pruebas/pruebas_figuras.py
python pruebas/pruebas_formato.py
python pruebas/pruebas_mapa.py
python pruebas/pruebas_orden_libre.py
python pruebas/pruebas_perfil_topologico.py
python pruebas/pruebas_piso.py
python pruebas/pruebas_progresivas.py
python pruebas/pruebas_tabla_heuristica.py
python pruebas/pruebas_tablas_resumen.py
```

Atención: `pruebas_agente.py` reescribe `outputs/datos/pruebas_agente.json` con
tiempos nuevos. Después de correrla hay que restaurar el archivo
(`git checkout outputs/datos/pruebas_agente.json`) para no cambiar los resultados
versionados.

Contraste de los informes y del guion con los datos, y comparación con la
entrega anterior:

```powershell
python pruebas/verificar_cifras.py      # debe terminar con 0 discrepancias
python pruebas/comparar_resultados.py   # identidad con corte2-entrega-8 en los pares sin piso
```

Estilo del código:

```powershell
python -m pycodestyle --max-line-length=79 --exclude=_archivo_transmilenio src experimentos informe pruebas
```

## 5. Compilar los informes

Desde la raíz, tres pasadas cada uno:

```powershell
pdflatex formulacion_corte1.tex
pdflatex formulacion_corte1.tex
pdflatex formulacion_corte1.tex
pdflatex informe_corte2.tex
pdflatex informe_corte2.tex
pdflatex informe_corte2.tex
```

El Corte 1 (`formulacion_corte1.tex`) tiene 21 páginas y el Corte 2
(`informe_corte2.tex`), 29. Los informes leen sus tablas, lecturas y figuras de
`outputs/`; no hace falta regenerarlas para compilar.

## 6. Regeneración completa

Cada paso indica qué produce y qué necesita. Los tiempos se midieron en el
equipo del proyecto.

### 6.1 Datos y red (requiere `data/carga/red_vial.csv`)

El archivo `data/carga/red_vial.csv` (238 MB, INVÍAS) **no está versionado**
porque supera el límite de GitHub. Se descarga y se comprueba su SHA-256
contra la tabla de `data/carga/VERIFICACION.md`
(`42667E510D8C504A690ADC53B7718ED1EF1C568070B7F48CDD5002FBD76CB549`):

```powershell
curl.exe -L -o data/carga/red_vial.csv "https://www.datos.gov.co/resource/ie7y-asdn.csv?`$limit=50000"
(Get-FileHash data/carga/red_vial.csv -Algorithm SHA256).Hash
```

Si el hash no coincide, la fuente cambió: ver las diferencias en
`VERIFICACION.md`. Con el archivo en su sitio, el orden es (cada paso lee los
anteriores; los pasos de este bloque no se ejecutaron en el clon limpio por no
estar el CSV, y el orden se dedujo de lo que lee y escribe cada script):

| Paso | Comando | Produce | Necesita |
|---|---|---|---|
| 1 | `python src/construir_red.py` | `outputs/datos/aristas_red.json`, `outputs/datos/nodos_red.json`, `outputs/datos/evaluacion_progresivas.json`, `outputs/datos/riesgo_mortalidad_aristas.json`, `outputs/datos/validacion_riesgo_mortalidad.json` (llama a `cruce_mortalidad.py`) | `red_vial.csv`, `peajes.csv`, `siniestralidad.csv`, `data/carga/nuevas/`, `outputs/datos/trazado_aristas.json` (versionado) |
| 2 | `python src/obtener_coordenadas.py` | `data/carga/coordenadas_nodos.csv`, `outputs/datos/verificacion_coordenadas.csv` | `red_vial.csv`, DIVIPOLA de `data/carga/` |
| 3 | `python src/mapa_geografico.py` | `outputs/datos/trazado_aristas.json` (solo si falta; si no, usa el versionado), mapas | `red_vial.csv` para rehacer el trazado, `aristas_red.json` |
| 4 | `python experimentos/auditar_aristas.py` | `outputs/datos/auditoria_aristas.csv` y `.md` | `red_vial.csv`, coordenadas |
| 5 | `python src/piso_geodesico.py` | `outputs/datos/aristas_piso_geodesico.csv` (probado sin `red_vial.csv`, con los insumos versionados) | `aristas_red.json`, `auditoria_aristas.csv` |
| 6 | `python experimentos/auditar_distancias.py` | `outputs/datos/auditoria_distancias.csv` | `red_vial.csv` |

### 6.2 Grafo y resultados (rápido, segundos)

| Paso | Comando | Produce |
|---|---|---|
| 7 | `python src/build_graph.py` | `outputs/datos/estadisticas_grafo.json`, `outputs/datos/grafo_carga.gpickle` |
| 8 | `python src/heuristica.py` | `outputs/datos/analisis_heuristica.json` |
| 9 | `python experimentos/perfil_topologico.py` | `outputs/datos/perfil_topologico.json` |

### 6.3 Mediciones (tardan; no repetirlas sin necesidad)

Estos scripts miden tiempos y memoria de la máquina: volver a correrlos cambia
los resultados guardados.

| Comando | Produce | Duración aproximada |
|---|---|---|
| `python experimentos/experimentos_corte2.py` | `resultados_corte2.json`, `barrido_pesos.json`, `barrido_total.json`, `sensibilidad_corte2.json` | minutos |
| `python experimentos/validacion_agente.py` | `validacion_agente.json`, `.csv`, `convergencia_aco.csv` | varios minutos |
| `python experimentos/medir_umbral.py` | `umbral_sesion_N.json`, `umbral_held_karp.json` (`--combinar` solo combina las sesiones guardadas) | varios minutos por sesión |
| `python experimentos/verificar_estructura.py` | `verificacion_estructura.json` | segundos (probado) |

`verificar_estructura.py` sí se corrió en la prueba (2 s). Los otros tres no se
ejecutaron: su duración y su efecto sobre los resultados guardados lo
desaconsejan; se documentan a partir de su código.

### 6.4 Tablas, lecturas y figuras de los informes (rápido)

Orden: los generadores de tablas leen los resultados; las lecturas y las
tablas de resumen dependen de ellos; las figuras leen resultados y tablas.

```powershell
python informe/exportar_latex.py        # tablas del Corte 1 (necesita pruebas_agente.json)
python informe/tablas_corte2.py         # tablas del Corte 2
python informe/tablas_agente.py         # tablas y figura del agente
python informe/lecturas_informe.py      # bloques «Cómo leerla»
python informe/tablas_resumen.py        # tablas de resumen (tabla_r_*.tex)
python informe/figuras_informe.py       # figuras de los informes
python informe/visualizar_rutas.py      # figuras de rutas y del barrido
python src/mapa_geografico.py       # mapas
python src/diagrama_red.py          # diagrama esquemático de la red
```

Todos terminan con código 0 desde un clon limpio y tardan segundos (las
figuras, unas decenas de segundos). Salvedades, comprobadas en esa prueba:

- Las figuras (PNG y PDF) salen con diferencias de metadatos y de bytes según
  la versión de matplotlib; su contenido es el mismo, pero los archivos
  versionados no quedan idénticos byte a byte.
- `exportar_latex.py` toma los tiempos de `outputs/datos/pruebas_agente.json`, que
  `pruebas_agente.py` reescribe en cada corrida; si se corrió esa prueba sin
  restaurar el JSON, `outputs/tablas/tabla_criterios.tex` cambia.
- `cruce_mortalidad.py` (lo llama `construir_red.py`) escribe
  `mortalidad_por_100km` con más decimales que el archivo versionado
  (4.186 contra 4.19 en Tunja a Duitama); por eso no conviene correrlo solo
  para «refrescar» resultados.
- `candidatos_tablas.py` y `cifras_movidas.py` son auditorías de una sola vez
  del cambio de texto a tablas (comparan contra la rama `master` de ese
  momento); no forman parte de la regeneración.

`python informe/formato_latex.py outputs/tablas/tabla_*.tex` aplica el estilo único de
tablas (cuadrícula y encabezado gris) y es idempotente.

## 7. Armar el zip de la entrega

```powershell
python src/empaquetar.py ..\Proyecto_IA_Corte2.zip
```

Incluye lo versionado y excluye `_archivo_transmilenio`,
`outputs/muestras_formato` y los documentos de terceros. Probado: se
descomprime aparte y los comandos de la sección 3 funcionan.

## 8. Qué tarda cuánto

Medido en el clon limpio (segundos):

- Menos de 5 s: agente, demostraciones, grafo, heurística, tablas, lecturas y
  la mayoría de las suites.
- 6 a 9 s: `visualizar_rutas.py`, `diagrama_red.py`, `mapa_geografico.py`,
  `pruebas_mapa.py`.
- 20 a 30 s: `pruebas_figuras.py`, `figuras_informe.py`, `verificar_cifras.py`
  (vuelve a correr los comandos del guion) y `cruce_mortalidad.py`.
- No medidos (mediciones largas, no ejecutadas): `experimentos_corte2.py`,
  `validacion_agente.py` y `medir_umbral.py`; los dos últimos tardan varios
  minutos o más y dependen de la máquina.
