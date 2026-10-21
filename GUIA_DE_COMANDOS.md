# Guía de comandos del Corte 2

Proyecto integrador de inteligencia artificial, Universidad Sergio Arboleda: enrutamiento de carga interurbana sobre una red fija de 32 nodos, 32 aristas y un ciclo. Esta guía acompaña al informe del Corte 2 (el PDF entregado aparte) y se escribió a partir de este mismo paquete: cada salida mostrada sale de una ejecución real, hecha desde el paquete descomprimido en un entorno virtual nuevo.

## 1. Qué contiene el paquete

| Carpeta | Contenido |
|---|---|
| `src/` | Núcleo que se ejecuta: construcción del grafo, los cinco algoritmos, heurística, agente, despachador, Held-Karp y ACO |
| `experimentos/` | Corridas que producen los resultados del informe (escenarios, validación, umbral de Held-Karp) |
| `informe/` | Código que arma las tablas, las lecturas y las figuras del informe |
| `pruebas/` | Pruebas automáticas (`pruebas_*.py`) y `ejecutar_pruebas.py`, que las corre todas |
| `visualizador/` | Aplicación web local: servidor FastAPI e interfaz con Leaflet y fuentes propias (sección 8) |
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

`requirements.txt` lista `numpy`, `scipy`, `networkx`, `matplotlib`, `pycodestyle` y, para el visualizador web, `fastapi` y `uvicorn` (con versión fijada). La variable `PYTHONIOENCODING` evita errores con las tildes en la consola. Si PowerShell bloquea la activación del entorno, ejecutar antes `Set-ExecutionPolicy -Scope Process Bypass`. En lo que sigue, `python` es el del entorno virtual y los comandos se dan desde la raíz del paquete (también funcionan desde otro directorio con la ruta completa del script).

## 3. Demostración del agente

El usuario da solo el origen y el destino; el agente decide el tipo de problema, el criterio, el algoritmo y la heurística. Los nombres de ciudades con espacio van entre comillas.

**Caso central: Duitama a Puente Nacional.**

```powershell
python src/agente_rutas.py Duitama "Puente Nacional"
```

```text
Origen: Duitama  Destinos: Puente Nacional  Regreso: no
Tipo de problema decidido: origen_destino
Ruta recomendada: Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté >
      Puente Nacional
Insumos del costo monetario: precio del galón 11 320 COP (verificada); rendimiento 9.78 km por
      galón (verificada); otros costos por km 0 COP (supuesto del equipo); costo variable 1
      157.0 COP por km
  Pesos del compuesto total (distancia, peaje, riesgo, costo variable): 0.25, 0.25, 0.25, 0.25
      (supuesto del equipo)
  Advertencia: el criterio por defecto sigue siendo el compuesto sin riesgo porque no todos los
      insumos del costo operativo están verificados (otros costos por km); el costo se calcula
      con ese valor marcado.
  Distancia: 370.54 km   Peaje: 170 800 COP
  Costo variable: 428 710 COP   Costo operativo (peaje + variable): 599 510 COP
  Riesgo (suma de GiZScore con dato): 9.85; dato en el 50 % de los tramos
  Costo compuesto sin riesgo: 3.367
Regla: menor costo compuesto sin riesgo = suma por tramo de (w_d*km/máx_km +
      w_p*peaje/máx_peaje)/(w_d+w_p), con w_d = 1 y w_p = 1
Método y heurística:
  distancia: A* por tramo; exacto: A* con heurística admisible, disponible para el criterio
      distancia; 14 nodos expandidos
  peaje: UCS por tramo; exacto: UCS, porque el criterio peaje no tiene heurística admisible
      informativa o no hay coordenadas; 14 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio compuesto_sin_riesgo; 22 nodos expandidos
  costo_operativo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio costo_operativo; 17 nodos expandidos
  alfa de la heurística: 1.000000; total de nodos expandidos: 67
Alternativas no dominadas:
  Duitama > La Palmera > Presidente > Pamplona > Cuestaboba > Bucaramanga > San Gil > Puente
…
```

El agente recomienda la ruta por Bogotá (370.54 km y 170 800 COP de peaje) con el criterio por defecto, el costo compuesto sin riesgo; la salida sigue con las alternativas y el criterio que prefiere cada candidata.

**Par sin ciclo: Bogotá a Granada.**

```powershell
python src/agente_rutas.py Bogotá Granada
```

```text
Origen: Bogotá  Destinos: Granada  Regreso: no
Tipo de problema decidido: origen_destino
Ruta recomendada: Bogotá > Villavicencio > Ye de Granada > Granada
Insumos del costo monetario: precio del galón 11 320 COP (verificada); rendimiento 9.78 km por
      galón (verificada); otros costos por km 0 COP (supuesto del equipo); costo variable 1
      157.0 COP por km
  Pesos del compuesto total (distancia, peaje, riesgo, costo variable): 0.25, 0.25, 0.25, 0.25
      (supuesto del equipo)
  Advertencia: el criterio por defecto sigue siendo el compuesto sin riesgo porque no todos los
      insumos del costo operativo están verificados (otros costos por km); el costo se calcula
      con ese valor marcado.
  Distancia: 169.39 km   Peaje: 46 700 COP
  Costo variable: 195 988 COP   Costo operativo (peaje + variable): 242 688 COP
  Riesgo (suma de GiZScore con dato): 7.30; dato en el 100 % de los tramos
  Costo compuesto sin riesgo: 1.162
Regla: menor costo compuesto sin riesgo = suma por tramo de (w_d*km/máx_km +
      w_p*peaje/máx_peaje)/(w_d+w_p), con w_d = 1 y w_p = 1
Método y heurística:
  distancia: A* por tramo; exacto: A* con heurística admisible, disponible para el criterio
      distancia; 4 nodos expandidos
  peaje: UCS por tramo; exacto: UCS, porque el criterio peaje no tiene heurística admisible
      informativa o no hay coordenadas; 11 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio compuesto_sin_riesgo; 10 nodos expandidos
  costo_operativo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio costo_operativo; 6 nodos expandidos
  alfa de la heurística: 1.000000; total de nodos expandidos: 31
Criterio que prefiere cada candidata:
  distancia, peaje, riesgo, compuesto_sin_riesgo, compuesto, costo_operativo: Bogotá >
      Villavicencio > Ye de Granada > Granada
…
```

Esta ruta no pasa por el ciclo (el desvío por Santander), de modo que solo hay un camino: no se listan alternativas y todos los criterios prefieren la misma ruta.

**Criterio por peaje.**

```powershell
python src/agente_rutas.py Duitama "Puente Nacional" --criterio peaje
```

```text
Origen: Duitama  Destinos: Puente Nacional  Regreso: no
Tipo de problema decidido: origen_destino
Criterio elegido por el usuario: peaje (el agente no aplicó su regla de compuesto sin riesgo)
Ruta recomendada: Duitama > La Palmera > Presidente > Pamplona > Cuestaboba > Bucaramanga > San
      Gil > Puente Nacional
Insumos del costo monetario: precio del galón 11 320 COP (verificada); rendimiento 9.78 km por
      galón (verificada); otros costos por km 0 COP (supuesto del equipo); costo variable 1
      157.0 COP por km
  Pesos del compuesto total (distancia, peaje, riesgo, costo variable): 0.25, 0.25, 0.25, 0.25
      (supuesto del equipo)
  Distancia: 654.25 km   Peaje: 100 200 COP
  Costo variable: 756 965 COP   Costo operativo (peaje + variable): 857 165 COP
  Riesgo (suma de GiZScore con dato): 0.00; dato en el 0 % de los tramos
  Costo compuesto sin riesgo: 3.524
Regla: menor costo peaje (criterio del usuario)
Método y heurística:
  distancia: A* por tramo; exacto: A* con heurística admisible, disponible para el criterio
      distancia; 14 nodos expandidos
  peaje: UCS por tramo; exacto: UCS, porque el criterio peaje no tiene heurística admisible
      informativa o no hay coordenadas; 14 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio compuesto_sin_riesgo; 22 nodos expandidos
  costo_operativo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio costo_operativo; 17 nodos expandidos
  alfa de la heurística: 1.000000; total de nodos expandidos: 67
Alternativas no dominadas:
  Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté > Puente
      Nacional: 370.54 km  170 800 COP  margen 70 600 COP (70.5 %) sobre la recomendada
Umbral del costo variable por km: la recomendación por costo operativo cambia en 248.8 COP/km
      (ahorro de peaje de 70 600 COP entre 283.71 km extra). Con un costo variable mayor gana
…
```

Con `--criterio peaje` el agente elige el desvío por Santander (654.25 km, 100 200 COP de peaje) y lo indica en la salida.

**Criterio por costo operativo.**

```powershell
python src/agente_rutas.py Duitama "Puente Nacional" --criterio costo_operativo
```

```text
Origen: Duitama  Destinos: Puente Nacional  Regreso: no
Tipo de problema decidido: origen_destino
Criterio elegido por el usuario: costo_operativo (el agente no aplicó su regla de compuesto sin
      riesgo)
Ruta recomendada: Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté >
      Puente Nacional
Insumos del costo monetario: precio del galón 11 320 COP (verificada); rendimiento 9.78 km por
      galón (verificada); otros costos por km 0 COP (supuesto del equipo); costo variable 1
      157.0 COP por km
  Pesos del compuesto total (distancia, peaje, riesgo, costo variable): 0.25, 0.25, 0.25, 0.25
      (supuesto del equipo)
  Distancia: 370.54 km   Peaje: 170 800 COP
  Costo variable: 428 710 COP   Costo operativo (peaje + variable): 599 510 COP
  Riesgo (suma de GiZScore con dato): 9.85; dato en el 50 % de los tramos
  Costo compuesto sin riesgo: 3.367
Regla: menor costo costo_operativo (criterio del usuario)
Método y heurística:
  distancia: A* por tramo; exacto: A* con heurística admisible, disponible para el criterio
      distancia; 14 nodos expandidos
  peaje: UCS por tramo; exacto: UCS, porque el criterio peaje no tiene heurística admisible
      informativa o no hay coordenadas; 14 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio compuesto_sin_riesgo; 22 nodos expandidos
  costo_operativo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio costo_operativo; 17 nodos expandidos
  alfa de la heurística: 1.000000; total de nodos expandidos: 67
Alternativas no dominadas:
  Duitama > La Palmera > Presidente > Pamplona > Cuestaboba > Bucaramanga > San Gil > Puente
      Nacional: 654.25 km  100 200 COP  margen 257 655 COP (43.0 %) sobre la recomendada
Umbral del costo variable por km: la recomendación por costo operativo cambia en 248.8 COP/km
…
```

Con el costo operativo (peaje más combustible) vuelve a ganar la ruta por Bogotá.

**Varios destinos con regreso.**

```powershell
python src/agente_rutas.py Duitama Tunja Bogotá Villeta --regreso
```

```text
Origen: Duitama  Destinos: Tunja, Bogotá, Villeta  Regreso: sí
Tipo de problema decidido: orden_libre_regreso
Ruta recomendada: Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Villeta > Bogotá > Tocancipá
      > Chocontá > Tunja > Duitama
Orden de las paradas: Duitama > Villeta > Bogotá > Tunja > Duitama
Insumos del costo monetario: precio del galón 11 320 COP (verificada); rendimiento 9.78 km por
      galón (verificada); otros costos por km 0 COP (supuesto del equipo); costo variable 1
      157.0 COP por km
  Pesos del compuesto total (distancia, peaje, riesgo, costo variable): 0.25, 0.25, 0.25, 0.25
      (supuesto del equipo)
  Advertencia: el criterio por defecto sigue siendo el compuesto sin riesgo porque no todos los
      insumos del costo operativo están verificados (otros costos por km); el costo se calcula
      con ese valor marcado.
  Distancia: 519.94 km   Peaje: 208 800 COP
  Costo variable: 601 570 COP   Costo operativo (peaje + variable): 810 370 COP
  Riesgo (suma de GiZScore con dato): 26.55; dato en el 100 % de los tramos
  Costo compuesto sin riesgo: 4.353
Regla: menor costo compuesto sin riesgo = suma por tramo de (w_d*km/máx_km +
      w_p*peaje/máx_peaje)/(w_d+w_p), con w_d = 1 y w_p = 1
Método y heurística:
  compuesto_sin_riesgo: Held-Karp; exacto viable: k = 3 paradas libres <= 19 (umbral medido en
      esta máquina para un presupuesto de 5.0 s); 41 nodos expandidos
  alfa de la heurística: 1.000000; total de nodos expandidos: 41
Advertencias:
  - La ruta usa Chocontá a Tunja, sector truncado en la fuente: su distancia oficial (17.69 km)
      es menor que la línea recta (56.96 km); el modelo usa la recta como cota inferior.
  - Aristas con piso geodésico (la distancia oficial es menor que la línea recta y el modelo usa
      la recta como cota inferior): Bogotá - Tocancipá (22.12 a 41.19 km); Duitama - Tunja
      (47.73 a 47.78 km).
  - Aristas marcadas por la auditoría geométrica: Bogotá - Villeta.
```

Con varios destinos el agente ordena las paradas y arma un recorrido de ida y vuelta.

**Ida y vuelta con el regreso bloqueado.**

```powershell
python src/agente_rutas.py Duitama "Puente Nacional" --regreso --bloquear-regreso "Tunja-Chocontá"
```

```text
Origen: Duitama  Destino: Puente Nacional  Regreso: sí
Tipo de problema decidido: ida_y_vuelta
Insumos del costo monetario: precio del galón 11 320 COP (verificada); rendimiento 9.78 km por
      galón (verificada); otros costos por km 0 COP (supuesto del equipo); costo variable 1
      157.0 COP por km
  Pesos del compuesto total (distancia, peaje, riesgo, costo variable): 0.25, 0.25, 0.25, 0.25
      (supuesto del equipo)
  Advertencia: el criterio por defecto sigue siendo el compuesto sin riesgo porque no todos los
      insumos del costo operativo están verificados (otros costos por km); el costo se calcula
      con ese valor marcado.
Ida: Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté > Puente
      Nacional
  Distancia: 370.54 km   Peaje: 170 800 COP
  Costo variable: 428 710 COP   Costo operativo (peaje + variable): 599 510 COP
  Riesgo (suma de GiZScore con dato): 9.85; dato en el 50 % de los tramos
Vuelta: Puente Nacional > San Gil > Bucaramanga > Cuestaboba > Pamplona > Presidente > La
      Palmera > Duitama
  Distancia: 654.25 km   Peaje: 100 200 COP
  Costo variable: 756 965 COP   Costo operativo (peaje + variable): 857 165 COP
  Regreso recalculado con los tramos bloqueados solo en el regreso: Tunja-Chocontá; costo
      compuesto sin riesgo +4.7 % respecto de la ida invertida
Total ida y vuelta: 1024.79 km   Peaje: 271 000 COP   Costo operativo: 1 456 675 COP
Método y heurística de la ida:
  distancia: A* por tramo; 14 nodos expandidos
  peaje: UCS por tramo; 14 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; 22 nodos expandidos
  costo_operativo: A* por tramo; 17 nodos expandidos
Método y heurística del regreso:
  distancia: A* por tramo; 26 nodos expandidos
  peaje: UCS por tramo; 13 nodos expandidos
…
```

`--bloquear-regreso` bloquea una arista solo en el viaje de vuelta: la ida sigue por Bogotá y la vuelta toma el desvío por Santander.

**Otros comandos del guion de la demostración** (fragmentos de 10 líneas).

```powershell
python src/agente_rutas.py Bogotá Fusagasugá
```

```text
Origen: Bogotá  Destinos: Fusagasugá  Regreso: no
Tipo de problema decidido: origen_destino
Ruta recomendada: Bogotá > Fusagasugá
Insumos del costo monetario: precio del galón 11 320 COP (verificada); rendimiento 9.78 km por
      galón (verificada); otros costos por km 0 COP (supuesto del equipo); costo variable 1
      157.0 COP por km
  Pesos del compuesto total (distancia, peaje, riesgo, costo variable): 0.25, 0.25, 0.25, 0.25
      (supuesto del equipo)
  Advertencia: el criterio por defecto sigue siendo el compuesto sin riesgo porque no todos los
      insumos del costo operativo están verificados (otros costos por km); el costo se calcula
…
```

```powershell
python src/agente_rutas.py Chiquinquirá Chocontá
```

```text
Origen: Chiquinquirá  Destinos: Chocontá  Regreso: no
Tipo de problema decidido: origen_destino
Ruta recomendada: Chiquinquirá > Sáchica > Tunja > Chocontá
Insumos del costo monetario: precio del galón 11 320 COP (verificada); rendimiento 9.78 km por
      galón (verificada); otros costos por km 0 COP (supuesto del equipo); costo variable 1
      157.0 COP por km
  Pesos del compuesto total (distancia, peaje, riesgo, costo variable): 0.25, 0.25, 0.25, 0.25
      (supuesto del equipo)
  Advertencia: el criterio por defecto sigue siendo el compuesto sin riesgo porque no todos los
      insumos del costo operativo están verificados (otros costos por km); el costo se calcula
…
```

```powershell
python src/agente_rutas.py Cajicá Zipaquirá
```

```text
Origen: Cajicá  Destinos: Zipaquirá  Regreso: no
Tipo de problema decidido: origen_destino
Ruta recomendada: Cajicá > Zipaquirá
Insumos del costo monetario: precio del galón 11 320 COP (verificada); rendimiento 9.78 km por
      galón (verificada); otros costos por km 0 COP (supuesto del equipo); costo variable 1
      157.0 COP por km
  Pesos del compuesto total (distancia, peaje, riesgo, costo variable): 0.25, 0.25, 0.25, 0.25
      (supuesto del equipo)
  Advertencia: el criterio por defecto sigue siendo el compuesto sin riesgo porque no todos los
      insumos del costo operativo están verificados (otros costos por km); el costo se calcula
…
```

```powershell
python src/agente_rutas.py Duitama Presidente
```

```text
Origen: Duitama  Destinos: Presidente  Regreso: no
Tipo de problema decidido: origen_destino
Ruta recomendada: Duitama > La Palmera > Presidente
Insumos del costo monetario: precio del galón 11 320 COP (verificada); rendimiento 9.78 km por
      galón (verificada); otros costos por km 0 COP (supuesto del equipo); costo variable 1
      157.0 COP por km
  Pesos del compuesto total (distancia, peaje, riesgo, costo variable): 0.25, 0.25, 0.25, 0.25
      (supuesto del equipo)
  Advertencia: el criterio por defecto sigue siendo el compuesto sin riesgo porque no todos los
      insumos del costo operativo están verificados (otros costos por km); el costo se calcula
…
```

```powershell
python src/agente_rutas.py Duitama "Puente Nacional" --regreso
```

```text
Origen: Duitama  Destino: Puente Nacional  Regreso: sí
Tipo de problema decidido: ida_y_vuelta
Insumos del costo monetario: precio del galón 11 320 COP (verificada); rendimiento 9.78 km por
      galón (verificada); otros costos por km 0 COP (supuesto del equipo); costo variable 1
      157.0 COP por km
  Pesos del compuesto total (distancia, peaje, riesgo, costo variable): 0.25, 0.25, 0.25, 0.25
      (supuesto del equipo)
  Advertencia: el criterio por defecto sigue siendo el compuesto sin riesgo porque no todos los
      insumos del costo operativo están verificados (otros costos por km); el costo se calcula
      con ese valor marcado.
…
```

```powershell
python src/agente_rutas.py Duitama "Puente Nacional" --precio-galon 14000 --rendimiento 8 --costo-otros-km 500
```

```text
Origen: Duitama  Destinos: Puente Nacional  Regreso: no
Tipo de problema decidido: origen_destino
Ruta recomendada: Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté >
      Puente Nacional
Insumos del costo monetario: precio del galón 14 000 COP (dado por el usuario); rendimiento 8.00
      km por galón (dado por el usuario); otros costos por km 500 COP (dado por el usuario);
      costo variable 2 250.0 COP por km
  Pesos del compuesto total (distancia, peaje, riesgo, costo variable): 0.25, 0.25, 0.25, 0.25
      (supuesto del equipo)
  Advertencia: el criterio por defecto sigue siendo el compuesto sin riesgo porque no todos los
…
```

Con `--precio-galon`, `--rendimiento` y `--costo-otros-km` el usuario reemplaza los insumos del costo monetario y la salida los rotula «dado por el usuario».

## 4. Despachador y algoritmos

`src/demostracion.py` corre los cinco algoritmos (BFS, DFS, costo uniforme, búsqueda voraz y A*) sobre un par de ciudades y un criterio, o llama al despachador. Los tiempos varían de una corrida a otra.

```powershell
python src/demostracion.py Duitama "Puente Nacional" distancia
```

```text
Duitama a Puente Nacional, criterio distancia
BFS    costo   654.250  expandidos  25  generados  32  frontera  7    294.3 us  7 saltos
       Duitama > La Palmera > Presidente > Pamplona > Cuestaboba > Bucaramanga > San Gil > Puente Nacional  [Santander]
DFS    costo   654.250  expandidos   7  generados   9  frontera  2    120.2 us  7 saltos
       Duitama > La Palmera > Presidente > Pamplona > Cuestaboba > Bucaramanga > San Gil > Puente Nacional  [Santander]
UCS    costo   370.537  expandidos  27  generados  31  frontera  7    301.1 us  8 saltos
       Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté > Puente Nacional  [Bogotá]
Voraz  costo   370.537  expandidos  12  generados  19  frontera  7    128.0 us  8 saltos
       Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté > Puente Nacional  [Bogotá]
A*     costo   370.537  expandidos  14  generados  19  frontera  7    193.2 us  8 saltos
       Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté > Puente Nacional  [Bogotá]
```

BFS y DFS devuelven el desvío por Santander (654.25 km); costo uniforme, voraz y A* devuelven la ruta por Bogotá (370.54 km), y A* expande menos nodos que costo uniforme.

```powershell
python src/demostracion.py Duitama "Puente Nacional" compuesto_sin_riesgo
```

```text
Duitama a Puente Nacional, criterio compuesto_sin_riesgo
BFS    costo     3.524  expandidos  25  generados  32  frontera  7    120.3 us  7 saltos
       Duitama > La Palmera > Presidente > Pamplona > Cuestaboba > Bucaramanga > San Gil > Puente Nacional  [Santander]
DFS    costo     3.524  expandidos   7  generados   9  frontera  2     42.6 us  7 saltos
       Duitama > La Palmera > Presidente > Pamplona > Cuestaboba > Bucaramanga > San Gil > Puente Nacional  [Santander]
UCS    costo     3.367  expandidos  29  generados  32  frontera  7    468.3 us  8 saltos
       Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté > Puente Nacional  [Bogotá]
Voraz  costo     3.367  expandidos  12  generados  19  frontera  7    131.8 us  8 saltos
       Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté > Puente Nacional  [Bogotá]
A*     costo     3.367  expandidos  22  generados  27  frontera  7    358.1 us  8 saltos
       Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté > Puente Nacional  [Bogotá]
```

```powershell
python src/demostracion.py Bucaramanga Bogotá distancia
```

```text
Bucaramanga a Bogotá, criterio distancia
BFS    costo   411.536  expandidos  12  generados  16  frontera  4     53.5 us  6 saltos
       Bucaramanga > San Gil > Puente Nacional > Ubaté > Zipaquirá > Cajicá > Bogotá  [Santander]
DFS    costo   613.251  expandidos  10  generados  13  frontera  4     68.9 us  9 saltos
       Bucaramanga > Cuestaboba > Pamplona > Presidente > La Palmera > Duitama > Tunja > Chocontá > Tocancipá > Bogotá  [Santander]
UCS    costo   411.536  expandidos  10  generados  12  frontera  2    144.8 us  6 saltos
       Bucaramanga > San Gil > Puente Nacional > Ubaté > Zipaquirá > Cajicá > Bogotá  [Santander]
Voraz  costo   411.536  expandidos   6  generados   8  frontera  2    214.2 us  6 saltos
       Bucaramanga > San Gil > Puente Nacional > Ubaté > Zipaquirá > Cajicá > Bogotá  [Santander]
A*     costo   411.536  expandidos   7  generados   9  frontera  2    319.6 us  6 saltos
       Bucaramanga > San Gil > Puente Nacional > Ubaté > Zipaquirá > Cajicá > Bogotá  [Santander]
```

El modo avanzado, `despachador TIPO ORIGEN`, resuelve el tipo de problema indicado (`a` origen a destino, `b` paradas en orden fijo, `c` obligatorias o bloqueadas, `d` orden libre con regreso, `e` orden libre sin regreso).

```powershell
python src/demostracion.py despachador a Duitama --destino "Puente Nacional"
```

```text
Tipo a (origen_destino), criterio distancia
Ruta: Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté > Puente Nacional
Orden de paradas: Duitama > Puente Nacional
Costo: 370.537
Método: A* por tramo
Motivo: exacto: A* con heurística admisible, disponible para el criterio distancia
  paradas: 2
  nodos_expandidos: 14
  tiempo_matriz_s: 0.0009750999997777399
  tiempo_s: 0.0011188999997102655
```

```powershell
python src/demostracion.py despachador d Bogotá --paradas "Tunja,Villeta,Girardot,Duitama,Zipaquirá"
```

```text
Tipo d (orden_libre_regreso), criterio distancia
Ruta: Bogotá > Villeta > Bogotá > Tocancipá > Chocontá > Tunja > Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Cajicá > Bogotá > Fusagasugá > Girardot > Fusagasugá > Bogotá
Orden de paradas: Bogotá > Villeta > Duitama > Tunja > Zipaquirá > Girardot > Bogotá
Costo: 862.173
Método: Held-Karp
Motivo: exacto viable: k = 5 paradas libres <= 19 (umbral medido en esta máquina para un presupuesto de 5.0 s)
  paradas: 6
  nodos_expandidos: 77
  tiempo_matriz_s: 0.004573700000037206
  k: 5
  umbral_k: 19
  modo: ciclo
  presupuesto_s: 5.0
  tiempo_orden_s: 0.002734200000304554
  tiempo_s: 0.0105174000000261
```

Con cinco paradas libres el despachador usa Held-Karp (método exacto) porque k = 5 no supera el umbral medido (K = 19).

```powershell
python src/demostracion.py despachador c Duitama --destino "Puente Nacional" --obligatorias Tunja --bloqueados "Tunja/Chocontá"
```

```text
Tipo c (obligatorias_o_bloqueados), criterio distancia
Ruta: Duitama > Tunja > Duitama > La Palmera > Presidente > Pamplona > Cuestaboba > Bucaramanga > San Gil > Puente Nacional
Orden de paradas: Duitama > Tunja > Puente Nacional
Costo: 749.818
Método: A* por tramo
Motivo: una parada obligatoria intermedia: orden determinado; 1 tramo(s) bloqueado(s) excluidos de todas las búsquedas; exacto: A* con heurística admisible, disponible para el criterio distancia
  paradas: 3
  nodos_expandidos: 23
  tiempo_matriz_s: 0.0029752999998891028
  tiempo_s: 0.0033637999999882595
```

## 5. Pruebas y verificación

Un solo comando corre todas las suites, cada una en su proceso (tarda unos 3 minutos). Algunas regeneran archivos de `outputs/`; `ejecutar_pruebas.py` toma una copia antes y restaura lo que cambió, de modo que los resultados guardados no se alteran.

```powershell
python pruebas/ejecutar_pruebas.py
```

```text
OK    pruebas_agente.py (2 s)
OK    pruebas_agente_rutas.py (5 s)
OK    pruebas_busquedas.py (17 s)
OK    pruebas_costos.py (21 s)
OK    pruebas_criterio.py (6 s)
OK    pruebas_despachador.py (7 s)
OK    pruebas_figuras.py (113 s)
OK    pruebas_formato.py (2 s)
OK    pruebas_mapa.py (27 s)
OK    pruebas_orden_libre.py (5 s)
OK    pruebas_perfil_topologico.py (3 s)
OK    pruebas_piso.py (4 s)
OK    pruebas_progresivas.py (2 s)
OK    pruebas_tabla_heuristica.py (6 s)
OK    pruebas_tablas_resumen.py (5 s)
OK    pruebas_trazas.py (38 s)
OK    pruebas_visualizador.py (15 s)
Se restauraron archivos de outputs/ que las pruebas reescriben: barrido_pesos_base.pdf, barrido_pesos_base.png, pruebas_agente.json
17 de 17 suites pasan
```

Resultado esperado: todas las suites en `OK` y la última línea «17 de 17 suites pasan» (código de salida 0). Para una sola suite: `python pruebas/pruebas_busquedas.py`.

El estilo del código (PEP 8) se comprueba con pycodestyle; no imprime nada si todo está bien.

```powershell
python -m pycodestyle --max-line-length=79 src pruebas experimentos informe visualizador
```

```text

```

El verificador de cifras (`verificar_cifras.py`) y el comparador con la entrega anterior (`comparar_resultados.py`) contrastan el informe en LaTeX y el historial de git del repositorio; por eso no forman parte de este paquete.

## 6. Reproducir los resultados del informe

Cada script regenera archivos de `outputs/`. Conviene hacer antes una copia de la carpeta (`Copy-Item -Recurse outputs outputs_copia`): los scripts de medición reescriben los resultados guardados, y volver a medir cambia los tiempos y la memoria que cita el informe.

| Script | Produce | Duración medida |
|---|---|---|
| `experimentos/experimentos_corte2.py` | `resultados_corte2.json`, `barrido_pesos.json`, `barrido_total.json`, `sensibilidad_corte2.json` | 44 s |
| `experimentos/validacion_agente.py` | `validacion_agente.json` y `.csv`, `convergencia_aco.csv` | 4 min 55 s |
| `experimentos/medir_umbral.py` | `umbral_sesion_N.json`, `umbral_held_karp.json` (el umbral K de Held-Karp) | 2 min 55 s |
| `experimentos/verificar_estructura.py` | `verificacion_estructura.json` | 2 s |
| `experimentos/perfil_topologico.py` | `perfil_topologico.json` | 1 s |
| `src/heuristica.py` | `analisis_heuristica.json` | 1 s |
| `informe/tablas_agente.py` | tablas del agente (`tabla_ag_*.tex`) | 3 s |
| `informe/lecturas_informe.py` | bloques «Cómo leerla» (`lectura_*.tex`) | 2 s |
| `informe/tablas_resumen.py` | tablas de resumen (`tabla_r_*.tex`) | 1 s |
| `informe/figuras_informe.py` | figuras del informe | 29 s |
| `informe/visualizar_rutas.py` | figuras de rutas y del barrido | 5 s |

Los tres primeros miden tiempos y memoria de la máquina: sus resultados cambian entre corridas y `medir_umbral.py` tarda varios minutos. Las duraciones se midieron en una copia temporal del paquete, no sobre los archivos entregados.

Las tablas, lecturas y figuras se regeneran sin medir nada:

```powershell
python informe/tablas_resumen.py
```

```text
Tablas de resumen escritas en outputs/ (tabla_r_*.tex)
```

```powershell
python experimentos/verificar_estructura.py
```

```text
300 grafos: 300 coincidencias, 0 discrepancias, mayor diferencia 4.26e-14
longitudes de ciclo: {3: 64, 4: 61, 5: 59, 6: 41, 7: 28, 8: 17, 9: 13, 10: 9, 11: 5, 12: 3}
```

El segundo comprueba la fórmula del óptimo por estructura del ciclo contra Held-Karp en grafos de prueba (`verificacion_estructura.json`).

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

## 8. Visualizador web

La aplicación local dibuja, sobre la red real, la animación paso a paso de los cinco algoritmos con su árbol de búsqueda, la construcción de la ruta con las métricas acumuladas, la comparación de algoritmos y de criterios, y el despachador. El comando levanta el servidor en `http://127.0.0.1:8000` y abre el navegador (se detiene con Ctrl+C); la documentación de la API está en `/docs`.

```powershell-manual
python visualizador/servidor.py
```

La verificación de arranque levanta el servidor en un puerto libre, pide `/`, `/api/red` y una búsqueda, comprueba los valores conocidos del caso central (370.54 km por Bogotá, 654.25 km por Santander, A* con 14 expandidos) y lo apaga. Tarda unos 15 segundos.

```powershell
python pruebas/pruebas_visualizador.py
```

```text
GET /api/red
GET /api/red: coordenadas de los 32 nodos dentro de Colombia
GET /api/salud y límites de la entrada
El servidor no escribe en disco (sistema de archivos de solo lectura)
GET /api/busqueda: caso central
  coincide con busquedas.py en los cinco algoritmos
Las métricas son la suma de las aristas de la ruta
GET /api/comparar
GET /api/criterios: el compromiso entre criterios
Errores con código HTTP y mensaje en español
POST /api/despachador
  tipo c con una obligatoria y un tramo bloqueado
  ida y vuelta con un tramo bloqueado solo en el regreso
Held-Karp con k = 19 y ACO con k = 20 (instancias de demostración)
  k = 19: Held-Karp, el límite del método exacto
Interfaz y documentación de la API
Arranque del servidor en un puerto libre
  / , /api/red y /api/busqueda responden en un puerto libre
Pruebas del visualizador: todas pasan
```

Límite: el proyecto no tiene datos de tiempo de viaje; el «tiempo estimado» de la aplicación es la distancia dividida por una velocidad supuesta (50 km/h, supuesto del equipo, editable) y no entra a ningún costo ni resultado. Las instancias de 19 y 20 paradas de los casos de ejemplo son de demostración, no casos de las pruebas del informe.
