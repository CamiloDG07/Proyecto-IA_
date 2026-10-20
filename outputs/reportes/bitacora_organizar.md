# Bitácora: organizar carpetas y documentar la ejecución

## Fase 1: documentación (rama `docs-ejecucion`, respaldo `respaldo-pre-docs`)

Base: `master` (contiene `corte2-entrega-concisa`).

### Comandos probados desde un clon limpio, con entorno virtual nuevo

Entorno creado con `python -m venv venv` y `pip install -r requirements.txt`
(numpy 2.5.4, scipy 1.18.1, networkx 3.7, matplotlib 3.11.2, pycodestyle 2.15.0;
Python 3.14.3). Cada comando terminó con código 0 (51 de 51):

- `src/build_graph.py` (rc 0, 0s)
- `src/agente.py` (rc 0, 1s)
- `src/heuristica.py` (rc 0, 1s)
- `src/demostracion.py Duitama Puente Nacional distancia` (rc 0, 1s)
- `src/demostracion.py Duitama Puente Nacional compuesto_sin_riesgo` (rc 0, 1s)
- `src/demostracion.py Bucaramanga Bogotá distancia` (rc 0, 1s)
- `src/demostracion.py Bogotá Granada distancia` (rc 0, 1s)
- `src/demostracion.py Mariquita Granada distancia` (rc 0, 0s)
- `src/agente_rutas.py Duitama Puente Nacional` (rc 0, 1s)
- `src/agente_rutas.py Bogotá Granada` (rc 0, 1s)
- `src/agente_rutas.py Duitama Tunja Bogotá Villeta --regreso` (rc 0, 1s)
- `src/agente_rutas.py Duitama Puente Nacional --regreso` (rc 0, 1s)
- `src/agente_rutas.py Duitama Puente Nacional --regreso --bloquear-regreso Tunja-Chocontá` (rc 0, 1s)
- `src/agente_rutas.py Duitama Puente Nacional --criterio peaje` (rc 0, 1s)
- `src/agente_rutas.py Duitama Puente Nacional --criterio costo_operativo` (rc 0, 2s)
- `src/agente_rutas.py Duitama Puente Nacional --precio-galon 14000 --rendimiento 8 --costo-otros-km 500` (rc 0, 0s)
- `src/demostracion.py despachador a Duitama --destino Puente Nacional` (rc 0, 1s)
- `src/demostracion.py despachador d Bogotá --paradas Tunja,Villeta,Girardot,Duitama,Zipaquirá` (rc 0, 1s)
- `src/demostracion.py despachador c Duitama --destino Puente Nacional --obligatorias Tunja --bloqueados Tunja/Chocontá` (rc 0, 1s)
- `src/pruebas_agente.py` (rc 0, 1s)
- `src/pruebas_agente_rutas.py` (rc 0, 2s)
- `src/pruebas_busquedas.py` (rc 0, 4s)
- `src/pruebas_costos.py` (rc 0, 6s)
- `src/pruebas_criterio.py` (rc 0, 2s)
- `src/pruebas_despachador.py` (rc 0, 2s)
- `src/pruebas_figuras.py` (rc 0, 29s)
- `src/pruebas_formato.py` (rc 0, 1s)
- `src/pruebas_mapa.py` (rc 0, 8s)
- `src/pruebas_orden_libre.py` (rc 0, 2s)
- `src/pruebas_perfil_topologico.py` (rc 0, 1s)
- `src/pruebas_piso.py` (rc 0, 1s)
- `src/pruebas_progresivas.py` (rc 0, 1s)
- `src/pruebas_tabla_heuristica.py` (rc 0, 1s)
- `src/pruebas_tablas_resumen.py` (rc 0, 2s)
- `src/comparar_resultados.py` (rc 0, 0s)
- `src/verificar_cifras.py` (rc 0, 21s)
- `src/exportar_latex.py` (rc 0, 1s)
- `src/tablas_corte2.py` (rc 0, 0s)
- `src/tablas_resumen.py` (rc 0, 2s)
- `src/tablas_agente.py` (rc 0, 2s)
- `src/lecturas_informe.py` (rc 0, 2s)
- `src/figuras_informe.py` (rc 0, 29s)
- `src/visualizar_rutas.py` (rc 0, 5s)
- `src/diagrama_red.py` (rc 0, 7s)
- `src/mapa_geografico.py` (rc 0, 7s)
- `src/perfil_topologico.py` (rc 0, 1s)
- `src/piso_geodesico.py` (rc 0, 0s)
- `src/cruce_mortalidad.py` (rc 0, 22s)
- `src/candidatos_tablas.py` (rc 0, 0s)
- `src/cifras_movidas.py` (rc 0, 0s)
- `src/verificar_estructura.py` (rc 0, 2s)

No se ejecutaron (se documentan por su código): `construir_red.py`,
`obtener_coordenadas.py`, `auditar_aristas.py`, `auditar_distancias.py` (exigen
`data/carga/red_vial.csv`, no versionado), y las mediciones largas
`experimentos_corte2.py`, `validacion_agente.py` y `medir_umbral.py` (cambiarían
los resultados guardados).

### Hallazgos

1. `requirements.txt` listaba `pandas`, que ningún código activo importa (solo
   `src/_archivo_transmilenio`); se quitó. Quedan numpy, scipy, networkx,
   matplotlib y pycodestyle.
2. Correr los generadores en un clon limpio modifica archivos versionados:
   figuras (metadatos de matplotlib), `pruebas_agente.json` (tiempos),
   `tabla_criterios.tex` (se alimenta de esos tiempos), `grafo_carga.gpickle`,
   `riesgo_mortalidad_aristas.json` (`cruce_mortalidad.py` escribe
   `mortalidad_por_100km` con más decimales: 4.186 contra 4.19) y los CSV de
   auditoría de una sola vez (`candidatos_tablas.csv`, `cifras_movidas.csv`).
   Quedó documentado en `EJECUTAR.md`; no se tocó ningún resultado.
3. El PDF versionado del Corte 2 estaba desactualizado respecto de su `.tex`
   (se había compilado antes de dos ajustes de redacción: una frase repetida en
   Limitaciones y la conclusión 2). Se recompiló desde clon limpio y se
   confirmó; el texto del `.tex` no cambia. Corte 1: texto idéntico.
4. `src/empaquetar.py` (opcional) se probó: 272 archivos, 13.6 MB; descomprimido
   aparte, `agente_rutas.py Bogotá Granada` y `demostracion.py` rc 0.

## Fase 2: reorganización (rama `organizar-carpetas`, respaldo `respaldo-pre-organizar`)

Base: `master` en `corte2-entrega-docs`. PDF y zip previos en
`D:\camilo\Descargas\previo_organizar\`.

### Decisiones

1. Estructura: `src` (núcleo), `experimentos`, `informe`, `pruebas` y `outputs`
   con `datos`, `tablas`, `lecturas`, `figuras` y `reportes`. Regla única de
   clasificación de salidas en `src/rutas.py` (`tipo`): `tabla_*.tex` a tablas,
   `lectura_*.tex` y `texto_*.tex` a lecturas, png y pdf a figuras, md y txt y
   los CSV de candidatos y cifras movidas a reportes, el resto a datos.
2. `src/rutas.py` define `RAIZ`, `DATA`, `CARGA`, `DATOS`, `TABLAS`, `LECTURAS`,
   `FIGURAS`, `REPORTES`, `SALIDA` y `ruta_salida`. `SALIDA / "archivo.ext"`
   devuelve la ruta según el tipo, de modo que ningún script escribe carpetas
   como cadenas sueltas.
3. Los scripts de `experimentos`, `informe` y `pruebas` llevan un encabezado de
   5 líneas que agrega las cuatro carpetas de código al path desde su ubicación;
   se ejecutan desde cualquier directorio (probado desde `/`).
4. Inventario: `outputs/reportes/mapa_archivos.csv` (archivo, origen, destino,
   motivo; 311 archivos versionados, cada uno una vez, más `rutas.py`).
   Reemplazos de rutas: `outputs/reportes/reemplazos_rutas.csv`.
5. Módulos ambiguos que se dejaron en `src`: `mapa_geografico.py` (dibuja los
   mapas del informe, pero `construir_red.py` y `cruce_mortalidad.py` lo
   importan), `diagrama_red.py` (lo importa `mapa_geografico.py`; se movió de
   `informe` a `src` al fallar la importación) y `empaquetar.py` (utilidad de
   entrega). Con esos tres, todo `src` se importa en aislamiento.
6. Los textos de los informes cambian solo en rutas citadas y en
   `\graphicspath` (`outputs/figuras/`). Dos rutas largas se pasaron a
   `\nolinkurl` y una a `\allowbreak` para no producir overfull ni underfull; el
   texto impreso es el mismo. En el Corte 1 también se corrigió la ruta de las
   pruebas citadas (`pruebas/...`).
7. El PDF versionado de ambos informes se volvió a compilar desde clon limpio.

### Puertas

- Inventario: 311 de 311 orígenes en el mapa, 0 destinos duplicados, 0
  ausentes; el hash de los 261 archivos que no son código ni documentación
  (datos, tablas, lecturas, figuras, PDF, `data/`) es idéntico al anterior; los
  50 que cambian son código, `.tex` y documentación (solo rutas, importaciones y
  encabezados).
- Clon limpio de la rama, con entorno virtual nuevo y desde otro directorio: 49
  de 49 comandos con código 0 (agente, demostración, despachador, 16 suites,
  comparador, verificador con 276 cifras y 0 discrepancias, generadores,
  empaquetado); pycodestyle limpio en las cuatro carpetas; red en 32 nodos, 32
  aristas, 1 ciclo.
- Generadores re-ejecutados con las rutas nuevas: las tablas, lecturas y PNG
  salen idénticos byte a byte; los 21 PDF de figuras difieren en metadatos pero
  son idénticos por píxeles. Dos excepciones que ya existían en master y no
  vienen de la reorganización: `tabla_criterios.tex` (los tiempos de
  `pruebas_agente.json` no coinciden con la tabla versionada) y
  `riesgo_mortalidad_aristas.json` (`cruce_mortalidad.py` escribe más
  decimales, 4.186 contra 4.19). Se restauraron los versionados.
- Informes: ambos compilan desde clon limpio con 0 errores, overfull, underfull
  y avisos; 21 y 29 páginas (iguales); 0 «Anexo», «??», «Discusión» y «PSO». El
  texto de los PDF coincide con el de master salvo las rutas citadas y
  corrimientos de salto de página (los números del índice de unas secciones
  cambian porque las rutas son más largas).
