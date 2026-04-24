const state = {
  surveys: [],
  layers: [],
  activeSurveyId: null,
  selection: null,
  layerIndex: new Map(),
};

let map;
let surveySource, surveyLayer;
let selectionSource, selectionLayer;
let contextTileLayers = {};

function banner(text, ms = 1800) {
  const el = document.getElementById("selection-banner");
  if (!el) return;
  if (!text) {
    el.style.display = "none";
    el.textContent = "";
    return;
  }
  el.textContent = text;
  el.style.display = "flex";
  if (ms > 0) {
    window.clearTimeout(window.__bannerTimer);
    window.__bannerTimer = window.setTimeout(() => {
      el.style.display = "none";
      el.textContent = "";
    }, ms);
  }
}

function safe(v, d = "") {
  return v === null || v === undefined ? d : v;
}

async function fetchJson(url, options) {
  const r = await fetch(url, options);
  const text = await r.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = null; }
  if (!r.ok) {
    throw new Error(data?.error?.message || data?.detail || text || `request failed: ${r.status}`);
  }
  return data;
}

function initMap() {
  map = new ol.Map({
    target: "map",
    layers: [new ol.layer.Tile({ source: new ol.source.OSM() })],
    view: new ol.View({
      center: ol.proj.fromLonLat([11, 48]),
      zoom: 7
    })
  });

  surveySource = new ol.source.Vector();
  surveyLayer = new ol.layer.Vector({
    source: surveySource,
    style: feature => {
      const props = feature.getProperties();
      const role = props.feature_role || "";
      if (role === "survey_boundary") {
        return new ol.style.Style({
          stroke: new ol.style.Stroke({ color: "#2563eb", width: 3 }),
          fill: new ol.style.Fill({ color: "rgba(37,99,235,0.08)" })
        });
      }
      return new ol.style.Style({
        stroke: new ol.style.Stroke({ color: "#0f766e", width: 2 }),
        fill: new ol.style.Fill({ color: "rgba(15,118,110,0.14)" }),
        image: new ol.style.Circle({
          radius: 6,
          fill: new ol.style.Fill({ color: "#0f766e" }),
          stroke: new ol.style.Stroke({ color: "#ffffff", width: 2 })
        })
      });
    }
  });

  selectionSource = new ol.source.Vector();
  selectionLayer = new ol.layer.Vector({
    source: selectionSource,
    style: new ol.style.Style({
      stroke: new ol.style.Stroke({ color: "#f59e0b", width: 4 }),
      fill: new ol.style.Fill({ color: "rgba(245,158,11,0.2)" }),
      image: new ol.style.Circle({
        radius: 8,
        fill: new ol.style.Fill({ color: "#f59e0b" }),
        stroke: new ol.style.Stroke({ color: "#ffffff", width: 2 })
      })
    })
  });

  map.addLayer(surveyLayer);
  map.addLayer(selectionLayer);

  map.on("singleclick", evt => {
    let selected = null;
    map.forEachFeatureAtPixel(evt.pixel, (feature) => {
      if (!selected) selected = feature;
    });
    setSelection(selected);
  });
}

function toHtml(s) {
  return String(safe(s, "")).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function setSelection(feature) {
  selectionSource.clear();

  if (!feature) {
    state.selection = null;
    render();
    return;
  }

  selectionSource.addFeature(feature.clone());

  const props = { ...feature.getProperties() };
  delete props.geometry;

  state.selection = {
    id: props.id || props.source_id || "unknown",
    layer: props.layer || props.layer_key || props.source_table || "",
    title: props.title || props.name || props.feature_role || "Selected feature",
    properties: props,
    feature
  };

  render();
}

async function loadSurveys() {
  state.surveys = await fetchJson("/api/surveys");
  render();
}

async function loadLayers() {
  const payload = await fetchJson("/api/layers");
  state.layers = Array.isArray(payload) ? payload : [];
  state.layerIndex = new Map(state.layers.map(x => [x.layer_key, x]));
  syncContextTileLayers();
  render();
}

async function loadSurveyFeatures(id, zoom = false) {
  const geo = await fetchJson(`/api/surveys/${id}/features?limit=20000`);
  const fmt = new ol.format.GeoJSON();
  const feats = fmt.readFeatures(geo, { featureProjection: map.getView().getProjection() });
  surveySource.clear();
  surveySource.addFeatures(feats);

  if (zoom && feats.length) {
    const ext = ol.extent.createEmpty();
    feats.forEach(f => ol.extent.extend(ext, f.getGeometry().getExtent()));
    map.getView().fit(ext, { padding: [40, 40, 40, 40], maxZoom: 18 });
  }

  banner(`Loaded ${feats.length} survey features.`);
}

function syncContextTileLayers() {
  const existingKeys = Object.keys(contextTileLayers);

  for (const key of existingKeys) {
    if (!state.layerIndex.has(key)) {
      map.removeLayer(contextTileLayers[key]);
      delete contextTileLayers[key];
    }
  }

  for (const layer of state.layers) {
    if (!contextTileLayers[layer.layer_key]) {
      const vt = new ol.layer.VectorTile({
        visible: !!layer.is_visible,
        source: new ol.source.VectorTile({
          format: new ol.format.MVT(),
          url: `/api/layers/${layer.layer_key}/tiles/{z}/{x}/{y}.mvt`
        }),
        style: feature => {
          const gt = (feature.getGeometry()?.getType?.() || "").toUpperCase();
          if (gt.includes("POINT")) {
            return new ol.style.Style({
              image: new ol.style.Circle({
                radius: 4,
                fill: new ol.style.Fill({ color: "#475569" }),
                stroke: new ol.style.Stroke({ color: "#ffffff", width: 1 })
              })
            });
          }
          if (gt.includes("LINE")) {
            return new ol.style.Style({
              stroke: new ol.style.Stroke({ color: "#475569", width: 1.5 })
            });
          }
          return new ol.style.Style({
            stroke: new ol.style.Stroke({ color: "#475569", width: 1.2 }),
            fill: new ol.style.Fill({ color: "rgba(71,85,105,0.08)" })
          });
        }
      });
      vt.set("layer_key", layer.layer_key);
      vt.setZIndex(10 + (layer.sort_order || 0));
      contextTileLayers[layer.layer_key] = vt;
      map.addLayer(vt);
    } else {
      contextTileLayers[layer.layer_key].setVisible(!!layer.is_visible);
      contextTileLayers[layer.layer_key].setZIndex(10 + (layer.sort_order || 0));
    }
  }
}

function setActiveSurvey() {
  const sel = document.getElementById("surveySelect");
  state.activeSurveyId = sel && sel.value ? sel.value : null;
  banner(state.activeSurveyId ? `Active survey set: ${state.activeSurveyId}` : "No active survey", 1200);
}

async function exportPermission() {
  if (!state.selection) {
    alert("Select feature first");
    return;
  }

  const payload = {
    layer: state.selection.layer,
    source_id: state.selection.id,
    description: "ui export"
  };

  const out = await fetchJson("/api/permissions/export", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });

  alert(out.ok ? "Permission exported" : "Export failed");
}

function renderLeft() {
  const surveys = state.surveys.map(s => `<option value="${toHtml(s.id)}" ${String(state.activeSurveyId) === String(s.id) ? "selected" : ""}>${toHtml(s.title || s.id)}</option>`).join("");

  return `
    <div style="background:white;padding:12px;width:360px;max-height:calc(100vh - 40px);overflow:auto;border-right:1px solid #ddd;">
      <h3 style="margin-top:0;">Manage</h3>

      <label>Survey</label><br>
      <select id="surveySelect" style="width:100%;margin-bottom:8px;">
        <option value="">Select</option>
        ${surveys}
      </select>

      <div style="margin-bottom:12px;">
        <button onclick="setActiveSurvey()">Set Active</button>
        <button onclick="loadSurveys()">Refresh</button>
        <button onclick="loadSelectedSurvey(false)">Load</button>
        <button onclick="loadSelectedSurvey(true)">Zoom</button>
      </div>

      <h3>Layers</h3>
      <div id="layerList">
        ${state.layers.map(layer => `
          <label style="display:block;margin-bottom:6px;">
            <input type="checkbox" data-layer="${toHtml(layer.layer_key)}" ${layer.is_visible ? "checked" : ""} onchange="toggleLayer(this)">
            ${toHtml(layer.layer_name || layer.layer_key)}
          </label>
        `).join("")}
      </div>

      <hr>
      <button onclick="exportPermission()">Export Permission</button>
    </div>
  `;
}

function renderRight() {
  if (!state.selection) {
    return `
      <div style="background:white;padding:12px;width:360px;max-height:calc(100vh - 40px);overflow:auto;border-left:1px solid #ddd;">
        <h3 style="margin-top:0;">Details</h3>
        <div>No selection</div>
      </div>
    `;
  }

  const props = state.selection.properties || {};
  const rows = Object.keys(props).sort().map(k => `<div style="margin-bottom:6px;"><b>${toHtml(k)}</b>: ${toHtml(props[k])}</div>`).join("");

  return `
    <div style="background:white;padding:12px;width:360px;max-height:calc(100vh - 40px);overflow:auto;border-left:1px solid #ddd;">
      <h3 style="margin-top:0;">Details</h3>
      <div><b>ID:</b> ${toHtml(state.selection.id)}</div>
      <div><b>Layer:</b> ${toHtml(state.selection.layer)}</div>
      <div><b>Title:</b> ${toHtml(state.selection.title)}</div>
      <hr>
      ${rows}
    </div>
  `;
}

function render() {
  const left = document.getElementById("left-panel");
  const right = document.getElementById("right-panel");

  if (left) {
    left.style.position = "absolute";
    left.style.left = "0";
    left.style.top = "0";
    left.style.pointerEvents = "auto";
    left.innerHTML = renderLeft();
  }

  if (right) {
    right.style.position = "absolute";
    right.style.right = "0";
    right.style.top = "0";
    right.style.pointerEvents = "auto";
    right.innerHTML = renderRight();
  }
}

async function loadSelectedSurvey(zoom) {
  if (!state.activeSurveyId) {
    alert("Select survey first");
    return;
  }
  await loadSurveyFeatures(state.activeSurveyId, zoom);
}

function toggleLayer(el) {
  const key = el.getAttribute("data-layer");
  const layer = state.layerIndex.get(key);
  if (!layer) return;
  layer.is_visible = !!el.checked;
  if (contextTileLayers[key]) contextTileLayers[key].setVisible(!!el.checked);
  banner(`Layer ${el.checked ? "shown" : "hidden"}: ${key}`, 1000);
}

async function start() {
  initMap();
  render();
  await loadSurveys();
  await loadLayers();
}

window.setActiveSurvey = setActiveSurvey;
window.loadSelectedSurvey = loadSelectedSurvey;
window.loadSurveys = loadSurveys;
window.toggleLayer = toggleLayer;
window.exportPermission = exportPermission;

start().catch(err => {
  console.error(err);
  alert(err.message || err);
});
