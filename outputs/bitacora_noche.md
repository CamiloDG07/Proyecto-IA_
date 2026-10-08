# Bitácora de la noche

| Hora | Decisión | Motivo | Evidencia |
|---|---|---|---|
| 00:35 | Se parte de master (corte2-entrega-6 verificado) y se crea la rama datos-y-costos; PDF y zip vigentes copiados a previo_entrega_6 | El encargo reemplaza cambios-figuras-ref, que ya se fusionó como corte2-entrega-6 | git ls-remote: master 00e696b |
| 00:36 | Etapa 1: ya hecha; se completa solo el ajuste de la viñeta 4 (limitación) dentro de la etapa 2 | El prompt pide cuatro viñetas; la entrega 6 tiene tres más la limitación en la lista de limitaciones | informe_corte2.tex |
| ≈01:00 a 02:10 | Fase 2A: más de 40 consultas al catálogo de datos.gov.co y a la web; fichas en data/carga/FUENTES_NUEVAS.md | Cumplir el encargo de investigación sin suponer identificadores | catalogo.py, ficha.py (scratchpad); FUENTES_NUEVAS.md |
| ≈02:16 | Riesgo: ANSV ybqk-8s42 solo sensibilidad | Cobertura 16 de 32 aristas pero Spearman −0.033 contra el GiZScore en las 11 aristas con dato: no reproduce el orden de lo conocido | outputs/validacion_riesgo_mortalidad.json |
| ≈02:08 | Combustible: precio CREG 11 320 COP/gal (13 ciudades, 2 oct 2026) y consumo UPME C2G 38.69 L/100 km (Tabla 2.7), ambos verificados; otros costos por km sin fuente: supuesto del equipo | SICE-TAC no publica tabla descargable; RNDC solo trae 2015 | FUENTES_NUEVAS.md |
| ≈02:20 | Chocontá a Tunja: se adopta 61.0 km (PR 120.0 − PR 59.0 en la ruta 55, tramo 5501; razón 1.071 ≥ 1 frente a la geodésica) | La regla del encargo se cumple: progresivas oficiales continuas del mismo corredor y tramo | Red Vial ie7y-asdn; postes ufg7-is7r |
| 02:30 | Se registran las condiciones de la sesión de medición (plan Equilibrado, con corriente) y empieza la regeneración de experimentos | Fase 2D: una sola sesión | outputs/condiciones_medicion_noche.txt |
| nota | Las horas con ≈ se reconstruyeron de las marcas de tiempo de los archivos descargados (02:01 a 02:08) porque no se anotaron en el momento | Honestidad de la bitácora | data/carga/nuevas |
| 02:40 a 03:00 | Fase 2E: informe del Corte 2 reescrito con las cifras vigentes; se quitaron del cuerpo dos tablas de nodos expandidos del compuesto sin riesgo y la tabla completa del barrido de cuatro pesos (se citan por archivo) | Mantener el informe en 30 páginas | informe_corte2.tex, 30 páginas |
| 03:00 a 03:15 | Informe del Corte 1 actualizado (PEAS, fuentes complementarias, costo monetario con estados, Chocontá a Tunja por progresivas, auditoría con siete aristas, limitaciones); sin vocabulario del Corte 2 | Encargo 2E | formulacion_corte1.tex, 19 páginas |
| 03:16 | La salida del agente rotula el margen con la unidad del criterio (COP con peaje o costo operativo, km con distancia) | Con --criterio peaje mostraba 70600.000 sin unidad | src/agente_rutas.py |
| 03:17 | Guion y README actualizados; las salidas del guion se regeneran con los comandos reales | Cifras vigentes | guion_demostracion.md |
| 03:19 | Verificador de cifras dentro del repo (src/verificar_cifras.py), con costo monetario, mortalidad, narrativa de ambos informes y comparación literal de las salidas del guion | Compuerta de verificación | 231 cifras, 0 discrepancias |
| 03:19 | Decisión propia: el criterio por defecto no cambia a costo operativo | Un insumo (otros costos por km) es supuesto del equipo; la regla del encargo exige todos verificados | config_costos.json |
