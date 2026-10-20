// Verificación del mapa del visualizador. Se pega en la consola del navegador
// (o en javascript_tool) con la aplicación abierta y define window.verif(),
// que devuelve {zoom, tam, n, fallos, peor}:
//  - por cada nodo, la distancia en píxeles entre el centro de su marcador en
//    pantalla y map.latLngToContainerPoint(latitud, longitud);
//  - por cada arista, la distancia entre cada extremo de su trazo SVG y el
//    centro del marcador del nodo correspondiente. Leaflet recorta los trazos
//    al área de su renderizador, así que solo se evalúan las aristas cuyos
//    dos extremos caen dentro de esa área.
// Cada fila con más de 1 px de desfase cuenta como fallo.
window.verif = () => {
  const V = window.VISUALIZADOR, mapa = V.mapa, filas = [];
  const caja = mapa.getContainer().getBoundingClientRect();
  const centro = (m) => { const r = m.getElement().getBoundingClientRect(); return [r.left + r.width / 2 - caja.left, r.top + r.height / 2 - caja.top]; };
  for (const [n, m] of Object.entries(V.marcadores)) {
    const e = mapa.latLngToContainerPoint(m.getLatLng()), c = centro(m);
    filas.push({tipo: "nodo", id: n, dx: c[0] - e.x, dy: c[1] - e.y, dist: Math.hypot(c[0] - e.x, c[1] - e.y)});
  }
  for (const [k, capa] of Object.entries(V.capasArista)) {
    const [u, v] = k.split("|");
    const area = mapa.getRenderer(capa.vis)._bounds;
    if (!area.contains(mapa.latLngToLayerPoint(V.marcadores[u].getLatLng()))
        || !area.contains(mapa.latLngToLayerPoint(V.marcadores[v].getLatLng()))) continue;
    const nums = capa.vis.getElement().getAttribute("d").match(/-?\d+(\.\d+)?/g).map(Number);
    const pa = mapa.layerPointToContainerPoint([nums[0], nums[1]]);
    const pb = mapa.layerPointToContainerPoint([nums[nums.length - 2], nums[nums.length - 1]]);
    const ca = centro(V.marcadores[u]), cb = centro(V.marcadores[v]);
    const d1 = Math.hypot(ca[0] - pa.x, ca[1] - pa.y), d2 = Math.hypot(cb[0] - pb.x, cb[1] - pb.y);
    filas.push({tipo: "arista", id: k, dx: d1, dy: d2, dist: Math.max(d1, d2)});
  }
  const peor = filas.slice().sort((a, b) => b.dist - a.dist);
  const de = (t) => filas.filter((f) => f.tipo === t);
  return {zoom: mapa.getZoom(), tam: [Math.round(caja.width), Math.round(caja.height)],
          nodos: de("nodo").length, aristas: de("arista").length,
          fallosNodos: de("nodo").filter((f) => f.dist > 1).length,
          fallosAristas: de("arista").filter((f) => f.dist > 1).length,
          maximo: peor[0].dist, peor: peor.slice(0, 2).map((f) => f.tipo + " " + f.id + " " + f.dist.toFixed(3))};
};
