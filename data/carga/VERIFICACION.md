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
