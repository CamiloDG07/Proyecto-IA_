# Bitácora del visualizador web (Corte 2)

Rama `visualizador-web`, creada desde `master` (que contiene `corte2-entregable`).
Etiqueta de respaldo: `respaldo-pre-visualizador`. Copia previa de los PDF y del
zip vigentes en `D:\camilo\Descargas\previo_visualizador\`.

## Alcance

Aplicación web local (FastAPI y Leaflet, sin Node ni compilación) que dibuja
sobre la red real de 32 nodos y 32 aristas la búsqueda paso a paso, el árbol,
la construcción de la ruta, la comparación de algoritmos y de criterios, y el
despachador. No cambia ningún resultado, cifra, tabla, figura ni texto de los
informes, y no modifica `busquedas.py`, `heuristica.py`, `build_graph.py` ni
`config_costos.json` (diff vacío frente a `master`).

## Decisiones propias

1. **Trazas en un módulo nuevo** (`src/trazas.py`): repite línea por línea la
   lógica de `busquedas.py` y registra entradas y pasos. Se prueba contra
   `busquedas.py` en los 44 640 casos (992 pares, 9 criterios, 5 algoritmos):
   ruta, costo, saltos, expandidos, generados, frontera máxima y
   reexpansiones idénticos, más los invariantes de la traza.
2. **Sin dependencias de prueba nuevas**: las pruebas de la API llaman a la
   aplicación por la interfaz ASGI con un llamador propio (el `TestClient` de
   FastAPI exigiría `httpx`). Las únicas dependencias nuevas son `fastapi` y
   `uvicorn`, con versiones fijadas (0.156.2 y 0.54.0).
3. **Instancias de 19 y 20 paradas**: el proyecto no tiene instancias de 19 o
   20 paradas sobre la red real (el umbral K = 19 se midió con instancias
   euclidianas aleatorias). Se definieron instancias de demostración: Bogotá de
   origen y las primeras 19 y 20 ciudades restantes en orden alfabético. La
   interfaz, la guía y el guion las rotulan «instancia de demostración» y no
   como casos de las pruebas del informe. El caso de 5 paradas sí es el del
   guion (Bogotá; Tunja, Villeta, Girardot, Duitama, Zipaquirá).
4. **Tiempo de viaje**: el proyecto no tiene datos de tiempo. La interfaz
   muestra «tiempo estimado» = distancia / velocidad con 50 km/h
   (`visualizador/config_visualizador.json`, estado «supuesto del equipo»,
   editable de 20 a 90 km/h), siempre rotulado «estimación con velocidad
   supuesta». No entra a ningún costo ni resultado.
5. **Matriz de costos del despachador**: `Despachador` no la devuelve, así que
   el servidor construye una `MatrizCostos` con los mismos argumentos (sin
   modificar el módulo); las pruebas comprueban que coincide con los tramos.
6. **Curva del ACO**: se muestra la `curva_media_aco` que ya entrega el
   despachador. El módulo no entrega una «referencia por estructura», así que
   no se dibuja ninguna ni se inventa.
7. **Ida y vuelta**: el despachador no tiene esa opción; la API resuelve el
   regreso como una segunda solicitud al mismo `Despachador` con el origen y el
   destino invertidos (y, si se pide, bloqueos propios del regreso).
8. **Prototipo** `D:\camilo\Descargas\prototipo_buscador_rutas.html`: no existe;
   la interfaz se diseñó desde la especificación. Tampoco se consultó ningún
   repositorio ajeno.
9. **Diseño propio**: carta de navegación nocturna (ámbar para la ruta, azul
   hielo para lo explorado; Fraunces, Public Sans e IBM Plex Mono, con sus
   licencias OFL en `static/vendor/fuentes/`), con modo claro equivalente.

## Pruebas

- `pruebas/pruebas_trazas.py`: 44 640 casos idénticos a `busquedas.py`.
- `pruebas/pruebas_visualizador.py`: cada endpoint con valores del informe
  (370.54 km por Bogotá, 654.25 km por Santander, A* con distancia y 14
  expandidos), errores 4xx en español, despachador (Held-Karp con k = 5 y 19,
  ACO con k = 20), coherencia de las métricas y arranque del servidor en un
  puerto libre.
- Las 17 suites pasan; el verificador de cifras da 276 cifras y 0
  discrepancias; la red sigue en 32 nodos, 32 aristas y 1 ciclo.
- pycodestyle limpio en `src`, `experimentos`, `informe`, `pruebas` y
  `visualizador`; ningún color ni tamaño suelto fuera de las variables CSS
  (comprobado con un script que descarta los bloques `:root`); contraste de
  texto de al menos 4.5:1 en los dos modos (calculado desde las variables).

## Revisión visual

Hecha con la extensión de Chrome sobre un servidor local. La ventana del
navegador no baja de unos 630 px de ancho, así que los anchos de 1440, 1280 y
400 px se obtuvieron incrustando la página en un marco de ese ancho (las
consultas de medios se aplican al marco). Capturas en
`D:\camilo\Descargas\capturas_visualizador\`: caso central al inicio, a la mitad
y al final (oscuro, 1440), caso de 5 paradas, final a 1280, y 400 px en claro y
oscuro. Correcciones de la primera ronda: estela luminosa de los tramos del
despachador (retirada), rótulos del mapa medidos antes de cargar la fuente
(ahora se reubican al terminar de cargar), tiempo estimado que se partía en dos
líneas, barras de desplazamiento claras en modo oscuro (`color-scheme`),
contrastes del modo claro por debajo de 4.5:1 (acentos oscurecidos), contraste
del mapa de calor de la matriz. Segunda ronda: se volvieron a capturar los casos
afectados sin hallazgos nuevos. No hay desborde horizontal a 400 px (ancho del
documento 381 px con barra de desplazamiento de 19 px).

No se pudo probar con Playwright (no está instalado); la prueba de navegador se
hizo a mano con la extensión de Chrome y, por eso, no hay una prueba
automática de consola en el repositorio. La consola, revisada en la primera carga,
solo mostró errores de una extensión ajena del navegador.

## Cierre

Ver el estado final (etiquetas, fusión y envío) en
`D:\camilo\Descargas\REPORTE_VISUALIZADOR.md`.
