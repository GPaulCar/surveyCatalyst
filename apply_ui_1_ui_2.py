from __future__ import annotations

import json
from pathlib import Path

ROOT = Path.cwd()
HTML_PATH = ROOT / "app" / "openlayers_map.html"
API_PATH = ROOT / "src" / "api" / "app.py"

SELECTION_BANNER_HTML = """
  <div id="selectionBanner" class="selectionBanner hidden">
    <span id="selectionBannerText">No selection</span>
    <button id="clearSelectionBtn" type="button">Clear</button>
  </div>
"""

UI2_CSS = """
  body, html { overflow: hidden; }
  #appShell { position: fixed; inset: 0; background: #dbe4ef; }
  #map { position: absolute !important; inset: 0 !important; width: 100% !important; height: 100% !important; z-index: 0; }
  #leftPanel {
    position: absolute !important; left: 16px; top: 16px; bottom: 16px; width: 340px; max-width: 340px;
    overflow-y: auto; background: rgba(245, 247, 251, 0.94); backdrop-filter: blur(8px);
    border: 1px solid rgba(160, 174, 192, 0.45); border-radius: 18px; box-shadow: 0 18px 50px rgba(15, 23, 42, 0.18);
    z-index: 15; transition: transform 0.2s ease;
  }
  #leftPanel.drawerCollapsed { transform: translateX(calc(-100% - 24px)); }
  #panelToggleRail {
    position: absolute; left: 16px; top: 50%; transform: translateY(-50%); z-index: 16;
    display: flex; flex-direction: column; gap: 10px;
  }
  .panelToggleHandle {
    width: 42px; height: 120px; border-radius: 16px; border: 1px solid rgba(160, 174, 192, 0.45);
    background: rgba(245, 247, 251, 0.94); box-shadow: 0 12px 24px rgba(15, 23, 42, 0.12);
    writing-mode: vertical-rl; text-orientation: mixed; cursor: pointer; font-weight: 700; color: #38517a;
  }
  #rightPanel {
    position: absolute !important; top: 16px; right: 72px; bottom: 16px; width: 520px; overflow-y: auto;
    background: rgba(245, 247, 251, 0.94); backdrop-filter: blur(8px);
    border: 1px solid rgba(160, 174, 192, 0.45); border-radius: 18px; box-shadow: 0 18px 50px rgba(15, 23, 42, 0.18);
    z-index: 15; transition: transform 0.2s ease, opacity 0.2s ease;
  }
  #rightPanel.rightPanelCollapsed { transform: translateX(calc(100% + 32px)); opacity: 0; pointer-events: none; }
  .sideTabs {
    position: absolute !important; top: 50%; right: 16px; transform: translateY(-50%); z-index: 16;
  }
  .selectionBanner {
    position: absolute; top: 16px; left: 50%; transform: translateX(-50%); z-index: 25; display: flex;
    align-items: center; gap: 12px; background: #f59e0b; color: #111827; border-radius: 14px;
    box-shadow: 0 12px 28px rgba(15, 23, 42, 0.22); padding: 12px 18px; font-weight: 700;
  }
  .selectionBanner.hidden { display: none; }
  .selectionBanner button {
    width: auto; margin: 0; padding: 6px 10px; background: rgba(255,255,255,0.9); color: #111827;
  }
  .workspaceFooter {
    position: absolute; left: 16px; right: 16px; bottom: 16px; z-index: 17; display: flex; gap: 16px;
    align-items: center; background: rgba(15, 23, 42, 0.92); color: white; border-radius: 16px; padding: 12px 16px;
    box-shadow: 0 18px 36px rgba(15, 23, 42, 0.32);
  }
  .workspaceFooter .footerBlock { display: flex; align-items: center; gap: 10px; }
  .workspaceFooter label { margin: 0; color: #cbd5e1; font-size: 12px; }
  .workspaceFooter input[type="checkbox"] { width: auto; margin: 0; }
  #scratchNoteBtn { width: auto; margin: 0; padding: 10px 14px; }
"""

UI2_JS = """
let allowCrossSurveySelection = false;
let activeSelection = null;
let selectionHighlightLayer = null;
let leftDrawerCollapsed = false;
let rightDrawerCollapsed = false;

function ensureAppShell() {
  if (document.getElementById('appShell')) return;
  const appShell = document.createElement('div');
  appShell.id = 'appShell';
  const mapEl = document.getElementById('map');
  mapEl.parentNode.insertBefore(appShell, mapEl);
  appShell.appendChild(mapEl);

  const leftPanel = document.getElementById('leftPanel');
  if (leftPanel) appShell.appendChild(leftPanel);

  let rightPanel = document.getElementById('rightPanel');
  if (!rightPanel) {
    rightPanel = document.createElement('div');
    rightPanel.id = 'rightPanel';
    const tabs = document.querySelector('.sideTabs');
    if (tabs) {
      tabs.parentNode.insertBefore(rightPanel, tabs);
      appShell.appendChild(tabs);
    } else {
      appShell.appendChild(rightPanel);
    }
  }

  appShell.insertAdjacentHTML('beforeend', `__SELECTION_BANNER_HTML__`);
  const rail = document.createElement('div');
  rail.id = 'panelToggleRail';
  rail.innerHTML = `
    <button class="panelToggleHandle" id="manageToggle" type="button">Manage</button>
    <button class="panelToggleHandle" id="layersToggle" type="button">Panels</button>
  `;
  appShell.appendChild(rail);

  const footer = document.createElement('div');
  footer.className = 'workspaceFooter';
  footer.innerHTML = `
    <div class="footerBlock">
      <label><input id="allowCrossSurveySelectionToggle" type="checkbox"> Allow cross-survey selection</label>
    </div>
    <div class="footerBlock">
      <button id="scratchNoteBtn" type="button">Scratch note</button>
    </div>
  `;
  appShell.appendChild(footer);

  document.getElementById('manageToggle').onclick = () => {
    leftDrawerCollapsed = !leftDrawerCollapsed;
    leftPanel.classList.toggle('drawerCollapsed', leftDrawerCollapsed);
  };
  document.getElementById('layersToggle').onclick = () => {
    rightDrawerCollapsed = !rightDrawerCollapsed;
    rightPanel.classList.toggle('rightPanelCollapsed', rightDrawerCollapsed);
  };
  document.getElementById('allowCrossSurveySelectionToggle').onchange = (e) => {
    allowCrossSurveySelection = !!e.target.checked;
  };
  document.getElementById('scratchNoteBtn').onclick = createScratchNote;
  document.getElementById('clearSelectionBtn').onclick = clearActiveSelection;
}

function selectionDisplayName(feature) {
  return feature.get('name') || feature.get('title') || feature.get('source_id') || '';
}

function updateSelectionBanner() {
  const banner = document.getElementById('selectionBanner');
  const text = document.getElementById('selectionBannerText');
  if (!banner || !text) return;
  if (!activeSelection) {
    banner.classList.add('hidden');
    text.textContent = 'No selection';
    return;
  }
  const name = selectionDisplayName(activeSelection.feature);
  text.textContent = `SELECTED: ${activeSelection.layer} | ${activeSelection.source_id || ''} | ${name}`;
  banner.classList.remove('hidden');
}

function ensureSelectionHighlightLayer() {
  if (selectionHighlightLayer) return;
  selectionHighlightLayer = new ol.layer.Vector({
    source: new ol.source.Vector(),
    style: new ol.style.Style({
      stroke: new ol.style.Stroke({ color: '#f59e0b', width: 4 }),
      fill: new ol.style.Fill({ color: 'rgba(245, 158, 11, 0.18)' }),
      image: new ol.style.Circle({
        radius: 8,
        fill: new ol.style.Fill({ color: '#f59e0b' }),
        stroke: new ol.style.Stroke({ color: '#fff', width: 2 })
      })
    })
  });
  selectionHighlightLayer.setZIndex(1000);
  map.addLayer(selectionHighlightLayer);
}

function highlightSelectedFeature(feature) {
  ensureSelectionHighlightLayer();
  selectionHighlightLayer.getSource().clear();
  selectionHighlightLayer.getSource().addFeature(feature.clone());
}

function clearActiveSelection() {
  activeSelection = null;
  if (selectionHighlightLayer) selectionHighlightLayer.getSource().clear();
  updateSelectionBanner();
}

function canSelectFeature(feature) {
  const layerType = feature.get('layer_type') || 'global';
  const surveyId = feature.get('survey_id');
  if (!allowCrossSurveySelection && layerType === 'survey' && activeSurveyId && surveyId && String(surveyId) !== String(activeSurveyId)) {
    setStatus('Object belongs to another survey.', 'error');
    return false;
  }
  return true;
}

function setGlobalSelection(feature) {
  if (!feature) {
    clearActiveSelection();
    return;
  }
  if (!canSelectFeature(feature)) return;
  activeSelection = {
    feature,
    layer: feature.get('layer') || feature.get('layer_key') || feature.get('source_table') || 'unknown',
    source_id: feature.get('source_id') || ''
  };
  updateSelectionBanner();
  highlightSelectedFeature(feature);
}

async function createScratchNote() {
  const note = window.prompt('Scratch note');
  if (!note) return;
  const payload = {
    note,
    survey_id: activeSurveyId || null,
    scope: activeSurveyId ? 'survey' : 'global'
  };
  const res = await fetch('/api/notes/create', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (res.ok && data.ok) {
    setStatus('Scratch note created.', 'success');
    if (typeof refreshContextLayers === 'function') refreshContextLayers();
  } else {
    setStatus(`Scratch note failed: ${data.error || 'unknown error'}`, 'error');
  }
}
"""

API_APPEND = """
# === ui2 scratch notes and selection support ===
from pydantic import BaseModel

class ScratchNotePayload(BaseModel):
    note: str
    survey_id: int | None = None
    scope: str = "global"

def _ensure_scratch_notes_layer():
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                \"\"\"
                INSERT INTO layers_registry (
                    layer_key, layer_name, layer_group, source_table, geometry_type,
                    is_user_selectable, is_visible, opacity, sort_order, metadata
                )
                VALUES (
                    'scratch_notes', 'Scratch / Notes', 'context', 'external_features', 'POINT',
                    TRUE, FALSE, 1.0, 330,
                    %s::jsonb
                )
                ON CONFLICT (layer_key) DO UPDATE
                SET layer_name = EXCLUDED.layer_name,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
                \"\"\",
                (json.dumps({
                    "subgroup": "scratch_notes",
                    "phase": "ui_2",
                    "description": "General notes and annotations across surveys and layers"
                }),),
            )
        conn.commit()
    finally:
        conn.close()

@app.post("/api/notes/create")
def create_scratch_note(payload: ScratchNotePayload):
    import time
    _ensure_scratch_notes_layer()
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                \"\"\"
                INSERT INTO external_features (layer, geom, properties, source_table, source_id)
                VALUES (
                    'scratch_notes',
                    ST_SetSRID(ST_MakePoint(11.0, 48.0), 4326),
                    %s::jsonb,
                    'scratch_notes',
                    %s
                )
                RETURNING id
                \"\"\",
                (
                    json.dumps({
                        "note": payload.note,
                        "survey_id": payload.survey_id,
                        "scope": payload.scope,
                        "layer_type": "survey" if payload.survey_id else "global"
                    }),
                    f"scratch_{int(time.time()*1000)}"
                ),
            )
            row = cur.fetchone()
        conn.commit()
    finally:
        conn.close()
    return {"ok": True, "id": row[0]}
"""

def patch_html(path: Path) -> None:
    text = path.read_text(encoding='utf-8')

    if '#appShell' not in text:
        text = text.replace('</style>', UI2_CSS + '\\n</style>', 1)

    js = UI2_JS.replace('__SELECTION_BANNER_HTML__', SELECTION_BANNER_HTML.replace('`', '\\`').replace('${', '\\${'))

    if 'function ensureAppShell()' not in text:
        text = text.replace('\\nfunction bindTabs() {', '\\n' + js + '\\nfunction bindTabs() {', 1)

    if 'ensureAppShell();' not in text:
        text = text.replace('bindTabs();', 'ensureAppShell();\\nbindTabs();', 1)

    if 'setGlobalSelection(feature);' not in text:
        text = text.replace('selectedFeature = feature;', 'selectedFeature = feature;\\n  setGlobalSelection(feature);')

    path.write_text(text, encoding='utf-8')

def patch_api(path: Path) -> None:
    text = path.read_text(encoding='utf-8')
    if '/api/notes/create' not in text:
        text = text.rstrip() + '\\n' + API_APPEND + '\\n'
        path.write_text(text, encoding='utf-8')

def main() -> None:
    if not HTML_PATH.exists():
        raise FileNotFoundError(HTML_PATH)
    if not API_PATH.exists():
        raise FileNotFoundError(API_PATH)

    patch_html(HTML_PATH)
    print(f"[OK] updated {HTML_PATH}")

    patch_api(API_PATH)
    print(f"[OK] updated {API_PATH}")

    print("[DONE] UI-1 and UI-2 applied")
    print("Restart API, then hard refresh browser (Ctrl + F5).")

if __name__ == '__main__':
    main()
