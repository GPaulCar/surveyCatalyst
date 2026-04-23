from pathlib import Path

ROOT = Path.cwd()
BOOT_PATH = ROOT / "app" / "static" / "ui_boot.js"

UI_BOOT = r'''async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return await res.json();
}

async function loadManifest() {
  const res = await fetch('/static/ui_manifest.json', { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to load ui_manifest.json');
  return await res.json();
}

const state = {
  manifest: null,
  system: null,
  surveys: [],
  activeSurveyId: null,
  layers: [],
  leftTab: 'manage',
  rightTab: 'layers',
  leftOpen: true,
  rightOpen: true,
  surveyFeatures: null,
  selection: null,
};

let map;
let surveyVectorSource;
let surveyVectorLayer;
let selectionSource;
let selectionLayer;
let contextTileLayers = {};

function injectStyles() {
  if (document.getElementById('ui3Styles')) return;
  const style = document.createElement('style');
  style.id = 'ui3Styles';
  style.textContent = `
    #ui-root { pointer-events:none; }
    .ui3Drawer {
      position:absolute;
      top:16px;
      bottom:16px;
      background:rgba(245,247,251,0.96);
      backdrop-filter: blur(10px);
      border:1px solid rgba(160,174,192,0.45);
      border-radius:18px;
      box-shadow:0 18px 50px rgba(15,23,42,0.18);
      color:#1f2937;
      overflow:hidden;
      pointer-events:auto;
      transition:transform 0.2s ease, opacity 0.2s ease;
      display:flex;
      flex-direction:column;
    }
    #left-panel.ui3Drawer { left:16px; width:390px; }
    #right-panel.ui3Drawer { right:16px; width:460px; }
    .ui3Drawer.closed-left { transform:translateX(calc(-100% - 18px)); }
    .ui3Drawer.closed-right { transform:translateX(calc(100% + 18px)); }
    .ui3DrawerHeader {
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:10px;
      padding:14px 16px 10px 16px;
      border-bottom:1px solid #dbe4ef;
      background:linear-gradient(180deg,#ffffff 0%,#f8fafc 100%);
    }
    .ui3DrawerTitle { font-size:18px; font-weight:800; color:#0f172a; }
    .ui3DrawerSub { font-size:12px; color:#64748b; }
    .ui3DrawerBody { flex:1; overflow:auto; padding:14px 16px 16px 16px; }
    .ui3TabsRail {
      position:absolute;
      top:50%;
      transform:translateY(-50%);
      z-index:26;
      display:flex;
      flex-direction:column;
      gap:8px;
      pointer-events:auto;
    }
    #leftRail { left:8px; }
    #rightRail { right:8px; }
    .ui3RailBtn {
      width:42px;
      min-height:108px;
      border:none;
      border-radius:14px;
      background:rgba(255,255,255,0.94);
      box-shadow:0 12px 24px rgba(15,23,42,0.14);
      color:#334155;
      cursor:pointer;
      font-weight:800;
      writing-mode:vertical-rl;
      text-orientation:mixed;
      padding:10px 6px;
    }
    .ui3RailBtn.active { background:#1d4ed8; color:#fff; }
    .ui3RailBtn.toggle { background:#0f172a; color:#fff; min-height:82px; }
    .ui3Section {
      border:1px solid #dbe4ef;
      border-radius:14px;
      background:#fff;
      padding:12px;
      margin-bottom:12px;
    }
    .ui3SectionTitle { font-weight:800; color:#0f172a; margin-bottom:10px; }
    .ui3Row { display:flex; justify-content:space-between; align-items:center; gap:10px; }
    .ui3Badge {
      display:inline-block; padding:4px 10px; border-radius:999px; font-weight:800; color:#fff; font-size:12px;
    }
    .ui3Badge.on { background:#16a34a; }
    .ui3Badge.off { background:#dc2626; }
    .ui3Btn {
      width:auto; margin:0 8px 8px 0; padding:10px 14px; border:none; border-radius:10px;
      background:#1d4ed8; color:#fff; font-weight:700; cursor:pointer;
    }
    .ui3Btn.secondary { background:#e2e8f0; color:#0f172a; }
    .ui3Select {
      width:100%; padding:10px; border-radius:10px; border:1px solid #cbd5e1; background:#fff;
    }
    .ui3ListItem {
      border:1px solid #e2e8f0; border-radius:12px; background:#fff; padding:10px 12px; margin-bottom:8px;
    }
    .ui3ListItemTitle { font-weight:700; color:#0f172a; }
    .ui3Muted { color:#64748b; font-size:12px; }
    .ui3ToggleRow { display:flex; align-items:flex-start; gap:10px; margin-bottom:10px; }
    .ui3ToggleRow input { margin-top:3px; }
    #selection-banner {
      display:none;
      position:absolute;
      top:16px; left:50%; transform:translateX(-50%);
      z-index:30; pointer-events:auto;
      align-items:center; gap:12px;
      padding:12px 16px; border-radius:14px;
      background:#f59e0b; color:#111827; font-weight:800;
      box-shadow:0 12px 28px rgba(15,23,42,0.22);
    }
  `;
  document.head.appendChild(style);
}

function shell() {
  injectStyles();
  const left = document.getElementById('left-panel');
  const right = document.getElementById('right-panel');
  left.className = 'ui3Drawer' + (state.leftOpen ? '' : ' closed-left');
  right.className = 'ui3Drawer' + (state.rightOpen ? '' : ' closed-right');

  let leftRail = document.getElementById('leftRail');
  let rightRail = document.getElementById('rightRail');

  if (!leftRail) {
    leftRail = document.createElement('div');
    leftRail.id = 'leftRail';
    leftRail.className = 'ui3TabsRail';
    document.getElementById('ui-root').appendChild(leftRail);
  }
  if (!rightRail) {
    rightRail = document.createElement('div');
    rightRail.id = 'rightRail';
    rightRail.className = 'ui3TabsRail';
    document.getElementById('ui-root').appendChild(rightRail);
  }

  const leftTabs = state.manifest.left_tabs || [];
  const rightTabs = state.manifest.right_tabs || [];

  leftRail.innerHTML = `
    ${leftTabs.map(tab => `<button class="ui3RailBtn ${state.leftTab===tab.id?'active':''}" data-left-tab="${tab.id}" type="button">${tab.title}</button>`).join('')}
    <button class="ui3RailBtn toggle" id="leftToggleBtn" type="button">${state.leftOpen ? 'Hide' : 'Show'}</button>
  `;
  rightRail.innerHTML = `
    ${rightTabs.map(tab => `<button class="ui3RailBtn ${state.rightTab===tab.id?'active':''}" data-right-tab="${tab.id}" type="button">${tab.title}</button>`).join('')}
    <button class="ui3RailBtn toggle" id="rightToggleBtn" type="button">${state.rightOpen ? 'Hide' : 'Show'}</button>
  `;

  leftRail.querySelectorAll('[data-left-tab]').forEach(btn => {
    btn.onclick = () => { state.leftTab = btn.getAttribute('data-left-tab'); state.leftOpen = true; render(); };
  });
  rightRail.querySelectorAll('[data-right-tab]').forEach(btn => {
    btn.onclick = () => { state.rightTab = btn.getAttribute('data-right-tab'); state.rightOpen = true; render(); };
  });
  document.getElementById('leftToggleBtn').onclick = () => { state.leftOpen = !state.leftOpen; render(); };
  document.getElementById('rightToggleBtn').onclick = () => { state.rightOpen = !state.rightOpen; render(); };
}

function badge(on) {
  return `<span class="ui3Badge ${on ? 'on' : 'off'}">${on ? 'ON' : 'OFF'}</span>`;
}

function setBanner(text) {
  const banner = document.getElementById('selection-banner');
  if (!banner) return;
  if (!text) {
    banner.style.display = 'none';
    banner.textContent = '';
    return;
  }
  banner.style.display = 'flex';
  banner.textContent = text;
}

function drawerFrame(title, subtitle, bodyHtml) {
  return `
    <div class="ui3DrawerHeader">
      <div>
        <div class="ui3DrawerTitle">${title}</div>
        <div class="ui3DrawerSub">${subtitle}</div>
      </div>
    </div>
    <div class="ui3DrawerBody">${bodyHtml}</div>
  `;
}

function detailsHtml() {
  if (!state.selection) return `<div class="ui3Muted">No feature selected.</div>`;
  const props = state.selection.properties || {};
  const rows = Object.keys(props).sort().map(key => `
    <div class="ui3Row" style="align-items:flex-start;border-top:1px solid #e5e7eb;padding-top:8px;margin-top:8px;">
      <strong style="max-width:40%;">${key}</strong>
      <span style="max-width:58%;word-break:break-word;">${String(props[key])}</span>
    </div>
  `).join('');
  return `
    <div class="ui3ListItem">
      <div class="ui3ListItemTitle">${state.selection.title || state.selection.layer || 'Selected feature'}</div>
      <div class="ui3Muted">layer: ${state.selection.layer || ''} | source_id: ${state.selection.source_id || ''}</div>
      ${rows || '<div class="ui3Muted">No properties.</div>'}
    </div>
  `;
}

function renderManage() {
  const sys = state.system || { db: false, api: false };
  return drawerFrame('Manage', 'System and survey workspace', `
    <div class="ui3Section">
      <div class="ui3SectionTitle">System</div>
      <div class="ui3Row"><span>Database</span>${badge(!!sys.db)}</div>
      <div class="ui3Row" style="margin-top:8px;"><span>API</span>${badge(!!sys.api)}</div>
      <div style="margin-top:12px;">
        <button class="ui3Btn secondary" id="sysRefreshBtn" type="button">Refresh status</button>
        <button class="ui3Btn secondary" id="sysHealthBtn" type="button">Health</button>
      </div>
      <div class="ui3Muted">System control remains Python-driven.</div>
    </div>
    <div class="ui3Section">
      <div class="ui3SectionTitle">Surveys</div>
      <select id="surveySelect" class="ui3Select">
        <option value="">Select survey</option>
        ${state.surveys.map(s => `<option value="${s.id}" ${String(state.activeSurveyId)===String(s.id)?'selected':''}>${(s.title || s.name || ('Survey ' + s.id))}</option>`).join('')}
      </select>
      <div style="margin-top:12px;">
        <button class="ui3Btn" id="surveySetBtn" type="button">Set active</button>
        <button class="ui3Btn secondary" id="surveyRefreshBtn" type="button">Refresh surveys</button>
        <button class="ui3Btn secondary" id="surveyZoomBtn" type="button">Zoom to</button>
        <button class="ui3Btn secondary" id="surveyFeaturesBtn" type="button">Load features</button>
      </div>
    </div>
  `);
}

function renderCreate() {
  return drawerFrame('Create', 'Authoring workflow shell', `<div class="ui3Section"><div class="ui3SectionTitle">Create workflow</div><div class="ui3Muted">Create/edit/export UI remains next. This bundle focuses on map integration.</div></div>`);
}

function renderEdit() {
  return drawerFrame('Edit', 'Selection-aware editing shell', `<div class="ui3Section"><div class="ui3SectionTitle">Edit workflow</div><div class="ui3Muted">Selection is now active on the map. Editing wiring is next.</div></div>`);
}

function renderExport() {
  return drawerFrame('Export', 'Export workflow shell', `<div class="ui3Section"><div class="ui3SectionTitle">Exports</div><div class="ui3Muted">Export UI is next. Current backend export endpoints remain available.</div></div>`);
}

function renderLayers() {
  const grouped = {};
  for (const layer of state.layers) {
    const meta = layer.metadata || {};
    const group = meta.subgroup || layer.layer_group || 'other';
    if (!grouped[group]) grouped[group] = [];
    grouped[group].push(layer);
  }
  const body = Object.keys(grouped).sort().map(group => `
    <div class="ui3Section">
      <div class="ui3SectionTitle">${group.replaceAll('_',' ').replace(/\b\w/g, c => c.toUpperCase())}</div>
      ${grouped[group].map(layer => `
        <label class="ui3ToggleRow">
          <input class="layerToggle" type="checkbox" data-layer="${layer.layer_key}" ${layer.is_visible ? 'checked' : ''}>
          <span>
            <div class="ui3ListItemTitle">${layer.layer_name || layer.layer_key}</div>
            <div class="ui3Muted">${layer.geometry_type || ''}</div>
          </span>
        </label>
      `).join('')}
    </div>
  `).join('');
  return drawerFrame('Layers', 'Context and working layers', body || `<div class="ui3Section"><div class="ui3Muted">No layers loaded.</div></div>`);
}

function renderHierarchy() {
  const body = state.surveys.length ? state.surveys.map(s => `
    <div class="ui3ListItem">
      <div class="ui3ListItemTitle">${s.title || s.name || ('Survey ' + s.id)}</div>
      <div class="ui3Muted">id: ${s.id}</div>
    </div>
  `).join('') : '<div class="ui3Section"><div class="ui3Muted">No surveys loaded.</div></div>';
  return drawerFrame('Hierarchy', 'Survey and object structure', body);
}

function renderDetails() {
  return drawerFrame('Details', 'Selection and record details', `<div class="ui3Section"><div class="ui3SectionTitle">Selection</div><div id="detailsContent">${detailsHtml()}</div></div>`);
}

function leftContent() {
  if (state.leftTab === 'manage') return renderManage();
  if (state.leftTab === 'create') return renderCreate();
  if (state.leftTab === 'edit') return renderEdit();
  if (state.leftTab === 'export') return renderExport();
  return drawerFrame('Panel', '', '');
}

function rightContent() {
  if (state.rightTab === 'layers') return renderLayers();
  if (state.rightTab === 'hierarchy') return renderHierarchy();
  if (state.rightTab === 'details') return renderDetails();
  return drawerFrame('Panel', '', '');
}

function ensureMapLayers() {
  if (!surveyVectorSource) {
    surveyVectorSource = new ol.source.Vector();
    surveyVectorLayer = new ol.layer.Vector({
      source: surveyVectorSource,
      style: feature => {
        const role = feature.get('feature_role');
        if (role === 'survey_boundary') {
          return new ol.style.Style({
            stroke: new ol.style.Stroke({ color: '#2563eb', width: 3 }),
            fill: new ol.style.Fill({ color: 'rgba(37,99,235,0.08)' })
          });
        }
        return new ol.style.Style({
          stroke: new ol.style.Stroke({ color: '#0f766e', width: 2 }),
          fill: new ol.style.Fill({ color: 'rgba(15,118,110,0.15)' }),
          image: new ol.style.Circle({
            radius: 6,
            fill: new ol.style.Fill({ color: '#0f766e' }),
            stroke: new ol.style.Stroke({ color: '#ffffff', width: 2 })
          })
        });
      }
    });
    surveyVectorLayer.setZIndex(40);
    map.addLayer(surveyVectorLayer);
  }

  if (!selectionSource) {
    selectionSource = new ol.source.Vector();
    selectionLayer = new ol.layer.Vector({
      source: selectionSource,
      style: new ol.style.Style({
        stroke: new ol.style.Stroke({ color: '#f59e0b', width: 4 }),
        fill: new ol.style.Fill({ color: 'rgba(245,158,11,0.18)' }),
        image: new ol.style.Circle({
          radius: 8,
          fill: new ol.style.Fill({ color: '#f59e0b' }),
          stroke: new ol.style.Stroke({ color: '#fff', width: 2 })
        })
      })
    });
    selectionLayer.setZIndex(1000);
    map.addLayer(selectionLayer);
  }
}

function updateSelectionFromFeature(feature) {
  if (!feature) {
    state.selection = null;
    if (selectionSource) selectionSource.clear();
    setBanner('');
    render();
    return;
  }
  const props = feature.getProperties();
  state.selection = {
    layer: props.layer || props.layer_key || props.source_table || '',
    source_id: props.source_id || props.id || '',
    title: props.title || props.name || props.feature_role || 'Selected feature',
    properties: props
  };
  if (selectionSource) {
    selectionSource.clear();
    selectionSource.addFeature(feature.clone());
  }
  setBanner(`Selected: ${state.selection.title}`);
  render();
}

async function loadSurveyFeaturesToMap(surveyId, zoomTo = false) {
  const geojson = await fetchJson(`/api/surveys/${surveyId}/features?limit=20000`);
  ensureMapLayers();
  const format = new ol.format.GeoJSON();
  const features = format.readFeatures(geojson, {
    featureProjection: map.getView().getProjection()
  });
  surveyVectorSource.clear();
  if (features.length) surveyVectorSource.addFeatures(features);
  state.surveyFeatures = features.length;
  if (zoomTo && features.length) {
    const extent = ol.extent.createEmpty();
    features.forEach(f => ol.extent.extend(extent, f.getGeometry().getExtent()));
    map.getView().fit(extent, { padding: [40, 40, 40, 40], duration: 300, maxZoom: 18 });
  }
  setBanner(`Loaded ${features.length} survey features.`);
  setTimeout(() => setBanner(''), 1500);
}

function syncContextTileLayers() {
  const existing = Object.keys(contextTileLayers);
  for (const key of existing) {
    const stillExists = state.layers.some(layer => layer.layer_key === key);
    if (!stillExists) {
      map.removeLayer(contextTileLayers[key]);
      delete contextTileLayers[key];
    }
  }

  state.layers.forEach(layer => {
    if (!contextTileLayers[layer.layer_key]) {
      const tileLayer = new ol.layer.VectorTile({
        visible: !!layer.is_visible,
        source: new ol.source.VectorTile({
          format: new ol.format.MVT(),
          url: `/api/layers/${layer.layer_key}/tiles/{z}/{x}/{y}.mvt`
        }),
        style: new ol.style.Style({
          stroke: new ol.style.Stroke({ color: '#64748b', width: 1.5 }),
          fill: new ol.style.Fill({ color: 'rgba(100,116,139,0.08)' }),
          image: new ol.style.Circle({ radius: 4, fill: new ol.style.Fill({ color: '#64748b' }) })
        })
      });
      tileLayer.set('layer_key', layer.layer_key);
      tileLayer.setZIndex(10 + (layer.sort_order || 0));
      contextTileLayers[layer.layer_key] = tileLayer;
      map.addLayer(tileLayer);
    } else {
      contextTileLayers[layer.layer_key].setVisible(!!layer.is_visible);
      contextTileLayers[layer.layer_key].setZIndex(10 + (layer.sort_order || 0));
    }
  });
}

function bindMapSelection() {
  map.on('singleclick', evt => {
    let selected = null;
    if (surveyVectorSource) {
      map.forEachFeatureAtPixel(evt.pixel, (feature, layer) => {
        if (layer === surveyVectorLayer && !selected) selected = feature;
      });
    }
    if (!selected) {
      map.forEachFeatureAtPixel(evt.pixel, feature => {
        if (!selected) selected = feature;
      });
    }
    updateSelectionFromFeature(selected);
  });
}

function bindManageEvents() {
  const refreshBtn = document.getElementById('sysRefreshBtn');
  const healthBtn = document.getElementById('sysHealthBtn');
  const surveyRefreshBtn = document.getElementById('surveyRefreshBtn');
  const surveySetBtn = document.getElementById('surveySetBtn');
  const surveyZoomBtn = document.getElementById('surveyZoomBtn');
  const surveyFeaturesBtn = document.getElementById('surveyFeaturesBtn');
  const surveySelect = document.getElementById('surveySelect');

  if (refreshBtn) refreshBtn.onclick = refreshSystem;
  if (healthBtn) healthBtn.onclick = async () => {
    try {
      const res = await fetch('/health', { cache: 'no-store' });
      setBanner(res.ok ? '127.0.0.1:8000 healthy' : 'Health check failed');
      setTimeout(() => setBanner(''), 2000);
    } catch {
      setBanner('Health check failed');
      setTimeout(() => setBanner(''), 2000);
    }
  };
  if (surveyRefreshBtn) surveyRefreshBtn.onclick = refreshSurveys;
  if (surveySetBtn) surveySetBtn.onclick = () => {
    state.activeSurveyId = surveySelect && surveySelect.value ? surveySelect.value : null;
    setBanner(state.activeSurveyId ? `Active survey set: ${state.activeSurveyId}` : '');
    setTimeout(() => setBanner(''), 1500);
  };
  if (surveyZoomBtn) surveyZoomBtn.onclick = async () => {
    const surveyId = surveySelect && surveySelect.value ? surveySelect.value : state.activeSurveyId;
    if (!surveyId) {
      setBanner('Select a survey first.');
      setTimeout(() => setBanner(''), 1500);
      return;
    }
    try {
      await loadSurveyFeaturesToMap(surveyId, true);
    } catch (err) {
      setBanner(`Zoom failed: ${err.message}`);
      setTimeout(() => setBanner(''), 1500);
    }
  };
  if (surveyFeaturesBtn) surveyFeaturesBtn.onclick = async () => {
    const surveyId = surveySelect && surveySelect.value ? surveySelect.value : state.activeSurveyId;
    if (!surveyId) {
      setBanner('Select a survey first.');
      setTimeout(() => setBanner(''), 1500);
      return;
    }
    try {
      await loadSurveyFeaturesToMap(surveyId, false);
    } catch (err) {
      setBanner(`Feature load failed: ${err.message}`);
      setTimeout(() => setBanner(''), 1500);
    }
  };
}

function bindLayerEvents() {
  document.querySelectorAll('.layerToggle').forEach(el => {
    el.onchange = () => {
      const key = el.getAttribute('data-layer');
      const layer = state.layers.find(x => String(x.layer_key) === String(key));
      if (layer) {
        layer.is_visible = el.checked;
        if (contextTileLayers[key]) contextTileLayers[key].setVisible(el.checked);
      }
      setBanner(`Layer ${el.checked ? 'shown' : 'hidden'}: ${key}`);
      setTimeout(() => setBanner(''), 1200);
    };
  });
}

function render() {
  shell();
  document.getElementById('left-panel').innerHTML = leftContent();
  document.getElementById('right-panel').innerHTML = rightContent();
  bindManageEvents();
  bindLayerEvents();
}

async function refreshSystem() {
  try {
    const health = await fetch('/health', { cache: 'no-store' });
    state.system = { db: true, api: health.ok };
  } catch {
    state.system = { db: false, api: false };
  }
  render();
}

async function refreshSurveys() {
  try {
    const payload = await fetchJson('/api/surveys');
    state.surveys = Array.isArray(payload) ? payload : (payload.items || payload.surveys || []);
  } catch {
    state.surveys = [];
    setBanner('Survey load failed');
    setTimeout(() => setBanner(''), 1500);
  }
  render();
}

async function refreshLayers() {
  try {
    const payload = await fetchJson('/api/layers');
    state.layers = Array.isArray(payload) ? payload : (payload.layers || []);
    syncContextTileLayers();
  } catch {
    state.layers = [];
    setBanner('Layer load failed');
    setTimeout(() => setBanner(''), 1500);
  }
  render();
}

function initMap() {
  map = new ol.Map({
    target: 'map',
    layers: [new ol.layer.Tile({ source: new ol.source.OSM() })],
    view: new ol.View({ center: ol.proj.fromLonLat([11, 48]), zoom: 7 })
  });
  ensureMapLayers();
  bindMapSelection();
}

async function initUI() {
  state.manifest = await loadManifest();
  initMap();
  render();
  await refreshSystem();
  await refreshSurveys();
  await refreshLayers();
}

initUI().catch(err => {
  console.error(err);
  document.getElementById('left-panel').innerHTML = `<div class="ui3DrawerHeader"><div><div class="ui3DrawerTitle">UI boot failed</div></div></div><div class="ui3DrawerBody"><pre>${String(err)}</pre></div>`;
});
'''

def main() -> None:
    if not BOOT_PATH.exists():
        raise FileNotFoundError(BOOT_PATH)
    BOOT_PATH.write_text(UI_BOOT, encoding='utf-8')
    print(f"[OK] updated {BOOT_PATH}")
    print("[DONE] map integration bundle applied")

if __name__ == "__main__":
    main()
