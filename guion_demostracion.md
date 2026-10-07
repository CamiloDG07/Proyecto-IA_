# Guion de la demostración, Corte 2

Duración sugerida: 10 minutos. Todos los comandos se ejecutan desde la raíz
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

## 6. Resultados completos y limitaciones (1 min)

```
python src/experimentos_corte2.py
python src/tablas_corte2.py
```

(Tarda cerca de un minuto: 2000 repeticiones por celda.) Cerrar con las
limitaciones del informe: Chocontá a Tunja truncada (cota inferior de la ruta
por Bogotá: 348.37 km), entrada urbana a Bogotá no cubierta por la fuente,
riesgo disponible en 11 de 32 aristas, mediciones de tiempo con dispersión
alta.
