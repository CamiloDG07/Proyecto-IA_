"use strict";
/* Página de aprendizaje automático del visualizador.
   El navegador solo dibuja: el tránsito, el nivel y el tiempo de cada tramo
   y la ruta de menor tiempo estimado llegan del servidor
   (/api/aprendizaje/*), que los lee de los resultados del proyecto. */

const $ = (id) => document.getElementById(id);
const ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"};
const esc = (t) => String(t == null ? "" : t).replace(/[&<>"']/g, (c) => ESC[c]);
const NBSP = " ";
const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
               "septiembre", "octubre", "noviembre", "diciembre"];
const ORIGEN_DATO = {
  prueba: "predicción a un mes",
  pronostico: "pronóstico",
  historico: "histórico",
  sin_dato: "tiempo libre",
};
const NOMBRE_VARIABLE = {
  log_rezago_1: "Tránsito del mes anterior",
  log_rezago_2: "Tránsito de hace 2 meses",
  log_rezago_3: "Tránsito de hace 3 meses",
  log_rezago_12: "Tránsito de hace 12 meses",
  log_rezago_13: "Tránsito de hace 13 meses",
  mes_del_anio: "Mes del año",
  dias_mes: "Días del mes",
  participacion_carga_rezago_1: "Participación de la carga",
};

function fmt(n, dec) {
  if (n == null || Number.isNaN(n)) return "—";
  const s = Number(n).toFixed(dec == null ? 0 : dec);
  const [ent, fra] = s.split(".");
  const miles = ent.replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);
  return fra ? `${miles},${fra}` : miles;
}
function fmtHoras(minutos) {
  const total = Math.round(minutos);
  return `${Math.floor(total / 60)}${NBSP}h ${String(total % 60).padStart(2, "0")}${NBSP}min`;
}
function nombreMes(clave) {
  const [anio, mes] = clave.split("-");
  return `${MESES[Number(mes) - 1]} de ${anio}`;
}
const par = (u, v) => (u < v ? `${u}|${v}` : `${v}|${u}`);

async function api(ruta, params) {
  const url = new URL(ruta, window.location.origin);
  Object.entries(params || {}).forEach(([k, v]) => url.searchParams.set(k, v));
  const r = await fetch(url);
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(datos.detail || `Error ${r.status}`);
  return datos;
}
function aviso(texto) {
  const caja = $("aviso");
  caja.hidden = !texto;
  caja.textContent = texto || "";
}

const S = {resumen: null, red: null, ruta: null, mes: null, origen: "Duitama", destino: "Puente Nacional"};

function aplicarTema(tema) {
  document.documentElement.dataset.tema = tema;
  try { localStorage.setItem("tema", tema); } catch (e) { /* sin almacenamiento */ }
  $("btn-tema-txt").textContent = tema === "claro" ? "Modo oscuro" : "Modo claro";
  $("btn-tema").setAttribute("aria-pressed", String(tema === "claro"));
}

/* ---- mapa ---------------------------------------------------------------- */
let mapa = null;
let capaMosaicos = null;
const capas = {};
const marcas = {};

function construirMapa() {
  mapa = L.map("mapa", {zoomControl: false, zoomSnap: 0.25});
  L.control.zoom({position: "bottomright", zoomInTitle: "Acercar", zoomOutTitle: "Alejar"}).addTo(mapa);
  mapa.attributionControl.setPrefix(false);
  capaMosaicos = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>',
  }).addTo(mapa);
  const coord = {};
  S.red.nodos.forEach((n) => { coord[n.nombre] = [n.latitud, n.longitud]; });
  const encuadrar = () => {
    mapa.invalidateSize({pan: false});
    mapa.fitBounds(Object.values(coord), {paddingTopLeft: [40, 40], paddingBottomRight: [120, 40], animate: false});
  };
  encuadrar();
  if (window.ResizeObserver) new ResizeObserver(encuadrar).observe($("mapa"));
  S.red.tramos.forEach((t) => {
    const pts = [coord[t.u], coord[t.v]];
    const vis = L.polyline(pts, {className: "tr", interactive: false}).addTo(mapa);
    const hit = L.polyline(pts, {className: "tr-hit", weight: 18, opacity: 0.001}).addTo(mapa);
    hit.bindTooltip(() => htmlTramo(par(t.u, t.v)), {className: "tip", sticky: true, direction: "top"});
    capas[par(t.u, t.v)] = vis;
  });
  S.red.nodos.forEach((n) => {
    const icono = L.divIcon({className: "nd-ml", iconSize: null,
      html: `<span class="punto"></span><span class="nombre">${esc(n.nombre)}</span>`});
    marcas[n.nombre] = L.marker(coord[n.nombre], {icon: icono, interactive: false, keyboard: false}).addTo(mapa);
  });
  $("leyenda").innerHTML = ["bajo", "medio", "alto"].map((c) =>
    `<div class="leyenda-item"><span class="ley-linea n-${c}"></span>Tránsito ${c}</div>`).join("")
    + '<div class="leyenda-item"><span class="ley-linea n-sin"></span>Sin dato de tránsito</div>'
    + '<p class="leyenda-nota">La línea gruesa es la ruta recomendada.</p>';
}

function tramoDe(clave) {
  return S.red.tramos.find((t) => par(t.u, t.v) === clave);
}

function htmlTramo(clave) {
  const t = tramoDe(clave);
  const d = t.dato;
  const filas = [`<b>${esc(t.u)} – ${esc(t.v)}</b>`,
    `<span class="n">${fmt(t.distancia_km, 1)}</span> km, ${t.doble_calzada ? "doble calzada" : "calzada sencilla"}`];
  if (t.peaje) filas.push(`Peaje ${esc(t.peaje)}`);
  if (d) {
    filas.push(`Tránsito: <span class="n">${fmt(d.transito_usado)}</span> veh/día (${esc(d.clase)})`);
    if (d.transito_observado != null) filas.push(`Observado: <span class="n">${fmt(d.transito_observado)}</span> veh/día`);
    filas.push(`Saturación en hora pico: <span class="n">${fmt(d.saturacion, 2)}</span>`);
    filas.push(`Tiempo: <span class="n">${fmt(d.tiempo_min, 1)}</span> min (libre ${fmt(t.tiempo_libre_min, 1)})`);
    filas.push(esc(ORIGEN_DATO[d.origen_dato]) + (t.estado === "historico" ? `, hasta ${esc(t.ultimo_mes)}` : ""));
  } else {
    filas.push(`Tiempo libre: <span class="n">${fmt(t.tiempo_libre_min, 1)}</span> min`);
    filas.push(t.peaje ? "El peaje no está en la fuente de la ANI" : "Tramo sin peaje: sin dato de tránsito");
  }
  return filas.join("<br>");
}

function pintarMapa() {
  const enRuta = new Set();
  if (S.ruta) {
    const r = S.ruta.elegida.ruta;
    for (let i = 0; i + 1 < r.length; i++) enRuta.add(par(r[i], r[i + 1]));
  }
  S.red.tramos.forEach((t) => {
    const clave = par(t.u, t.v);
    const el = capas[clave].getElement();
    if (!el) return;
    el.setAttribute("class", `leaflet-interactive tr n-${t.dato ? t.dato.clase : "sin"}`
      + (enRuta.has(clave) ? " en-ruta" : (S.ruta ? " fuera-ruta" : "")));
  });
  Object.entries(marcas).forEach(([nombre, m]) => {
    const extremo = S.ruta && (nombre === S.ruta.origen || nombre === S.ruta.destino);
    m.getElement().classList.toggle("extremo", Boolean(extremo));
  });
}

/* ---- panel de la ruta ---------------------------------------------------- */
const cifra = (valor, etiqueta, nota) =>
  `<div class="cifra"><span class="cifra-v">${valor}</span><span class="cifra-e">${etiqueta}</span>`
  + (nota ? `<span class="cifra-n">${nota}</span>` : "") + "</div>";
const insigniaNivel = (nivel) => (nivel
  ? `<span class="insignia nivel n-${esc(nivel)}">${esc(nivel)}</span>`
  : '<span class="insignia">sin dato</span>');

function pintarRuta() {
  const r = S.ruta;
  if (!r) return;
  const e = r.elegida;
  const filas = e.detalle.map((d) => `<tr>
    <td>${esc(d.origen)} – ${esc(d.destino)}</td>
    <td class="n">${fmt(d.distancia_km, 1)}</td>
    <td class="n">${d.transito_diario == null ? "—" : fmt(d.transito_diario)}</td>
    <td>${insigniaNivel(d.nivel_transito)}</td>
    <td class="n">${d.saturacion == null ? "—" : fmt(d.saturacion, 2)}</td>
    <td class="n">${fmt(d.tiempo_min, 1)}</td>
    <td>${esc(ORIGEN_DATO[d.origen_dato])}</td></tr>`).join("");
  const otras = r.alternativas.map((a) => `<tr>
    <td class="ruta-celda">${esc(a.ruta.join(" > "))}</td>
    <td class="n">${fmt(a.distancia_km, 2)}</td>
    <td class="n">${fmtHoras(a.tiempo_min)}</td>
    <td class="n">${a.tramos_por_nivel.alto}</td></tr>`).join("");
  $("panel-ruta").innerHTML = `
    <p class="ruta-texto">${esc(e.ruta.join(" > "))}</p>
    <div class="cifras-4">
      ${cifra(fmtHoras(e.tiempo_min), "Tiempo estimado", `libre ${fmtHoras(e.tiempo_libre_min)}`)}
      ${cifra(`${fmt(e.demora_min, 2)}${NBSP}min`, "Demora por tránsito", "función BPR")}
      ${cifra(`${fmt(e.distancia_km, 2)}${NBSP}km`, "Distancia", `${e.saltos} tramos`)}
      ${cifra(`${e.tramos_por_nivel.alto} de ${e.saltos}`, "Tramos con tránsito alto", `${fmt(e.peaje_cop)} COP de peaje`)}
    </div>
    <h3 class="subtitulo-bloque">Tramo por tramo</h3>
    <div class="tabla-scroll tabla-libre"><table>
      <thead><tr><th>Tramo</th><th class="n">km</th><th class="n">veh/día</th><th>Nivel</th>
        <th class="n">v/c</th><th class="n">min</th><th>Dato</th></tr></thead>
      <tbody>${filas}</tbody></table></div>
    ${otras ? `<h3 class="subtitulo-bloque">Alternativa</h3><div class="tabla-scroll"><table>
      <thead><tr><th>Ruta</th><th class="n">km</th><th class="n">Tiempo</th><th class="n">Tramos en alto</th></tr></thead>
      <tbody>${otras}</tbody></table></div>` : ""}
    ${r.avisos.length ? `<h3 class="subtitulo-bloque">Avisos</h3><ul class="lista-avisos">${
      r.avisos.map((a) => `<li>${esc(a)}</li>`).join("")}</ul>` : ""}
    <p class="ayuda">A* con h = geodésica a ${r.velocidad_libre_kmh}${NBSP}km/h: ${r.nodos_expandidos} nodos expandidos, ${r.reexpansiones} reexpansiones.</p>`;
}

/* ---- pestañas de modelos ------------------------------------------------- */
function tablaModelos(modelos, mejor, columnas) {
  const filas = Object.entries(modelos).map(([nombre, m]) => {
    const clase = nombre === mejor ? "mejor" : (m.tipo !== "modelo" ? "referencia" : "");
    const celdas = columnas.map((c) => `<td class="n">${fmt(m.prueba[c.clave] * (c.factor || 1), c.dec)}</td>`).join("");
    const nota = nombre === mejor ? ' <span class="insignia ok">elegido en validación</span>'
      : (m.tipo === "referencia" ? ' <span class="insignia">referencia</span>' : "");
    return `<tr class="${clase}"><td>${esc(nombre)}${nota}</td>${celdas}</tr>`;
  }).join("");
  return `<div class="tabla-scroll"><table><thead><tr><th>Método</th>${
    columnas.map((c) => `<th class="n">${c.titulo}</th>`).join("")}</tr></thead><tbody>${filas}</tbody></table></div>`;
}

function graficaHorizonte(datos) {
  const W = 560, H = 260, mi = 46, md = 14, ms = 14, mb = 40;
  const maximo = Math.ceil(Math.max(...datos.flatMap((d) => [d.modelo, d.persistencia, d.estacional])) / 5) * 5;
  const x = (h) => mi + (h - 1) * (W - mi - md) / (datos.length - 1);
  const y = (v) => H - mb - v * (H - mb - ms) / maximo;
  const linea = (clave) => datos.map((d, i) => `${i ? "L" : "M"}${x(d.horizonte).toFixed(1)} ${y(d[clave]).toFixed(1)}`).join(" ");
  let guias = "";
  for (let v = 0; v <= maximo; v += 5) {
    guias += `<line class="guia" x1="${mi}" x2="${W - md}" y1="${y(v)}" y2="${y(v)}"/>`
      + `<text x="${mi - 6}" y="${y(v) + 4}" text-anchor="end">${v}</text>`;
  }
  const marcasX = datos.map((d) => `<text x="${x(d.horizonte)}" y="${H - mb + 16}" text-anchor="middle">${d.horizonte}</text>`).join("");
  return `<svg class="grafica" viewBox="0 0 ${W} ${H}" role="img" aria-label="Error porcentual mediano por horizonte del pronóstico">
    ${guias}${marcasX}
    <text x="${(W + mi) / 2}" y="${H - 4}" text-anchor="middle">Horizonte del pronóstico (meses)</text>
    <text x="12" y="${H / 2}" text-anchor="middle" transform="rotate(-90 12 ${H / 2})">Error mediano (%)</text>
    <path class="s-persistencia" d="${linea("persistencia")}"/>
    <path class="s-estacional" d="${linea("estacional")}"/>
    <path class="s-modelo" d="${linea("modelo")}"/></svg>
    <p class="ayuda"><span class="insignia amb">línea continua</span> modelo recursivo;
    <span class="insignia info">rayas</span> persistencia; <span class="insignia ok">puntos</span> estacional.</p>`;
}

function pintarRegresion() {
  const r = S.resumen.regresion;
  const p = S.resumen.particion;
  const importancias = Object.entries(r.importancias).map(([clave, valor]) =>
    `<tr><td>${esc(NOMBRE_VARIABLE[clave] || clave)}</td><td class="n">${fmt(valor, 4)}</td></tr>`).join("");
  $("tab-regresion").innerHTML = `
    <p class="parrafo">Objetivo: tránsito diario del mes siguiente en un peaje. Entrenamiento con ${fmt(p.entrenamiento.filas)} filas
    (${esc(p.entrenamiento.desde)} a ${esc(p.entrenamiento.hasta)}), validación con ${fmt(p.validacion.filas)} y prueba con
    ${fmt(p.prueba.filas)} (${esc(p.prueba.desde)} a ${esc(p.prueba.hasta)}, ${p.prueba.peajes} peajes). Métricas en la prueba.</p>
    <div class="dos-col"><div>
    ${tablaModelos(r.modelos, r.mejor, [
      {clave: "mae", titulo: "MAE (veh/día)", dec: 1}, {clave: "rmse", titulo: "RMSE (veh/día)", dec: 1},
      {clave: "r2", titulo: "R²", dec: 4}, {clave: "error_porcentual_mediano", titulo: "Error mediano (%)", dec: 2}])}
    <h3 class="subtitulo-bloque">Importancia por permutación (${esc(r.mejor)})</h3>
    <div class="tabla-scroll"><table><thead><tr><th>Variable</th><th class="n">Aumento del MAE (escala logarítmica)</th></tr></thead>
    <tbody>${importancias}</tbody></table></div></div>
    <div><h3 class="subtitulo-bloque">Pronóstico recursivo de 12 meses</h3>${graficaHorizonte(r.error_por_horizonte)}</div></div>`;
}

function pintarClasificacion() {
  const c = S.resumen.clasificacion;
  const cortes = S.resumen.cortes_clase;
  const matriz = c.modelos[c.mejor].prueba.matriz_confusion;
  const clases = S.resumen.clases;
  const filas = matriz.map((fila, i) => {
    const total = fila.reduce((a, b) => a + b, 0);
    return `<tr><th>${esc(clases[i])}</th>${fila.map((v, j) =>
      `<td class="celda-c${i === j ? " diagonal" : ""}" style="--v:${Math.round(60 * v / total)}">${v}</td>`).join("")}</tr>`;
  }).join("");
  $("tab-clasificacion").innerHTML = `
    <p class="parrafo">Nivel de tránsito del mes, indicador de congestión del proyecto: bajo hasta ${fmt(cortes[0])} vehículos por día,
    medio hasta ${fmt(cortes[1])} y alto por encima. Los cortes son los terciles del entrenamiento.</p>
    <div class="dos-col"><div>
    ${tablaModelos(c.modelos, c.mejor, [
      {clave: "exactitud", titulo: "Exactitud (%)", dec: 2, factor: 100},
      {clave: "f1_macro", titulo: "F1 macro (%)", dec: 2, factor: 100}])}</div>
    <div><h3 class="subtitulo-bloque">Matriz de confusión (${esc(c.mejor)})</h3>
    <div class="tabla-scroll"><table class="confusion"><thead><tr><th>Real \\ predicho</th>${
      clases.map((x) => `<th class="n">${esc(x)}</th>`).join("")}</tr></thead><tbody>${filas}</tbody></table></div></div></div>`;
}

function graficaGrupos(grupos, peajesRed) {
  const W = 560, H = 360, m = 30;
  const xs = grupos.map((g) => g.componente_1), ys = grupos.map((g) => g.componente_2);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const x = (v) => m + (v - x0) * (W - 2 * m) / (x1 - x0);
  const y = (v) => H - m - (v - y0) * (H - 2 * m) / (y1 - y0);
  const puntos = grupos.map((g) => {
    const deRed = peajesRed.has(g.peaje_normal);
    return `<circle class="pt g-${g.grupo}${deRed ? " de-red" : ""}" cx="${x(g.componente_1).toFixed(1)}" cy="${y(g.componente_2).toFixed(1)}" r="${deRed ? 6 : 4}">
      <title>${esc(g.peaje)}: grupo ${g.grupo}, ${fmt(g.transito_diario_medio)} veh/día, carga ${fmt(100 * g.participacion_carga, 1)} %</title></circle>`;
  }).join("");
  return `<svg class="grafica" viewBox="0 0 ${W} ${H}" role="img" aria-label="Peajes en el plano de las dos componentes principales">
    <line class="eje" x1="${m}" x2="${W - m}" y1="${H - m}" y2="${H - m}"/><line class="eje" x1="${m}" x2="${m}" y1="${m}" y2="${H - m}"/>
    <text x="${W / 2}" y="${H - 8}" text-anchor="middle">Componente principal 1</text>
    <text x="12" y="${H / 2}" text-anchor="middle" transform="rotate(-90 12 ${H / 2})">Componente principal 2</text>
    ${puntos}</svg>`;
}

function pintarAgrupamiento() {
  const a = S.resumen.agrupamiento;
  const sinTilde = (t) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase().trim();
  const grupos = S.resumen.grupos.map((g) => ({...g, peaje_normal: sinTilde(g.peaje)}));
  const peajesRed = new Set(S.resumen.peajes_red);
  const porGrupo = {};
  grupos.forEach((g) => { (porGrupo[g.grupo] = porGrupo[g.grupo] || []).push(g); });
  const media = (lista, clave) => lista.reduce((s, g) => s + g[clave], 0) / lista.length;
  const filas = Object.keys(porGrupo).sort().map((k) => {
    const lista = porGrupo[k];
    const deRed = lista.filter((g) => peajesRed.has(g.peaje_normal)).map((g) => g.peaje);
    return `<tr><td class="sin-corte"><span class="muestra g-${k}"></span>Grupo ${k}</td><td class="n">${lista.length}</td>
      <td class="n">${fmt(media(lista, "transito_diario_medio"))}</td>
      <td class="n">${fmt(100 * media(lista, "participacion_carga"), 1)}</td>
      <td class="n">${fmt(100 * media(lista, "participacion_buses"), 1)}</td>
      <td class="n">${fmt(media(lista, "amplitud_estacional"), 2)}</td>
      <td class="ruta-celda">${esc(deRed.join(", ") || "—")}</td></tr>`;
  }).join("");
  const curva = a.curva.find((c) => c.k === a.k);
  $("tab-agrupamiento").innerHTML = `
    <p class="parrafo">${a.peajes} peajes agrupados por volumen, participación de carga y de buses y amplitud estacional.
    K-medias con k = ${a.k} (silueta ${fmt(curva.silueta_k_medias, 3)}); el jerárquico de Ward con el mismo k da
    ${fmt(curva.silueta_jerarquico, 3)} y un índice de Rand ajustado de ${fmt(a.indice_rand_ajustado, 2)} frente a K-medias.
    La silueta es baja: los peajes forman un continuo más que grupos separados.</p>
    <div class="tabla-scroll tabla-libre"><table><thead><tr><th>Grupo</th><th class="n">Peajes</th>
      <th class="n">Tránsito medio (veh/día)</th><th class="n">Carga (%)</th><th class="n">Buses (%)</th>
      <th class="n">Amplitud estacional</th><th>Peajes de la red</th></tr></thead><tbody>${filas}</tbody></table></div>
    <div class="grafica-caja">${graficaGrupos(grupos, peajesRed)}
    <p class="ayuda">Cada punto es un peaje; los de borde grueso están en la red del proyecto.</p></div>`;
}

function pintarSupuestos() {
  const c = S.resumen.config_tiempo;
  const t = S.resumen.tiempo;
  const red = S.resumen.red;
  $("tab-supuestos").innerHTML = `
    <p class="parrafo">El proyecto no tiene tiempos medidos. El tiempo de un tramo es
    <code>t = t_libre · (1 + α · (v / c)^β)</code>, con <code>v</code> igual al factor de hora pico por el tránsito diario.
    La distancia y el tránsito son datos; lo demás son supuestos del equipo.</p>
    <div class="dos-col"><div class="tabla-scroll"><table><thead><tr><th>Insumo</th><th class="n">Valor</th><th>Estado</th></tr></thead><tbody>
      <tr><td>Velocidad libre</td><td class="n">${c.velocidad_libre_kmh} km/h</td><td><span class="insignia amb">supuesto</span></td></tr>
      <tr><td>α y β de la función BPR</td><td class="n">${fmt(c.bpr_alfa, 2)} y ${c.bpr_beta}</td><td><span class="insignia amb">supuesto</span></td></tr>
      <tr><td>Factor de hora pico</td><td class="n">${fmt(c.factor_hora_pico, 2)}</td><td><span class="insignia amb">supuesto</span></td></tr>
      <tr><td>Capacidad, calzada sencilla</td><td class="n">${fmt(c.capacidad_calzada_sencilla_veh_h)} veh/h</td><td><span class="insignia amb">supuesto</span></td></tr>
      <tr><td>Capacidad, doble calzada</td><td class="n">${fmt(c.capacidad_doble_calzada_veh_h)} veh/h</td><td><span class="insignia amb">supuesto</span></td></tr>
      <tr><td>Doble calzada (razón digitalizada / registrada)</td><td class="n">${fmt(c.banda_doble_calzada[0], 1)} a ${fmt(c.banda_doble_calzada[1], 1)}</td><td><span class="insignia ok">dato del proyecto</span></td></tr>
    </tbody></table></div>
    <div class="tabla-scroll"><table><thead><tr><th>Resultado</th><th class="n">Valor</th></tr></thead><tbody>
      <tr><td>Tramos con serie vigente, terminada y sin dato</td><td class="n">${red.vigente}, ${red.historico} y ${red.sin_dato}</td></tr>
      <tr><td>Saturación mediana y máxima observadas</td><td class="n">${fmt(t.saturacion_mediana, 2)} y ${fmt(t.saturacion_maxima, 2)}</td></tr>
      <tr><td>Mayor demora de un tramo en un mes</td><td class="n">${fmt(t.demora_maxima_min, 2)} min</td></tr>
      <tr><td>Tramo y mes de esa demora</td><td class="n">${esc(t.tramo_factor_maximo)}, ${esc(t.mes_factor_maximo)}</td></tr>
      <tr><td>Error medio del tiempo en la prueba</td><td class="n">${fmt(t.mae_min, 3)} min</td></tr>
    </tbody></table></div></div>
    <p class="parrafo">Con promedios mensuales la saturación queda lejos de 1 y la demora es de pocos minutos:
    el orden de las rutas por tiempo es el de la distancia. Lo que sí cambia de un mes a otro es el nivel de tránsito de cada tramo.</p>`;
}

function activarPestana(id) {
  ["regresion", "clasificacion", "agrupamiento", "supuestos"].forEach((t) => {
    const activa = t === id;
    $(`tab-b-${t}`).setAttribute("aria-selected", String(activa));
    $(`tab-b-${t}`).tabIndex = activa ? 0 : -1;
    $(`tab-${t}`).hidden = !activa;
  });
}

/* ---- flujo --------------------------------------------------------------- */
function poblarControles() {
  const grupo = (titulo, meses) => `<optgroup label="${titulo}">${
    meses.map((m) => `<option value="${m}">${nombreMes(m)}</option>`).join("")}</optgroup>`;
  $("sel-mes").innerHTML = grupo("Pronóstico", S.resumen.meses_pronostico)
    + grupo("Periodo de prueba (hay dato observado)", S.resumen.meses_prueba);
  S.mes = S.resumen.meses_pronostico[0];
  $("sel-mes").value = S.mes;
}
function poblarCiudades() {
  const opciones = S.red.nodos.map((n) => `<option>${esc(n.nombre)}</option>`).join("");
  $("sel-origen").innerHTML = opciones;
  $("sel-destino").innerHTML = opciones;
  $("sel-origen").value = S.origen;
  $("sel-destino").value = S.destino;
}

async function calcular() {
  aviso("");
  try {
    S.red = await api("/api/aprendizaje/red", {mes: S.mes});
    if (!mapa) { construirMapa(); poblarCiudades(); }
    S.ruta = S.origen === S.destino ? null
      : await api("/api/aprendizaje/ruta", {origen: S.origen, destino: S.destino, mes: S.mes});
    if (!S.ruta) aviso("El origen y el destino son la misma ciudad.");
    pintarMapa();
    pintarRuta();
    $("nota-mes").textContent = S.red.es_pronostico
      ? "Mes futuro: el tránsito sale del pronóstico recursivo del modelo."
      : "Mes del periodo de prueba: el tránsito es la predicción a un mes; al pasar por un tramo se ve también el observado.";
    $("caso-activo").textContent = `${S.origen} a ${S.destino}, ${nombreMes(S.mes)}`;
  } catch (e) {
    aviso(e.message);
  }
}

async function iniciar() {
  aplicarTema(document.documentElement.dataset.tema || "oscuro");
  try {
    S.resumen = await api("/api/aprendizaje/resumen");
  } catch (e) {
    aviso(e.message);
    $("caso-activo").textContent = "Sin resultados de aprendizaje automático";
    return;
  }
  poblarControles();
  pintarRegresion();
  pintarClasificacion();
  pintarAgrupamiento();
  pintarSupuestos();
  await calcular();
  $("sel-mes").addEventListener("change", (ev) => { S.mes = ev.target.value; calcular(); });
  $("sel-origen").addEventListener("change", (ev) => { S.origen = ev.target.value; calcular(); });
  $("sel-destino").addEventListener("change", (ev) => { S.destino = ev.target.value; calcular(); });
  $("btn-calcular").addEventListener("click", calcular);
  $("btn-tema").addEventListener("click", () =>
    aplicarTema(document.documentElement.dataset.tema === "claro" ? "oscuro" : "claro"));
  $("chk-sinfondo").addEventListener("change", (ev) => {
    if (ev.target.checked) mapa.removeLayer(capaMosaicos); else capaMosaicos.addTo(mapa);
  });
  ["regresion", "clasificacion", "agrupamiento", "supuestos"].forEach((t) =>
    $(`tab-b-${t}`).addEventListener("click", () => activarPestana(t)));
  window.addEventListener("resize", () => mapa && mapa.invalidateSize());
}

iniciar();
