/* Visualizador de rutas de carga.
   El navegador solo dibuja: toda búsqueda, costo y métrica se calcula en
   Python (API de servidor.py). Aquí se presentan, paso a paso. */
(function () {
"use strict";

/* ====================== utilidades ====================== */
const $ = (id) => document.getElementById(id);
const ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"};
const esc = (t) => String(t == null ? "" : t).replace(/[&<>"']/g, (c) => ESC[c]);
const NBSP = " ";

function fmt(n, dec) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const d = dec == null ? 0 : dec;
  const [ent, fra] = Number(n).toFixed(d).split(".");
  const signo = ent.startsWith("-") ? "-" : "";
  const grupos = ent.replace("-", "").replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);
  return signo + grupos + (fra ? "." + fra : "");
}
function fmtHoras(h) {
  if (!Number.isFinite(h)) return "—";
  const total = Math.round(h * 60);
  const hh = Math.floor(total / 60);
  const mm = total % 60;
  const u = (t) => `<small>${t}</small>`;
  return hh > 0 ? `${hh}${u("h")} ${String(mm).padStart(2, "0")}${u("min")}` : `${mm}${u("min")}`;
}
const reducirMovimiento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const par = (u, v) => (u < v ? `${u}|${v}` : `${v}|${u}`);

async function api(ruta, params, cuerpo) {
  const url = ruta + (params ? "?" + new URLSearchParams(params) : "");
  const opciones = cuerpo
    ? {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(cuerpo)}
    : undefined;
  const r = await fetch(url, opciones);
  let datos = null;
  try { datos = await r.json(); } catch (e) { datos = null; }
  if (!r.ok) throw new Error((datos && typeof datos.detail === "string" && datos.detail) || `Error ${r.status} del servidor.`);
  return datos;
}

function aviso(texto) {
  const caja = $("aviso");
  if (!texto) { caja.hidden = true; caja.textContent = ""; return; }
  caja.textContent = texto;
  caja.hidden = false;
}

/* ====================== estado ====================== */
const TIPOS = {
  a: "Origen a destino: una sola ruta.",
  b: "Paradas en orden fijo: se visitan en el orden de los clics y se termina en el destino.",
  c: "Paradas obligatorias en orden libre entre origen y destino, y/o aristas bloqueadas (mayús + clic marca obligatorias).",
  d: "Orden libre de las paradas con regreso al origen.",
  e: "Orden libre de las paradas sin regreso al origen.",
};
const VELOCIDADES = [0.5, 1, 2, 3, 4, 6, 8, 12];
const COLORES_ESTADO = ["frontera", "expandido", "actual", "meta", "ruta"];

const S = {
  red: null, modo: "ruta", fase: "busqueda",
  origen: "Duitama", destino: "Puente Nacional",
  criterio: "distancia", algoritmo: "astar",
  busqueda: null, comparar: null, criterios: null, despacho: null,
  paso: 0, tramo: 0, jugando: false, temporizador: null, velocidad: 3,
  velKmh: 50, mostrarH: false, sinFondo: false,
  tipo: "d", idaVuelta: false, modoBloqueo: false,
  libres: [], obligatorias: [], bloqueados: new Set(),
  ultimoExtremo: "destino", token: 0, hover: null, encuadreAuto: true,
  aristasRuta: [], piernas: [], tiempoFin: [], caso: "",
};

/* ====================== tema ====================== */
function aplicarTema(tema) {
  document.documentElement.dataset.tema = tema;
  $("btn-tema").setAttribute("aria-pressed", String(tema === "claro"));
  $("btn-tema-txt").textContent = tema === "claro" ? "Modo oscuro" : "Modo claro";
  try { localStorage.setItem("tema", tema); } catch (e) { /* sin almacenamiento */ }
}

/* ====================== datos de la red ====================== */
const NODO = {};      // nombre -> {nombre, latitud, longitud}
const ARISTA = {};    // clave -> arista del servidor

function indexarRed() {
  S.red.nodos.forEach((n) => { NODO[n.nombre] = n; });
  S.red.aristas.forEach((a) => { ARISTA[par(a.u, a.v)] = a; });
}

function poblarSelects() {
  const nombres = S.red.nodos.map((n) => n.nombre);
  for (const id of ["sel-origen", "sel-destino"]) {
    $(id).innerHTML = nombres.map((n) => `<option value="${esc(n)}">${esc(n)}</option>`).join("");
  }
  $("sel-criterio").innerHTML = Object.entries(S.red.criterios)
    .map(([c, d]) => `<option value="${esc(c)}" title="${esc(d.descripcion)}">${esc(c.replace(/_/g, " "))}${d.limitado ? " (limitado)" : ""}</option>`).join("");
  $("sel-algoritmo").innerHTML = Object.entries(S.red.algoritmos)
    .map(([k, v]) => `<option value="${esc(k)}">${esc(v)}</option>`).join("");
  $("sel-tipo").innerHTML = Object.entries(S.red.tipos)
    .map(([k, v]) => `<option value="${esc(k)}">${esc(k)}: ${esc(v.replace(/_/g, " "))}</option>`).join("");
  $("ejemplos").innerHTML = S.red.ejemplos.map((e) =>
    `<button type="button" class="chip" data-ejemplo="${esc(e.id)}" title="${esc(e.detalle)}">${esc(e.titulo)}${e.id === "diecinueve" || e.id === "veinte" ? " <small>demostración</small>" : ""}</button>`).join("");
  sincronizarControles();
}

function sincronizarControles() {
  if (typeof encuadrar === "function") requestAnimationFrame(() => encuadrar(false));
  $("sel-origen").value = S.origen;
  $("sel-destino").value = S.destino || S.red.nodos[0].nombre;
  $("sel-criterio").value = S.criterio;
  $("sel-algoritmo").value = S.algoritmo;
  $("sel-tipo").value = S.tipo;
  $("chk-ida-vuelta").checked = S.idaVuelta;
  $("desc-tipo").textContent = TIPOS[S.tipo];
  const desp = S.modo === "despachador";
  $("campo-algoritmo").hidden = desp;
  $("campo-destino").hidden = desp && (S.tipo === "d" || S.tipo === "e");
  $("grupo-despachador").hidden = !desp;
  $("chk-ida-vuelta").disabled = !(S.tipo === "a" || S.tipo === "b" || S.tipo === "c");
  $("fase-busqueda").disabled = desp;
  $("modo-ruta").checked = !desp;
  $("modo-desp").checked = desp;
  $("btn-bloqueo").setAttribute("aria-pressed", String(S.modoBloqueo));
  pintarContador();
}

/* ====================== vista derivada del paso ====================== */
const fc = (x) => (x == null ? "—" : x === 0 ? "0" : x >= 1000 ? fmt(x, 0) : x >= 10 ? fmt(x, 2) : fmt(x, 3));
const ESTADO_TXT = {
  libre: "sin explorar", frontera: "en la frontera", expandido: "expandido",
  actual: "extraído ahora", meta: "meta alcanzada", ruta: "en la ruta",
  "parada-libre": "parada libre", "parada-obligatoria": "parada obligatoria",
};

/* Estado de cada entrada, ciudad y arista en el paso actual (solo búsqueda). */
function vistaBusqueda() {
  const b = S.busqueda;
  if (!b) return null;
  const p = S.fase === "ruta" ? b.pasos.length - 1 : S.paso;
  const entradas = b.entradas.map((e) => {
    if (e.creado > p) return null;
    if (e.extraido == null || e.extraido > p) return "frontera";
    if (e.extraido === p) return e.resultado === "meta" ? "meta" : "actual";
    return e.resultado;
  });
  const paso = b.pasos[p];
  const actualId = p === 0 ? 0 : paso.extraida;
  const rama = [];
  for (let i = actualId; i != null; i = b.entradas[i].padre) rama.push(i);
  rama.reverse();
  const ciudades = {};
  const rango = {actual: 6, meta: 5, frontera: 4, expandido: 3, descartado: 1};
  b.entradas.forEach((e, i) => {
    const s = entradas[i];
    if (!s) return;
    const previo = ciudades[e.ciudad];
    if (!previo || rango[s] > rango[previo]) ciudades[e.ciudad] = s;
  });
  const aristas = {};
  b.entradas.forEach((e, i) => {
    if (entradas[i] && e.padre != null) aristas[par(e.ciudad, b.entradas[e.padre].ciudad)] = "ar-exp";
  });
  for (let i = 1; i < rama.length; i++) {
    aristas[par(b.entradas[rama[i]].ciudad, b.entradas[rama[i - 1]].ciudad)] = "ar-prov";
  }
  return {p, paso, entradas, rama, ciudades, aristas, actualId};
}

/* Número de aristas de la ruta ya dibujadas en la fase «construir ruta». */
function tramosVisibles() {
  if (S.modo === "despachador" || S.fase === "ruta") return S.tramo;
  return 0;
}

/* ====================== mapa ====================== */
let mapa = null;
let capaMosaicos = null;
let mosaicosOk = 0;
let mosaicosError = 0;
let capaRuta = null;
let capaOrden = null;
const marcadores = {};
const capasArista = {};
let elementosRuta = [];
let marcadoresOrden = [];

function ll(nombre) { return [NODO[nombre].latitud, NODO[nombre].longitud]; }

function fijarFondo(sin, motivo) {
  S.sinFondo = sin;
  $("chk-sinfondo").checked = sin;
  if (sin && mapa.hasLayer(capaMosaicos)) mapa.removeLayer(capaMosaicos);
  if (!sin && !mapa.hasLayer(capaMosaicos)) { mosaicosOk = 0; mosaicosError = 0; capaMosaicos.addTo(mapa); }
  if (motivo) aviso(motivo);
}

/* Tamaño real del contenedor y encuadre de la red completa. invalidateSize
   recalcula el origen de píxeles de Leaflet; fitBounds se aplica después, y
   solo mientras la persona no haya movido o acercado el mapa a mano. */
let encuadrando = false;
function encuadrar(forzar) {
  if (!mapa) return;
  mapa.invalidateSize({pan: false});
  if (forzar) S.encuadreAuto = true;
  if (!S.encuadreAuto) { reubicarRotulos(); return; }
  encuadrando = true;
  mapa.fitBounds(S.red.nodos.map((n) => [n.latitud, n.longitud]), {padding: [40, 40], animate: false});
  encuadrando = false;
  reubicarRotulos();
}
let temporizadorTam = null;
function alCambiarTamano() {
  clearTimeout(temporizadorTam);
  temporizadorTam = setTimeout(() => encuadrar(false), 80);
}

function construirMapa() {
  mapa = L.map("mapa", {zoomControl: false, zoomSnap: 0.25, keyboard: false, zoomAnimation: !reducirMovimiento,
                        fadeAnimation: !reducirMovimiento});
  L.control.zoom({position: "bottomright", zoomInTitle: "Acercar", zoomOutTitle: "Alejar"}).addTo(mapa);
  mapa.attributionControl.setPrefix(false);
  mapa.createPane("aristas").style.zIndex = 420;
  mapa.createPane("ruta").style.zIndex = 430;
  capaMosaicos = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>',
  });
  capaMosaicos.on("tileload", () => { mosaicosOk++; });
  capaMosaicos.on("tileerror", () => {
    mosaicosError++;
    if (mosaicosOk === 0 && mosaicosError >= 4 && !S.sinFondo) {
      fijarFondo(true, "Sin conexión: se omitió el fondo de OpenStreetMap. La red se dibuja igual.");
    }
  });
  capaMosaicos.addTo(mapa);
  mapa.fitBounds(S.red.nodos.map((n) => [n.latitud, n.longitud]), {padding: [40, 40], animate: false});
  mapa.on("dragstart zoomstart", () => { if (!encuadrando) S.encuadreAuto = false; });

  S.red.aristas.forEach((a) => {
    const pts = [ll(a.u), ll(a.v)];
    const vis = L.polyline(pts, {pane: "aristas", className: "ar", weight: 3, interactive: false}).addTo(mapa);
    const hit = L.polyline(pts, {pane: "aristas", className: "ar-hit", weight: 18, opacity: 0.001}).addTo(mapa);
    hit.bindTooltip(() => htmlArista(a), {className: "tip", sticky: true, direction: "top"});
    hit.on("mouseover", () => vis.getElement().classList.add("ar-sel"));
    hit.on("mouseout", () => vis.getElement().classList.remove("ar-sel"));
    hit.on("click", () => { if (S.modo === "despachador" && S.modoBloqueo) alternarBloqueo(a.u, a.v); });
    hit.on("contextmenu", (ev) => {
      L.DomEvent.preventDefault(ev.originalEvent);
      if (S.modo === "despachador") alternarBloqueo(a.u, a.v);
    });
    capasArista[par(a.u, a.v)] = {vis, hit};
  });

  S.red.nodos.forEach((n) => {
    const icono = L.divIcon({className: "nd", iconSize: null,
      html: '<span class="nd-f"></span><span class="rot lado-d"></span>'});
    const m = L.marker(ll(n.nombre), {icon: icono, keyboard: true, riseOnHover: false}).addTo(mapa);
    m.bindTooltip(() => htmlNodo(n.nombre), {className: "tip", direction: "top", offset: [0, -12]});
    m.on("click", (ev) => onNodoClick(n.nombre, ev.originalEvent && ev.originalEvent.shiftKey));
    m.on("mouseover", () => resaltar(n.nombre));
    m.on("mouseout", () => resaltar(null));
    const el = m.getElement();
    el.setAttribute("role", "button");
    el.setAttribute("aria-label", n.nombre);
    el.querySelector(".rot").textContent = n.nombre;
    marcadores[n.nombre] = m;
  });
  mapa.on("zoomend moveend resize", reubicarRotulos);
  actualizarGrosores();
  // lectura para la verificación automática del mapa (pruebas/verificar_mapa.js)
  window.VISUALIZADOR = {mapa, marcadores, capasArista};
}

function htmlArista(a) {
  const bloqueada = S.bloqueados.has(par(a.u, a.v));
  const piso = a.piso
    ? `con piso geodésico (oficial <span class="n">${fmt(a.distancia_oficial_km, 2)} km</span>)`
    : "sin piso geodésico";
  return `<b>${esc(a.u)} – ${esc(a.v)}</b><br>Distancia del modelo: <span class="n">${fmt(a.distancia_km, 2)} km</span>, ${piso}`
    + `<br>Peaje: ${a.peaje_cop > 0 ? `${esc(a.peaje_nombre)}, <span class="n">${fmt(a.peaje_cop)} COP</span>` : "sin peaje"}`
    + `<br>Riesgo (GiZScore): ${a.riesgo == null ? "sin dato" : `<span class="n">${fmt(a.riesgo, 2)}</span>`}`
    + (bloqueada ? "<br><b>Bloqueada para el despachador</b>" : "");
}

function estadoNodo(nombre) {
  if (S.modo === "despachador") {
    if (S.obligatorias.includes(nombre)) return "parada-obligatoria";
    if (S.libres.includes(nombre)) return "parada-libre";
    if (enRutaVisible(nombre)) return "ruta";
    return "libre";
  }
  if (S.fase === "ruta" && enRutaVisible(nombre)) return "ruta";
  const V = S.vista;
  return (V && V.ciudades[nombre] && V.ciudades[nombre] !== "descartado") ? V.ciudades[nombre] : "libre";
}

function enRutaVisible(nombre) {
  const n = tramosVisibles();
  for (let i = 0; i < n && i < S.aristasRuta.length; i++) {
    const r = S.aristasRuta[i];
    if (r.desde === nombre || r.hasta === nombre) return true;
  }
  return false;
}

function rolNodo(nombre) {
  if (nombre === S.origen) return "origen";
  if (nombre === S.destino && !(S.modo === "despachador" && (S.tipo === "d" || S.tipo === "e"))) return "destino";
  return "";
}

function htmlNodo(nombre) {
  const e = estadoNodo(nombre);
  let txt = `<b>${esc(nombre)}</b><br>${esc(ESTADO_TXT[e] || e)}`;
  const rol = rolNodo(nombre);
  if (rol) txt += ` · ${rol}`;
  if (S.busqueda && S.busqueda.h[nombre] != null && S.modo === "ruta") {
    txt += `<br>h(n) = <span class="n">${fc(S.busqueda.h[nombre])}</span>`;
  }
  return txt;
}

function actualizarGrosores() {
  const c = S.criterio;
  const tope = Math.max(...S.red.aristas.map((a) => a.costos[c]));
  S.red.aristas.forEach((a) => {
    const w = 2 + 4 * (tope > 0 ? a.costos[c] / tope : 0);
    capasArista[par(a.u, a.v)].vis.setStyle({weight: w});
  });
}

function prioridadNodo(nombre, estado) {
  if (rolNodo(nombre)) return 100;
  const base = {actual: 90, ruta: 80, "parada-libre": 75, "parada-obligatoria": 75, meta: 70, frontera: 60, expandido: 40, libre: 10};
  return base[estado] || 10;
}

function pintarMapa(animar) {
  const V = S.vista;
  for (const [clave, capas] of Object.entries(capasArista)) {
    const el = capas.vis.getElement();
    let clases = "ar";
    if (S.modo === "ruta" && V && V.aristas[clave]) clases += " " + V.aristas[clave];
    if (S.bloqueados.has(clave)) clases += " ar-bloq";
    el.setAttribute("class", clases);
  }
  for (const nombre of Object.keys(marcadores)) {
    const el = marcadores[nombre].getElement();
    const estado = estadoNodo(nombre);
    el.dataset.e = estado;
    el.dataset.r = rolNodo(nombre);
    el.style.zIndex = 400 + prioridadNodo(nombre, estado);
    const rot = el.querySelector(".rot");
    const h = S.busqueda && S.mostrarH && S.modo === "ruta" ? S.busqueda.h[nombre] : null;
    rot.innerHTML = esc(nombre) + (h != null ? `<span class="h">h ${fc(h)}</span>` : "");
  }
  pintarRutaMapa(animar);
  reubicarRotulos();
}

/* Rótulos sin montarse. Al alejar solo se muestran los relevantes (origen,
   destino, paradas, ruta, extraído y frontera); al acercar, todos. Cada uno
   prueba ocho posiciones alrededor de su nodo, de mayor a menor prioridad, y
   se oculta si ninguna queda libre (salvo origen, destino y el nodo actual). */
const ZOOM_TODOS = 8.5;
const PRIORIDAD_RELEVANTE = 60;
function reubicarRotulos() {
  if (!mapa) return;
  const todos = mapa.getZoom() >= ZOOM_TODOS;
  const info = Object.keys(marcadores).map((nombre) => {
    const el = marcadores[nombre].getElement();
    const rot = el.querySelector(".rot");
    rot.hidden = false;
    rot.className = "rot lado-d";
    return {nombre, rot, p: mapa.latLngToContainerPoint(marcadores[nombre].getLatLng()),
            prio: prioridadNodo(nombre, el.dataset.e), w: rot.offsetWidth, h: rot.offsetHeight};
  });
  const tam = mapa.getSize();
  const radio = 14;
  const aire = 2;
  const ocupados = info.map((i) => ({x0: i.p.x - radio, y0: i.p.y - radio, x1: i.p.x + radio, y1: i.p.y + radio, dueno: i.nombre}));
  const choca = (r, dueno) => ocupados.some((o) => o.dueno !== dueno
    && r.x0 < o.x1 + aire && r.x1 + aire > o.x0 && r.y0 < o.y1 + aire && r.y1 + aire > o.y0);
  const lados = [
    ["lado-d", (i) => ({x0: i.p.x + radio, y0: i.p.y - i.h / 2, x1: i.p.x + radio + i.w, y1: i.p.y + i.h / 2})],
    ["lado-i", (i) => ({x0: i.p.x - radio - i.w, y0: i.p.y - i.h / 2, x1: i.p.x - radio, y1: i.p.y + i.h / 2})],
    ["lado-s", (i) => ({x0: i.p.x - i.w / 2, y0: i.p.y - radio - i.h, x1: i.p.x + i.w / 2, y1: i.p.y - radio})],
    ["lado-n", (i) => ({x0: i.p.x - i.w / 2, y0: i.p.y + radio, x1: i.p.x + i.w / 2, y1: i.p.y + radio + i.h})],
    ["lado-ne", (i) => ({x0: i.p.x + radio, y0: i.p.y - radio - i.h, x1: i.p.x + radio + i.w, y1: i.p.y - radio})],
    ["lado-se", (i) => ({x0: i.p.x + radio, y0: i.p.y + radio, x1: i.p.x + radio + i.w, y1: i.p.y + radio + i.h})],
    ["lado-no", (i) => ({x0: i.p.x - radio - i.w, y0: i.p.y - radio - i.h, x1: i.p.x - radio, y1: i.p.y - radio})],
    ["lado-so", (i) => ({x0: i.p.x - radio - i.w, y0: i.p.y + radio, x1: i.p.x - radio, y1: i.p.y + radio + i.h})],
  ];
  const dentro = (r) => r.x0 >= 0 && r.y0 >= 0 && r.x1 <= tam.x && r.y1 <= tam.y;
  info.sort((a, b) => (b.prio - a.prio) || (a.nombre < b.nombre ? -1 : 1)).forEach((i) => {
    if (!todos && i.prio < PRIORIDAD_RELEVANTE) { i.rot.hidden = true; return; }
    let puesto = null;
    for (const [clase, caja] of lados) {
      const r = caja(i);
      if (dentro(r) && !choca(r, i.nombre)) { puesto = [clase, r]; break; }
    }
    if (!puesto && i.prio >= 90) puesto = [lados[0][0], lados[0][1](i)];
    if (puesto) {
      i.rot.className = "rot " + puesto[0];
      ocupados.push(Object.assign({dueno: "r" + i.nombre}, puesto[1]));
    } else {
      i.rot.hidden = true;
    }
  });
}

function resaltar(ciudad) {
  S.hover = ciudad;
  for (const [nombre, m] of Object.entries(marcadores)) m.getElement().classList.toggle("resaltado", nombre === ciudad);
  for (const caja of S.cajas || []) caja.g.classList.toggle("resaltado", caja.ciudad === ciudad);
}

/* ---- ruta dibujada tramo por tramo y marcadores de orden ---- */
function construirCapaRuta() {
  if (capaRuta) capaRuta.remove();
  if (capaOrden) capaOrden.remove();
  capaRuta = L.layerGroup().addTo(mapa);
  capaOrden = L.layerGroup().addTo(mapa);
  elementosRuta = S.aristasRuta.map((r) => L.polyline([ll(r.desde), ll(r.hasta)], {
    pane: "ruta", weight: 6, interactive: false,
    className: `ar-ruta pierna-${(r.pierna % 6) + 1} oculto`}).addTo(capaRuta));
  marcadoresOrden = [];
  if (S.modo === "despachador" && S.despacho && S.piernas.length) {
    const orden = S.piernas.map((p) => p.desde).concat([S.piernas[S.piernas.length - 1].hasta]);
    const porCiudad = {};
    orden.forEach((c, i) => { (porCiudad[c] = porCiudad[c] || []).push(i + 1); });
    for (const [ciudad, nums] of Object.entries(porCiudad)) {
      const mk = L.marker(ll(ciudad), {interactive: false, zIndexOffset: 1500,
        icon: L.divIcon({className: "ord", iconSize: null, html: `<span class="orden">${nums.join(", ")}</span>`})});
      mk.addTo(capaOrden);
      marcadoresOrden.push({mk, minimo: Math.min(...nums)});
    }
  }
}

function paradaAlcanzada(indice) {
  // la parada número `indice` (base 1) se alcanza al terminar su pierna anterior
  if (indice <= 1) return true;
  const fin = S.tiempoFin[indice - 2];
  return fin != null && tramosVisibles() >= fin;
}

function pintarRutaMapa(animar) {
  const n = tramosVisibles();
  elementosRuta.forEach((pl, i) => {
    const el = pl.getElement();
    if (!el) return;
    el.classList.toggle("oculto", i >= n);
    if (animar && !reducirMovimiento && i === n - 1) {
      el.style.setProperty("--largo", String(el.getTotalLength()));
      el.classList.remove("dibujando");
      void el.getBoundingClientRect();
      el.classList.add("dibujando");
    } else {
      el.classList.remove("dibujando");
    }
  });
  marcadoresOrden.forEach((o) => o.mk.setOpacity(paradaAlcanzada(o.minimo) ? 1 : 0));
}

/* ====================== árbol de búsqueda ====================== */
const GX = 40;
const GY = 14;
const MARGEN = 16;
const ALTO_CAJA = 66;
const SVGNS = "http://www.w3.org/2000/svg";

function svgEl(tag, atributos, padre) {
  const el = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(atributos || {})) el.setAttribute(k, v);
  if (padre) padre.appendChild(el);
  return el;
}

function textosCaja(e) {
  const a = S.busqueda.algoritmo;
  const paso = `paso ${e.creado}`;
  if (a === "astar") return [`g ${fc(e.g)} + h ${fc(e.h)}`, `f = ${fc(e.f)}`];
  if (a === "voraz") return [`h = ${fc(e.h)}`, `g ${fc(e.g)} · ${paso}`];
  if (a === "ucs") return [`g = f = ${fc(e.g)}`, paso];
  return [`g ${fc(e.g)}`, paso];
}

function glifo(estado, cx, cy) {
  if (estado === "frontera") return `M${cx} ${cy - 6}L${cx + 6} ${cy}L${cx} ${cy + 6}L${cx - 6} ${cy}Z`;
  if (estado === "meta") return `M${cx - 5} ${cy - 5}h10v10h-10Z`;
  if (estado === "descartado") return `M${cx - 5} ${cy - 5}L${cx + 5} ${cy + 5}M${cx + 5} ${cy - 5}L${cx - 5} ${cy + 5}`;
  return `M${cx - 6} ${cy}a6 6 0 1 0 12 0a6 6 0 1 0 -12 0`;
}

function construirArbol() {
  const svg = $("arbol-svg");
  svg.innerHTML = "";
  S.cajas = [];
  S.enlaces = [];
  const b = S.busqueda;
  $("arbol-vacio").hidden = !!b;
  if (!b) {
    svg.setAttribute("width", "0");
    svg.setAttribute("height", "0");
    $("arbol-vacio").textContent = S.modo === "despachador"
      ? "El despachador resuelve cada tramo con A* o UCS y ordena las paradas con Held-Karp o ACO; no hay un árbol único que mostrar. Use «Una ruta» para ver la búsqueda."
      : "Calculando…";
    $("arbol-nota").textContent = "";
    return;
  }
  const hijos = b.entradas.map(() => []);
  b.entradas.forEach((e) => { if (e.padre != null) hijos[e.padre].push(e.id); });
  const textos = b.entradas.map(textosCaja);
  const letras = Math.max(...b.entradas.map((e, i) => Math.max(e.ciudad.length + 4, ...textos[i].map((t) => t.length))));
  const ancho = Math.max(160, Math.ceil(letras * 8.8) + 36);
  const pos = [];
  let fila = 0;
  let profMax = 0;
  const colocar = (id, prof) => {
    profMax = Math.max(profMax, prof);
    let y;
    if (!hijos[id].length) { y = fila; fila += 1; }
    else {
      hijos[id].forEach((h) => colocar(h, prof + 1));
      y = (pos[hijos[id][0]].fila + pos[hijos[id][hijos[id].length - 1]].fila) / 2;
    }
    pos[id] = {fila: y, x: MARGEN + prof * (ancho + GX), y: MARGEN + y * (ALTO_CAJA + GY)};
  };
  colocar(0, 0);
  svg.setAttribute("width", MARGEN * 2 + (profMax + 1) * (ancho + GX) - GX);
  svg.setAttribute("height", MARGEN * 2 + fila * (ALTO_CAJA + GY) - GY);

  b.entradas.forEach((e) => {
    if (e.padre == null) return;
    const p = pos[e.padre];
    const q = pos[e.id];
    const x1 = p.x + ancho;
    const y1 = p.y + ALTO_CAJA / 2;
    const y2 = q.y + ALTO_CAJA / 2;
    const camino = svgEl("path", {class: "arbol-enlace oculto",
      d: `M${x1} ${y1}C${x1 + GX / 2} ${y1} ${q.x - GX / 2} ${y2} ${q.x} ${y2}`}, svg);
    S.enlaces.push({id: e.id, padre: e.padre, el: camino});
  });
  b.entradas.forEach((e) => {
    const q = pos[e.id];
    const g = svgEl("g", {class: "cj oculto", transform: `translate(${q.x} ${q.y})`, tabindex: "0", role: "button"}, svg);
    svgEl("rect", {class: "cj-caja", width: ancho, height: ALTO_CAJA, rx: 8}, g);
    const ciudad = svgEl("text", {class: "cj-ciudad", x: 12, y: 21}, g);
    ciudad.textContent = e.ciudad;
    textos[e.id].forEach((t, i) => {
      const linea = svgEl("text", {class: "cj-dato", x: 12, y: 40 + i * 18}, g);
      linea.textContent = t;
    });
    const marca = svgEl("path", {class: "cj-glifo", d: glifo("frontera", ancho - 18, 16)}, g);
    const titulo = svgEl("title", {}, g);
    titulo.textContent = `${e.ciudad}: g ${fc(e.g)}${e.h != null ? `, h ${fc(e.h)}` : ""}${e.f != null ? `, f ${fc(e.f)}` : ""}; creada en el paso ${e.creado}`
      + (e.extraido != null ? `; extraída en el paso ${e.extraido} (${e.resultado})` : "; nunca salió de la frontera");
    g.addEventListener("mouseenter", () => resaltar(e.ciudad));
    g.addEventListener("mouseleave", () => resaltar(null));
    const ir = () => { pausar(); S.fase = "busqueda"; S.paso = e.extraido != null ? e.extraido : e.creado; render(); };
    g.addEventListener("click", ir);
    g.addEventListener("keydown", (ev) => { if (ev.key === "Enter") ir(); });
    S.cajas.push({id: e.id, ciudad: e.ciudad, g, marca, ancho, x: q.x, y: q.y});
  });
  $("arbol-nota").textContent = `${b.entradas.length} cajas, una por entrada de la frontera. Borde punteado: en la frontera. Tachada: descartada.`;
}

function pintarArbol() {
  const V = S.vista;
  if (!V || !S.cajas) return;
  const rama = new Set(V.rama);
  S.cajas.forEach((c) => {
    const estado = V.entradas[c.id];
    c.g.classList.toggle("oculto", !estado);
    if (!estado) return;
    c.g.dataset.e = estado;
    c.g.classList.toggle("rama", rama.has(c.id));
    c.marca.setAttribute("d", glifo(estado, c.ancho - 18, 16));
  });
  S.enlaces.forEach((l) => {
    l.el.classList.toggle("oculto", !V.entradas[l.id]);
    l.el.classList.toggle("rama", rama.has(l.id) && rama.has(l.padre));
  });
  const actual = S.cajas[V.actualId];
  const caja = $("arbol");
  if (actual && V.p > 0) {
    const izq = actual.x - caja.clientWidth / 2 + actual.ancho / 2;
    const arriba = actual.y - caja.clientHeight / 2 + ALTO_CAJA / 2;
    caja.scrollTo({left: Math.max(0, izq), top: Math.max(0, arriba), behavior: reducirMovimiento ? "auto" : "smooth"});
  }
}

/* ====================== explicación de cada paso ====================== */
function claveSalida(b, e) {
  if (b.algoritmo === "astar") return {nombre: "f", valor: e.f};
  if (b.algoritmo === "voraz") return {nombre: "h", valor: e.h};
  return {nombre: "g", valor: e.g};
}
const lista = (ids, b) => ids.map((i) => `${esc(b.entradas[i].ciudad)} (g ${fc(b.entradas[i].g)})`).join(", ");

function fraseDePaso(b, p) {
  const paso = b.pasos[p];
  if (p === 0) {
    return `<strong>Inicio.</strong> ${esc(b.origen)} entra a la frontera con g = 0. `
      + `La prueba de meta se hace al <em>extraer</em> un nodo, no al generarlo.`;
  }
  const e = b.entradas[paso.extraida];
  const antes = b.pasos[p - 1].frontera.map((i) => b.entradas[i]);
  let porque = "";
  if (b.algoritmo === "bfs") porque = "es la entrada más antigua de la cola (primero en entrar, primero en salir)";
  else if (b.algoritmo === "dfs") porque = "es la última apilada (el último en entrar es el primero en salir)";
  else {
    const k = claveSalida(b, e);
    const etiqueta = b.algoritmo === "ucs" ? "el menor costo acumulado g"
      : b.algoritmo === "voraz" ? "la menor h" : "la menor f = g + h";
    const detalle = b.algoritmo === "astar" ? `${fc(e.g)} + ${fc(e.h)} = ${fc(e.f)}` : fc(k.valor);
    const empatadas = antes.filter((x) => claveSalida(b, x).valor === k.valor).length;
    porque = `tiene ${etiqueta} (${detalle})`
      + (empatadas > 1 ? `; empata con ${empatadas - 1} más y gana la de inserción más antigua` : "");
  }
  const base = `<strong>Paso ${p}.</strong> Sale ${esc(e.ciudad)} porque ${porque}. `;
  if (paso.resultado === "meta") {
    return base + `<strong>Es la meta:</strong> la búsqueda termina. Ruta ${b.ruta.map(esc).join(" › ")}, costo ${fc(b.costo)}.`;
  }
  if (paso.resultado === "descartado") {
    const motivo = b.algoritmo === "dfs" ? "la ciudad ya fue visitada"
      : b.algoritmo === "voraz" ? "la ciudad ya fue expandida"
      : "es una entrada vieja: ya se encontró un costo menor para esta ciudad";
    return base + `<strong>Se descarta:</strong> ${motivo}.`;
  }
  const previas = b.pasos.slice(1, p).filter((s) => b.entradas[s.extraida].ciudad === e.ciudad && s.resultado === "expandido").length;
  const nota = previas ? " Es una <strong>reexpansión</strong>: la ciudad ya se había expandido con un costo peor." : "";
  const entra = paso.nuevas.length
    ? `Se expande y entran a la frontera: ${lista(paso.nuevas, b)}.`
    : "Se expande, pero no genera entradas nuevas: sus vecinos ya fueron visitados o no mejoran el costo conocido.";
  return base + entra + nota;
}

function fraseRuta() {
  const n = S.tramo;
  const total = S.aristasRuta.length;
  if (n === 0) {
    return `<strong>Construcción de la ruta.</strong> ${total} tramos: se dibujan de uno en uno y las cifras se acumulan.`;
  }
  const r = S.aristasRuta[n - 1];
  const ac = sumar(S.aristasRuta.slice(0, n));
  const peaje = r.peaje_cop > 0 ? `peaje ${esc(r.peaje_nombre)} (${fmt(r.peaje_cop)} COP)` : "sin peaje";
  const nota = r.piso ? ", distancia con piso geodésico" : "";
  return `<strong>Tramo ${n} de ${total}.</strong> ${esc(r.desde)} › ${esc(r.hasta)}: ${fmt(r.distancia_km, 2)} km${nota}, ${peaje}. `
    + `Acumulado: ${fmt(ac.dist, 2)} km, ${fmt(ac.peaje)} COP de peajes.`;
}

function pintarFrase() {
  let html = "";
  if (S.modo === "ruta" && S.fase === "busqueda" && S.busqueda) html = fraseDePaso(S.busqueda, S.paso);
  else if (S.aristasRuta.length) html = fraseRuta();
  else html = "Elija una consulta y pulse «Calcular».";
  $("frase").innerHTML = html;
}

/* ====================== métricas acumuladas ====================== */
function registro(a, desde, hasta) {
  return {desde, hasta, distancia_km: a.distancia_km, piso: a.piso, peaje_cop: a.peaje_cop,
          peaje_nombre: a.peaje_nombre, costo_operativo_cop: a.costos.costo_operativo, riesgo: a.riesgo};
}

function sumar(edges) {
  const r = {dist: 0, peaje: 0, op: 0, riesgo: 0, conRiesgo: 0, sinRiesgo: 0, piso: 0, saltos: edges.length, peajes: []};
  edges.forEach((t) => {
    r.dist += t.distancia_km;
    r.peaje += t.peaje_cop;
    r.op += t.costo_operativo_cop;
    if (t.riesgo == null) r.sinRiesgo += 1; else { r.riesgo += t.riesgo; r.conRiesgo += 1; }
    if (t.piso) r.piso += 1;
    if (t.peaje_cop > 0) r.peajes.push(t.peaje_nombre);
  });
  return r;
}

function aristasDeCadena(ciudades) {
  const out = [];
  for (let i = 1; i < ciudades.length; i++) out.push(registro(ARISTA[par(ciudades[i - 1], ciudades[i])], ciudades[i - 1], ciudades[i]));
  return out;
}

/* ====================== paneles ====================== */
const cifra = (valor, etiqueta, nota, acento) =>
  `<div class="cifra${acento ? " acento" : ""}"><span class="cifra-v">${valor}</span><span class="cifra-e">${etiqueta}</span>${nota ? `<span class="cifra-n">${nota}</span>` : ""}</div>`;

function pintarEstado() {
  const cont = $("panel-estado");
  if (S.modo === "despachador") {
    const d = S.despacho;
    if (!d) { cont.innerHTML = '<p class="vacio">Marque paradas en el mapa y pulse «Calcular».</p>'; return; }
    cont.innerHTML = `<div class="cifras">`
      + cifra(esc(d.metodo.split(" (")[0]), "Método")
      + cifra(fmt(d.k == null ? 0 : d.k), "Paradas libres k", `umbral exacto K = ${fmt(d.umbral_k)}`)
      + cifra(fmt(d.paradas.obligatorias), "Obligatorias")
      + cifra(fmt(d.metricas_despachador.nodos_expandidos), "Nodos expandidos", "al armar la matriz de costos")
      + `</div>`
      + `<div class="bloque"><h3>Motivo de la elección</h3><p class="ruta-prov">${esc(d.motivo)}</p></div>`;
    return;
  }
  const V = S.vista;
  const b = S.busqueda;
  if (!V || !b) { cont.innerHTML = '<p class="cargando">Calculando…</p>'; return; }
  const p = V.paso;
  const frontera = p.frontera.map((id, i) => {
    const e = b.entradas[id];
    const k = claveSalida(b, e);
    return `<li><span>${esc(e.ciudad)}${i === 0 ? ' <span class="insignia amb">sigue</span>' : ""}</span><span class="n">${k.nombre} ${fc(k.valor)}</span></li>`;
  }).join("");
  const cadena = V.rama.map((i) => esc(b.entradas[i].ciudad)).join('<span class="sep">›</span>');
  const g = b.entradas[V.actualId].g;
  cont.innerHTML = `<div class="cifras">`
    + cifra(fmt(p.expandidos), "Expandidos")
    + cifra(fmt(p.generados), "Generados")
    + cifra(fmt(p.frontera_max), "Frontera máxima")
    + cifra(fmt(p.reexpansiones), "Reexpansiones")
    + `</div>`
    + `<div class="bloque"><h3>Frontera, en orden de salida (${p.frontera.length})</h3>`
    + (frontera ? `<ul class="lista-frontera">${frontera}</ul>` : '<p class="ayuda">Vacía.</p>') + `</div>`
    + `<div class="bloque"><h3>Ruta provisional hasta el nodo actual</h3><p class="ruta-prov">${cadena} <span class="n">(g = ${fc(g)})</span></p></div>`;
}

function construirPanelRuta() {
  const cfg = S.red.config.velocidad_promedio_kmh;
  $("panel-ruta").innerHTML = `
    <p class="nota" id="pr-etiqueta"></p>
    <div class="cifras" id="pr-cifras"></div>
    <div class="progreso" aria-hidden="true"><i id="pr-prog"></i></div>
    <div class="tiempo-ctl">
      <label for="vel-kmh">Velocidad supuesta para el tiempo estimado</label>
      <div class="fila"><input type="range" id="vel-kmh" min="${cfg.minimo}" max="${cfg.maximo}" step="1" value="${cfg.valor}">
      <output id="vel-kmh-txt" for="vel-kmh"></output></div>
      <p class="ayuda" id="pr-ayuda-tiempo"></p>
    </div>
    <div class="bloque"><h3>Peajes cruzados</h3><p class="ruta-prov" id="pr-peajes"></p></div>
    <div class="bloque"><h3>Ciudades intermedias</h3><p class="ruta-prov" id="pr-inter"></p></div>`;
  $("vel-kmh").addEventListener("input", (ev) => { S.velKmh = Number(ev.target.value); pintarRuta(); });
}

function edgesMostrados() {
  if (S.modo === "ruta" && S.fase === "busqueda") {
    const V = S.vista;
    if (!V) return {edges: [], etiqueta: ""};
    const cadena = V.rama.map((i) => S.busqueda.entradas[i].ciudad);
    const fin = V.p === S.busqueda.pasos.length - 1;
    return {edges: aristasDeCadena(cadena),
            etiqueta: fin ? "Ruta final de la búsqueda" : `Ruta provisional hasta ${cadena[cadena.length - 1]}`,
            total: S.aristasRuta.length, hecho: fin};
  }
  const n = tramosVisibles();
  return {edges: S.aristasRuta.slice(0, n),
          etiqueta: n >= S.aristasRuta.length ? "Ruta completa" : `Acumulado hasta el tramo ${n} de ${S.aristasRuta.length}`,
          total: S.aristasRuta.length, hecho: n >= S.aristasRuta.length};
}

function pintarRuta() {
  if (!$("pr-cifras")) return;
  const {edges, etiqueta, total, hecho} = edgesMostrados();
  const r = sumar(edges);
  const vel = S.velKmh;
  $("pr-etiqueta").textContent = etiqueta;
  const desp = S.modo === "despachador" && S.despacho;
  $("pr-cifras").innerHTML =
    cifra(`${fmt(r.dist, 2)}<small>km</small>`, "Distancia", r.piso ? `${r.piso} tramo(s) con piso geodésico` : "sin tramos con piso geodésico", true)
    + cifra(fmtHoras(r.dist / vel), "Tiempo estimado", `estimación con velocidad supuesta (${vel} km/h)`)
    + cifra(`${fmt(r.peaje)}<small>COP</small>`, "Peajes", `categoría III, ${r.peajes.length} cruzado(s)`)
    + cifra(`${fmt(r.op)}<small>COP</small>`, "Costo operativo", "peajes + costo variable")
    + cifra(fmt(r.riesgo, 2), "Riesgo (GiZScore)", `${r.sinRiesgo} tramo(s) sin dato, no se imputa`)
    + cifra(fmt(r.saltos), "Saltos", desp ? `${S.despacho.paradas.libres} libres, ${S.despacho.paradas.obligatorias} obligatorias` : "aristas de la ruta");
  $("pr-prog").style.setProperty("--w", total ? `${Math.round(100 * r.saltos / total)}%` : "0%");
  $("vel-kmh-txt").textContent = `${vel} km/h`;
  $("pr-ayuda-tiempo").textContent = `Distancia ÷ velocidad, con una velocidad que es ${S.red.config.velocidad_promedio_kmh.estado}. `
    + "El proyecto no tiene datos de tiempo de viaje; no es un criterio de búsqueda y no entra a ningún costo ni resultado.";
  $("pr-peajes").textContent = r.peajes.length ? r.peajes.join(", ") : "Ninguno hasta ahora.";
  const nombres = edges.length ? [edges[0].desde, ...edges.map((t) => t.hasta)] : [];
  $("pr-inter").textContent = nombres.length > 2 ? nombres.slice(1, -1).join(", ") : "Ninguna.";
  void hecho;
}

function comandoHtml(texto) {
  return `<div class="comando"><code>${esc(texto)}</code>`
    + `<button type="button" class="boton boton-tenue" data-copiar="${esc(texto)}">Copiar</button></div>`;
}

function pintarAlgoritmo() {
  const cont = $("panel-algoritmo");
  if (S.modo === "despachador") {
    const d = S.despacho;
    if (!d) { cont.innerHTML = '<p class="vacio">Sin consulta todavía.</p>'; return; }
    const m = d.metricas_despachador;
    cont.innerHTML = `<p><span class="insignia amb">${esc(d.metodo)}</span> <span class="insignia info">tipo ${esc(d.tipo)}: ${esc(d.nombre_tipo.replace(/_/g, " "))}</span></p>`
      + `<div class="bloque"><h3>Cifras del cómputo</h3><div class="cifras">`
      + cifra(`${fmt(m.tiempo_s * 1000, 1)}<small>ms</small>`, "Tiempo total", "una corrida en este equipo")
      + cifra(`${fmt((m.tiempo_matriz_s || 0) * 1000, 1)}<small>ms</small>`, "Matriz de costos", `${fmt(m.paradas)} paradas`)
      + `</div></div>`
      + `<div class="bloque"><h3>Comando equivalente</h3>${comandoHtml(d.comando)}`
      + (d.regreso ? `<p class="ayuda">Regreso:</p>${comandoHtml(d.regreso.comando)}` : "") + `</div>`;
    return;
  }
  const b = S.busqueda;
  if (!b) { cont.innerHTML = '<p class="cargando">Calculando…</p>'; return; }
  const t = b.tiempo;
  const hi = b.heuristica;
  let heuristica = "";
  if (b.algoritmo === "voraz" || b.algoritmo === "astar") {
    heuristica = `<div class="bloque"><h3>Heurística del criterio</h3><p class="formula">${esc(hi.formula)}</p>`
      + `<p class="ayuda">α = <span class="num">${fmt(hi.alfa, 6)}</span>; factor aplicado a la distancia geodésica = <span class="num">${fmt(hi.factor, 6)}</span></p>`
      + hi.avisos.map((a) => `<p class="alerta">${esc(a)}</p>`).join("") + `</div>`;
  } else {
    heuristica = `<div class="bloque"><h3>Heurística</h3><p class="ayuda">${esc(b.nombre_algoritmo)} no usa heurística. La tabla h(n) (casilla «Ver h(n)») muestra la del criterio elegido, que usarían la voraz y A*.</p></div>`;
  }
  cont.innerHTML = `<p><span class="insignia ${b.optimo ? "ok" : "no"}">${b.optimo ? "ruta óptima" : "ruta no óptima"}</span> `
    + `<span class="insignia info">${esc(b.nombre_algoritmo)}</span></p>`
    + `<div class="bloque"><h3>Cómputo y resultado</h3><div class="cifras">`
    + cifra(`${fmt(t.media_ms, 3)}<small>ms</small>`, "Tiempo de cómputo", `media de ${t.repeticiones} repeticiones, desviación ${fmt(t.desviacion_ms, 3)} ms`)
    + cifra(fc(b.costo), "Costo de la ruta", esc(b.criterio.replace(/_/g, " ")))
    + `</div><p class="ayuda">${esc(t.equipo.procesador)}, ${t.equipo.nucleos_logicos} núcleos lógicos, Python ${esc(t.equipo.python)}; medido el ${esc(t.fecha)}.</p></div>`
    + heuristica
    + `<div class="bloque"><h3>Comando equivalente en la terminal</h3>${comandoHtml(b.comando)}</div>`;
}

/* ====================== tablas ====================== */
const nombreCriterio = (c) => c.replace(/_/g, " ");
const via = (v) => (v ? `<span class="insignia ${v === "Santander" ? "amb" : "info"}">por ${esc(v)}</span>` : "");

function pintarTablaAlgoritmos() {
  const cont = $("tab-algoritmos");
  const c = S.comparar;
  if (!c) { cont.innerHTML = '<p class="cargando">Calculando…</p>'; return; }
  const tope = Math.max(...c.algoritmos.map((a) => a.expandidos));
  const filas = c.algoritmos.map((a) => `
    <tr class="fila-clic${a.algoritmo === S.algoritmo ? " activa" : ""}" tabindex="0" data-algoritmo="${esc(a.algoritmo)}" title="Animar ${esc(a.nombre)}">
      <td><strong>${esc(a.nombre)}</strong></td>
      <td class="ruta-celda">${a.ruta.map(esc).join(" › ")}</td>
      <td class="n">${fc(a.costo)}</td>
      <td class="n">${fmt(a.metricas.distancia_km, 2)}</td>
      <td class="n">${a.saltos}</td>
      <td class="n celda-barra" style="--w:${Math.round(100 * a.expandidos / tope)}%"><span class="num">${a.expandidos}</span></td>
      <td class="n">${a.generados}</td>
      <td class="n">${a.frontera_max}</td>
      <td><span class="insignia ${a.optimo ? "ok" : "no"}">${a.optimo ? "óptima" : "no óptima"}</span></td>
    </tr>`).join("");
  cont.innerHTML = `<p class="ayuda">${esc(c.origen)} a ${esc(c.destino)}, criterio ${esc(nombreCriterio(c.criterio))}. Clic en una fila para animar ese algoritmo.</p>`
    + `<div class="tabla-scroll"><table><thead><tr><th>Algoritmo</th><th>Ruta</th><th class="n">Costo</th><th class="n">Distancia km</th><th class="n">Saltos</th>`
    + `<th class="n">Expandidos</th><th class="n">Generados</th><th class="n">Frontera máx.</th><th>Resultado</th></tr></thead><tbody>${filas}</tbody></table></div>`
    + `<div class="bloque">${comandoHtml(c.comando)}</div>`;
}

function pintarTablaCriterios() {
  const cont = $("tab-criterios");
  const c = S.criterios;
  if (!c) { cont.innerHTML = '<p class="cargando">Calculando…</p>'; return; }
  const maxExp = Math.max(...c.criterios.map((f) => f.expandidos));
  const maxDist = Math.max(...c.criterios.map((f) => f.metricas.distancia_km));
  const filas = c.criterios.map((f) => {
    const info = S.red.criterios[f.criterio];
    const h = info.factor_heuristica === 0 ? '<span class="insignia no">h = 0</span>'
      : info.limitado ? '<span class="insignia amb">limitado</span>' : '<span class="insignia ok">informativa</span>';
    return `<tr class="fila-clic${f.criterio === S.criterio ? " activa" : ""}" tabindex="0" data-criterio="${esc(f.criterio)}" title="${esc(info.descripcion)}">
      <td><strong>${esc(nombreCriterio(f.criterio))}</strong></td>
      <td>${via(f.via)}</td>
      <td class="n celda-barra dist" style="--w:${Math.round(100 * f.metricas.distancia_km / maxDist)}%"><span class="num">${fmt(f.metricas.distancia_km, 2)}</span></td>
      <td class="n">${fmt(f.metricas.peaje_cop)}</td>
      <td class="n">${fmt(f.metricas.costo_operativo_cop)}</td>
      <td class="n">${fmt(f.metricas.riesgo_gizscore, 2)}</td>
      <td class="n">${f.metricas.saltos}</td>
      <td class="n celda-barra" style="--w:${Math.round(100 * f.expandidos / maxExp)}%"><span class="num">${f.expandidos}</span></td>
      <td>${h}</td></tr>`;
  }).join("");
  cont.innerHTML = `<p class="ayuda">${esc(c.origen)} a ${esc(c.destino)} con ${esc(c.nombre_algoritmo)}: la ruta que resulta bajo cada criterio. Clic en una fila para animarla.</p>`
    + `<div class="tabla-scroll"><table><thead><tr><th>Criterio</th><th>Corredor</th><th class="n">Distancia km</th><th class="n">Peajes COP</th>`
    + `<th class="n">Costo operativo COP</th><th class="n">Riesgo</th><th class="n">Saltos</th><th class="n">Expandidos</th><th>Heurística</th></tr></thead><tbody>${filas}</tbody></table></div>`;
}

function curvaSvg(curva) {
  const W = 560;
  const H = 220;
  const ml = 76;
  const mr = 16;
  const mt = 12;
  const mb = 40;
  const lo = Math.min(...curva);
  const hi = Math.max(...curva);
  const x = (i) => ml + i * (W - ml - mr) / Math.max(1, curva.length - 1);
  const y = (v) => mt + (hi === lo ? 0.5 : (hi - v) / (hi - lo)) * (H - mt - mb);
  const puntos = curva.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  return `<svg class="curva" width="${W}" height="${H}" role="img" aria-label="Curva de convergencia del ACO">
    <line class="eje" x1="${ml}" y1="${mt}" x2="${ml}" y2="${H - mb}"/><line class="eje" x1="${ml}" y1="${H - mb}" x2="${W - mr}" y2="${H - mb}"/>
    <polyline class="linea" points="${puntos}"/>
    <text x="${ml - 8}" y="${mt + 12}" text-anchor="end">${fc(hi)}</text>
    <text x="${ml - 8}" y="${H - mb}" text-anchor="end">${fc(lo)}</text>
    <text x="${ml}" y="${H - 12}">iteración 1</text>
    <text x="${W - mr}" y="${H - 12}" text-anchor="end">iteración ${curva.length}</text></svg>`;
}

function pintarTablaDespachador() {
  const cont = $("tab-despachador");
  const d = S.despacho;
  if (!d) {
    cont.innerHTML = '<p class="vacio">Pase al modo «Despachador», marque las paradas en el mapa y pulse «Calcular», o use un caso de ejemplo.</p>';
    return;
  }
  const orden = d.orden_paradas.map((c, i) => `<li><span class="orden">${i + 1}</span>${esc(c)}</li>`).join("");
  const filasTramo = (lista, desplazamiento) => lista.map((t, i) => `<tr><td class="n">${desplazamiento + i + 1}</td><td>${esc(t.desde)}</td><td>${esc(t.hasta)}</td>`
    + `<td class="ruta-celda">${t.ruta.map(esc).join(" › ")}</td><td class="n">${fmt(t.metricas.distancia_km, 2)}</td>`
    + `<td class="n">${fmt(t.metricas.peaje_cop)}</td><td class="n">${fc(t.costo)}</td></tr>`).join("");
  const m = d.matriz;
  let tope = 0;
  m.costos.forEach((f, i) => f.forEach((v, j) => { if (i !== j) tope = Math.max(tope, v); }));
  const cabecera = m.nodos.map((_, j) => `<th class="n">${j + 1}</th>`).join("");
  const filasMatriz = m.costos.map((f, i) => `<tr><th scope="row">${i + 1} ${esc(m.nodos[i])}</th>`
    + f.map((v, j) => (i === j ? '<td class="diag">·</td>' : `<td class="calor" style="--v:${Math.round(45 * v / tope)}">${fc(v)}</td>`)).join("") + "</tr>").join("");
  let aco = "";
  if (d.aco) {
    aco = `<div class="ancho"><h3>Convergencia del ACO</h3>`
      + `<p class="ayuda">Mejor costo acumulado por iteración, media de las semillas del despachador. Costo medio final ${fc(d.aco.costo_medio)}, peor ${fc(d.aco.costo_peor)}, desviación ${fc(d.aco.desviacion)}. `
      + `El módulo no entrega una referencia por estructura, así que no se dibuja ninguna.</p>`
      + `<div class="tabla-scroll">${curvaSvg(d.aco.curva)}</div></div>`;
  }
  const demo = S.ejemplo && (S.ejemplo === "diecinueve" || S.ejemplo === "veinte")
    ? '<p class="alerta">Instancia de demostración: Bogotá de origen y las primeras ciudades restantes en orden alfabético. No es un caso de las pruebas del informe.</p>' : "";
  let regreso = "";
  if (d.regreso) {
    const r = d.regreso;
    regreso = `<div class="ancho"><h3>Regreso (ida y vuelta)</h3><p class="ayuda">${r.ruta.map(esc).join(" › ")}</p>`
      + `<p>Distancia ${fmt(r.metricas.distancia_km, 2)} km, peajes ${fmt(r.metricas.peaje_cop)} COP, costo ${fc(r.costo)} (${esc(r.criterio.replace(/_/g, " "))}).</p></div>`;
  }
  cont.innerHTML = demo
    + `<p><span class="insignia amb">${esc(d.metodo)}</span> <span class="insignia info">k = ${d.k == null ? 0 : d.k}, umbral K = ${d.umbral_k}</span> `
    + `<span class="insignia">costo ${fc(d.costo)} (${esc(d.criterio.replace(/_/g, " "))})</span></p>`
    + `<p class="ayuda">${esc(d.motivo)}</p>`
    + `<div class="desp-rejilla"><div class="ancho"><h3>Orden de visita</h3><ol class="orden-visita">${orden}</ol></div>`
    + `<div class="ancho"><h3>Tramos</h3><div class="tabla-scroll"><table><thead><tr><th class="n">N.º</th><th>Desde</th><th>Hasta</th><th>Ruta</th><th class="n">Km</th><th class="n">Peaje COP</th><th class="n">Costo</th></tr></thead>`
    + `<tbody>${filasTramo(d.tramos, 0)}${d.regreso ? filasTramo(d.regreso.tramos, d.tramos.length) : ""}</tbody></table></div></div>`
    + `<div class="ancho"><h3>Matriz de costos entre paradas (${esc(d.criterio.replace(/_/g, " "))})</h3><div class="tabla-scroll"><table class="matriz"><thead><tr><th>Parada</th>${cabecera}</tr></thead><tbody>${filasMatriz}</tbody></table></div></div>`
    + aco + regreso + `</div>`;
}

function pintarTablas() {
  pintarTablaAlgoritmos();
  pintarTablaCriterios();
  pintarTablaDespachador();
}

function activarPestana(id) {
  for (const t of ["algoritmos", "criterios", "despachador"]) {
    const sel = t === id;
    const boton = $(`tab-b-${t}`);
    boton.setAttribute("aria-selected", String(sel));
    boton.tabIndex = sel ? 0 : -1;
    $(`tab-${t}`).hidden = !sel;
  }
}

/* ====================== reproductor ====================== */
const enBusqueda = () => S.modo === "ruta" && S.fase === "busqueda" && !!S.busqueda;
const maxPos = () => (enBusqueda() ? S.busqueda.pasos.length - 1 : S.aristasRuta.length);
const posActual = () => (enBusqueda() ? S.paso : S.tramo);

function fijarPos(valor, animar) {
  const v = Math.max(0, Math.min(maxPos(), valor));
  if (enBusqueda()) S.paso = v; else S.tramo = v;
  render({animar: !!animar});
}

function pausar() {
  S.jugando = false;
  clearTimeout(S.temporizador);
  const b = $("p-jugar");
  if (b) { b.dataset.jugando = "no"; b.setAttribute("aria-label", "Animar"); }
}

function ciclo() {
  clearTimeout(S.temporizador);
  S.temporizador = setTimeout(() => {
    if (!S.jugando) return;
    if (posActual() < maxPos()) fijarPos(posActual() + 1, true);
    if (posActual() >= maxPos()) pausar(); else ciclo();
  }, 1000 / VELOCIDADES[S.velocidad - 1]);
}

function alternarJuego() {
  if (S.jugando) { pausar(); return; }
  if (!maxPos() && !S.aristasRuta.length) return;
  if (posActual() >= maxPos()) {
    if (enBusqueda() && S.aristasRuta.length) { S.fase = "ruta"; S.tramo = 0; } else fijarPos(0);
  }
  S.jugando = true;
  $("p-jugar").dataset.jugando = "si";
  $("p-jugar").setAttribute("aria-label", "Pausar");
  render();
  ciclo();
}

function cambiarFase(fase) {
  if (S.modo === "despachador") fase = "ruta";
  pausar();
  S.fase = fase;
  render();
}

/* ====================== render general ====================== */
function render(opciones) {
  const animar = opciones && opciones.animar;
  S.vista = S.modo === "ruta" ? vistaBusqueda() : null;
  const max = maxPos();
  const barra = $("p-barra");
  barra.max = String(max);
  barra.value = String(posActual());
  $("p-et").textContent = enBusqueda() ? "Paso" : "Tramo";
  $("p-pos").textContent = `${posActual()} de ${max}`;
  $("fase-busqueda").checked = S.fase === "busqueda" && S.modo === "ruta";
  $("fase-ruta").checked = !($("fase-busqueda").checked);
  $("fase-ruta").disabled = !S.aristasRuta.length;
  const sinDatos = !S.aristasRuta.length && !S.busqueda;
  for (const id of ["p-reiniciar", "p-atras", "p-jugar", "p-adelante", "p-final"]) $(id).disabled = sinDatos;
  pintarMapa(animar);
  pintarArbol();
  pintarFrase();
  pintarEstado();
  pintarRuta();
  pintarCaso();
}

function pintarCaso() {
  let html = "";
  if (S.modo === "ruta" && S.busqueda) {
    html = `<strong>${esc(S.origen)} › ${esc(S.destino)}</strong> · ${esc(nombreCriterio(S.criterio))} · ${esc(S.red.algoritmos[S.algoritmo])}`;
  } else if (S.modo === "despachador") {
    const k = S.libres.length;
    html = `<strong>Despachador, tipo ${esc(S.tipo)}</strong> desde ${esc(S.origen)} · ${k} libres, ${S.obligatorias.length} obligatorias · ${esc(nombreCriterio(S.criterio))}`;
  } else {
    html = "Cargando la red…";
  }
  $("caso-activo").innerHTML = html;
}

function pintarContador() {
  const el = $("contador-paradas");
  if (!el) return;
  let extra = "";
  if (S.tipo === "b" && S.libres.length) extra = `<br>Orden fijo: ${[S.origen, ...S.libres, S.destino].map(esc).join(" › ")}`;
  el.innerHTML = `paradas: <strong>${S.libres.length}</strong> libres, <strong>${S.obligatorias.length}</strong> obligatorias${extra}`;
  const bl = $("lista-bloqueados");
  bl.innerHTML = [...S.bloqueados].map((k) => {
    const [u, v] = k.split("|");
    return `<button type="button" class="chip chip-bloqueo" data-desbloquear="${esc(k)}" title="Quitar el bloqueo">${esc(u)} – ${esc(v)} ×</button>`;
  }).join("");
}

function construirLeyenda() {
  const forma = (clase, d) => `<svg class="glifo" viewBox="0 0 16 16" aria-hidden="true"><path class="${clase}" d="${d}"/></svg>`;
  const circulo = "M8 2.5a5.5 5.5 0 1 0 0.01 0Z";
  const rombo = "M8 1.5L14.5 8L8 14.5L1.5 8Z";
  const cuadro = "M2.5 2.5h11v11h-11Z";
  const hexa = "M4.5 1.5h7L15 8l-3.5 6.5h-7L1 8Z";
  const linea = (clase) => `<svg class="glifo" viewBox="0 0 16 16" aria-hidden="true"><path class="${clase}" d="M1 8H15"/></svg>`;
  const items = S.modo === "ruta" ? [
    [forma("gl-libre", circulo), "Sin explorar"], [forma("gl-frontera", rombo), "En la frontera"],
    [forma("gl-actual", circulo), "Extraído ahora"], [forma("gl-expandido", circulo), "Expandido"],
    [forma("gl-meta", cuadro), "Meta"], [linea("gl-l-ruta"), "Ruta"],
    [linea("gl-l-exp"), "Arista explorada"], [linea("gl-l-prov"), "Ruta provisional"],
  ] : [
    [forma("gl-parada", hexa), "Parada libre"], [forma("gl-meta", cuadro), "Parada obligatoria"],
    [`<span class="orden">1</span>`, "Orden de visita"], [linea("gl-l-ruta"), "Tramo de la ruta"],
    [linea("gl-l-bloq"), "Arista bloqueada"],
  ];
  $("leyenda").innerHTML = `<details><summary>Leyenda</summary><div class="leyenda-lista">`
    + items.map(([g, t]) => `<div class="leyenda-item">${g}<span>${t}</span></div>`).join("")
    + `</div><p class="leyenda-nota">Trazo esquemático: recta entre nodos. El grosor sigue el costo de cada arista en el criterio elegido; la distancia es la del modelo.</p></details>`;
}

/* ====================== consultas ====================== */
async function calcularRuta() {
  pausar();
  aviso("");
  if (S.origen === S.destino) { aviso("El origen y el destino deben ser distintos."); return; }
  const tok = ++S.token;
  const p = {origen: S.origen, destino: S.destino, criterio: S.criterio};
  const pBus = api("/api/busqueda", Object.assign({algoritmo: S.algoritmo}, p));
  const pCom = api("/api/comparar", p);
  const pCri = api("/api/criterios", {origen: S.origen, destino: S.destino, algoritmo: S.algoritmo});
  try {
    const bus = await pBus;
    if (tok !== S.token) return;
    S.modo = "ruta";
    S.busqueda = bus;
    S.despacho = null;
    S.fase = "busqueda";
    S.paso = 0;
    S.tramo = 0;
    S.piernas = [];
    S.tiempoFin = [];
    S.aristasRuta = bus.metricas.tramos.map((t) => Object.assign({pierna: 0}, t));
    sincronizarControles();
    construirLeyenda();
    construirArbol();
    construirCapaRuta();
    actualizarGrosores();
    pintarAlgoritmo();
    pintarTablaDespachador();
    render();
  } catch (e) {
    if (tok === S.token) aviso(e.message);
  }
  pCom.then((c) => { if (tok === S.token) { S.comparar = c; pintarTablaAlgoritmos(); } }).catch((e) => aviso(e.message));
  pCri.then((c) => { if (tok === S.token) { S.criterios = c; pintarTablaCriterios(); } }).catch((e) => aviso(e.message));
}

function cuerpoDespachador() {
  const t = S.tipo;
  return {
    tipo: t, origen: S.origen,
    destino: ["a", "b", "c"].includes(t) ? S.destino : null,
    paradas: ["b", "d", "e"].includes(t) ? S.libres : [],
    obligatorias: t === "c" ? S.obligatorias : [],
    bloqueados: [...S.bloqueados].map((k) => k.split("|")),
    criterio: S.criterio, ida_vuelta: S.idaVuelta && ["a", "b", "c"].includes(t),
  };
}

async function calcularDespacho() {
  pausar();
  aviso("");
  const cuerpo = cuerpoDespachador();
  if (["d", "e"].includes(S.tipo) && !cuerpo.paradas.length) { aviso("Marque al menos una parada en el mapa."); return; }
  if (S.tipo === "c" && !cuerpo.obligatorias.length && !cuerpo.bloqueados.length) {
    aviso("El tipo c necesita paradas obligatorias (mayús + clic) o aristas bloqueadas."); return;
  }
  if (["a", "b", "c"].includes(S.tipo) && S.origen === S.destino) { aviso("El origen y el destino deben ser distintos."); return; }
  const tok = ++S.token;
  S.modo = "despachador";
  sincronizarControles();
  construirLeyenda();
  activarPestana("despachador");
  $("tab-despachador").innerHTML = `<p class="cargando">Calculando${cuerpo.paradas.length >= 15 ? ` con ${cuerpo.paradas.length} paradas libres; Held-Karp puede tardar varios segundos` : ""}…</p>`;
  $("btn-calcular").disabled = true;
  try {
    const d = await api("/api/despachador", null, cuerpo);
    if (tok !== S.token) return;
    S.despacho = d;
    S.busqueda = null;
    S.comparar = S.comparar;
    S.piernas = d.tramos.map((t, i) => Object.assign({}, t, {pierna: i}));
    if (d.regreso) d.regreso.tramos.forEach((t, i) => S.piernas.push(Object.assign({}, t, {pierna: d.tramos.length + i})));
    S.aristasRuta = [];
    S.tiempoFin = [];
    S.piernas.forEach((p) => {
      p.metricas.tramos.forEach((e) => S.aristasRuta.push(Object.assign({pierna: p.pierna}, e)));
      S.tiempoFin.push(S.aristasRuta.length);
    });
    S.fase = "ruta";
    S.tramo = 0;
    construirArbol();
    construirCapaRuta();
    pintarAlgoritmo();
    pintarTablaDespachador();
    render();
  } catch (e) {
    if (tok === S.token) { aviso(e.message); pintarTablaDespachador(); }
  } finally {
    $("btn-calcular").disabled = false;
  }
}

function calcular() { return S.modo === "despachador" ? calcularDespacho() : calcularRuta(); }

/* ====================== interacción con el mapa ====================== */
function alternarBloqueo(u, v) {
  const k = par(u, v);
  if (S.bloqueados.has(k)) S.bloqueados.delete(k); else S.bloqueados.add(k);
  pintarContador();
  pintarMapa();
}

function onNodoClick(nombre, mayus) {
  aviso("");
  if (S.modo === "ruta") {
    const campo = S.ultimoExtremo === "destino" ? "origen" : "destino";
    if (campo === "origen") S.origen = nombre; else S.destino = nombre;
    S.ultimoExtremo = campo;
    sincronizarControles();
    if (S.origen !== S.destino) calcularRuta(); else pintarMapa();
    return;
  }
  S.ejemplo = null;
  if (nombre === S.origen || (nombre === S.destino && ["a", "b", "c"].includes(S.tipo))) {
    aviso(`${nombre} es el ${nombre === S.origen ? "origen" : "destino"}: no puede ser además una parada.`);
    return;
  }
  const iLibre = S.libres.indexOf(nombre);
  const iObl = S.obligatorias.indexOf(nombre);
  if (iLibre >= 0) S.libres.splice(iLibre, 1);
  else if (iObl >= 0) S.obligatorias.splice(iObl, 1);
  else if (mayus) S.obligatorias.push(nombre);
  else S.libres.push(nombre);
  pintarContador();
  pintarMapa();
  pintarCaso();
}

function limpiarParadas() {
  S.libres = [];
  S.obligatorias = [];
  S.bloqueados.clear();
  S.despacho = null;
  S.aristasRuta = [];
  S.piernas = [];
  S.ejemplo = null;
  construirCapaRuta();
  pintarContador();
  pintarTablaDespachador();
  render();
}

function aplicarEjemplo(id) {
  const ej = S.red.ejemplos.find((e) => e.id === id);
  if (!ej) return;
  pausar();
  S.ejemplo = id;
  S.criterio = ej.criterio;
  S.origen = ej.origen;
  S.bloqueados.clear();
  if (ej.modo === "ruta") {
    S.destino = ej.destino;
    S.algoritmo = ej.algoritmo;
    S.modo = "ruta";
    activarPestana("algoritmos");
    sincronizarControles();
    calcularRuta();
  } else {
    S.tipo = ej.tipo;
    S.libres = ej.paradas.slice();
    S.obligatorias = [];
    S.idaVuelta = false;
    S.modo = "despachador";
    sincronizarControles();
    calcularDespacho();
  }
}

/* ====================== eventos ====================== */
function enlazar() {
  document.querySelectorAll('input[name="modo"]').forEach((r) => r.addEventListener("change", (ev) => {
    pausar();
    S.modo = ev.target.value;
    S.despacho = S.modo === "despachador" ? S.despacho : null;
    sincronizarControles();
    construirLeyenda();
    if (S.modo === "despachador") {
      S.fase = "ruta";
      S.busqueda = null;
      S.aristasRuta = S.despacho ? S.aristasRuta : [];
      construirArbol();
      construirCapaRuta();
      pintarAlgoritmo();
      activarPestana("despachador");
      pintarTablaDespachador();
      render();
    } else {
      activarPestana("algoritmos");
      calcularRuta();
    }
  }));
  $("sel-origen").addEventListener("change", (ev) => {
    S.origen = ev.target.value;
    S.libres = S.libres.filter((c) => c !== S.origen);
    S.obligatorias = S.obligatorias.filter((c) => c !== S.origen);
    if (S.modo === "ruta") calcularRuta(); else { pintarContador(); pintarMapa(); pintarCaso(); }
  });
  $("sel-destino").addEventListener("change", (ev) => {
    S.destino = ev.target.value;
    if (S.modo === "ruta") calcularRuta(); else { pintarContador(); pintarMapa(); }
  });
  $("sel-criterio").addEventListener("change", (ev) => {
    S.criterio = ev.target.value;
    actualizarGrosores();
    if (S.modo === "ruta") calcularRuta(); else pintarCaso();
  });
  $("sel-algoritmo").addEventListener("change", (ev) => { S.algoritmo = ev.target.value; calcularRuta(); });
  $("sel-tipo").addEventListener("change", (ev) => {
    S.tipo = ev.target.value;
    S.ejemplo = null;
    sincronizarControles();
    pintarMapa();
    pintarCaso();
  });
  $("chk-ida-vuelta").addEventListener("change", (ev) => { S.idaVuelta = ev.target.checked; });
  $("btn-intercambiar").addEventListener("click", () => {
    [S.origen, S.destino] = [S.destino, S.origen];
    sincronizarControles();
    if (S.modo === "ruta") calcularRuta(); else { pintarMapa(); pintarCaso(); }
  });
  $("btn-calcular").addEventListener("click", calcular);
  $("btn-bloqueo").addEventListener("click", () => { S.modoBloqueo = !S.modoBloqueo; sincronizarControles(); });
  $("btn-limpiar").addEventListener("click", limpiarParadas);
  $("ejemplos").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-ejemplo]");
    if (b) aplicarEjemplo(b.dataset.ejemplo);
  });
  $("lista-bloqueados").addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-desbloquear]");
    if (b) { S.bloqueados.delete(b.dataset.desbloquear); pintarContador(); pintarMapa(); }
  });
  $("chk-h").addEventListener("change", (ev) => { S.mostrarH = ev.target.checked; pintarMapa(); });
  $("btn-encuadrar").addEventListener("click", () => encuadrar(true));
  $("chk-sinfondo").addEventListener("change", (ev) => fijarFondo(ev.target.checked));
  $("btn-tema").addEventListener("click", () => aplicarTema(document.documentElement.dataset.tema === "claro" ? "oscuro" : "claro"));

  $("p-reiniciar").addEventListener("click", () => { pausar(); fijarPos(0); });
  $("p-atras").addEventListener("click", () => { pausar(); fijarPos(posActual() - 1); });
  $("p-adelante").addEventListener("click", () => { pausar(); fijarPos(posActual() + 1, true); });
  $("p-final").addEventListener("click", () => { pausar(); fijarPos(maxPos()); });
  $("p-jugar").addEventListener("click", alternarJuego);
  $("p-barra").addEventListener("input", (ev) => { pausar(); fijarPos(Number(ev.target.value)); });
  $("p-vel").addEventListener("input", (ev) => {
    S.velocidad = Number(ev.target.value);
    $("p-vel-txt").textContent = `${VELOCIDADES[S.velocidad - 1]} ${VELOCIDADES[S.velocidad - 1] === 1 ? "paso" : "pasos"}/s`;
  });
  document.querySelectorAll('input[name="fase"]').forEach((r) => r.addEventListener("change", (ev) => cambiarFase(ev.target.value)));

  for (const t of ["algoritmos", "criterios", "despachador"]) {
    $(`tab-b-${t}`).addEventListener("click", () => activarPestana(t));
  }
  const activarFila = (ev) => {
    if (ev.type === "keydown" && ev.key !== "Enter" && ev.key !== " ") return;
    const fa = ev.target.closest("[data-algoritmo]");
    const fc2 = ev.target.closest("[data-criterio]");
    if (fa) { S.algoritmo = fa.dataset.algoritmo; sincronizarControles(); calcularRuta(); }
    if (fc2) { S.criterio = fc2.dataset.criterio; sincronizarControles(); actualizarGrosores(); calcularRuta(); }
    if ((fa || fc2) && ev.type === "keydown") ev.preventDefault();
  };
  $("tab-algoritmos").addEventListener("click", activarFila);
  $("tab-algoritmos").addEventListener("keydown", activarFila);
  $("tab-criterios").addEventListener("click", activarFila);
  $("tab-criterios").addEventListener("keydown", activarFila);

  document.addEventListener("click", (ev) => {
    const b = ev.target.closest("[data-copiar]");
    if (!b) return;
    const aviso1 = () => { b.textContent = "Copiado"; setTimeout(() => { b.textContent = "Copiar"; }, 1500); };
    try { navigator.clipboard.writeText(b.dataset.copiar).then(aviso1, () => {}); } catch (e) { /* sin portapapeles */ }
  });
  document.addEventListener("keydown", (ev) => {
    const t = ev.target;
    const tag = t.tagName;
    if (tag === "SELECT" || tag === "TEXTAREA" || (tag === "INPUT" && t.type !== "checkbox" && t.type !== "radio")) return;
    if (t.getAttribute && t.getAttribute("role") === "tab") return;
    if (ev.key === " " && (tag === "BUTTON" || tag === "SUMMARY" || (t.getAttribute && t.getAttribute("role") === "button"))) return;
    if (ev.altKey || ev.ctrlKey || ev.metaKey) return;
    if (ev.key === " ") { ev.preventDefault(); alternarJuego(); }
    else if (ev.key === "ArrowRight") { ev.preventDefault(); pausar(); fijarPos(posActual() + 1, true); }
    else if (ev.key === "ArrowLeft") { ev.preventDefault(); pausar(); fijarPos(posActual() - 1); }
    else if (ev.key === "Home") { ev.preventDefault(); pausar(); fijarPos(0); }
    else if (ev.key === "End") { ev.preventDefault(); pausar(); fijarPos(maxPos()); }
  });
  $("p-vel-txt").textContent = `${VELOCIDADES[S.velocidad - 1]} ${VELOCIDADES[S.velocidad - 1] === 1 ? "paso" : "pasos"}/s`;
}

/* ====================== arranque ====================== */
async function iniciar() {
  const tema = document.documentElement.dataset.tema === "claro" ? "claro" : "oscuro";
  document.documentElement.dataset.tema = tema;
  $("btn-tema").setAttribute("aria-pressed", String(tema === "claro"));
  $("btn-tema-txt").textContent = tema === "claro" ? "Modo oscuro" : "Modo claro";
  try {
    S.red = await api("/api/red");
  } catch (e) {
    aviso(`No se pudo cargar la red: ${e.message}`);
    $("caso-activo").textContent = "Sin conexión con el servidor.";
    return;
  }
  S.velKmh = S.red.config.velocidad_promedio_kmh.valor;
  indexarRed();
  poblarSelects();
  construirMapa();
  if (document.fonts) document.fonts.ready.then(reubicarRotulos);
  encuadrar(true);
  window.addEventListener("load", () => encuadrar(false));
  if (window.ResizeObserver) new ResizeObserver(alCambiarTamano).observe($("mapa"));
  window.addEventListener("resize", alCambiarTamano);
  construirPanelRuta();
  construirLeyenda();
  enlazar();
  pintarTablas();
  pintarEstado();
  pintarAlgoritmo();
  const central = S.red.ejemplos.find((e) => e.id === "central");
  S.ejemplo = "central";
  S.origen = central.origen;
  S.destino = central.destino;
  S.criterio = central.criterio;
  S.algoritmo = central.algoritmo;
  sincronizarControles();
  await calcularRuta();
}

iniciar();
})();
