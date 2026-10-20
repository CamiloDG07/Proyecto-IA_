# Bitácora de tablas en vez de texto

| Hora | Decisión | Motivo | Evidencia |
|---|---|---|---|
| 2026-10-19 20:09 | Rama tablas-en-vez-de-texto desde master (contiene corte2-entrega-9), etiqueta respaldo-pre-tablas, copia de PDF y zip a previo_entrega_9 | Seguridad | git |
| 20:13 | tabla_criterios.tex (Corte 1) no se regenera: el archivo versionado difiere de pruebas_agente.json en los tiempos de una sola corrida (diferencia anterior a esta tarea); se conserva el versionado para que los resultados queden idénticos | Regla de diff vacío; se reporta | git diff |
| 2026-10-19 | Se agregó src/tablas_resumen.py (tabla_r_*.tex) y dos filas de pesos a tabla_rutas.tex | Convertir párrafos a tablas | outputs/tabla_r_*.tex |
| 2026-10-19 | Corte 2: Tablas 7 a 10, 13, 14, 17, 22, 24 y 25 reemplazan párrafos y viñetas con cifras por algoritmo, criterio, variante o instancia; cifras duplicadas de heurística y barrido se quitan de la prosa y se remiten a las tablas existentes | Objetivo del encargo | outputs/candidatos_tablas.csv, outputs/cifras_movidas.csv |
| 2026-10-19 | Corte 1: Tabla 6 (pruebas del ciclo) y dos filas de pesos en la Tabla 8 | Objetivo del encargo | outputs/tabla_r_pruebas_ciclo.tex |
| 2026-10-19 | El Corte 2 llegó a 32 páginas; se recuperó con floats [!htbp], parámetros de flotantes y figuras al 80–90 % del ancho (30 páginas) | Tope de 30 páginas | pdflatex |
| 2026-10-19 | La razón mínima 0.3105704113 se había quitado por error; se restituyó | cifras_movidas.csv la marcó sin respaldo | src/cifras_movidas.py |
| 2026-10-19 | pruebas_agente.py reescribe outputs/pruebas_agente.json (tiempos de una corrida); se restauró el versionado tras correr las pruebas | Diff vacío de resultados | git checkout |
