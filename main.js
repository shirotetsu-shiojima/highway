// 高速道路マップ(Web版) — 路線網の描画とズーム別の視認性制御
(async () => {
  const C = window.APP_CONFIG;
  const FONT = C.fontStack;

  const baseStyle = C.styleUrl || {
    version: 8,
    glyphs: C.fallbackGlyphs,
    sources: {},
    layers: [{ id: 'bg', type: 'background', paint: { 'background-color': '#eef1f4' } }],
  };

  const map = new maplibregl.Map({
    container: 'map', style: baseStyle, center: C.center, zoom: C.zoom,
    minZoom: C.minZoom, maxZoom: C.maxZoom, maxBounds: C.bounds,
    hash: true, attributionControl: { compact: true },
    // CJK 文字は端末のフォントで描画(グリフPBFを持たない背景でも日本語が出る)
    localIdeographFontFamily: "'Noto Sans JP','Hiragino Sans','Yu Gothic','Meiryo','Noto Sans CJK JP',sans-serif",
  });
  window.__map = map;
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), 'bottom-right');
  map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left');

  const [roads, fac, names] = await Promise.all(
    ['roads', 'facilities', 'roadnames'].map(n => fetch(`./data/${n}.geojson`).then(r => r.json())));
  await new Promise(res => (map.loaded() ? res() : map.once('load', res)));

  // ---- 施設の優先度(衝突時に残す順。小さいほど優先) ----
  for (const f of fac.features) {
    const p = f.properties;
    p.prio = p.kind === '路線番号' ? 0 : p.jct ? 1 : p.kind === 'SA/PA' ? 2
      : p.kind === 'スマートIC' ? 5 : p.kind === '料金所' ? 6 : 3;
  }

  // ---- ラベル箱の画像(枠固定で伸縮する 9-slice) ----
  const fills = [...new Set(fac.features.map(f => f.properties.fill))];
  for (const fill of fills) {
    const S = 16, cv = document.createElement('canvas'); cv.width = cv.height = S;
    const g = cv.getContext('2d');
    g.fillStyle = '#000'; g.fillRect(0, 0, S, S);
    g.fillStyle = fill; g.fillRect(2, 2, S - 4, S - 4);
    map.addImage(`box${fill}`, g.getImageData(0, 0, S, S),
      { pixelRatio: 2, stretchX: [[3, 13]], stretchY: [[3, 13]], content: [3, 3, 13, 13] });
  }

  map.addSource('roads', { type: 'geojson', data: roads });
  map.addSource('fac', { type: 'geojson', data: fac });
  map.addSource('names', { type: 'geojson', data: names });

  // ---- 道路: 線幅はズームに応じて拡大。細い線は低ズームで太らせすぎない ----
  const W = k => ['interpolate', ['linear'], ['zoom'],
    4.5, ['*', ['get', 'w'], 0.38 * k], 7, ['*', ['get', 'w'], 0.75 * k], 9, ['*', ['get', 'w'], 1.25 * k],
    11, ['*', ['get', 'w'], 2.1 * k], 13, ['*', ['get', 'w'], 3.5 * k], 15, ['*', ['get', 'w'], 5.5 * k]];
  const road = (id, filter, paint, extra = {}) => map.addLayer({
    id, type: 'line', source: 'roads', filter,
    layout: { 'line-cap': 'round', 'line-join': 'round', ...(extra.layout || {}) },
    paint, ...(extra.minzoom ? { minzoom: extra.minzoom } : {}) });

  road('road-grey', ['==', ['get', 'k'], 'grey'],
    { 'line-color': '#a9a9a9', 'line-width': W(0.9), 'line-dasharray': [2, 1.5], 'line-opacity': 0.9 }, { minzoom: 6.5 });
  road('road-main', ['all', ['!=', ['get', 'k'], 'grey'], ['!=', ['get', 'k'], 'urban']],
    { 'line-color': ['get', 'c'], 'line-width': W(1.0) });
  // 二重線の白い芯(中ズーム以上で現れる)
  road('road-core', ['all', ['!=', ['get', 'k'], 'grey'], ['!=', ['get', 'k'], 'urban']],
    { 'line-color': '#fff', 'line-width': W(0.34),
      'line-opacity': ['interpolate', ['linear'], ['zoom'], 8.5, 0, 10, 0.95] });
  road('road-urban', ['==', ['get', 'k'], 'urban'],
    { 'line-color': ['get', 'c'], 'line-width': W(0.95) }, { minzoom: 7.5 });

  // ---- 施設: 重要度ごとに minzoom を分けて段階的に出す ----
  const tiers = [...new Set(fac.features.map(f => f.properties.z))].sort((a, b) => a - b);
  const sizeBy = (a, b, c) => ['interpolate', ['linear'], ['zoom'], 8, a, 11.5, b, 14.5, c];
  for (const T of tiers) {
    const sel = ['==', ['get', 'z'], T];
    map.addLayer({
      id: `fd-${T}`, type: 'circle', source: 'fac', minzoom: T,
      filter: ['all', sel, ['==', ['get', 'exact'], true], ['!=', ['get', 'kind'], '路線番号']],
      paint: {
        'circle-radius': sizeBy(1.6, 3.4, 5.5),
        'circle-color': ['case', ['get', 'jct'], '#3c3c3c', ['==', ['get', 'kind'], 'SA/PA'], '#1599ff', '#ffffff'],
        'circle-stroke-color': ['case', ['get', 'jct'], '#ffffff', '#4a4a4a'],
        'circle-stroke-width': sizeBy(0.5, 1, 1.4),
      } });
    map.addLayer({
      id: `fl-${T}`, type: 'symbol', source: 'fac', minzoom: T, filter: sel,
      layout: {
        'icon-image': ['concat', 'box', ['get', 'fill']],
        'icon-text-fit': 'both', 'icon-text-fit-padding': [1, 3, 1, 3],
        'text-field': ['get', 'name'], 'text-font': FONT,
        'text-size': ['interpolate', ['linear'], ['zoom'], 8, 9, 11.5, 11, 14.5, 14],
        'text-max-width': 12, 'text-padding': 2,
        'text-variable-anchor': ['top', 'bottom', 'right', 'left', 'top-right', 'top-left', 'bottom-right', 'bottom-left'],
        'text-radial-offset': 1.0, 'symbol-sort-key': ['get', 'prio'],
      },
      paint: { 'text-color': ['case', ['==', ['get', 'fill'], '#ffffff'], '#0b4a6e', '#ffffff'] } });
  }

  // ---- 路線番号のバッジ ----
  map.addLayer({
    id: 'route-badge', type: 'symbol', source: 'fac', minzoom: 7.5, filter: ['==', ['get', 'kind'], '路線番号'],
    layout: {
      'icon-image': ['concat', 'box', ['get', 'fill']], 'icon-text-fit': 'both', 'icon-text-fit-padding': [1, 3, 1, 3],
      'text-field': ['get', 'name'], 'text-font': FONT,
      'text-size': ['interpolate', ['linear'], ['zoom'], 7.5, 9, 12, 12], 'symbol-sort-key': 0, 'text-padding': 4 },
    paint: { 'text-color': '#fff' } });

  // ---- 道路名(線に沿った向きで) ----
  map.addLayer({
    id: 'road-names', type: 'symbol', source: 'names', minzoom: 8.2,
    layout: {
      'text-field': ['get', 'name'], 'text-font': FONT, 'text-rotate': ['get', 'rot'],
      'text-rotation-alignment': 'map', 'text-pitch-alignment': 'map', 'text-letter-spacing': 0.12,
      'text-size': ['interpolate', ['linear'], ['zoom'], 8.2, 9, 12, 13], 'text-padding': 8 },
    paint: { 'text-color': ['get', 'fill'], 'text-halo-color': 'rgba(255,255,255,.95)', 'text-halo-width': 1.6 } });

  // ---- UI ----
  const bind = (id, layers) => document.getElementById(id).addEventListener('change', e =>
    layers().forEach(l => map.setLayoutProperty(l, 'visibility', e.target.checked ? 'visible' : 'none')));
  const facLayers = () => [...tiers.flatMap(T => [`fd-${T}`, `fl-${T}`]), 'route-badge'];
  bind('t-grey', () => ['road-grey']);
  bind('t-urban', () => ['road-urban']);
  bind('t-fac', facLayers);
  bind('t-names', () => ['road-names']);
  const z = document.getElementById('zoom');
  const upd = () => { z.textContent = map.getZoom().toFixed(1); };
  map.on('zoom', upd); upd();
  document.body.dataset.ready = '1';
})();
