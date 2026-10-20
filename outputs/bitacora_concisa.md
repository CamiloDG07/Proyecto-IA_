# Bitácora: informe del Corte 2 más conciso, sin las sensibilidades

Rama `sin-sensibilidades` desde `master` (35aa3aa, contiene `corte2-entrega-heuristica`);
respaldo `respaldo-pre-sensibilidades`; PDF y zip previos en
`D:\camilo\Descargas\previo_concisa\`.

## Decisiones

1. Inventario: `outputs\candidatos_sensibilidad.csv` (apariciones en master de
   «sensibilidad», «sin piso», «61.0», «progresiv», «sin corregir», «cruda» en el
   informe, los generadores, el guion y el README, con su decisión).
2. Se quitó del informe: columnas «Progres. 61.0» y «Sin piso» de las tablas del
   barrido; la subsección «Sensibilidad con distancias sin corregir» y su tabla;
   la sección «Sensibilidad de A* sin piso» y su tabla de nodos; la tabla del
   umbral de costo en tres variantes; los dos paneles extra de la figura del
   barrido; las menciones en conclusiones (2, 3, 4, 5, 6), limitaciones y
   la sección de heurística.
3. Se conservó la frase analítica (Chocontá a Tunja: h = 56.96 km > c = 17.69 km)
   con la variante «sin piso» de la sección 3 (α = 0.310570), sin la palabra
   «sensibilidad».
4. Tabla única «Resultado del barrido de pesos» (`outputs\tabla_r_barrido_pesos.tex`,
   generada en `src\tablas_resumen.py` desde `barrido_pesos.json` y
   `barrido_total.json`; columnas tres pesos y cuatro pesos) con su «Cómo leerla»
   (`lectura_r_barrido_pesos.tex`). Se conservan las ecuaciones y la regla de
   decisión.
5. Figura de un solo panel `outputs\barrido_pesos_base.png/pdf`
   (`visualizar_rutas.figura_barrido_base`), ancho de texto, letra mínima de 8 pt,
   círculo y triángulo además del color; revisada como imagen. La figura de tres
   paneles (`barrido_pesos.png`) queda en `outputs\`, sin cambios.
6. Dinero: el texto (`texto_c2_dinero.tex`, generado por `lecturas_informe.py`) da
   el umbral de la base con su fórmula cerrada (248.8 COP/km, 283.71 km extra,
   70 600 COP), el costo variable vigente (1 157.0 COP/km) y las veces (4.6). La
   tabla de tres variantes (`tabla_r_umbral_costo.tex`) queda en `outputs\`.
7. Se conservó «Tabla del efecto de corregir las distancias» (sin corregir contra
   corregidas): es resultado de la corrección de datos y no una sensibilidad
   (aparece en el Corte 1). La conclusión 4 ahora cita esa tabla (antes
   `tab:sens-cruda`, mismas cifras 3.197/3.415 y 3.367/3.524).
8. Limitaciones: se quitó la cifra de 61.0 km y «entran como sensibilidad»; se
   conservan Chocontá a Tunja truncada con su distancia de modelo como cota
   inferior, entrada urbana a Bogotá y riesgo incompleto. La mortalidad ya no se
   describe como «sensibilidad» sino como un dato que no sustituye al GiZScore (el
   hecho no cambia).
9. Verificador: 276 comprobaciones, 0 discrepancias; se quitaron las citas de lo
   que salió y se agregó que el informe NO incluye 0.4095, 0.4611, «ensibilidad»,
   «Progres», «61.0 km», 204.5, 252.4, 13 377 ni las etiquetas retiradas. Las
   comprobaciones contra los datos guardados de las variantes se mantienen (los
   resultados siguen en `outputs\`).
10. `guion_demostracion.md` sección 5 y dos comentarios del README ajustados; el
    resto del guion y del README describe el código y la demostración, no secciones
    del informe.
11. Prueba nueva en `src\pruebas_figuras.py` para la figura del barrido de un panel.

## Conteos

«sensibilidad» en el Corte 2 compilado: 0. Páginas: 30 antes, 29 después.
