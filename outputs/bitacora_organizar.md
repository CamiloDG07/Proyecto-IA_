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
