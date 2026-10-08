# Guion de la demostración, Corte 2

Duración sugerida: 20 minutos. Todos los comandos se ejecutan desde la raíz
del repositorio, con el entorno virtual activo (`venv\Scripts\activate`).
Los valores que se mencionan salen de las corridas guardadas en `outputs\`.

## 1. La red y el agente (2 min)

```
python src/build_graph.py
python src/agente.py
```

Mostrar: 32 nodos, 32 aristas, 1 ciclo; el agente devuelve, para Duitama a
Puente Nacional, la ruta por Bogotá con `distancia` y `compuesto_sin_riesgo`
(352.41 km) y la ruta por Santander con `peaje`, `riesgo` y `compuesto`
(654.25 km). Los criterios nuevos `costo_operativo` y `compuesto_total_sin_riesgo`
eligen Bogotá; `compuesto_total` elige Santander. Abrir `outputs\diagrama_red.png` para señalar el ciclo.

## 2. Corrección de los algoritmos (1 min)

```
python src/pruebas_busquedas.py
```

Mostrar que BFS, DFS, UCS, voraz y A* (programados desde cero) coinciden con
`networkx` en costo, y que DFS y voraz devuelven rutas válidas, en un grafo de
juguete, en grafos aleatorios y en los 992 pares de la red.

## 3. Heurística (2 min)

```
python src/heuristica.py
```

Mostrar: alfa = 0.458156, determinado por Bogotá a Madrid (entrada urbana
a Bogotá); 0 violaciones de admisibilidad y de consistencia en las siete
heurísticas, con margen mínimo de 0.000008 km en la distancia; con la
geodésica pura (alfa = 1) hay 34 violaciones de admisibilidad en 992 pares.
Con la distancia registrada de Chocontá a Tunja (17.69 km, variante de
sensibilidad) el alfa sería 0.310570. Mencionar las aristas con razón
carretera/geodésica menor que 1 (`outputs\analisis_heuristica.json`).

## 4. Comparación en vivo (3 min)

```
python src/demostracion.py Duitama "Puente Nacional" distancia
python src/demostracion.py Duitama "Puente Nacional" compuesto_sin_riesgo
python src/demostracion.py Bucaramanga Bogotá distancia
python src/demostracion.py Bogotá Granada distancia
python src/demostracion.py Mariquita Granada distancia
```

Qué comentar en cada uno:

| Escenario | Qué mostrar |
|---|---|
| Duitama a Puente Nacional (ciclo) | BFS y DFS devuelven el desvío por Santander (654.25 km); UCS, voraz y A* la ruta óptima (352.41 km). BFS minimiza saltos, no costo |
| Duitama a Puente Nacional, compuesto sin riesgo | Con la corrección de distancias gana la ruta por Bogotá; con las distancias sin corregir ganaba el desvío |
| Bucaramanga a Bogotá (ciclo) | DFS devuelve una ruta más cara que el óptimo (598.17 km contra 408.49 km) |
| Bogotá a Granada (ruta única) | Los cinco devuelven la misma ruta; solo cambian los nodos expandidos |
| Mariquita a Granada (ruta única, 6 saltos) | Igual; la búsqueda voraz expande muy pocos nodos |

Decir sin adornos: con un solo ciclo, solo los pares que lo cruzan muestran
diferencias de ruta entre algoritmos.

## 5. Rutas y barrido de pesos (1 min)

Abrir `outputs\rutas_central_distancia.png` y `outputs\barrido_pesos.png`:
la ruta de cada algoritmo sobre las coordenadas oficiales y la frontera
exacta entre las dos rutas (17 de 66 puntos de la malla favorecen la ruta por
Bogotá en la red corregida; la frontera con riesgo en cero está en
$w_1 = 0.4422$).

## 6. Agente autónomo de rutas y costo monetario (5 min)

El usuario solo da origen y destino(s); el agente decide el tipo de problema,
el criterio, el algoritmo y la heurística, y devuelve la mejor ruta con su
explicación. Regla: con un destino calcula la ruta óptima por distancia, por
peaje, por compuesto sin riesgo y por costo operativo (A* con heurística
admisible o UCS), añade las rutas alternativas que quedan al bloquear una
arista de cada una, descarta las dominadas en km y peaje y recomienda la de
menor compuesto sin riesgo con pesos iguales. Con varios destinos, o con
regreso, ordena las paradas con el despachador (Held-Karp si k es menor o
igual que K_exacto; ACO si no).

Costo monetario: peaje más costo variable, con el costo variable igual a los
km por (precio del galón / rendimiento + otros costos por km). Insumos de
`config_costos.json`: precio del galón 11 320 COP (CREG, verificada), consumo
38.69 litros por 100 km (UPME, verificada) y otros costos por km 0 COP
(supuesto del equipo, no estimado); el costo variable es 1 157.0 COP por km.
Como un insumo es supuesto, el criterio por defecto sigue siendo el compuesto
sin riesgo y el agente lo advierte en la salida; el costo operativo se
calcula y se muestra siempre.

```
python src/agente_rutas.py Duitama "Puente Nacional"
python src/agente_rutas.py Bogotá Granada
python src/agente_rutas.py Duitama Tunja Bogotá Villeta --regreso
python src/agente_rutas.py Duitama "Puente Nacional" --criterio peaje
python src/agente_rutas.py Duitama "Puente Nacional" --criterio costo_operativo
python src/agente_rutas.py Duitama "Puente Nacional" --precio-galon 14000 --rendimiento 8 --costo-otros-km 500
```

Con `--criterio {distancia,peaje,riesgo,compuesto,compuesto_sin_riesgo,costo_operativo,compuesto_total,compuesto_total_sin_riesgo,compuesto_mortalidad}` el usuario elige el criterio con que se escoge la ruta recomendada; sin la opción se usa el compuesto sin riesgo (el compuesto de mortalidad es una variante de sensibilidad). Con `--precio-galon`, `--rendimiento`, `--costo-otros-km` y `--pesos` el usuario cambia los insumos, y la salida los rotula como «dado por el usuario».

| Caso | Qué mostrar |
|---|---|
| Duitama a Puente Nacional (cruza el ciclo) | Recomienda la ruta por Bogotá: 352.41 km, 170 800 COP de peaje, 407 737 COP de combustible (578 537 COP en total), compuesto sin riesgo 3.302. La alternativa por Santander (654.25 km, 100 200 COP de peaje, 857 165 COP en total) queda a 0.222 (6.7 %). Los criterios peaje, riesgo y compuesto prefieren el desvío; el aviso dice que el riesgo solo tiene dato en el 50 % de los tramos de la recomendada y en el 0 % de los del desvío. Advierte que Chocontá a Tunja sale de las progresivas oficiales |
| Umbral de costo | La recomendación por costo operativo cambia en 233.9 COP por km (ahorro de peaje de 70 600 COP entre 301.84 km extra); el combustible solo cuesta 1 157.0 COP por km, unas cinco veces el umbral. Con `--criterio peaje` la alternativa por Bogotá queda a 70 600 COP |
| Bogotá a Granada (ruta única) | Una sola candidata: 168.78 km, 46 700 COP de peaje, 241 978 COP en total; todos los criterios coinciden; solo advierte aristas marcadas por la auditoría |
| Duitama, Tunja, Bogotá y Villeta con regreso | Orden libre: Held-Karp (k = 3); orden Duitama, Villeta, Bogotá, Tunja, Duitama; 489.78 km, 208 800 COP de peaje y 775 474 COP de costo operativo |

Decir sin adornos: la recomendación es la de menor compuesto sin riesgo; los
criterios con riesgo se avisan, no se imponen, porque faltan datos, y el costo
en pesos es un piso porque los otros costos por km valen 0 como supuesto.

## 7. Perfil de la red y casos por tipo de par (5 min)

`python src/perfil_topologico.py` calcula, sobre los 496 pares, cuántos
tienen uno o dos caminos simples y cuántos son de paso obligatorio, de atajo
o de camino único; escribe `outputs\perfil_topologico.json`. En la red de 32
nodos: 111 pares con un camino y
385 con dos;
374 de paso obligatorio,
105 con atajo y
17 de camino único;
10 puntos de articulación. La prueba
`python src/pruebas_perfil_topologico.py` lo contrasta con una enumeración
independiente.

El margen es la diferencia porcentual del costo compuesto sin riesgo entre la
segunda ruta y la recomendada (la regla del agente); todos los pares con
alternativa superan el 5 %.

| Tipo de par | Par | Clase según el perfil | Margen de la segunda ruta |
|---|---|---|---|
| Camino único | Bogotá a Fusagasugá | camino único (1 camino; obligatorios: ninguno) | sin segunda ruta |
| Paso obligatorio | Chiquinquirá a Chocontá | paso obligatorio (2 caminos; obligatorios: Sáchica, Tunja) | 483.0 % |
| Atajo | Cajicá a Zipaquirá | atajo (2 caminos; obligatorios: ninguno) | 20 956.7 % |
| Atajo | Duitama a Presidente | atajo (2 caminos; obligatorios: ninguno) | 595.9 % |
| Ida y vuelta con regreso distinto | Duitama a Puente Nacional, con Tunja-Chocontá bloqueado solo en el regreso | ida por Bogotá, regreso por Santander | 6.7 % (regreso contra ida invertida) |

Con un destino y `--regreso`, el agente resuelve ida y vuelta: sin bloqueos el
regreso es la ida invertida; con `--bloquear-regreso "A-B;C-D"` el regreso se
recalcula con esos tramos bloqueados solo en el regreso (solo con un destino).

Comandos y salidas reales:

```
python src/agente_rutas.py Bogotá Fusagasugá

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
      con ese valor marcado.
  Distancia: 59.02 km   Peaje: 31 500 COP
  Costo variable: 68 286 COP   Costo operativo (peaje + variable): 99 786 COP
  Riesgo (suma de GiZScore con dato): 2.44; dato en el 100 % de los tramos
  Costo compuesto sin riesgo: 0.588
Regla: menor costo compuesto sin riesgo = suma por tramo de (w_d*km/máx_km +
      w_p*peaje/máx_peaje)/(w_d+w_p), con w_d = 1 y w_p = 1
Método y heurística:
  distancia: A* por tramo; exacto: A* con heurística admisible, disponible para el criterio
      distancia; 2 nodos expandidos
  peaje: UCS por tramo; exacto: UCS, porque el criterio peaje no tiene heurística admisible
      informativa o no hay coordenadas; 8 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio compuesto_sin_riesgo; 5 nodos expandidos
  costo_operativo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio costo_operativo; 3 nodos expandidos
  alfa de la heurística: 0.458156; total de nodos expandidos: 18
Criterio que prefiere cada candidata:
  distancia, peaje, riesgo, compuesto_sin_riesgo, compuesto, costo_operativo: Bogotá >
      Fusagasugá
Advertencias:
  - Aristas marcadas por la auditoría geométrica: Bogotá - Fusagasugá.
```

```
python src/agente_rutas.py Chiquinquirá Chocontá

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
      con ese valor marcado.
  Distancia: 133.61 km   Peaje: 58 600 COP
  Costo variable: 154 586 COP   Costo operativo (peaje + variable): 213 186 COP
  Riesgo (suma de GiZScore con dato): 2.57; dato en el 33 % de los tramos
  Costo compuesto sin riesgo: 1.178
Regla: menor costo compuesto sin riesgo = suma por tramo de (w_d*km/máx_km +
      w_p*peaje/máx_peaje)/(w_d+w_p), con w_d = 1 y w_p = 1
Método y heurística:
  distancia: A* por tramo; exacto: A* con heurística admisible, disponible para el criterio
      distancia; 3 nodos expandidos
  peaje: UCS por tramo; exacto: UCS, porque el criterio peaje no tiene heurística admisible
      informativa o no hay coordenadas; 4 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio compuesto_sin_riesgo; 3 nodos expandidos
  costo_operativo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio costo_operativo; 3 nodos expandidos
  alfa de la heurística: 0.458156; total de nodos expandidos: 13
Descartadas por dominadas en km y peaje:
  Chiquinquirá > Sáchica > Tunja > Duitama > La Palmera > Presidente > Pamplona > Cuestaboba >
      Bucaramanga > San Gil > Puente Nacional > Ubaté > Zipaquirá > Cajicá > Bogotá > Tocancipá
      > Chocontá: 1018.27 km  271 000 COP
Criterio que prefiere cada candidata:
  distancia, peaje, riesgo, compuesto_sin_riesgo, compuesto, costo_operativo: Chiquinquirá >
      Sáchica > Tunja > Chocontá
Advertencias:
  - La ruta usa Chocontá a Tunja, cuyo sector está truncado en la fuente: su distancia (61.00 km
      frente a 56.96 km en línea recta) sale de las progresivas oficiales y no de la longitud
      registrada.
  - 2 de 3 tramos no tienen dato de riesgo y valen 0 en los criterios que lo incluyen.
```

```
python src/agente_rutas.py Cajicá Zipaquirá

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
      con ese valor marcado.
  Distancia: 9.10 km   Peaje: 0 COP
  Costo variable: 10 529 COP   Costo operativo (peaje + variable): 10 529 COP
  Riesgo (suma de GiZScore con dato): 0.00; dato en el 0 % de los tramos
  Costo compuesto sin riesgo: 0.032
Regla: menor costo compuesto sin riesgo = suma por tramo de (w_d*km/máx_km +
      w_p*peaje/máx_peaje)/(w_d+w_p), con w_d = 1 y w_p = 1
Método y heurística:
  distancia: A* por tramo; exacto: A* con heurística admisible, disponible para el criterio
      distancia; 1 nodos expandidos
  peaje: UCS por tramo; exacto: UCS, porque el criterio peaje no tiene heurística admisible
      informativa o no hay coordenadas; 1 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio compuesto_sin_riesgo; 1 nodos expandidos
  costo_operativo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio costo_operativo; 1 nodos expandidos
  alfa de la heurística: 0.458156; total de nodos expandidos: 4
Descartadas por dominadas en km y peaje:
  Cajicá > Bogotá > Tocancipá > Chocontá > Tunja > Duitama > La Palmera > Presidente > Pamplona
      > Cuestaboba > Bucaramanga > San Gil > Puente Nacional > Ubaté > Zipaquirá: 997.56 km  271
      000 COP
Criterio que prefiere cada candidata:
  distancia, peaje, riesgo, compuesto_sin_riesgo, compuesto, costo_operativo: Cajicá > Zipaquirá
Advertencias:
  - Aristas marcadas por la auditoría geométrica: Cajicá - Zipaquirá.
  - 1 de 1 tramos no tienen dato de riesgo y valen 0 en los criterios que lo incluyen.
```

```
python src/agente_rutas.py Duitama Presidente

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
      con ese valor marcado.
  Distancia: 241.91 km   Peaje: 0 COP
  Costo variable: 279 889 COP   Costo operativo (peaje + variable): 279 889 COP
  Riesgo (suma de GiZScore con dato): 0.00; dato en el 0 % de los tramos
  Costo compuesto sin riesgo: 0.858
Regla: menor costo compuesto sin riesgo = suma por tramo de (w_d*km/máx_km +
      w_p*peaje/máx_peaje)/(w_d+w_p), con w_d = 1 y w_p = 1
Método y heurística:
  distancia: A* por tramo; exacto: A* con heurística admisible, disponible para el criterio
      distancia; 7 nodos expandidos
  peaje: UCS por tramo; exacto: UCS, porque el criterio peaje no tiene heurística admisible
      informativa o no hay coordenadas; 2 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio compuesto_sin_riesgo; 3 nodos expandidos
  costo_operativo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio costo_operativo; 5 nodos expandidos
  alfa de la heurística: 0.458156; total de nodos expandidos: 17
Descartadas por dominadas en km y peaje:
  Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté > Puente Nacional
      > San Gil > Bucaramanga > Cuestaboba > Pamplona > Presidente: 764.75 km  271 000 COP
Criterio que prefiere cada candidata:
  distancia, peaje, riesgo, compuesto_sin_riesgo, compuesto, costo_operativo: Duitama > La
      Palmera > Presidente
Advertencias:
  - 2 de 2 tramos no tienen dato de riesgo y valen 0 en los criterios que lo incluyen.
```

```
python src/agente_rutas.py Duitama "Puente Nacional" --regreso --bloquear-regreso "Tunja-Chocontá"

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
  Distancia: 352.41 km   Peaje: 170 800 COP
  Costo variable: 407 737 COP   Costo operativo (peaje + variable): 578 537 COP
  Riesgo (suma de GiZScore con dato): 9.85; dato en el 50 % de los tramos
Vuelta: Puente Nacional > San Gil > Bucaramanga > Cuestaboba > Pamplona > Presidente > La
      Palmera > Duitama
  Distancia: 654.25 km   Peaje: 100 200 COP
  Costo variable: 756 965 COP   Costo operativo (peaje + variable): 857 165 COP
  Regreso recalculado con los tramos bloqueados solo en el regreso: Tunja-Chocontá; costo
      compuesto sin riesgo +6.7 % respecto de la ida invertida
Total ida y vuelta: 1006.66 km   Peaje: 271 000 COP   Costo operativo: 1 435 702 COP
Método y heurística de la ida:
  distancia: A* por tramo; 18 nodos expandidos
  peaje: UCS por tramo; 14 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; 27 nodos expandidos
  costo_operativo: A* por tramo; 21 nodos expandidos
Método y heurística del regreso:
  distancia: A* por tramo; 27 nodos expandidos
  peaje: UCS por tramo; 13 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; 24 nodos expandidos
  costo_operativo: A* por tramo; 27 nodos expandidos
  alfa de la heurística: 0.458156; total de nodos expandidos: 171
Advertencias:
  - La ruta usa Chocontá a Tunja, cuyo sector está truncado en la fuente: su distancia (61.00 km
      frente a 56.96 km en línea recta) sale de las progresivas oficiales y no de la longitud
      registrada.
  - Aristas marcadas por la auditoría geométrica: Bogotá - Cajicá; Bogotá - Tocancipá; Cajicá -
      Zipaquirá; Duitama - Tunja.
  - 4 de 8 tramos no tienen dato de riesgo y valen 0 en los criterios que lo incluyen.
  - Los criterios riesgo y compuesto prefieren otra ruta: Duitama > La Palmera > Presidente >
      Pamplona > Cuestaboba > Bucaramanga > San Gil > Puente Nacional. El riesgo solo tiene dato
      en el 50 % de los tramos de la ruta recomendada y en el 0 % de los de la otra; el resto
      vale 0, por lo que esa preferencia puede deberse a falta de datos.
  - Regreso: 7 de 7 tramos no tienen dato de riesgo y valen 0 en los criterios que lo incluyen.
```

```
python src/agente_rutas.py Duitama "Puente Nacional" --regreso

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
  Distancia: 352.41 km   Peaje: 170 800 COP
  Costo variable: 407 737 COP   Costo operativo (peaje + variable): 578 537 COP
  Riesgo (suma de GiZScore con dato): 9.85; dato en el 50 % de los tramos
Vuelta: Puente Nacional > Ubaté > Zipaquirá > Cajicá > Bogotá > Tocancipá > Chocontá > Tunja >
      Duitama
  Distancia: 352.41 km   Peaje: 170 800 COP
  Costo variable: 407 737 COP   Costo operativo (peaje + variable): 578 537 COP
  Sin bloqueos, el regreso es la ida invertida
Total ida y vuelta: 704.82 km   Peaje: 341 600 COP   Costo operativo: 1 157 074 COP
Método y heurística de la ida:
  distancia: A* por tramo; 18 nodos expandidos
  peaje: UCS por tramo; 14 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; 27 nodos expandidos
  costo_operativo: A* por tramo; 21 nodos expandidos
  alfa de la heurística: 0.458156; total de nodos expandidos: 80
Advertencias:
  - La ruta usa Chocontá a Tunja, cuyo sector está truncado en la fuente: su distancia (61.00 km
      frente a 56.96 km en línea recta) sale de las progresivas oficiales y no de la longitud
      registrada.
  - Aristas marcadas por la auditoría geométrica: Bogotá - Cajicá; Bogotá - Tocancipá; Cajicá -
      Zipaquirá; Duitama - Tunja.
  - 4 de 8 tramos no tienen dato de riesgo y valen 0 en los criterios que lo incluyen.
  - Los criterios riesgo y compuesto prefieren otra ruta: Duitama > La Palmera > Presidente >
      Pamplona > Cuestaboba > Bucaramanga > San Gil > Puente Nacional. El riesgo solo tiene dato
      en el 50 % de los tramos de la ruta recomendada y en el 0 % de los de la otra; el resto
      vale 0, por lo que esa preferencia puede deberse a falta de datos.
```

## 8. Modo avanzado: despachador, Held-Karp y ACO (3 min)

El despachador elige el método según el tipo de solicitud (a, origen a
destino; b, paradas en orden fijo; c, obligatorias o tramos bloqueados; d,
orden libre con regreso; e, orden libre sin regreso). Solo llama a las
búsquedas, a Held-Karp y al ACO ya programados; la interfaz es de línea de
comandos.

```
python src/demostracion.py despachador a Duitama --destino "Puente Nacional"
python src/demostracion.py despachador d Bogotá --paradas "Tunja,Villeta,Girardot,Duitama,Zipaquirá"
python src/demostracion.py despachador c Duitama --destino "Puente Nacional" --obligatorias Tunja --bloqueados "Tunja/Chocontá"
```

| Comando | Qué mostrar |
|---|---|
| Tipo a | A* por tramo; el motivo dice que hay heurística admisible para `distancia`; 352.41 km |
| Tipo d con cinco paradas | Held-Karp, porque k = 5 es menor o igual que el umbral medido (K = 19); el motivo y las métricas salen en la respuesta |
| Tipo c con obligatoria y tramo bloqueado | El orden queda determinado (una obligatoria) y el tramo bloqueado se excluye de todas las búsquedas |

Umbral: `outputs\umbral_held_karp.json` combina las sesiones guardadas
(`outputs\umbral_sesion_N.json`) y toma el mayor k dentro del presupuesto en
todas ellas. Aclarar que los tiempos dependen del estado de la máquina; la
tabla del informe muestra la mediana de cada sesión.

ACO: tipos d y e con más de 20 paradas libres, o con matriz asimétrica (sin
2-opt). Validación en `outputs\validacion_agente.json`: en la red de carga
alcanza la referencia en las 130 semillas; en las euclidianas con n = 20
(semillas 1 a 5), brecha media de 0.040 % con 2-opt (48 de 50 semillas) y de 0.357 %
sin 2-opt (32 de 50); con la ciudad de salida fija, sin 2-opt, 2.212 % (1 de
50).

Pregunta preparada: ¿por qué ACO si el 2-opt ya llega al óptimo? Respuesta
con los datos: en la red de carga la brecha de la iteración 1 ya es
0.000 % y el ACO sin 2-opt también llega a la referencia: el aporte
del 2-opt es nulo ahí, pequeño con n = 20 (0.357 % sin 2-opt contra 0.040 %
con él) y crece con n. Donde el exacto no es viable, con n = 100 y 200, sin
2-opt la brecha es 5.599 % y 6.209 %, y con 2-opt el ACO mejora la mejor
solución de 2-opt con inicios múltiples en 0.171 % y 1.400 % de brecha media
(0 de 10 semillas la igualan). No se conoce la distancia al óptimo en esas
instancias.

## 9. Resultados completos y limitaciones (1 min)

```
python src/experimentos_corte2.py
python src/tablas_corte2.py
```

(Tarda cerca de un minuto: 2000 repeticiones por celda.) Cerrar con las
limitaciones del informe: Chocontá a Tunja con distancia por progresivas
(61.00 km; la longitud registrada de 17.69 km queda como sensibilidad), entrada
urbana a Bogotá no cubierta por la fuente, riesgo (GiZScore) disponible en 11
de 32 aristas y mortalidad de la ANSV en 16 solo como sensibilidad, otros
costos por km como supuesto del equipo (el costo en pesos es un piso),
mediciones de tiempo con dispersión alta.
