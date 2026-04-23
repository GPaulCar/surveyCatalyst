from pathlib import Path
import json

ROOT = Path.cwd()
BOOT_PATH = ROOT / "app" / "static" / "ui_boot.js"
MANIFEST_PATH = ROOT / "app" / "static" / "ui_manifest.json"

UI_BOOT = """async function fetchJson(url, options = {}) {
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
};

function badge(on) {
  return `<span style="display:inline-block;padding:4px 10px;border-radius:999px;font-weight:700;background:${on ? '#16a34a' : '#dc2626'};color:white;">${on ? 'ON' : 'OFF'}</span>`;
}

function compactButton(id, label) {
  return `<button id="${id}" type="button" style="width:auto;padding:10px 14px;margin:0 8px 8px 0;">${label}</button>`;
}

function section(title, body) {
  return `<div class="tabItem"><div style="font-weight:700;margin-bottom:10px;">${title}</div>${body}</div>`;
}

function renderManage() {
  const sys = state.system || { db: false, api: false };
  return `
    <div class="tabTitle">Manage</div>
    ${section('System', `
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;"><span>Database</span>${badge(!!sys.db)}</div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;"><span>API</span>${badge(!!sys.api)}</div>
      <div>${compactButton('sysStartBtn','Start')}${compactButton('sysRestartBtn','Restart')}${compactButton('sysStatusBtn','Refresh')}</div>
    `)}
    ${section('Surveys', `
      <div style="margin-bottom:8px;">
        <select id="surveySelect" style="width:100%;padding:10px;border-radius:10px;border:1px solid #cbd5e1;background:#fff;">
          <option value="">Select survey</option>
          ${state.surveys.map(s => `<option value="${s.id}" ${String(state.activeSurveyId)===String(s.id)?'selected':''}>${(s.title || s.name || ('Survey ' + s.id))}</option>`).join('')}
        </select>
      </div>
      <div>${compactButton('surveyRefreshBtn','Refresh surveys')}${compactButton('surveyLoadBtn','Set active')}</div>
    `)}
  `;
}

function renderLayers() {
  const grouped = {};
  for (const layer of state.layers) {
    const meta = layer.metadata || {};
    const group = meta.subgroup || layer.layer_group || 'other';
    if (!grouped[group]) grouped[group] = [];
    grouped[group].push(layer);
  }
  let html = '<div class="tabTitle">Layers</div>';
  Object.keys(grouped).sort().forEach(group => {
    html += section(group.replaceAll('_',' ').replace(/\b\w/g, c => c.toUpperCase()), grouped[group].map(layer => `
      <label style="display:flex;align-items:flex-start;gap:10px;margin-bottom:8px;">
        <input class="layerToggle" type="checkbox" data-layer="${layer.layer_key}" ${layer.is_visible ? 'checked' : ''}>
        <span>
          <div style="font-weight:600;">${layer.layer_name || layer.layer_key}</div>
          <div class="muted">${layer.geometry_type || ''}</div>
        </span>
      </label>
    `).join(''));
  });
  return html;
}

function renderHierarchy() {
  return `
    <div class="tabTitle">Hierarchy</div>
    ${section('Surveys', state.surveys.length ? state.surveys.map(s => `
      <div style="padding:8px 0;border-bottom:1px solid #e5e7eb;">
        <strong>${s.title || s.name || ('Survey ' + s.id)}</strong><br>
        <span class="muted">id: ${s.id}</span>
      </div>
    `).join('') : '<div class="muted">No surveys loaded.</div>')}
  `;
}

function renderDetails() {
  return `
    <div class="tabTitle">Details</div>
    ${section('Selection', `
      <div id="detailsContent" class="muted">Selection wiring comes next.</div>
    `)}
  `;
}

function mountLeft() {
  const left = document.getElementById('left-panel');
  left.innerHTML = renderManage();
  bindManageEvents();
}

function mountRight() {
  const right = document.getElementById('right-panel');
  right.innerHTML = renderLayers() + renderHierarchy() + renderDetails();
  bindLayerEvents();
}

function setStatusText(text) {
  const banner = document.getElementById('selection-banner');
  banner.textContent = text;
  banner.style.display = text ? 'flex' : 'none';
}

async function refreshSystem() {
  try {
    const health = await fetch('/health', { cache: 'no-store' });
    state.system = { db: true, api: health.ok };
  } catch {
    state.system = { db: false, api: false };
  }
  mountLeft();
}

async function refreshSurveys() {
  try {
    const payload = await fetchJson('/api/surveys');
    state.surveys = Array.isArray(payload) ? payload : (payload.items || payload.surveys || []);
  } catch (err) {
    state.surveys = [];
    setStatusText('Survey load failed');
  }
  mountLeft();
  mountRight();
}

async function refreshLayers() {
  try {
    const payload = await fetchJson('/api/layers');
    state.layers = Array.isArray(payload) ? payload : (payload.layers || []);
  } catch (err) {
    state.layers = [];
    setStatusText('Layer load failed');
  }
  mountRight();
}

async function systemStart() {
  setStatusText('Use python scripts/system_control.py start');
  setTimeout(() => setStatusText(''), 2500);
}

async function systemRestart() {
  setStatusText('Use python scripts/system_control.py restart');
  setTimeout(() => setStatusText(''), 2500);
}

function bindManageEvents() {
  const startBtn = document.getElementById('sysStartBtn');
  const restartBtn = document.getElementById('sysRestartBtn');
  const statusBtn = document.getElementById('sysStatusBtn');
  const surveyRefreshBtn = document.getElementById('surveyRefreshBtn');
  const surveyLoadBtn = document.getElementById('surveyLoadBtn');
  const surveySelect = document.getElementById('surveySelect');

  if (startBtn) startBtn.onclick = systemStart;
  if (restartBtn) restartBtn.onclick = systemRestart;
  if (statusBtn) statusBtn.onclick = refreshSystem;
  if (surveyRefreshBtn) surveyRefreshBtn.onclick = refreshSurveys;
  if (surveyLoadBtn) surveyLoadBtn.onclick = () => {
    if (surveySelect) {
      state.activeSurveyId = surveySelect.value || null;
      setStatusText(state.activeSurveyId ? `Active survey set: ${state.activeSurveyId}` : '');
    }
  };
}

function bindLayerEvents() {
  document.querySelectorAll('.layerToggle').forEach(el => {
    el.onchange = () => {
      const key = el.getAttribute('data-layer');
      const layer = state.layers.find(x => String(x.layer_key) === String(key));
      if (layer) layer.is_visible = el.checked;
      setStatusText(`Layer toggle tracked: ${key}`);
      setTimeout(() => setStatusText(''), 1500);
    };
  });
}

const map = new ol.Map({
  target: 'map',
  layers: [new ol.layer.Tile({ source: new ol.source.OSM() })],
  view: new ol.View({
    center: ol.proj.fromLonLat([11, 48]),
    zoom: 7
  })
});

async function initUI() {
  state.manifest = await loadManifest();
  mountLeft();
  mountRight();
  await refreshSystem();
  await refreshSurveys();
  await refreshLayers();
}

initUI().catch(err => {
  console.error(err);
  document.getElementById('left-panel').innerHTML = `<div class="tabTitle">UI boot failed</div><pre>${String(err)}</pre>`;
});
"""

MANIFEST = {
  "left_tabs": [
    {"id": "manage", "title": "Manage"},
    {"id": "create", "title": "Create"},
    {"id": "edit", "title": "Edit"},
    {"id": "export", "title": "Export"}
  ],
  "right_tabs": [
    {"id": "layers", "title": "Layers"},
    {"id": "hierarchy", "title": "Hierarchy"},
    {"id": "details", "title": "Details"}
  ]
}

def main() -> None:
    BOOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    BOOT_PATH.write_text(UI_BOOT, encoding="utf-8")
    print(f"[OK] wrote {BOOT_PATH}")

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(MANIFEST, indent=2), encoding="utf-8")
    print(f"[OK] wrote {MANIFEST_PATH}")

    print("[DONE] UI modules generated")
    print("Restart the API and hard refresh the browser (Ctrl + F5).")

if __name__ == "__main__":
    main()
