# Bitácora: entregable del Corte 2 y guía de comandos

Rama `entregable-corte2` desde `master` (c790241, contiene
`corte2-entrega-organizada`); respaldo `respaldo-pre-entregable`; PDF y zip
previos en `D:\camilo\Descargas\previo_entregable\`.

## Decisiones

1. Paquete mínimo (`python src/empaquetar.py --entregable DESTINO.zip`): código
   (`src`, `experimentos`, `informe`, `pruebas`, solo `.py`), `outputs/datos`,
   `tablas`, `lecturas`, `figuras` y los archivos `LICENCIA*` y `condiciones*` de
   `reportes`, seis archivos de `data/carga` (coordenadas, peajes,
   siniestralidad, mapa departamental, `VERIFICACION.md`, `FUENTES_NUEVAS.md`) y
   la mortalidad ANSV (CC BY-SA, 131 KB), y en la raíz `config_costos.json`,
   `requirements.txt`, `README.md`, `EJECUTAR.md`, `GUIA_DE_COMANDOS.md` y
   `guion_demostracion.md`. Se excluyen `.git`, `venv`, `_archivo_transmilenio`,
   `muestras_formato`, los `.tex` y `.pdf` de los informes, `red_vial.csv`, los
   DIVIPOLA, los postes de INVÍAS (2.8 MB, solo los usa la construcción de la
   red), las bitácoras y los documentos de terceros.
2. Quedan fuera del paquete, porque necesitan el repositorio (historial de git o
   fuentes `.tex`): `empaquetar.py`, `comparar_resultados.py`,
   `verificar_cifras.py`, `candidatos_tablas.py`, `cifras_movidas.py` y el
   generador de la guía. El verificador de cifras y el comparador no se
   documentan como comandos del paquete (la guía lo dice).
3. Contenido mínimo determinado con una prueba: copia solo con esos archivos,
   descomprimida en un directorio con espacios y tildes, entorno virtual nuevo,
   todas las suites y generadores. Única falla en la primera prueba:
   `pruebas_piso.py` llama a `git show corte2-entrega-8:...`; ahora omite esa
   comprobación (y lo imprime) cuando no hay historial de git. En el repositorio
   la comprobación se sigue ejecutando.
4. `pruebas/ejecutar_pruebas.py` (nuevo): corre las 15 suites en procesos
   aparte, toma una copia de `outputs/` antes y restaura lo que las pruebas
   reescriben (`pruebas_agente.json`, `barrido_pesos_base.pdf` y `.png`).
5. La guía se genera con `informe/guia_comandos.py` desde
   `informe/guia_plantilla.md`: ejecuta cada comando dentro del paquete
   descomprimido y pega las primeras 10 a 30 líneas reales. El modo `verificar`
   recorre la guía y compara la salida real con el fragmento, sin los tiempos
   (que varían) ni la lista de archivos restaurados; el resultado está en
   `outputs/reportes/verificacion_guia.csv`.
6. La guía impresa (`GUIA_DE_COMANDOS.pdf`) se arma con LaTeX desde el `.md`:
   3 páginas, con las salidas recortadas a 5 líneas y sin las salidas de los
   seis comandos adicionales del guion (la nota lo dice).
7. Las corridas largas (`experimentos_corte2.py`, `validacion_agente.py`,
   `medir_umbral.py`, `verificar_estructura.py`) se ejecutaron SOLO en una copia
   temporal del paquete, fuera del repositorio: 44 s, 4 min 55 s, 2 min 55 s y
   2 s. Las duraciones de los scripts rápidos (heurística, perfil, tablas,
   lecturas y figuras) salen de la prueba del paquete.
8. README y EJECUTAR llevan una nota inicial que remite a la guía cuando se
   recibe el paquete.

## Pruebas (resumen)

Ver `outputs/reportes/verificacion_guia.csv` (22 comandos, todos con código 0 y
salida coincidente, ejecutados desde un paquete descomprimido en
`...\Entrega ñ final 2\con espacios\` con un entorno virtual nuevo) y el reporte.
