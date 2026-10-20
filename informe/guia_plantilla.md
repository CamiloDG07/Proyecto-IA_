# Guía de comandos del Corte 2

Proyecto integrador de inteligencia artificial, Universidad Sergio Arboleda: enrutamiento de carga interurbana sobre una red fija de 32 nodos, 32 aristas y un ciclo. Esta guía acompaña al informe del Corte 2 (el PDF entregado aparte) y se escribió a partir de este mismo paquete: cada salida mostrada sale de una ejecución real, hecha desde el paquete descomprimido en un entorno virtual nuevo.

## 1. Qué contiene el paquete

| Carpeta | Contenido |
|---|---|
| `src/` | Núcleo que se ejecuta: construcción del grafo, los cinco algoritmos, heurística, agente, despachador, Held-Karp y ACO |
| `experimentos/` | Corridas que producen los resultados del informe (escenarios, validación, umbral de Held-Karp) |
| `informe/` | Código que arma las tablas, las lecturas y las figuras del informe |
| `pruebas/` | Pruebas automáticas (`pruebas_*.py`) y `ejecutar_pruebas.py`, que las corre todas |
| `outputs/` | Resultados guardados (`datos/`), tablas, lecturas y figuras del informe |
| `data/carga/` | Datos livianos de entrada: coordenadas, peajes, siniestralidad y mapa departamental |
| raíz | `config_costos.json`, `requirements.txt`, `README.md`, `EJECUTAR.md`, `guion_demostracion.md` y esta guía |

El paquete no incluye el informe en LaTeX ni el archivo `red_vial.csv` (238 MB, ver la sección 6).

## 2. Requisitos e instalación

Se usó Python 3.14.3 en Windows. En PowerShell, desde la carpeta del paquete:

```powershell-manual
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:PYTHONIOENCODING = "utf-8"
```

`requirements.txt` lista `numpy`, `scipy`, `networkx`, `matplotlib` y `pycodestyle`. La variable `PYTHONIOENCODING` evita errores con las tildes en la consola. Si PowerShell bloquea la activación del entorno, ejecutar antes `Set-ExecutionPolicy -Scope Process Bypass`. En lo que sigue, `python` es el del entorno virtual y los comandos se dan desde la raíz del paquete (también funcionan desde otro directorio con la ruta completa del script).

## 3. Demostración del agente

El usuario da solo el origen y el destino; el agente decide el tipo de problema, el criterio, el algoritmo y la heurística. Los nombres de ciudades con espacio van entre comillas.

**Caso central: Duitama a Puente Nacional.**

```powershell
python src/agente_rutas.py Duitama "Puente Nacional"
```

{{salida 30}}

El agente recomienda la ruta por Bogotá (370.54 km y 170 800 COP de peaje) con el criterio por defecto, el costo compuesto sin riesgo; la salida sigue con las alternativas y el criterio que prefiere cada candidata.

**Par sin ciclo: Bogotá a Granada.**

```powershell
python src/agente_rutas.py Bogotá Granada
```

{{salida 30}}

Esta ruta no pasa por el ciclo (el desvío por Santander), de modo que solo hay un camino: no se listan alternativas y todos los criterios prefieren la misma ruta.

**Criterio por peaje.**

```powershell
python src/agente_rutas.py Duitama "Puente Nacional" --criterio peaje
```

{{salida 30}}

Con `--criterio peaje` el agente elige el desvío por Santander (654.25 km, 100 200 COP de peaje) y lo indica en la salida.

**Criterio por costo operativo.**

```powershell
python src/agente_rutas.py Duitama "Puente Nacional" --criterio costo_operativo
```

{{salida 30}}

Con el costo operativo (peaje más combustible) vuelve a ganar la ruta por Bogotá.

**Varios destinos con regreso.**

```powershell
python src/agente_rutas.py Duitama Tunja Bogotá Villeta --regreso
```

{{salida 30}}

Con varios destinos el agente ordena las paradas y arma un recorrido de ida y vuelta.

**Ida y vuelta con el regreso bloqueado.**

```powershell
python src/agente_rutas.py Duitama "Puente Nacional" --regreso --bloquear-regreso "Tunja-Chocontá"
```

{{salida 30}}

`--bloquear-regreso` bloquea una arista solo en el viaje de vuelta: la ida sigue por Bogotá y la vuelta toma el desvío por Santander.

**Otros comandos del guion de la demostración** (fragmentos de 10 líneas).

```powershell
python src/agente_rutas.py Bogotá Fusagasugá
```

{{salida 10}}

```powershell
python src/agente_rutas.py Chiquinquirá Chocontá
```

{{salida 10}}

```powershell
python src/agente_rutas.py Cajicá Zipaquirá
```

{{salida 10}}

```powershell
python src/agente_rutas.py Duitama Presidente
```

{{salida 10}}

```powershell
python src/agente_rutas.py Duitama "Puente Nacional" --regreso
```

{{salida 10}}

```powershell
python src/agente_rutas.py Duitama "Puente Nacional" --precio-galon 14000 --rendimiento 8 --costo-otros-km 500
```

{{salida 10}}

Con `--precio-galon`, `--rendimiento` y `--costo-otros-km` el usuario reemplaza los insumos del costo monetario y la salida los rotula «dado por el usuario».

## 4. Despachador y algoritmos

`src/demostracion.py` corre los cinco algoritmos (BFS, DFS, costo uniforme, búsqueda voraz y A*) sobre un par de ciudades y un criterio, o llama al despachador. Los tiempos varían de una corrida a otra.

```powershell
python src/demostracion.py Duitama "Puente Nacional" distancia
```

{{salida 12}}

BFS y DFS devuelven el desvío por Santander (654.25 km); costo uniforme, voraz y A* devuelven la ruta por Bogotá (370.54 km), y A* expande menos nodos que costo uniforme.

```powershell
python src/demostracion.py Duitama "Puente Nacional" compuesto_sin_riesgo
```

{{salida 12}}

```powershell
python src/demostracion.py Bucaramanga Bogotá distancia
```

{{salida 12}}

El modo avanzado, `despachador TIPO ORIGEN`, resuelve el tipo de problema indicado (`a` origen a destino, `b` paradas en orden fijo, `c` obligatorias o bloqueadas, `d` orden libre con regreso, `e` orden libre sin regreso).

```powershell
python src/demostracion.py despachador a Duitama --destino "Puente Nacional"
```

{{salida 25}}

```powershell
python src/demostracion.py despachador d Bogotá --paradas "Tunja,Villeta,Girardot,Duitama,Zipaquirá"
```

{{salida 25}}

Con cinco paradas libres el despachador usa Held-Karp (método exacto) porque k = 5 no supera el umbral medido (K = 19).

```powershell
python src/demostracion.py despachador c Duitama --destino "Puente Nacional" --obligatorias Tunja --bloqueados "Tunja/Chocontá"
```

{{salida 25}}

## 5. Pruebas y verificación

Un solo comando corre todas las suites, cada una en su proceso. Algunas regeneran archivos de `outputs/`; `ejecutar_pruebas.py` toma una copia antes y restaura lo que cambió, de modo que los resultados guardados no se alteran.

```powershell
python pruebas/ejecutar_pruebas.py
```

{{salida 20}}

Resultado esperado: todas las suites en `OK` y la última línea «15 de 15 suites pasan» (código de salida 0). Para una sola suite: `python pruebas/pruebas_busquedas.py`.

El estilo del código (PEP 8) se comprueba con pycodestyle; no imprime nada si todo está bien.

```powershell
python -m pycodestyle --max-line-length=79 src pruebas experimentos informe
```

{{salida 5}}

El verificador de cifras (`verificar_cifras.py`) y el comparador con la entrega anterior (`comparar_resultados.py`) contrastan el informe en LaTeX y el historial de git del repositorio; por eso no forman parte de este paquete.

## 6. Reproducir los resultados del informe

Cada script regenera archivos de `outputs/`. Conviene hacer antes una copia de la carpeta (`Copy-Item -Recurse outputs outputs_copia`): los scripts de medición reescriben los resultados guardados, y volver a medir cambia los tiempos y la memoria que cita el informe.

| Script | Produce | Duración medida |
|---|---|---|
| `experimentos/experimentos_corte2.py` | `resultados_corte2.json`, `barrido_pesos.json`, `barrido_total.json`, `sensibilidad_corte2.json` | {{tiempo experimentos/experimentos_corte2.py}} |
| `experimentos/validacion_agente.py` | `validacion_agente.json` y `.csv`, `convergencia_aco.csv` | {{tiempo experimentos/validacion_agente.py}} |
| `experimentos/medir_umbral.py` | `umbral_sesion_N.json`, `umbral_held_karp.json` (el umbral K de Held-Karp) | {{tiempo experimentos/medir_umbral.py}} |
| `experimentos/verificar_estructura.py` | `verificacion_estructura.json` | {{tiempo experimentos/verificar_estructura.py}} |
| `experimentos/perfil_topologico.py` | `perfil_topologico.json` | {{tiempo experimentos/perfil_topologico.py}} |
| `src/heuristica.py` | `analisis_heuristica.json` | {{tiempo src/heuristica.py}} |
| `informe/tablas_agente.py` | tablas del agente (`tabla_ag_*.tex`) | {{tiempo informe/tablas_agente.py}} |
| `informe/lecturas_informe.py` | bloques «Cómo leerla» (`lectura_*.tex`) | {{tiempo informe/lecturas_informe.py}} |
| `informe/tablas_resumen.py` | tablas de resumen (`tabla_r_*.tex`) | {{tiempo informe/tablas_resumen.py}} |
| `informe/figuras_informe.py` | figuras del informe | {{tiempo informe/figuras_informe.py}} |
| `informe/visualizar_rutas.py` | figuras de rutas y del barrido | {{tiempo informe/visualizar_rutas.py}} |

Los tres primeros miden tiempos y memoria de la máquina: sus resultados cambian entre corridas y `medir_umbral.py` tarda varios minutos. Las duraciones se midieron en una copia temporal del paquete, no sobre los archivos entregados.

Las tablas, lecturas y figuras se regeneran sin medir nada:

```powershell
python informe/tablas_resumen.py
```

{{salida 5}}

```powershell
python informe/lecturas_informe.py
```

{{salida 5}}

La construcción de la red desde cero (`src/construir_red.py`) requiere `data/carga/red_vial.csv`, que no se incluye: pesa 238 MB y es la descarga oficial de INVÍAS en datos.gov.co (`https://www.datos.gov.co/resource/ie7y-asdn.csv`). Su huella SHA-256 está en `data/carga/VERIFICACION.md`. Sin ese archivo el script termina con `FileNotFoundError` por `red_vial.csv`; el grafo ya está construido en `outputs/datos/`.

## 7. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `Error: Ciudad fuera de la red: Puente` | El nombre tiene un espacio y falta la comilla: escribir `"Puente Nacional"` |
| Tildes ilegibles en la consola | Ejecutar `$env:PYTHONIOENCODING = "utf-8"` antes del comando |
| `ModuleNotFoundError: No module named 'networkx'` | El entorno virtual no está activado o no se instaló `requirements.txt` |
| `FileNotFoundError` con una ruta relativa | Ejecutar desde la raíz del paquete o usar la ruta completa del script |
| `FileNotFoundError: ... red_vial.csv` | Solo `construir_red.py` lo necesita; ver la sección 6 |
| Una prueba reescribió un archivo de `outputs/` | Usar `python pruebas/ejecutar_pruebas.py`, que lo restaura |
