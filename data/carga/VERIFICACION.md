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

El script `construir_red.py` original (tarifas escritas a mano, red de 33
nodos, antes de excluir Mosquera) se ejecutó sin cambios contra ambas versiones. Resultado idéntico en las dos: 33 nodos, 33
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

## Exclusión de Mosquera (7 de octubre de 2026)

La arista Bogotá a Mosquera usaba el sector `Puente Mosquera - Cruce Avenida
del Ferrocarril` (ruta 29, Troncal del Eje Cafetero), ubicado en torno a
lon -75.68 y lat 4.81, a unos 160 km de Mosquera (Cundinamarca) (razón
carretera/geodésica 0.7307; extremo de la geometría a 159.93 km del nodo). La
Red Vial no tiene un sector oficial de reemplazo: el sector `Madrid - Bogotá
(Rio Bogotá)`, cuya geometría pasa a 0.67 km de Mosquera, ya se usa en la
arista Madrid a Bogotá. Mosquera era una hoja (grado 1, solo conectaba con
Bogotá), por lo que se excluyó el nodo con su arista, con el mismo criterio
que la rama Villavicencio, Barranca de Upía y Yopal (sector de otra región, sin
sector oficial de reemplazo). La red queda en 32 nodos, 32 aristas y un ciclo
independiente (24 aristas con peaje y 11 con dato de riesgo). Como el máximo
de riesgo era el de esa arista, $r_{\max}$ pasa de 4.771 a 3.423.

## Regla de doble calzada digitalizada y verificación (7 de octubre de 2026)

`src/auditar_distancias.py` calcula, por registro (sin unir) de los sectores
usados, tres medidas oficiales (salida completa en
`outputs/auditoria_distancias.csv`):

- **A**: longitud registrada, `shape__length`, con la columna `calzada`.
- **B**: tramo entre progresivas. Columnas usadas: `poste_de_referencia_inicial`
  y `poste_de_referencia_final` (PR, en km) y `distancia_inicial` y
  `distancia_final` (desplazamiento sobre el PR, interpretado en metros).
  B_tot = |(PR_final + distancia_final / 1000) - (PR_inicial +
  distancia_inicial / 1000)|.
- **C**: longitud a lo largo de la geometría del registro (`multiline`): la
  suma de todas sus partes y el camino más corto entre sus extremos.

Observación: A coincide con la suma de las partes de la geometría en los 44
registros (A / C_suma entre 0.994 y 0.999); en los registros de calzada
sencilla A es cercano a B_tot.

**Regla (fijada de antemano):** por registro, distancia = B_tot si
1.7 <= A / B_tot <= 2.3 (doble calzada digitalizada); en cualquier otro caso,
A. Los registros de un mismo sector se combinan como antes (mayor por sector;
suma de los dos registros en San Gil a Bucaramanga). Implementada en
`construir_red.py` (`largo_corregido`).

**Verificación con una segunda medida oficial:** en cada registro corregido,
abs(B_tot - C_camino) / C_camino no debe superar 0.15. Resultado: 9 registros
corregidos, 0 fallas (máximo 0.123, Bogotá a Villeta).

| Arista | Sector | Calzada | A (km) | B_tot (km) | C_camino (km) | A/B_tot | abs(B_tot - C_camino) / C_camino |
|---|---|---|---|---|---|---|---|
| Bogotá - Fusagasugá | Fusagasugá - Silvania - Bogotá (Bosa) | 2 | 111.761 | 59.020 | 59.042 | 1.894 | 0.000 |
| Bogotá - Tocancipá | Bogotá - Tocancipá | 2 | 38.368 | 22.118 | 22.436 | 1.735 | 0.014 |
| Bogotá - Villeta | Villeta - Bogotá | 2 | 167.668 | 81.000 | 72.140 | 2.070 | 0.123 |
| Cajicá - Zipaquirá | Cajicá - Zipaquirá | 2 | 18.691 | 9.100 | 9.108 | 2.054 | 0.001 |
| Fusagasugá - Girardot | Girardot - Fusagasugá | 2 | 111.392 | 62.769 | 62.047 | 1.775 | 0.012 |
| Madrid - Bogotá | Madrid - Bogotá (Rio Bogotá) | 2 | 19.464 | 9.122 | 8.471 | 2.134 | 0.077 |
| San Gil - Bucaramanga | San Gil - Bucaramanga | 2 | 26.189 | 12.299 | 12.407 | 2.129 | 0.009 |
| Tocancipá - Chocontá | Tocancipá - Chocontá | 2 | 66.485 | 33.036 | 32.498 | 2.013 | 0.017 |
| Tunja - Duitama | Tunja - Duitama | 2 | 94.182 | 47.730 | 47.976 | 1.973 | 0.005 |

Registros con A / B_tot entre 1.2 y 3.5 fuera de la banda (conservan A):

| Arista | Sector | Calzada | A (km) | B_tot (km) | C_camino (km) | A/B_tot | abs(B_tot - C_camino) / C_camino |
|---|---|---|---|---|---|---|---|
| Bogotá - Cajicá | Bogotá - Cajicá | 2 | 37.179 | 11.700 | 11.229 | 3.178 | 0.042 |
| Chocontá - Tunja | Chocontá - Tunja | 2 | 17.689 | 11.904 | 11.854 | 1.486 | 0.004 |
| Girardot - El Espinal | El Espinal - Girardot | 2 | 19.361 | 16.000 | 15.752 | 1.210 | 0.016 |

Registros con **patrón no estándar** (A / B_tot menor que 0.8 o mayor que 1.2
y fuera de la banda; conservan A): Bogotá - Cajicá (A/B_tot 3.178); Chocontá - Tunja (A/B_tot 1.486); Girardot - El Espinal (A/B_tot 1.210); Villavicencio - Ye de Granada (A/B_tot 9.773); Villavicencio - Ye de Granada (A/B_tot 9.773).

**Efecto sobre el grafo:** cambian 9 aristas (Bogotá a Tocancipá 38.37 a
22.12 km, Tocancipá a Chocontá 66.49 a 33.04, Tunja a Duitama 94.18 a 47.73,
Cajicá a Zipaquirá 18.69 a 9.10, Madrid a Bogotá 19.46 a 9.12, Bogotá a
Villeta 167.67 a 81.00, Bogotá a Fusagasugá 111.76 a 59.02, Fusagasugá a
Girardot 111.39 a 62.77 y San Gil a Bucaramanga 109.14 a 95.25). El resto de
los campos del JSON no cambia. El 167.67 km de Bogotá a Villeta no es un valor
atípico de la fuente sino un artefacto de la doble calzada digitalizada.

**Variante sin corregir (sensibilidad):** `aristas_red.json` guarda en cada
arista `distancia_cruda_km`, la longitud con `shape__length` (la versión
anterior a la regla); `build_graph.construir_grafo(distancia="cruda")` la
construye sin duplicar archivos.

## Auditoría geométrica de las 32 aristas (con la regla aplicada)

Generada por `src/auditar_aristas.py` (salida completa en
`outputs/auditoria_aristas.csv`). Compara, por arista, la distancia por
carretera que usa el grafo con la geodésica entre las coordenadas de sus
nodos y con la geometría (`multiline`) del sector de INVÍAS. Umbrales fijos:
razón menor que 1; extremo de la geometría a más de 5 km del nodo; nodo a
más de 5 km de la geometría; registro mayor que 1.5 veces el camino más
corto entre los extremos de su propia geometría. El camino de la geometría
es una medida aproximada (extremos por doble barrido).

| Arista | Carretera (km) | Geodésica (km) | Razón | Extremo a nodo, máx. (km) | Registro / camino | Anomalía |
|---|---|---|---|---|---|---|
| Bogotá - Tocancipá | 22.12 | 41.19 | 0.537 | 18.90 | 0.986 | carretera menor que geodésica; extremo lejos del nodo; nodo lejos de la geometría |
| Tocancipá - Chocontá | 33.04 | 32.31 | 1.023 | 1.26 | 1.017 | - |
| Chocontá - Tunja | 17.69 | 56.96 | 0.311 | 43.70 | 1.492 | carretera menor que geodésica; extremo lejos del nodo; nodo lejos de la geometría |
| Tunja - Duitama | 47.73 | 47.78 | 0.999 | 4.17 | 0.995 | carretera menor que geodésica |
| Barbosa - Tunja | 62.83 | 52.31 | 1.201 | 4.24 | 0.999 | - |
| Chiquinquirá - Sáchica | 37.46 | 30.74 | 1.218 | 4.55 | 0.998 | - |
| Sáchica - Tunja | 35.15 | 21.28 | 1.652 | 4.55 | 0.499 | - |
| Bogotá - Cajicá | 37.18 | 31.51 | 1.180 | 19.02 | 3.311 | extremo lejos del nodo; nodo lejos de la geometría; registro mayor que el camino de la geometría |
| Cajicá - Zipaquirá | 9.10 | 12.15 | 0.749 | 2.14 | 0.999 | carretera menor que geodésica |
| Zipaquirá - Ubaté | 47.76 | 37.16 | 1.285 | 1.26 | 1.189 | - |
| Ubaté - Puente Nacional | 94.48 | 65.26 | 1.448 | 0.84 | 1.050 | - |
| Madrid - Bogotá | 9.12 | 19.91 | 0.458 | 8.96 | 1.077 | carretera menor que geodésica; extremo lejos del nodo; nodo lejos de la geometría |
| Bogotá - Guasca | 34.88 | 35.12 | 0.993 | 11.17 | 0.509 | carretera menor que geodésica; extremo lejos del nodo; nodo lejos de la geometría |
| Bogotá - Villavicencio | 93.72 | 79.15 | 1.184 | 19.06 | 1.097 | extremo lejos del nodo; nodo lejos de la geometría |
| Villavicencio - Ye de Granada | 72.63 | 62.48 | 1.163 | 2.08 | - | geometría sin camino entre extremos |
| Ye de Granada - Granada | 2.43 | 3.04 | 0.798 | 0.86 | 0.498 | carretera menor que geodésica |
| Villavicencio - Puerto López | 77.62 | 73.88 | 1.051 | 3.09 | 0.999 | - |
| Puerto López - Puerto Gaitán | 108.55 | 99.54 | 1.091 | 1.40 | 0.494 | - |
| Bogotá - Villeta | 81.00 | 57.00 | 1.421 | 8.50 | 1.123 | extremo lejos del nodo; nodo lejos de la geometría |
| Villeta - Honda | 58.45 | 38.76 | 1.508 | 7.56 | 0.512 | extremo lejos del nodo; nodo lejos de la geometría |
| Honda - Mariquita | 18.95 | 14.71 | 1.288 | 1.93 | 1.001 | - |
| Bogotá - Fusagasugá | 59.02 | 45.75 | 1.290 | 10.39 | 1.000 | extremo lejos del nodo; nodo lejos de la geometría |
| Fusagasugá - Girardot | 62.77 | 46.95 | 1.337 | 5.00 | 1.012 | - |
| Girardot - El Espinal | 19.36 | 20.42 | 0.948 | 3.07 | 1.229 | carretera menor que geodésica |
| Girardot - Cambao | 88.71 | 66.51 | 1.334 | 9.98 | - | extremo lejos del nodo; geometría sin camino entre extremos |
| Puente Nacional - San Gil | 124.72 | 95.97 | 1.300 | 0.84 | 0.997 | - |
| San Gil - Bucaramanga | 95.25 | 62.77 | 1.517 | 4.13 | 1.030 | - |
| Bucaramanga - Cuestaboba | 70.06 | 33.29 | 2.105 | 3.93 | 1.085 | - |
| Cuestaboba - Pamplona | 54.31 | 28.32 | 1.918 | 1.68 | 1.068 | - |
| Pamplona - Presidente | 68.00 | 39.38 | 1.727 | 1.32 | 1.046 | - |
| Presidente - La Palmera | 100.90 | 56.37 | 1.790 | 0.13 | 0.503 | - |
| La Palmera - Duitama | 141.01 | 85.38 | 1.651 | 2.19 | 1.039 | - |

### Hallazgos

1. **Chocontá a Tunja está truncada.** La geometría del sector cubre 17.69 km
   (el tramo final hacia Tunja); Chocontá queda a 43.70 km de ella. Se buscó,
   en los 715 registros, un sector que complete el trazado: ninguno toca los
   dos extremos del hueco y el único con vértices cerca de Chocontá es
   `Chocontá - Brisas`, de la ruta 56. La arista se deja con 17.69 km y queda
   como limitación: la distancia está subestimada, con razón medida
   carretera/geodésica de 0.3106.
2. **Cota inferior de la ruta corta.** En la red corregida, la ruta corta de
   Duitama a Puente Nacional mide 309.10 km y su cota inferior es
   309.10 - 17.69 + 56.96 = 348.37 km (cota inferior: la geodésica no excede la
   distancia por carretera). No es un valor estimado ni se usa como distancia.
3. **Evidencia de progresivas en Chocontá a Tunja.** Los sectores Tocancipá a
   Chocontá y Chocontá a Tunja comparten la ruta 55 y el tramo 5501. Las
   progresivas no son continuas entre los registros: Tocancipá a Chocontá
   termina en PR 59.0 y Chocontá a Tunja va de PR 108.096 a PR 120.0, es decir,
   hay 49.096 km de progresivas sin registro (el intervalo que falta en la
   fuente). Por progresivas, Chocontá a Tunja mediría 120.0 - 59.0 = 61.0 km.
   Se cita solo como evidencia de que la cota inferior de 56.96 km es ajustada
   (56.96 / 61.0 = 0.934); no se aplica.
4. **Entrada urbana a Bogotá.** Las geometrías de los sectores que salen de
   Bogotá empiezan en el límite urbano, no en la coordenada DANE del
   municipio: a 18.90 km (Tocancipá), 19.02 (Cajicá), 19.06 (Villavicencio),
   11.17 (Guasca), 10.39 (Fusagasugá) y 8.50 km (Villeta). Es una limitación
   de la fuente y no se corrige; explica por qué las razones carretera/
   geodésica de Madrid a Bogotá (0.458) y Bogotá a Tocancipá (0.537) quedan
   bajas tras la corrección.
5. **Aristas con razón carretera/geodésica menor que 1** tras la corrección:
   Chocontá a Tunja 0.3106, Madrid a Bogotá 0.4582, Bogotá a Tocancipá 0.5371,
   Cajicá a Zipaquirá 0.7492, Granada a Yé de Granada 0.7984, El Espinal a
   Girardot 0.9479, Bogotá a Guasca 0.9931 y Tunja a Duitama 0.9989. Ninguna
   arista se revirtió por incumplir la heurística.
6. **Independencia de las coordenadas.** Para Cuestaboba, La Palmera y Yé de
   Granada no hay punto DANE; su coordenada se estima con la misma geometría
   de INVÍAS de la que sale la distancia por carretera de sus aristas, por lo
   que en esos tres nodos coordenada y geometría no son independientes.
   Presidente tiene punto DANE (centro poblado), solo contrastado con la
   geometría.

## Límites departamentales para los mapas (descarga del 7 de octubre de 2026)

| Campo | Valor |
|---|---|
| Archivo | `data/carga/mgn2020_departamentos_dane.json` |
| Nombre | Nivel de Información Departamento del Marco Geoestadístico Nacional (MGN), Versión 2020 (capa «Departamentos») |
| Entidad | Departamento Administrativo Nacional de Estadística (DANE); límites oficiales suministrados por el IGAC |
| Catálogo | https://www.datos.gov.co/d/jjim-6r88 |
| Servicio | https://portalgis.dane.gov.co/mparcgis/rest/services/MGN2020/Serv_CapaDepartamentos_2020/MapServer/0 |
| Fecha de descarga | 7 de octubre de 2026 |
| Consulta | `query?where=OBJECTID>0&outFields=*&returnGeometry=true&outSR=4326&maxAllowableOffset=0.003&f=json` |
| Contenido | 33 departamentos (incluido Bogotá, D.C.), anillos en grados (EPSG:4326), formato JSON de ArcGIS |
| SHA-256 | `3e7ee22f955d9b853d526005c4944287a5e03646f9e0bb8491d11f4ac95804c6` |

El parámetro `maxAllowableOffset=0.003` (unos 330 m) es una generalización que
aplica el propio servicio; los límites sirven solo de fondo de las figuras, no
para medir distancias ni áreas. Las capas MGN 2024 y 2025 del mismo portal
respondieron sin geometría en la misma consulta, por eso se usó la versión
2020. Las figuras no usan mosaicos (tiles).

## Descargas nuevas del 8 de octubre de 2026 (`nuevas\`)

Evaluadas en `FUENTES_NUEVAS.md`.

| Archivo | Fuente | URL | Filas o bytes | SHA-256 |
|---|---|---|---|---|
| `sectores_criticos_mortalidad_2022_ybqk-8s42.csv` | ANSV | https://www.datos.gov.co/resource/ybqk-8s42.csv | 647 filas | `4dd8f8a9432aa61557dfd8752c0514e5af3ed7b596f914800a1e6debfd828173` |
| `postes_referencia_ufg7-is7r.csv` | INVÍAS | https://www.datos.gov.co/resource/ufg7-is7r.csv | 17 816 filas | `cd4637ba05fa01999c8b8b9acaede1d7917e6ebf16446f5104abede3ba1ea472` |
| `creg_precios_combustibles_liquidos_15565.html` | CREG | https://creg.gov.co/publicaciones/15565/precios-de-combustibles-liquidos/ | 293 035 bytes | `42c6c9baeeb1d6a608a3b2bc5a5e0b310f187ef436b65e9b4912aa2895ed70b6` |
| `upme_linea_base_consumo_carga.pdf` | UPME | https://docs.upme.gov.co/DemandayEficiencia/Documents/1_Reporte_linea_base_EE_carga.pdf | 4 490 050 bytes | `a12f8622f00bc7d37b89a650995b08930c59871929ceb0435821ef8d28261593` |

Los dos CSV se descargaron con `?$limit=50000` y el conteo de filas coincide con el de la API. La página de la CREG
cambia con cada actualización de precios: el hash corresponde a la consulta del 8 de octubre de 2026.
