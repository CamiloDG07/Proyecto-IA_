# Fuentes nuevas evaluadas (8 de octubre de 2026)

Búsqueda: catálogo de datos.gov.co (API de Socrata, `api.us.socrata.com/api/catalog/v1`, más de 40 consultas con los
términos de siniestralidad, tránsito, combustible, fletes, costos de transporte, estado de vías, toponimia y
coordenadas), página de la CREG, portal SICE-TAC del Ministerio de Transporte, informe de la UPME y búsqueda web.
Cada consulta quedó en `outputs/bitacora_noche.md`. La red no cambia de nodos ni de aristas (32/32/1).

Criterios de aceptación: entidad oficial y licencia clara; descarga reproducible con hash; cruce determinista
contra la geometría (sin emparejar por nombre aproximado); validación retrospectiva sobre lo ya conocido; una sola
escala por atributo.

## Resumen

| Tema | Fuente | Decisión |
|---|---|---|
| Riesgo | ANSV, Sectores críticos mortalidad 2022 (`ybqk-8s42`) | **Solo sensibilidad** (no reproduce el orden del GiZScore) |
| Riesgo | ANSV, Sectores críticos por exceso de velocidad (`24ny-2dhf`) | Rechazada |
| Riesgo | Policía Nacional, Homicidios en accidente de tránsito (`ha6j-pa2r`) | Rechazada |
| Riesgo | Policía Nacional, Estado de Vías (`7i66-rps2`) | Rechazada |
| Riesgo | Registros municipales (Caldas, Palmira, Pereira, Fusagasugá y otros) | Rechazada |
| Tránsito | ANI, Tráfico Vehicular (`8yi9-t44c`) | Válida, no integrada |
| Tránsito | INVÍAS, tránsito promedio diario | Sin fuente aceptable |
| Distancia | INVÍAS, Red Vial (`ie7y-asdn`, progresivas) y Postes de Referencia (`ufg7-is7r`) | **Aceptada** para Chocontá a Tunja |
| Distancia | Entrada urbana a Bogotá | Sin fuente aceptable |
| Coordenadas | Cuestaboba, La Palmera, Yé de Granada | Sin fuente aceptable |
| Combustible | CREG, Precios de combustibles líquidos | **Aceptada** (precio del galón) |
| Combustible | UPME, Línea base de consumo de combustible de vehículos de carga | **Aceptada** (consumo del C2G) |
| Fletes y costos | MinTransporte, RNDC (`vn9u-yhwq`, `v7bz-7nq2`) | Rechazada |
| Fletes y costos | MinTransporte, SICE-TAC | Sin fuente aceptable (sin datos descargables) |

## Fichas

### ANSV, Sectores críticos mortalidad 2022 (`ybqk-8s42`)

- Entidad: Agencia Nacional de Seguridad Vial. Licencia: CC BY-SA 4.0. Actualizada: 15 de julio de 2022.
- URL: https://www.datos.gov.co/resource/ybqk-8s42.csv. Formato CSV, 647 filas, SHA-256
  `4dd8f8a9432aa61557dfd8752c0514e5af3ed7b596f914800a1e6debfd828173`.
- Campos clave: `actorvial`, `prioridad`, `cod`, `corredor`, `codvia`, `xi`, `yi`, `xf`, `yf`. Son segmentos de a lo
  sumo 10 km, en cuatro listas por actor vial (todos, moto, peatón, vehículo), con prioridad; no hay fallecidos ni
  una tasa.
- Cruce: geométrico (extremos del segmento a no más de 0.3 km del trazado de la arista, `src/cruce_mortalidad.py`),
  sin emparejar por nombre. Cada segmento (`cod`) cuenta una vez.
- Cobertura medida: 16 de las 32 aristas tienen al menos un segmento (el GiZScore actual cubre 11; la unión, 20).
- Validación retrospectiva (11 aristas con GiZScore, `outputs/validacion_riesgo_mortalidad.json`): 7 de las 11 tienen
  segmento; el orden no coincide (Spearman con el GiZScore −0.033 y con los fallecidos históricos 0.193).
- Decisión: **solo sensibilidad.** No reproduce el orden de lo conocido, no mide fallecidos y solo trae los sectores de
  mayor prioridad (que no figure no es que no haya muertes). Entra como atributo y como variante rotulada del
  compuesto, nunca como base.

### ANSV, Sectores críticos por exceso de velocidad (`24ny-2dhf`)

- Licencia CC BY-SA 4.0, 970 filas, actualizada el 21 de abril de 2021. Mide tramos de 1 km con reportes de vehículos de
  carga a más de 80 km/h (NAVISAF 2020). Es exposición a velocidad, no siniestralidad. **Rechazada.**

### Policía Nacional, Homicidios en accidente de tránsito (`ha6j-pa2r`)

- Licencia CC BY-SA 4.0, 98 430 filas (2010 a julio de 2026). Es por municipio (código DANE), incluye vía urbana y no
  tiene tramo ni vía. Asignarla a las aristas por los municipios de sus extremos mezclaría escalas y vías.
  **Rechazada.**

### Policía Nacional, Estado de Vías (`7i66-rps2`)

- 409 filas de eventos de afectación vial (cierres, derrumbes), sin identificador de tramo ni geometría. **Rechazada.**

### Registros municipales

- Palmira, Pereira, Fusagasugá, Calarcá, Caldas (mortalidad `2bk8-65js`), Bucaramanga y otros: cobertura de un
  municipio o departamento, sin escala común con el resto. **Rechazadas.**

### ANI, Tráfico Vehicular (`8yi9-t44c`)

- Licencia CC BY-SA 4.0, 149 944 filas, tráfico mensual por peaje y categoría desde 2014 hasta mayo de 2026. De los 24
  peajes de la red, 21 coinciden por nombre exacto normalizado. Es válida pero ningún atributo del modelo la necesita:
  **no integrada.**

### INVÍAS, tránsito promedio diario

- No existe un conjunto en datos.gov.co (consultas «tránsito promedio diario», «TPD», «aforos»). **Sin fuente
  aceptable.**

### INVÍAS, Red Vial (`ie7y-asdn`) y Postes de Referencia (`ufg7-is7r`): Chocontá a Tunja

- Red Vial (ya descargada, ver `VERIFICACION.md`): en la ruta 55, tramo 5501, el sector «Tocancipá - Chocontá» termina
  en el PR 59.0 y el sector «Chocontá - Tunja» (registrado entre los PR 108.096 y 120.0) termina en el PR 120.0. Las
  progresivas son continuas en el mismo corredor y tramo, y su diferencia es 61.0 km (hueco sin sector: 49.1 km).
- Postes de Referencia: licencia CC BY-SA 4.0, 17 816 filas, actualizada el 19 de septiembre de 2026; SHA-256
  `cd4637ba05fa01999c8b8b9acaede1d7917e6ebf16446f5104abede3ba1ea472`. En el tramo 5501 el poste PR 60 queda a 0.36 km de
  Chocontá y el PR 120 existe en el mismo tramo, con numeración de a un kilómetro; corroboran la continuidad.
- Condición de la regla: 61.0 km ≥ distancia geodésica entre los nodos (56.96 km). Se cumple (razón 1.071).
- Decisión: **aceptada.** La distancia base de Chocontá a Tunja pasa de 17.69 km (longitud registrada de un sector
  truncado) a 61.0 km. La longitud registrada queda como `distancia_cruda_km`.

### Entrada urbana a Bogotá

- Las geometrías de INVÍAS que salen de Bogotá empiezan en el límite urbano. No se halló una fuente oficial que dé el
  tramo urbano. **Sin fuente aceptable:** sigue como limitación declarada.

### Coordenadas de Cuestaboba, La Palmera y Yé de Granada

- DIVIPOLA (DANE) no trae esos tres puntos (no son cabeceras ni centros poblados) y datos.gov.co no tiene un
  nomenclátor del IGAC. **Sin fuente aceptable:** las coordenadas siguen derivadas de la unión de los tramos de
  INVÍAS y no son independientes de la geometría.

### CREG, Precios de combustibles líquidos

- Entidad: Comisión de Regulación de Energía y Gas. URL: https://creg.gov.co/publicaciones/15565/precios-de-combustibles-liquidos/.
  Licencia: publicación oficial de una entidad del Estado (datos públicos; sin licencia explícita). Consulta: 8 de
  octubre de 2026. Archivo `data/carga/nuevas/creg_precios_combustibles_liquidos_15565.html`, SHA-256
  `42c6c9baeeb1d6a608a3b2bc5a5e0b310f187ef436b65e9b4912aa2895ed70b6`.
- Contenido: precios del ACPM por galón en las 13 ciudades principales vigentes desde el 2 de octubre de 2026 (promedio
  del precio de venta al público: 11 320 COP/gal) y en 18 ciudades desde el 1 de octubre (promedio 11 399).
- Decisión: **aceptada.** El precio por defecto es 11 320 COP/gal (promedio de las 13 ciudades principales).

### UPME, Línea base de consumo de combustible de vehículos de carga en Colombia

- Entidad: Unidad de Planeación Minero Energética (mayo de 2025). URL:
  https://docs.upme.gov.co/DemandayEficiencia/Documents/1_Reporte_linea_base_EE_carga.pdf. Archivo
  `data/carga/nuevas/upme_linea_base_consumo_carga.pdf`, SHA-256
  `a12f8622f00bc7d37b89a650995b08930c59871929ceb0435821ef8d28261593`.
- Tabla 2.7: camión rígido de dos ejes grande (C2G, unos 12 t), diésel, modelo reciente: consumo específico de
  combustible 38.69 ± 2.99 L (diésel equivalente) por 100 km, medido en pista con el ciclo de conducción de vehículos
  de carga. El C2G corresponde a la categoría III de peaje del modelo.
- Decisión: **aceptada** (38.69 L/100 km = 9.78 km por galón). Es un valor de vehículo nuevo en ciclo de pista; la flota
  en uso mostró entre 30 y 40 L/100 km en dos empresas (Tabla 2.8).

### MinTransporte, RNDC (`vn9u-yhwq`, `v7bz-7nq2`)

- `vn9u-yhwq` trae solo el año 2015 (camión de dos ejes con kilómetros y valores pagados); `v7bz-7nq2` es de 2020.
  Es el flete pagado (ingreso), no el costo de operación, y está desactualizado. **Rechazada.**

### MinTransporte, SICE-TAC

- El sistema calcula costos eficientes por viaje en una calculadora interactiva; el protocolo (Resolución
  20243040057465 de 2024) da las fórmulas, pero no publica una tabla descargable de costos por kilómetro de llantas,
  lubricantes, mantenimiento ni conductor. **Sin fuente aceptable:** esos costos entran como «supuesto del equipo».
