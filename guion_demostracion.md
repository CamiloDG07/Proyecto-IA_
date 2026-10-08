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
(309.10 km) y la ruta por Santander con `peaje`, `riesgo` y `compuesto`
(654.25 km). Abrir `outputs\diagrama_red.png` para señalar el ciclo.

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

Mostrar: alfa = 0.310570, determinado por Chocontá a Tunja (sector truncado
en la fuente); 0 violaciones de admisibilidad y de consistencia, con margen
mínimo de 0.000023 km; con la geodésica pura (alfa = 1) hay violaciones.
Mencionar las aristas con razón carretera/geodésica menor que 1
(`outputs\analisis_heuristica.json`).

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
| Duitama a Puente Nacional (ciclo) | BFS y DFS devuelven el desvío por Santander (654.25 km); UCS, voraz y A* la ruta óptima (309.10 km). BFS minimiza saltos, no costo |
| Duitama a Puente Nacional, compuesto sin riesgo | Con la corrección de distancias gana la ruta por Bogotá; con las distancias sin corregir ganaba el desvío |
| Bucaramanga a Bogotá (ciclo) | DFS devuelve una ruta más cara que el óptimo |
| Bogotá a Granada (ruta única) | Los cinco devuelven la misma ruta; solo cambian los nodos expandidos |
| Mariquita a Granada (ruta única, 6 saltos) | Igual; la búsqueda voraz expande muy pocos nodos |

Decir sin adornos: con un solo ciclo, solo los pares que lo cruzan muestran
diferencias de ruta entre algoritmos.

## 5. Rutas y barrido de pesos (1 min)

Abrir `outputs\rutas_central_distancia.png` y `outputs\barrido_pesos.png`:
la ruta de cada algoritmo sobre las coordenadas oficiales y la frontera
exacta entre las dos rutas (19 de 66 puntos de la malla favorecen la ruta por
Bogotá en la red corregida).

## 6. Agente autónomo de rutas (4 min)

El usuario solo da origen y destino(s); el agente decide el tipo de problema,
el criterio, el algoritmo y la heurística, y devuelve la mejor ruta con su
explicación. Regla: con un destino calcula la ruta óptima por distancia, por
peaje y por compuesto sin riesgo (A* con heurística admisible o UCS), añade las
rutas alternativas que quedan al bloquear una arista de cada una, descarta las
dominadas en km y peaje y recomienda la de menor compuesto sin riesgo con pesos
iguales. Con varios destinos, o con regreso, ordena las paradas con el
despachador (Held-Karp si k es menor o igual que K_exacto; ACO si no).

```
python src/agente_rutas.py Duitama "Puente Nacional"
python src/agente_rutas.py Bogotá Granada
python src/agente_rutas.py Duitama Tunja Bogotá Villeta --regreso
python src/agente_rutas.py Duitama "Puente Nacional" --criterio peaje
```

Con `--criterio {distancia,peaje,riesgo,compuesto,compuesto_sin_riesgo}` el usuario elige el criterio con que se escoge la ruta recomendada; sin la opción se usa el compuesto sin riesgo.

| Caso | Qué mostrar |
|---|---|
| Duitama a Puente Nacional (cruza el ciclo) | Recomienda la ruta por Bogotá: 309.10 km, 170 800 COP, compuesto sin riesgo 3.149. La alternativa por Santander (654.25 km, 100 200 COP) queda a 0.375 (11.9 %). Los criterios peaje, riesgo y compuesto prefieren el desvío; el aviso dice que el riesgo solo tiene dato en el 50 % de los tramos de la recomendada y en el 0 % de los del desvío. Advierte Chocontá a Tunja truncada |
| Bogotá a Granada (ruta única) | Una sola candidata: 168.78 km, 46 700 COP; todos los criterios coinciden; solo advierte aristas marcadas por la auditoría |
| Duitama, Tunja, Bogotá y Villeta con regreso | Orden libre: Held-Karp (k = 3); orden Duitama, Villeta, Bogotá, Tunja, Duitama; 403.16 km y 208 800 COP |

Decir sin adornos: la recomendación es la de menor compuesto sin riesgo; los
criterios con riesgo se avisan, no se imponen, porque faltan datos.

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
| Paso obligatorio | Chiquinquirá a Chocontá | paso obligatorio (2 caminos; obligatorios: Sáchica, Tunja) | 570.3 % |
| Atajo | Cajicá a Zipaquirá | atajo (2 caminos; obligatorios: ninguno) | 20 480.8 % |
| Atajo | Duitama a Presidente | atajo (2 caminos; obligatorios: ninguno) | 578.0 % |
| Ida y vuelta con regreso distinto | Duitama a Puente Nacional, con Tunja-Chocontá bloqueado solo en el regreso | ida por Bogotá, regreso por Santander | 11.9 % (regreso contra ida invertida) |

Con un destino y `--regreso`, el agente resuelve ida y vuelta: sin bloqueos el
regreso es la ida invertida; con `--bloquear-regreso "A-B;C-D"` el regreso se
recalcula con esos tramos bloqueados solo en el regreso (solo con un destino).

Comandos y salidas reales:

```
python src/agente_rutas.py Bogotá Fusagasugá

Origen: Bogotá  Destinos: Fusagasugá  Regreso: no
Tipo de problema decidido: origen_destino
Ruta recomendada: Bogotá > Fusagasugá
  Distancia: 59.02 km   Peaje: 31 500 COP
  Riesgo (suma de GiZScore con dato): 2.44; dato en el 100 % de los tramos
  Costo compuesto sin riesgo: 0.588
Regla: menor costo compuesto sin riesgo = suma por tramo de (w_d*km/máx_km +
      w_p*peaje/máx_peaje)/(w_d+w_p), con w_d = 1 y w_p = 1
Método y heurística:
  distancia: A* por tramo; exacto: A* con heurística admisible, disponible para el criterio
      distancia; 3 nodos expandidos
  peaje: UCS por tramo; exacto: UCS, porque el criterio peaje no tiene heurística admisible
      informativa o no hay coordenadas; 8 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio compuesto_sin_riesgo; 6 nodos expandidos
  alfa de la heurística: 0.310570; total de nodos expandidos: 17
Criterio que prefiere cada candidata:
  distancia, peaje, riesgo, compuesto_sin_riesgo, compuesto: Bogotá > Fusagasugá
Advertencias:
  - Aristas marcadas por la auditoría geométrica: Bogotá - Fusagasugá.
```

```
python src/agente_rutas.py Chiquinquirá Chocontá

Origen: Chiquinquirá  Destinos: Chocontá  Regreso: no
Tipo de problema decidido: origen_destino
Ruta recomendada: Chiquinquirá > Sáchica > Tunja > Chocontá
  Distancia: 90.30 km   Peaje: 58 600 COP
  Riesgo (suma de GiZScore con dato): 2.57; dato en el 33 % de los tramos
  Costo compuesto sin riesgo: 1.025
Regla: menor costo compuesto sin riesgo = suma por tramo de (w_d*km/máx_km +
      w_p*peaje/máx_peaje)/(w_d+w_p), con w_d = 1 y w_p = 1
Método y heurística:
  distancia: A* por tramo; exacto: A* con heurística admisible, disponible para el criterio
      distancia; 3 nodos expandidos
  peaje: UCS por tramo; exacto: UCS, porque el criterio peaje no tiene heurística admisible
      informativa o no hay coordenadas; 4 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio compuesto_sin_riesgo; 3 nodos expandidos
  alfa de la heurística: 0.310570; total de nodos expandidos: 10
Descartadas por dominadas en km y peaje:
  Chiquinquirá > Sáchica > Tunja > Duitama > La Palmera > Presidente > Pamplona > Cuestaboba >
      Bucaramanga > San Gil > Puente Nacional > Ubaté > Zipaquirá > Cajicá > Bogotá > Tocancipá
      > Chocontá: 1018.27 km  271 000 COP
Criterio que prefiere cada candidata:
  distancia, peaje, riesgo, compuesto_sin_riesgo, compuesto: Chiquinquirá > Sáchica > Tunja >
      Chocontá
Advertencias:
  - La ruta usa Chocontá a Tunja, sector truncado en la fuente (17.69 km frente a 56.96 km en
      línea recta): su distancia está subestimada.
  - 2 de 3 tramos no tienen dato de riesgo y valen 0 en los criterios que lo incluyen.
```

```
python src/agente_rutas.py Cajicá Zipaquirá

Origen: Cajicá  Destinos: Zipaquirá  Regreso: no
Tipo de problema decidido: origen_destino
Ruta recomendada: Cajicá > Zipaquirá
  Distancia: 9.10 km   Peaje: 0 COP
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
  alfa de la heurística: 0.310570; total de nodos expandidos: 3
Descartadas por dominadas en km y peaje:
  Cajicá > Bogotá > Tocancipá > Chocontá > Tunja > Duitama > La Palmera > Presidente > Pamplona
      > Cuestaboba > Bucaramanga > San Gil > Puente Nacional > Ubaté > Zipaquirá: 954.25 km  271
      000 COP
Criterio que prefiere cada candidata:
  distancia, peaje, riesgo, compuesto_sin_riesgo, compuesto: Cajicá > Zipaquirá
Advertencias:
  - Aristas marcadas por la auditoría geométrica: Cajicá - Zipaquirá.
  - 1 de 1 tramos no tienen dato de riesgo y valen 0 en los criterios que lo incluyen.
```

```
python src/agente_rutas.py Duitama Presidente

Origen: Duitama  Destinos: Presidente  Regreso: no
Tipo de problema decidido: origen_destino
Ruta recomendada: Duitama > La Palmera > Presidente
  Distancia: 241.91 km   Peaje: 0 COP
  Riesgo (suma de GiZScore con dato): 0.00; dato en el 0 % de los tramos
  Costo compuesto sin riesgo: 0.858
Regla: menor costo compuesto sin riesgo = suma por tramo de (w_d*km/máx_km +
      w_p*peaje/máx_peaje)/(w_d+w_p), con w_d = 1 y w_p = 1
Método y heurística:
  distancia: A* por tramo; exacto: A* con heurística admisible, disponible para el criterio
      distancia; 11 nodos expandidos
  peaje: UCS por tramo; exacto: UCS, porque el criterio peaje no tiene heurística admisible
      informativa o no hay coordenadas; 2 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; exacto: A* con heurística admisible, disponible para el
      criterio compuesto_sin_riesgo; 3 nodos expandidos
  alfa de la heurística: 0.310570; total de nodos expandidos: 16
Descartadas por dominadas en km y peaje:
  Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté > Puente Nacional
      > San Gil > Bucaramanga > Cuestaboba > Pamplona > Presidente: 721.44 km  271 000 COP
Criterio que prefiere cada candidata:
  distancia, peaje, riesgo, compuesto_sin_riesgo, compuesto: Duitama > La Palmera > Presidente
Advertencias:
  - 2 de 2 tramos no tienen dato de riesgo y valen 0 en los criterios que lo incluyen.
```

```
python src/agente_rutas.py Duitama "Puente Nacional" --regreso --bloquear-regreso "Tunja-Chocontá"

Origen: Duitama  Destino: Puente Nacional  Regreso: sí
Tipo de problema decidido: ida_y_vuelta
Ida: Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté > Puente
      Nacional
  Distancia: 309.10 km   Peaje: 170 800 COP
  Riesgo (suma de GiZScore con dato): 9.85; dato en el 50 % de los tramos
Vuelta: Puente Nacional > San Gil > Bucaramanga > Cuestaboba > Pamplona > Presidente > La
      Palmera > Duitama
  Distancia: 654.25 km   Peaje: 100 200 COP
  Regreso recalculado con los tramos bloqueados solo en el regreso: Tunja-Chocontá; costo
      compuesto sin riesgo +11.9 % respecto de la ida invertida
Total ida y vuelta: 963.35 km   Peaje: 271 000 COP
Método y heurística de la ida:
  distancia: A* por tramo; 20 nodos expandidos
  peaje: UCS por tramo; 14 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; 28 nodos expandidos
Método y heurística del regreso:
  distancia: A* por tramo; 27 nodos expandidos
  peaje: UCS por tramo; 13 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; 25 nodos expandidos
  alfa de la heurística: 0.310570; total de nodos expandidos: 127
Advertencias:
  - La ruta usa Chocontá a Tunja, sector truncado en la fuente (17.69 km frente a 56.96 km en
      línea recta): su distancia está subestimada.
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
Ida: Duitama > Tunja > Chocontá > Tocancipá > Bogotá > Cajicá > Zipaquirá > Ubaté > Puente
      Nacional
  Distancia: 309.10 km   Peaje: 170 800 COP
  Riesgo (suma de GiZScore con dato): 9.85; dato en el 50 % de los tramos
Vuelta: Puente Nacional > Ubaté > Zipaquirá > Cajicá > Bogotá > Tocancipá > Chocontá > Tunja >
      Duitama
  Distancia: 309.10 km   Peaje: 170 800 COP
  Sin bloqueos, el regreso es la ida invertida
Total ida y vuelta: 618.20 km   Peaje: 341 600 COP
Método y heurística de la ida:
  distancia: A* por tramo; 20 nodos expandidos
  peaje: UCS por tramo; 14 nodos expandidos
  compuesto_sin_riesgo: A* por tramo; 28 nodos expandidos
  alfa de la heurística: 0.310570; total de nodos expandidos: 62
Advertencias:
  - La ruta usa Chocontá a Tunja, sector truncado en la fuente (17.69 km frente a 56.96 km en
      línea recta): su distancia está subestimada.
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
| Tipo a | A* por tramo; el motivo dice que hay heurística admisible para `distancia`; 309.10 km |
| Tipo d con cinco paradas | Held-Karp, porque k = 5 es menor o igual que el umbral medido (K = 19); el motivo y las métricas salen en la respuesta |
| Tipo c con obligatoria y tramo bloqueado | El orden queda determinado (una obligatoria) y el tramo bloqueado se excluye de todas las búsquedas |

Umbral: `outputs\umbral_held_karp.json` combina las sesiones guardadas
(`outputs\umbral_sesion_N.json`) y toma el mayor k dentro del presupuesto en
todas ellas. Aclarar que los tiempos dependen del estado de la máquina; la
tabla del informe muestra la mediana de cada sesión.

ACO: tipos d y e con más de 20 paradas libres, o con matriz asimétrica (sin
2-opt). Validación en `outputs\validacion_agente.json`: en la red de carga
alcanza la referencia en las 130 semillas; en las instancias del taller con
n = 20, brecha media de 0.040 % con 2-opt (48 de 50 semillas) y de 0.357 %
sin 2-opt (32 de 50); con la ciudad de salida fija, sin 2-opt, 2.212 % (1 de
50).

Pregunta preparada: ¿por qué ACO si el 2-opt ya llega al óptimo? Respuesta
con los datos: en la red de carga la brecha de la iteración 1 ya es a lo
sumo 0.029 % y el ACO sin 2-opt también llega a la referencia: el aporte
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
limitaciones del informe: Chocontá a Tunja truncada (cota inferior de la ruta
por Bogotá: 348.37 km), entrada urbana a Bogotá no cubierta por la fuente,
riesgo disponible en 11 de 32 aristas, mediciones de tiempo con dispersión
alta.
