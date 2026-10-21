# Bitácora: preparación del visualizador para Vercel

Rama `despliegue-vercel` desde `master` (contiene `corte2-visualizador-2`).
Etiqueta de respaldo: `respaldo-pre-vercel`. Etiqueta de cierre:
`corte2-vercel`. Documentación de Vercel consultada el 20 de octubre de 2026
(`/docs/frameworks/backend/fastapi`, actualizada el 27 de agosto de 2026, y
`/docs/functions/runtimes/python`, del 12 de agosto de 2026). No se instaló la
CLI ni se inició sesión en Vercel, y no se creó ningún proyecto.

## 1. Revisión previa

- **Importación de `src\`**: `servidor.py` inserta `src` en `sys.path` desde
  `Path(__file__)`; no depende del directorio de trabajo.
- **Escrituras en disco**: ninguna en el camino del servidor (solo `main()` de
  `heuristica.py` y `build_graph.py` escriben, y el servidor no los llama).
  `webbrowser` y `uvicorn` solo se importan dentro de `main()`; el servidor
  sirve `/` con `FileResponse` y `/static` con `StaticFiles`.
- **Grafo**: antes se leía `outputs/datos/grafo_carga.gpickle`, que depende de
  las versiones de Python y de networkx. Ahora se arma con `construir_grafo()`
  desde los JSON de la red (12 ms); se comprobó que el grafo resultante es
  idéntico al del pickle (mismos atributos en las 32 aristas y mismo
  `graph`). No se tocó `build_graph.py`.
- **Dependencias que el servidor importa**: `fastapi` (con `starlette`,
  `pydantic`), `networkx` y `numpy`. No importa `scipy`, `matplotlib` ni
  `pycodestyle` (comprobado en `sys.modules`).
- **Archivos que lee en ejecución**: `src\*.py`, `outputs\datos\*.json`
  (`nodos_red`, `aristas_red`, `umbral_held_karp`), `data\carga\coordenadas_nodos.csv`,
  `config_costos.json` y `visualizador\` (con `config_visualizador.json` y
  `static\`).
- **Peor caso de cómputo** (portátil Intel Core i7-8750H, Python 3.14.3, tres
  corridas): 19 paradas libres con Held-Karp, 3.28 a 3.55 s; 20 paradas con
  ACO, 1.92 a 2.68 s; `/api/busqueda` con A*, 0.15 s (200 repeticiones
  incluidas); `/api/comparar`, 0.01 s; `/api/criterios`, 0.03 s. Memoria pico
  de Held-Karp con k = 19: 112 MiB (tracemalloc).

## 2. Decisiones

1. **Punto de entrada**: `pyproject.toml` con `[tool.vercel]` y
   `entrypoint = "visualizador.servidor:app"`, que es lo que la documentación
   indica para un módulo propio; es más robusto que un `app.py` en la raíz,
   porque no obliga a duplicar la creación de la aplicación. El archivo no
   declara dependencias: siguen en `requirements.txt`.
2. **Dependencias**: se deja `requirements.txt` sin cambios. En un entorno
   nuevo con solo ese archivo, `site-packages` pesa 293 MB y el proyecto sin
   `.git` 2.0 MB (unos 295 MB en total, bajo el límite de 500 MB). Quedan
   `scipy`, `matplotlib` y `pycodestyle`, que el servidor no usa (unos 150 MB
   de más y 3 min de instalación); no se separó porque Vercel lee
   `requirements.txt` o `pyproject.toml` sin que la documentación aclare la
   precedencia si hay ambos, y un `requirements.txt` aparte rompería la guía del
   paquete. Si el tamaño o el tiempo de instalación fueran un problema, la
   alternativa es declarar solo `fastapi`, `networkx` y `numpy` en
   `[project].dependencies`.
3. **Versión de Python**: `.python-version` con `3.14` (versiones disponibles
   en Vercel: 3.12 por defecto, 3.13 y 3.14); es la versión con que se probó todo
   el proyecto.
4. **`vercel.json`**: `functions` con la clave `visualizador/servidor.py` y
   `maxDuration` de 60 s. El peor caso medido es de 3.55 s (el doble son 7.1 s);
   se dejó 60 s, el valor del ejemplo de la documentación, por el margen ante un
   procesador más lento que el del portátil de pruebas, y porque 60 s no excede
   lo que permite la plataforma. Si la plataforma lo rechaza en el plan gratuito,
   hay que bajarlo (el peor caso real cabe en 10 s).
5. **`.vercelignore`**: deja fuera `.git`, `venv`, `informe`, `experimentos`,
   `pruebas`, `outputs/figuras`, `tablas`, `lecturas`, `reportes`, los archivos
   de TransMilenio, los datos pesados no usados (`red_vial.csv`, DIVIPOLA, MGN,
   descargas previas), PDF, `.tex`, auxiliares de LaTeX y `*.md`. Sin reglas de
   negación. Se comprobó que NADA de lo que el servidor lee queda excluido: se
   aplicó el archivo a un clon limpio y la aplicación funcionó (proyecto
   resultante de 2.0 MB).
6. **Límites de entrada** (solo en `servidor.py`): máximo 20 paradas libres u
   obligatorias (422), máximo 64 aristas bloqueadas (422) y cuerpo de hasta
   64 KiB (413), con mensajes en español. Ninguna respuesta válida anterior
   cambia (el mayor caso del proyecto, 20 paradas, sigue válido).
7. **`/api/salud`** devuelve `{"estado": "ok"}` sin calcular nada.
8. **Tipos de contenido**: `.js`, `.css`, `.woff2` y `.html` se registran
   explícitamente en `mimetypes` para no depender de `/etc/mime.types` del
   sistema donde corra la función. Se conserva `Cache-Control: no-cache`; como
   hay un middleware de nivel superior, los montajes estáticos se quedan en la
   función (válido según la documentación).
9. **Zip del entregable**: no incluye `vercel.json`, `.vercelignore`,
   `pyproject.toml` ni `.python-version` (son del repositorio, no sirven para
   ejecutar el paquete); `empaquetar.py` ya los excluye porque solo copia una
   lista fija de archivos de la raíz. No hizo falta cambiarlo. El zip sí lleva
   el `servidor.py` nuevo.
10. **Arranque en frío**: la importación del servidor tarda unos 3.5 s en este
    equipo (fastapi 1.5 s, networkx 1.1 s, el resto numpy y los módulos del
    proyecto); el arranque completo con uvicorn, sin bytecode de los módulos del
    proyecto y con la caché de disco fría, tardó 6.4 s hasta responder
    `/api/salud` y 0.12 s la primera búsqueda. Lo único que se movió a carga
    perezosa fue `uvicorn` y `webbrowser` (solo se usan al arrancar en local, ~0.5 s).
    Aplazar el despachador (0.35 s) no compensa: la interfaz lo pide en su primera
    llamada a `/api/red`, porque `REPETICIONES` viene de `demostracion.py`. Vercel
    precompila el bytecode al compilar, y en Linux las importaciones suelen ser
    más rápidas; no se pudo medir allí.

## 3. Pruebas

- No hay CLI de Vercel ni sesión: se hizo la prueba alternativa. Clon limpio de
  la rama, con `.vercelignore` aplicado, entorno virtual nuevo con solo
  `requirements.txt`, archivos del clon en solo lectura (`attrib +R`) y
  `python -m uvicorn visualizador.servidor:app` desde la raíz (la misma ruta de
  módulo que usa Vercel). Resultado: `/api/salud` 200; `/` y `/docs` 200;
  búsqueda del caso central 370.54 km con 14 expandidos y 654.25 km por
  Santander con peaje; `/static` de Leaflet, estilos, `app.js` y fuentes con
  el tipo de contenido correcto (`text/javascript`, `text/css`, `font/woff2`,
  `image/png`); despachador con 19 paradas (Held-Karp, 3.69 s) y con 20 (ACO,
  3.80 s). No se probó en la plataforma real.
- `pruebas/pruebas_visualizador.py`: nuevas comprobaciones de `/api/salud`, de
  los tres límites (422, 422 y 413), de que 20 paradas siguen siendo válidas,
  de los tipos de contenido y de que el servidor no escribe en disco (se
  sustituye `open` por una versión que falla ante cualquier escritura).
- Todas las suites, el verificador de cifras y pycodestyle: ver el reporte.
