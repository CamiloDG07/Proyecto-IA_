# Verificación de los datos de la red de carga

Fecha de la descarga oficial: 6 de octubre de 2026 (hora local de Bogotá,
entre las 22:54 y las 22:59). Método: API Socrata de datos.gov.co,
`https://www.datos.gov.co/resource/<identificador>.csv?$limit=50000`.
Conteo de referencia: `$select=count(*)` sobre el mismo recurso.

## Fuentes y descargas oficiales (versión de referencia)

| Dataset | Entidad | URL | Filas | Conteo API | SHA-256 |
|---|---|---|---|---|---|
| `red_vial.csv` | INVÍAS | https://www.datos.gov.co/resource/ie7y-asdn.csv | 715 | 715 | `42667E510D8C504A690ADC53B7718ED1EF1C568070B7F48CDD5002FBD76CB549` |
| `peajes.csv` | INVÍAS | https://www.datos.gov.co/resource/68qj-5xux.csv | 179 | 179 | `A751F27743A7006E4B38698EA5F3455AB7573D8DF5CB51EABA6368657B32B974` |
| `siniestralidad.csv` | ANSV | https://www.datos.gov.co/resource/rs3u-8r4q.csv | 316 | 316 | `5E6DAE1C92297876CF2E73CD92F3975882B2D45F5EB13285742D2524A3E17CAB` |

El `red_vial.csv` oficial pesa 238 311 633 bytes (incluye la geometría en la
columna `multiline`) y supera el límite de 100 MB de GitHub, por lo que no se
versiona (está en `.gitignore`). Se reproduce con la URL anterior y se
comprueba con el hash de la tabla.

## Descarga previa (conservada en `_descarga_previa\`)

| Archivo | Filas | Bytes | SHA-256 |
|---|---|---|---|
| `red_vial.csv` | 714 | 90 996 | `11DB06D1B8A6A34CF5A7DD6E58445E02A5D4B4F7CF7FB7DF59E9D163B56AC87D` |
| `peajes.csv` | 179 | 85 104 | `F2A4F3851B891EA4EC8706EAFDD7E3565DE835EF262B974E8639B858C9C4C7AC` |
| `siniestralidad.csv` | 316 | 45 882 | `5E6DAE1C92297876CF2E73CD92F3975882B2D45F5EB13285742D2524A3E17CAB` |

Se incluyen también `aristas_red_tarifas_previas.json` y `nodos_red_previo.json`,
generados con esa descarga y con las tarifas de peaje escritas a mano.

## Diferencias encontradas entre la descarga previa y la oficial

| Dataset | Diferencia |
|---|---|
| `siniestralidad` | Ninguna (mismo hash). |
| `red_vial` | 715 filas contra 714. |
| `red_vial` | La descarga oficial trae 9 columnas adicionales: `categoria`, `calzada`, `superficie`, `administrador`, `grupo_administrador_vial`, `fuente`, `multiline`, `poste_de_referencia_inicial`, `poste_de_referencia_final`. |
| `red_vial` | Corredor 2503 (Mojarras - Popayán): la descarga previa tiene un registro (distancias 0 y 0, 121 085 m); la oficial lo divide en dos (distancias 0-788 con 85 220 m y 788-0 con 35 864 m). Está fuera del alcance regional del grafo. |
| `red_vial` | 100 filas duplicadas exactas en ambas versiones. Tocan 9 sectores del grafo (Bogotá (Los Patios) - Guasca, Girardot - Cambao, Honda - Villeta, La Palmera - Presidente, Paso por el Puente sobre el Río Ocoa - Villavicencio, Puerto López - Puerto Gaitán, Sáchica - Tunja, Ye de Granada - Casco Urbano Granada, Ye de Granada - Paso por el Puente sobre el Río Ocoa). No alteran el resultado porque el script toma la longitud máxima por sector. |
| `peajes` | 47 de 179 filas difieren (mismo orden y mismas columnas). Cambian los nombres (mayúsculas, p. ej. `Los Garzones II` contra `LOS GARZONES 2`) y, sobre todo, las tarifas de las categorías, además de `responsable` y `administrador` en algunas filas. No es una diferencia solo de mayúsculas. |

### Efecto sobre la categoría III de los peajes del grafo

De los 24 peajes del grafo, 14 conservan la misma tarifa y 10 cambian:

| Peaje | Previa (COP) | Oficial 6/10/2026 (COP) |
|---|---|---|
| Arcabuco | 27 900 | 29 300 |
| Sáchica | 27 900 | 29 300 |
| Casablanca | 33 500 | 35 200 |
| Saboyá | 33 500 | 35 200 |
| Oiba | 33 500 | 35 200 |
| Los Curos | 33 500 | 35 200 |
| Río Bogotá | 15 400 | 16 200 |
| Los Patios | 29 600 | 35 700 |
| Bicentenario | 39 600 | 41 600 |
| El Picacho | 28 400 | 29 800 |

Decisión: la versión de los datos del proyecto es la descarga oficial del
6 de octubre de 2026. Las tarifas de peaje se actualizan cada año, por lo que
constituyen una limitación de vigencia.

## Prueba de reproducibilidad

El script `construir_red.py` original (tarifas escritas a mano) se ejecutó sin
cambios contra ambas versiones. Resultado idéntico en las dos: 33 nodos, 33
aristas, 1 ciclo independiente, 24 aristas con peaje, 12 con riesgo, mismos
`aristas_red.json` y `nodos_red.json` byte a byte, Duitama a Puente Nacional
en 414.8 y 668.1 km y San Gil a Bucaramanga en 109.14 km. La igualdad se
explica porque ese script no leía `peajes.csv`; la lectura de la tarifa desde
el CSV se incorpora en el cambio siguiente. Para correr el script contra el
`red_vial.csv` oficial hizo falta ampliar el límite de campo de `csv`, por la
columna `multiline`.

## Coordenadas de los nodos

Fuente primaria: DANE, DIVIPOLA, con corte al 30 de diciembre de 2024,
descargada de datos.gov.co el 7 de octubre de 2026 (formato decimal con coma).

| Archivo | Identificador | Filas | Conteo API | SHA-256 |
|---|---|---|---|---|
| `divipola_municipios_gdxc-w37w.csv` | `gdxc-w37w` | 1122 | 1122 | `56f42b7cb97049ce52ee86e86b1393df0025aa1b1aec32b2b09f4b6acd5e1221` |
| `divipola_centros_poblados_xaxy-8nri.csv` | `xaxy-8nri` | 8161 | 8161 | `d767c6845cfc0f79c17c1f3b1eecc9bec10729e33766ad6e28875aef027c93ec` |

`coordenadas_nodos.csv` se genera con `src/obtener_coordenadas.py`. Cada
punto DANE se contrasta con los extremos de la geometría INVÍAS
(`multiline` de `red_vial.csv`) de los tramos adyacentes; la separación por
nodo está en `outputs/verificacion_coordenadas.csv`. Los nodos sin
coordenada DANE verificable se estiman como la unión de los dos tramos
INVÍAS que llegan a ellos.

## Auditoría geométrica de las aristas (7 de octubre de 2026)

Generada por `src/auditar_aristas.py` (salida completa en
`outputs/auditoria_aristas.csv`). Compara, por arista, la distancia por
carretera que usa el grafo con la geodésica entre las coordenadas de sus
nodos y con la geometría (`multiline`) del sector de INVÍAS. Umbrales fijos:
razón menor que 1; extremo de la geometría a más de 5 km del nodo; nodo a
más de 5 km de la geometría; registro mayor que 1.5 veces el camino más
corto entre los extremos de su propia geometría. El camino de la geometría
es una medida aproximada (extremos por doble barrido): sirve para detectar
registros mucho mayores que su trazado, no como distancia.

| Arista | Carretera (km) | Geodésica (km) | Razón | Extremo a nodo, máx. (km) | Registro / camino | Anomalía |
|---|---|---|---|---|---|---|
| Bogotá - Tocancipá | 38.37 | 41.19 | 0.932 | 18.90 | 1.710 | carretera menor que geodésica; extremo lejos del nodo; nodo lejos de la geometría; registro mayor que el camino de la geometría |
| Tocancipá - Chocontá | 66.49 | 32.31 | 2.058 | 1.26 | 2.046 | registro mayor que el camino de la geometría |
| Chocontá - Tunja | 17.69 | 56.96 | 0.311 | 43.70 | 1.492 | carretera menor que geodésica; extremo lejos del nodo; nodo lejos de la geometría |
| Tunja - Duitama | 94.18 | 47.78 | 1.971 | 4.17 | 1.963 | registro mayor que el camino de la geometría |
| Barbosa - Tunja | 62.83 | 52.31 | 1.201 | 4.24 | 0.999 | - |
| Chiquinquirá - Sáchica | 37.46 | 30.74 | 1.218 | 4.55 | 0.998 | - |
| Sáchica - Tunja | 35.15 | 21.28 | 1.652 | 4.55 | 0.499 | - |
| Bogotá - Cajicá | 37.18 | 31.51 | 1.180 | 19.02 | 3.311 | extremo lejos del nodo; nodo lejos de la geometría; registro mayor que el camino de la geometría |
| Cajicá - Zipaquirá | 18.69 | 12.15 | 1.539 | 2.14 | 2.052 | registro mayor que el camino de la geometría |
| Zipaquirá - Ubaté | 47.76 | 37.16 | 1.285 | 1.26 | 1.189 | - |
| Ubaté - Puente Nacional | 94.48 | 65.26 | 1.448 | 0.84 | 1.050 | - |
| Bogotá - Mosquera | 10.35 | 14.16 | 0.731 | 175.63 | 1.823 | carretera menor que geodésica; extremo lejos del nodo; nodo lejos de la geometría; registro mayor que el camino de la geometría |
| Madrid - Bogotá | 19.46 | 19.91 | 0.978 | 8.96 | 2.297 | carretera menor que geodésica; extremo lejos del nodo; nodo lejos de la geometría; registro mayor que el camino de la geometría |
| Bogotá - Guasca | 34.88 | 35.12 | 0.993 | 11.17 | 0.509 | carretera menor que geodésica; extremo lejos del nodo; nodo lejos de la geometría |
| Bogotá - Villavicencio | 93.72 | 79.15 | 1.184 | 19.06 | 1.097 | extremo lejos del nodo; nodo lejos de la geometría |
| Villavicencio - Ye de Granada | 72.63 | 62.48 | 1.163 | 2.08 | - | geometría sin camino entre extremos |
| Ye de Granada - Granada | 2.43 | 3.04 | 0.798 | 0.86 | 0.498 | carretera menor que geodésica |
| Villavicencio - Puerto López | 77.62 | 73.88 | 1.051 | 3.09 | 0.999 | - |
| Puerto López - Puerto Gaitán | 108.55 | 99.54 | 1.091 | 1.40 | 0.494 | - |
| Bogotá - Villeta | 167.67 | 57.00 | 2.942 | 8.50 | 2.324 | extremo lejos del nodo; nodo lejos de la geometría; registro mayor que el camino de la geometría |
| Villeta - Honda | 58.45 | 38.76 | 1.508 | 7.56 | 0.512 | extremo lejos del nodo; nodo lejos de la geometría |
| Honda - Mariquita | 18.95 | 14.71 | 1.288 | 1.93 | 1.001 | - |
| Bogotá - Fusagasugá | 111.76 | 45.75 | 2.443 | 10.39 | 1.893 | extremo lejos del nodo; nodo lejos de la geometría; registro mayor que el camino de la geometría |
| Fusagasugá - Girardot | 111.39 | 46.95 | 2.373 | 5.00 | 1.795 | registro mayor que el camino de la geometría |
| Girardot - El Espinal | 19.36 | 20.42 | 0.948 | 3.07 | 1.229 | carretera menor que geodésica |
| Girardot - Cambao | 88.71 | 66.51 | 1.334 | 9.98 | - | extremo lejos del nodo; geometría sin camino entre extremos |
| Puente Nacional - San Gil | 124.72 | 95.97 | 1.300 | 0.84 | 0.997 | - |
| San Gil - Bucaramanga | 109.14 | 62.77 | 1.739 | 4.13 | 1.180 | - |
| Bucaramanga - Cuestaboba | 70.06 | 33.29 | 2.105 | 3.93 | 1.085 | - |
| Cuestaboba - Pamplona | 54.31 | 28.32 | 1.918 | 1.68 | 1.068 | - |
| Pamplona - Presidente | 68.00 | 39.38 | 1.727 | 1.32 | 1.046 | - |
| Presidente - La Palmera | 100.90 | 56.37 | 1.790 | 0.13 | 0.503 | - |
| La Palmera - Duitama | 141.01 | 85.38 | 1.651 | 2.19 | 1.039 | - |

### Hallazgos

1. **Bogotá a Mosquera usa un sector de otra región.** El sector `Puente
   Mosquera - Cruce Avenida del Ferrocarril` (ruta 29, Troncal del Eje
   Cafetero) está en torno a lon -75.68 y lat 4.81, a unos 160 km de Mosquera
   (Cundinamarca). Ese sector no se usa en ninguna otra arista, pero Mosquera
   queda sobre la geometría del sector `Madrid - Bogotá (Rio Bogotá)` (a 0.67
   km), que ya se usa en la arista Madrid a Bogotá. Está pendiente de
   decisión; no se modificó.
2. **Chocontá a Tunja está truncada.** La geometría del sector cubre 17.69 km
   (el tramo final hacia Tunja); Chocontá queda a 43.70 km de ella. Se buscó,
   en los 715 registros, un sector que complete el trazado (extremos
   coincidentes y vértices dentro del corredor entre ambos nodos): ninguno
   toca los dos extremos del hueco y el único con vértices cerca de Chocontá
   es `Chocontá - Brisas`, de la ruta 56. La arista se deja con 17.69 km y
   queda como limitación: la distancia está subestimada, con razón medida
   carretera/geodésica de 0.3106.
3. **Entrada urbana a Bogotá.** Las geometrías de los sectores que salen de
   Bogotá empiezan en el límite urbano, no en la coordenada DANE del
   municipio: a 18.90 km (Tocancipá), 19.02 (Cajicá), 19.06 (Villavicencio),
   11.17 (Guasca), 10.39 (Fusagasugá) y 8.50 km (Villeta). Es una limitación
   de la fuente y no se corrige.
4. **Registros mayores que su trazado.** En 10 aristas el registro supera en
   más de 1.5 veces el camino de su geometría (Bogotá a Tocancipá, Tocancipá a
   Chocontá, Tunja a Duitama, Bogotá a Cajicá, Cajicá a Zipaquirá, Bogotá a
   Mosquera, Madrid a Bogotá, Bogotá a Villeta, Bogotá a Fusagasugá y
   Fusagasugá a Girardot). La geometría de esos sectores contiene partes
   paralelas, compatible con ambas calzadas digitalizadas, pero la columna
   `calzada` no lo explica por sí sola. No se corrigió ningún valor.
5. **Siete aristas con razón carretera/geodésica menor que 1** (Chocontá a
   Tunja 0.3106, Bogotá a Mosquera 0.7307, Granada a Yé de Granada 0.7984,
   Bogotá a Tocancipá 0.9316, El Espinal a Girardot 0.9479, Bogotá a Madrid
   0.9776 y Bogotá a Guasca 0.9931).
6. **Independencia de las coordenadas.** Para Cuestaboba, La Palmera y Yé de
   Granada no hay punto DANE; su coordenada se estima con la misma geometría
   de INVÍAS de la que sale la distancia por carretera de sus aristas, por lo
   que en esos tres nodos coordenada y geometría no son independientes.
   Presidente tiene punto DANE (centro poblado), solo contrastado con la
   geometría.
