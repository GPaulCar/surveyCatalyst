from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
BOOT = ROOT / "app" / "static" / "ui_boot.js"
SHELL = ROOT / "app" / "openlayers_map_shell.html"
MANIFEST = ROOT / "app" / "static" / "ui_manifest.json"

SHELL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>SurveyCatalyst</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ol@latest/ol.css">
</head>
<body>
  <div id="map"></div>
  <div id="ui-root">
    <div id="topbar"></div>
    <div id="left-tabs"></div>
    <div id="right-tabs"></div>
    <div id="left-panel"></div>
    <div id="right-panel"></div>
    <div id="toast"></div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/ol@latest/dist/ol.js"></script>
  <script src="/static/ui_boot.js"></script>
</body>
</html>
"""

MANIFEST_JSON = """{
  "left": [
    {"id": "manage", "title": "Manage"},
    {"id": "plan", "title": "Plan"},
    {"id": "create", "title": "Create"},
    {"id": "edit", "title": "Edit"},
    {"id": "export", "title": "Export"}
  ],
  "right": [
    {"id": "layers", "title": "Layers"},
    {"id": "details", "title": "Details"},
    {"id": "region", "title": "Region"},
    {"id": "notes", "title": "Notes"}
  ]
}
"""

UI_BOOT = r"""
const state = {
  manifest: null,
  surveys: [],
  layers: [],
  activeSurveyId: null,
  activeLeft: "manage",
  activeRight: "layers",
  leftOpen: true,
  rightOpen: true,
  selection: null,
  layerIndex: new Map(),
  system: { api: false, db: false },
  labelVisibility: true
};

let map;
let surveySource, surveyLayer;
let selectionSource, selectionLayer;
let drawSource, drawLayer, drawInteraction;
let contextTileLayers = {};

function esc(v) {
  return String(v ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function css() {
  if (document.getElementById("minimalUiCss")) return;
  const style = document.createElement("style");
  style.id = "minimalUiCss";
  style.textContent = `
    :root {
      --bg: rgba(248,250,252,.94);
      --panel: rgba(255,255,255,.94);
      --line: #d8dee8;
      --text: #172033;
      --muted: #667085;
      --blue: #2563eb;
      --dark: rgba(15,23,42,.88);
    }
    html, body {
      margin: 0;
      height: 100%;
      overflow: hidden;
      font-family: Segoe UI, Inter, Arial, sans-serif;
      font-size: 12px;
      color: var(--text);
      background: #e5e7eb;
    }
    #map {
      position:absolute;
      inset:0;
      z-index:0;
    }
    #ui-root {
      position:absolute;
      inset:0;
      pointer-events:none;
      z-index:20;
    }
    #topbar {
      position:absolute;
      top:8px;
      left:50%;
      transform:translateX(-50%);
      z-index:40;
      pointer-events:auto;
    }
    .topbar {
      display:flex;
      align-items:center;
      gap:14px;
      height:34px;
      padding:0 12px;
      border-radius:10px;
      color:#f8fafc;
      background:var(--dark);
      border:1px solid rgba(255,255,255,.12);
      box-shadow:0 8px 26px rgba(15,23,42,.22);
      backdrop-filter:blur(10px);
      white-space:nowrap;
    }
    .brand {
      display:flex;
      align-items:center;
      gap:7px;
      font-weight:700;
      letter-spacing:.1px;
    }
    .mark {
      width:16px;
      height:16px;
      border-radius:4px;
      background:#38bdf8;
    }
    .top-meta {
      display:flex;
      gap:8px;
      color:#cbd5e1;
      font-size:11px;
    }
    .status-dot {
      display:inline-block;
      width:7px;
      height:7px;
      border-radius:99px;
      margin-right:5px;
      background:#ef4444;
    }
    .status-dot.on { background:#22c55e; }
    #left-tabs, #right-tabs {
      position:absolute;
      top:60px;
      display:flex;
      flex-direction:column;
      gap:4px;
      z-index:35;
      pointer-events:auto;
    }
    #left-tabs { left:8px; }
    #right-tabs { right:8px; }
    .tab {
      width:30px;
      height:74px;
      border:1px solid var(--line);
      border-radius:8px;
      background:rgba(255,255,255,.88);
      color:#334155;
      writing-mode:vertical-rl;
      text-orientation:mixed;
      font-size:11px;
      font-weight:600;
      cursor:pointer;
      box-shadow:0 4px 12px rgba(15,23,42,.08);
    }
    .tab.active {
      color:#fff;
      background:#1d4ed8;
      border-color:#1d4ed8;
    }
    .tab.toggle {
      height:48px;
      color:#fff;
      background:#111827;
      border-color:#111827;
    }
    .panel {
      position:absolute;
      top:52px;
      bottom:10px;
      width:330px;
      z-index:30;
      pointer-events:auto;
      background:var(--bg);
      border:1px solid rgba(148,163,184,.45);
      border-radius:12px;
      box-shadow:0 14px 38px rgba(15,23,42,.14);
      backdrop-filter:blur(10px);
      overflow:hidden;
      display:flex;
      flex-direction:column;
      transition:transform .18s ease, opacity .18s ease;
    }
    #left-panel { left:46px; }
    #right-panel { right:46px; width:360px; }
    .panel.closed-left { transform:translateX(-390px); opacity:0; }
    .panel.closed-right { transform:translateX(390px); opacity:0; }
    .panel-head {
      height:42px;
      padding:8px 11px;
      box-sizing:border-box;
      border-bottom:1px solid var(--line);
      background:rgba(255,255,255,.7);
    }
    .panel-title {
      font-size:13px;
      font-weight:700;
      line-height:14px;
    }
    .panel-sub {
      color:var(--muted);
      font-size:10px;
      margin-top:2px;
    }
    .panel-body {
      padding:9px;
      overflow:auto;
      flex:1;
    }
    .section {
      margin-bottom:10px;
      padding-bottom:8px;
      border-bottom:1px solid #e5e7eb;
    }
    .section:last-child { border-bottom:0; }
    .section-title {
      font-size:11px;
      font-weight:700;
      color:#334155;
      margin:0 0 6px 0;
    }
    label {
      font-size:11px;
      color:#344054;
    }
    select, input, textarea {
      width:100%;
      box-sizing:border-box;
      height:28px;
      border:1px solid #cbd5e1;
      border-radius:7px;
      background:#fff;
      color:#111827;
      padding:4px 7px;
      font-size:12px;
      margin:4px 0 6px 0;
      outline:none;
    }
    textarea {
      height:62px;
      resize:vertical;
      line-height:16px;
    }
    button {
      height:26px;
      border:1px solid #cbd5e1;
      border-radius:7px;
      padding:0 9px;
      margin:0 4px 5px 0;
      background:#fff;
      color:#1f2937;
      font-size:11px;
      font-weight:600;
      cursor:pointer;
    }
    button.primary {
      border-color:#1d4ed8;
      background:#1d4ed8;
      color:white;
    }
    button.danger {
      border-color:#dc2626;
      background:#dc2626;
      color:white;
    }
    .hint {
      color:var(--muted);
      font-size:11px;
      line-height:15px;
    }
    .row {
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:8px;
      margin:4px 0;
    }
    .badge {
      padding:2px 6px;
      border-radius:99px;
      color:#fff;
      font-size:10px;
      font-weight:700;
      background:#ef4444;
    }
    .badge.on { background:#16a34a; }
    .layer-row {
      display:grid;
      grid-template-columns:18px 1fr;
      gap:6px;
      padding:5px 0;
      border-bottom:1px solid #eef2f7;
    }
    .layer-row:last-child { border-bottom:0; }
    .layer-name {
      font-size:11px;
      font-weight:600;
      color:#1f2937;
      line-height:14px;
    }
    .layer-meta {
      color:#667085;
      font-size:10px;
      line-height:13px;
    }
    .props {
      font-size:11px;
    }
    .prop {
      display:grid;
      grid-template-columns:36% 1fr;
      gap:6px;
      padding:5px 0;
      border-bottom:1px solid #eef2f7;
    }
    .prop-k {
      font-weight:700;
      color:#475569;
      word-break:break-word;
    }
    .prop-v {
      word-break:break-word;
      color:#111827;
    }
    #toast {
      position:absolute;
      left:50%;
      bottom:10px;
      transform:translateX(-50%);
      display:none;
      z-index:45;
      pointer-events:none;
      background:rgba(15,23,42,.9);
      color:#fff;
      border-radius:8px;
      padding:8px 11px;
      font-size:12px;
      box-shadow:0 8px 22px rgba(15,23,42,.22);
    }
  `;
  document.head.appendChild(style);
}

function toast(text, ms=1500) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = text || "";
  el.style.display = text ? "block" : "none";
  clearTimeout(window.__toastTimer);
  if (text) window.__toastTimer = setTimeout(() => el.style.display = "none", ms);
}

async function fetchJson(url, opts) {
  const res = await fetch(url, opts);
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = null; }
  if (!res.ok) throw new Error(data?.error?.message || data?.detail || text || `Request failed ${res.status}`);
  return data;
}

async function loadManifest() {
  try {
    return await fetchJson("/static/ui_manifest.json?ts=" + Date.now());
  } catch {
    return {
      left: [{id:"manage",title:"Manage"},{id:"plan",title:"Plan"},{id:"create",title:"Create"},{id:"edit",title:"Edit"},{id:"export",title:"Export"}],
      right: [{id:"layers",title:"Layers"},{id:"details",title:"Details"},{id:"region",title:"Region"},{id:"notes",title:"Notes"}]
    };
  }
}

function initMap() {
  map = new ol.Map({
    target:"map",
    layers:[new ol.layer.Tile({source:new ol.source.OSM()})],
    view:new ol.View({center:ol.proj.fromLonLat([11,48]), zoom:7})
  });

  surveySource = new ol.source.Vector();
  surveyLayer = new ol.layer.Vector({
    source:surveySource,
    style:f => {
      const role = f.get("feature_role");
      if (role === "survey_boundary") {
        return new ol.style.Style({
          stroke:new ol.style.Stroke({color:"#2563eb",width:2}),
          fill:new ol.style.Fill({color:"rgba(37,99,235,.06)"})
        });
      }
      return new ol.style.Style({
        stroke:new ol.style.Stroke({color:"#0f766e",width:1.5}),
        fill:new ol.style.Fill({color:"rgba(15,118,110,.10)"}),
        image:new ol.style.Circle({radius:4, fill:new ol.style.Fill({color:"#0f766e"})})
      });
    }
  });

  selectionSource = new ol.source.Vector();
  selectionLayer = new ol.layer.Vector({
    source:selectionSource,
    style:new ol.style.Style({
      stroke:new ol.style.Stroke({color:"#f59e0b",width:3}),
      fill:new ol.style.Fill({color:"rgba(245,158,11,.14)"}),
      image:new ol.style.Circle({radius:6, fill:new ol.style.Fill({color:"#f59e0b"})})
    })
  });

  drawSource = new ol.source.Vector();
  drawLayer = new ol.layer.Vector({
    source:drawSource,
    style:new ol.style.Style({
      stroke:new ol.style.Stroke({color:"#7c3aed",width:2}),
      fill:new ol.style.Fill({color:"rgba(124,58,237,.10)"}),
      image:new ol.style.Circle({radius:5, fill:new ol.style.Fill({color:"#7c3aed"})})
    })
  });

  map.addLayer(surveyLayer);
  map.addLayer(drawLayer);
  map.addLayer(selectionLayer);

  map.on("singleclick", e => {
    let hit = null;
    map.forEachFeatureAtPixel(e.pixel, f => { if (!hit) hit = f; });
    setSelection(hit);
  });
}

function layerColour(key) {
  key = (key || "").toLowerCase();
  if (key.includes("river") || key.includes("water") || key.includes("flood") || key.includes("creek") || key.includes("channel")) return "#0284c7";
  if (key.includes("protection") || key.includes("restricted") || key.includes("legal")) return "#ea580c";
  if (key.includes("roman")) return "#7c2d12";
  if (key.includes("parcel")) return "#64748b";
  if (key.includes("field") || key.includes("geonames")) return "#111827";
  return "#475569";
}

function makeStyle(layer) {
  return feature => {
    const key = layer.layer_key || "";
    const color = layerColour(key);
    const gt = (feature.getGeometry()?.getType?.() || "").toUpperCase();
    const name = feature.get("name") || feature.get("title") || feature.get("place") || "";
    const styles = [];

    if (gt.includes("POINT")) {
      styles.push(new ol.style.Style({
        image:new ol.style.Circle({
          radius:3,
          fill:new ol.style.Fill({color}),
          stroke:new ol.style.Stroke({color:"#fff",width:1})
        })
      }));
      if (state.labelVisibility && name) {
        styles.push(new ol.style.Style({
          text:new ol.style.Text({
            text:String(name),
            font:"11px Segoe UI, Arial",
            fill:new ol.style.Fill({color:"#111827"}),
            stroke:new ol.style.Stroke({color:"#fff",width:3}),
            offsetY:-10
          })
        }));
      }
      return styles;
    }

    if (gt.includes("LINE")) {
      return new ol.style.Style({stroke:new ol.style.Stroke({color,width:key.includes("roman") ? 2 : 1.4})});
    }

    return new ol.style.Style({
      stroke:new ol.style.Stroke({color,width:1}),
      fill:new ol.style.Fill({color:key.includes("protection") ? "rgba(234,88,12,.10)" : "rgba(2,132,199,.06)"})
    });
  };
}

function syncContextLayers() {
  for (const key of Object.keys(contextTileLayers)) {
    if (!state.layerIndex.has(key)) {
      map.removeLayer(contextTileLayers[key]);
      delete contextTileLayers[key];
    }
  }

  for (const layer of state.layers) {
    if (!contextTileLayers[layer.layer_key]) {
      const vt = new ol.layer.VectorTile({
        visible:!!layer.is_visible,
        declutter:true,
        source:new ol.source.VectorTile({
          format:new ol.format.MVT(),
          url:`/api/layers/${layer.layer_key}/tiles/{z}/{x}/{y}.mvt`
        }),
        style:makeStyle(layer)
      });
      vt.setZIndex(10 + (layer.sort_order || 0));
      contextTileLayers[layer.layer_key] = vt;
      map.addLayer(vt);
    } else {
      contextTileLayers[layer.layer_key].setVisible(!!layer.is_visible);
      contextTileLayers[layer.layer_key].setStyle(makeStyle(layer));
    }
  }
}

function setSelection(feature) {
  selectionSource.clear();
  if (!feature) {
    state.selection = null;
    render();
    return;
  }

  selectionSource.addFeature(feature.clone());
  const props = {...feature.getProperties()};
  delete props.geometry;

  state.selection = {
    feature,
    id: props.source_id || props.id || "",
    layer: props.layer || props.layer_key || props.source_table || "",
    title: props.title || props.name || props.place || props.feature_role || "Selected feature",
    properties: props
  };

  render();
}

async function refreshSystem() {
  try {
    const r = await fetch("/health", {cache:"no-store"});
    state.system = {api:r.ok, db:r.ok};
  } catch {
    state.system = {api:false, db:false};
  }
  render();
}

async function loadSurveys() {
  state.surveys = await fetchJson("/api/surveys");
  render();
}

async function loadLayers() {
  const layers = await fetchJson("/api/layers");
  state.layers = Array.isArray(layers) ? layers : [];
  state.layerIndex = new Map(state.layers.map(l => [l.layer_key, l]));
  syncContextLayers();
  render();
}

async function loadSurveyFeatures(id, zoom=false) {
  const geo = await fetchJson(`/api/surveys/${id}/features?limit=20000`);
  const fmt = new ol.format.GeoJSON();
  const fs = fmt.readFeatures(geo, {featureProjection:map.getView().getProjection()});
  surveySource.clear();
  surveySource.addFeatures(fs);

  if (zoom && fs.length) {
    const ext = ol.extent.createEmpty();
    fs.forEach(f => ol.extent.extend(ext, f.getGeometry().getExtent()));
    map.getView().fit(ext, {padding:[36,36,36,36], maxZoom:18});
  }

  toast(`Loaded ${fs.length} features`);
}

function topbar() {
  const survey = state.surveys.find(s => String(s.id) === String(state.activeSurveyId));
  document.getElementById("topbar").innerHTML = `
    <div class="topbar">
      <div class="brand"><span class="mark"></span>SurveyCatalyst</div>
      <div class="top-meta">
        <span><span class="status-dot ${state.system.api ? "on" : ""}"></span>API</span>
        <span>Survey: ${esc(survey?.title || state.activeSurveyId || "none")}</span>
        <span>Selection: ${esc(state.selection?.title || "none")}</span>
      </div>
    </div>
  `;
}

function tabs() {
  const left = state.manifest.left || [];
  const right = state.manifest.right || [];

  document.getElementById("left-tabs").innerHTML = `
    ${left.map(t => `<button class="tab ${state.activeLeft === t.id ? "active" : ""}" onclick="setLeft('${esc(t.id)}')">${esc(t.title)}</button>`).join("")}
    <button class="tab toggle" onclick="toggleLeft()">${state.leftOpen ? "Hide" : "Show"}</button>
  `;

  document.getElementById("right-tabs").innerHTML = `
    ${right.map(t => `<button class="tab ${state.activeRight === t.id ? "active" : ""}" onclick="setRight('${esc(t.id)}')">${esc(t.title)}</button>`).join("")}
    <button class="tab toggle" onclick="toggleRight()">${state.rightOpen ? "Hide" : "Show"}</button>
  `;
}

function panel(id, side, title, sub, body) {
  const el = document.getElementById(id);
  el.className = `panel ${side === "left" ? (state.leftOpen ? "" : "closed-left") : (state.rightOpen ? "" : "closed-right")}`;
  el.innerHTML = `<div class="panel-head"><div class="panel-title">${esc(title)}</div><div class="panel-sub">${esc(sub)}</div></div><div class="panel-body">${body}</div>`;
}

function leftBody() {
  if (state.activeLeft === "manage") return manageBody();
  if (state.activeLeft === "plan") return `<div class="section"><div class="section-title">Planning context</div><div class="hint">Use hydrology, protection, parcels and Roman roads to assess regional suitability before creating survey data.</div></div>`;
  if (state.activeLeft === "create") return createBody();
  if (state.activeLeft === "edit") return editBody();
  if (state.activeLeft === "export") return exportBody();
  return "";
}

function rightBody() {
  if (state.activeRight === "layers") return layersBody();
  if (state.activeRight === "details") return detailsBody();
  if (state.activeRight === "region") return regionBody();
  if (state.activeRight === "notes") return `<div class="section"><div class="section-title">Scratch notes</div><textarea placeholder="Planning note"></textarea><button onclick="toast('Notes placeholder')">Save</button></div>`;
  return "";
}

function manageBody() {
  const opts = state.surveys.map(s => `<option value="${esc(s.id)}" ${String(s.id)===String(state.activeSurveyId) ? "selected" : ""}>${esc(s.title || s.id)}</option>`).join("");
  return `
    <div class="section">
      <div class="section-title">System</div>
      <div class="row"><span>API</span><span class="badge ${state.system.api ? "on" : ""}">${state.system.api ? "ON" : "OFF"}</span></div>
      <div class="row"><span>DB</span><span class="badge ${state.system.db ? "on" : ""}">${state.system.db ? "ON" : "OFF"}</span></div>
      <button onclick="refreshSystem()">Refresh</button>
    </div>
    <div class="section">
      <div class="section-title">Survey</div>
      <select id="surveySelect"><option value="">Select survey</option>${opts}</select>
      <button class="primary" onclick="setActiveSurvey()">Set active</button>
      <button onclick="loadSelectedSurvey(false)">Load</button>
      <button onclick="loadSelectedSurvey(true)">Zoom</button>
      <button onclick="loadSurveys()">Refresh</button>
    </div>
  `;
}

function createBody() {
  return `
    <div class="section">
      <div class="section-title">Survey</div>
      <input id="createSurveyTitle" placeholder="Survey title">
      <input id="createSurveyStatus" value="active" placeholder="Status">
      <button onclick="startDraw('polygon')">Draw boundary</button>
      <button class="primary" onclick="createSurvey()">Create</button>
    </div>
    <div class="section">
      <div class="section-title">Object</div>
      <select id="createObjectType"><option value="note">note</option><option value="findspot">findspot</option><option value="track">track</option><option value="polygon">polygon</option></select>
      <input id="createObjectTitle" placeholder="Object title">
      <textarea id="createObjectNote" placeholder="Notes"></textarea>
      <button onclick="startDraw('point')">Point</button>
      <button onclick="startDraw('line')">Line</button>
      <button onclick="startDraw('polygon')">Polygon</button>
      <button class="primary" onclick="createObject()">Create</button>
    </div>
  `;
}

function editBody() {
  if (!state.selection) return `<div class="section"><div class="hint">Select a survey object first.</div></div>`;
  const p = state.selection.properties || {};
  return `
    <div class="section">
      <div class="section-title">Selected object</div>
      <input id="editTitle" value="${esc(p.title || state.selection.title || "")}" placeholder="Title">
      <textarea id="editNote" placeholder="Notes">${esc(p.note || p.annotation || "")}</textarea>
      <button class="primary" onclick="saveSelection()">Save</button>
      <button class="danger" onclick="deleteSelection()">Delete</button>
    </div>
  `;
}

function exportBody() {
  return `
    <div class="section">
      <div class="section-title">Survey export</div>
      <button class="primary" onclick="exportLayer()">GeoJSON</button>
      <button onclick="exportData()">Data</button>
      <button onclick="exportDocument()">Document</button>
    </div>
    <div class="section">
      <div class="section-title">Permission</div>
      <button class="primary" onclick="exportPermission()">Export selected</button>
      <div class="hint">Select a parcel or context feature first.</div>
    </div>
  `;
}

function layersBody() {
  const groups = {};
  state.layers.forEach(l => {
    const g = l.metadata?.subgroup || l.layer_group || "other";
    if (!groups[g]) groups[g] = [];
    groups[g].push(l);
  });

  return `
    <div class="section">
      <label><input type="checkbox" ${state.labelVisibility ? "checked" : ""} onchange="toggleLabels(this.checked)"> Point labels</label>
    </div>
    ${Object.keys(groups).sort().map(g => `
      <div class="section">
        <div class="section-title">${esc(g.replaceAll("_"," "))}</div>
        ${groups[g].map(l => `
          <label class="layer-row">
            <input type="checkbox" ${l.is_visible ? "checked" : ""} onchange="toggleLayer('${esc(l.layer_key)}', this.checked)">
            <span><span class="layer-name">${esc(l.layer_name || l.layer_key)}</span><br><span class="layer-meta">${esc(l.geometry_type || "")}</span></span>
          </label>
        `).join("")}
      </div>
    `).join("")}
  `;
}

function detailsBody() {
  if (!state.selection) return `<div class="section"><div class="hint">Click a map feature to inspect it.</div></div>`;
  const p = state.selection.properties || {};
  return `
    <div class="section">
      <div class="section-title">${esc(state.selection.title)}</div>
      <div class="hint">Layer: ${esc(state.selection.layer)}<br>ID: ${esc(state.selection.id)}</div>
    </div>
    <div class="props">${Object.keys(p).sort().map(k => `<div class="prop"><div class="prop-k">${esc(k)}</div><div class="prop-v">${esc(p[k])}</div></div>`).join("")}</div>
  `;
}

function regionBody() {
  return `
    <div class="section"><div class="section-title">Region</div>
      <div class="row"><span>Layers</span><strong>${state.layers.length}</strong></div>
      <div class="row"><span>Survey</span><strong>${esc(state.activeSurveyId || "none")}</strong></div>
      <div class="row"><span>Selection</span><strong>${state.selection ? "yes" : "no"}</strong></div>
    </div>
  `;
}

function render() {
  css();
  topbar();
  tabs();
  panel("left-panel", "left", titleFor("left", state.activeLeft), subtitleFor(state.activeLeft), leftBody());
  panel("right-panel", "right", titleFor("right", state.activeRight), subtitleFor(state.activeRight), rightBody());
}

function titleFor(side, id) {
  const tabs = side === "left" ? state.manifest.left : state.manifest.right;
  return tabs.find(t => t.id === id)?.title || id;
}

function subtitleFor(id) {
  return {
    manage:"Workspace controls",
    plan:"Planning context",
    create:"Create survey data",
    edit:"Edit selected object",
    export:"Outputs",
    layers:"Map layers",
    details:"Feature inspection",
    region:"Summary",
    notes:"Scratch space"
  }[id] || "";
}

function setLeft(id){ state.activeLeft = id; state.leftOpen = true; render(); }
function setRight(id){ state.activeRight = id; state.rightOpen = true; render(); }
function toggleLeft(){ state.leftOpen = !state.leftOpen; render(); }
function toggleRight(){ state.rightOpen = !state.rightOpen; render(); }

function setActiveSurvey() {
  state.activeSurveyId = document.getElementById("surveySelect")?.value || null;
  toast(state.activeSurveyId ? "Survey set" : "No survey selected");
  render();
}

async function loadSelectedSurvey(zoom) {
  if (!state.activeSurveyId) return alert("Select a survey first");
  await loadSurveyFeatures(state.activeSurveyId, zoom);
}

function toggleLayer(key, value) {
  const l = state.layerIndex.get(key);
  if (l) l.is_visible = !!value;
  if (contextTileLayers[key]) contextTileLayers[key].setVisible(!!value);
  toast(value ? "Layer shown" : "Layer hidden");
}

function toggleLabels(value) {
  state.labelVisibility = !!value;
  syncContextLayers();
  toast(value ? "Labels on" : "Labels off");
}

function startDraw(type) {
  if (drawInteraction) map.removeInteraction(drawInteraction);
  drawSource.clear();
  const olType = type === "point" ? "Point" : type === "line" ? "LineString" : "Polygon";
  drawInteraction = new ol.interaction.Draw({source:drawSource, type:olType});
  drawInteraction.on("drawend", () => {
    map.removeInteraction(drawInteraction);
    drawInteraction = null;
    toast("Geometry captured");
  });
  map.addInteraction(drawInteraction);
}

function drawnFeature(){ return drawSource.getFeatures()[0] || null; }

function toGeoJSONGeometry(feature) {
  return JSON.parse(new ol.format.GeoJSON().writeFeature(feature, {
    featureProjection:map.getView().getProjection(),
    dataProjection:"EPSG:4326"
  })).geometry;
}

async function createSurvey() {
  const title = document.getElementById("createSurveyTitle")?.value?.trim();
  const status = document.getElementById("createSurveyStatus")?.value?.trim() || "active";
  const f = drawnFeature();
  if (!title) return alert("Enter title");
  if (!f) return alert("Draw boundary first");
  await fetchJson("/api/surveys", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({expedition_id:null,title,status,geometry:toGeoJSONGeometry(f),metadata:{}})});
  drawSource.clear();
  await loadSurveys();
  toast("Survey created");
}

async function createObject() {
  if (!state.activeSurveyId) return alert("Set active survey first");
  const f = drawnFeature();
  if (!f) return alert("Draw geometry first");
  const type = document.getElementById("createObjectType")?.value || "note";
  const title = document.getElementById("createObjectTitle")?.value || null;
  const note = document.getElementById("createObjectNote")?.value || "";
  await fetchJson(`/api/surveys/${state.activeSurveyId}/objects`, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({expedition_id:null,type,geometry:toGeoJSONGeometry(f),properties:{note},title,annotation:note,details:null})});
  drawSource.clear();
  await loadSurveyFeatures(state.activeSurveyId, false);
  toast("Object created");
}

async function saveSelection() {
  if (!state.selection) return alert("Select an object first");
  const id = state.selection.properties.id;
  if (!id) return alert("Selected feature cannot be edited");
  const title = document.getElementById("editTitle")?.value || null;
  const note = document.getElementById("editNote")?.value || "";
  const props = {...state.selection.properties, title, note};
  await fetchJson(`/api/survey-objects/${id}`, {method:"PATCH", headers:{"Content-Type":"application/json"}, body:JSON.stringify({geometry:toGeoJSONGeometry(state.selection.feature),type:props.type || "note",properties:props,title,annotation:note,details:null,is_active:true})});
  await loadSurveyFeatures(state.activeSurveyId, false);
  toast("Saved");
}

async function deleteSelection() {
  if (!state.selection) return alert("Select object first");
  const id = state.selection.properties.id;
  if (!id) return alert("Selected feature cannot be deleted");
  await fetchJson(`/api/survey-objects/${id}`, {method:"DELETE"});
  setSelection(null);
  if (state.activeSurveyId) await loadSurveyFeatures(state.activeSurveyId, false);
  toast("Deleted");
}

function downloadText(name, content) {
  const blob = new Blob([content], {type:"application/json"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

async function exportLayer() {
  if (!state.activeSurveyId) return alert("Set active survey first");
  const d = await fetchJson(`/api/surveys/${state.activeSurveyId}/export/layer.geojson`);
  downloadText(`survey_${state.activeSurveyId}_layer.geojson`, JSON.stringify(d,null,2));
}
async function exportData() {
  if (!state.activeSurveyId) return alert("Set active survey first");
  const d = await fetchJson(`/api/surveys/${state.activeSurveyId}/export/data.json`);
  downloadText(`survey_${state.activeSurveyId}_data.json`, JSON.stringify(d,null,2));
}
async function exportDocument() {
  if (!state.activeSurveyId) return alert("Set active survey first");
  const d = await fetchJson(`/api/surveys/${state.activeSurveyId}/export/document.json`);
  downloadText(`survey_${state.activeSurveyId}_document.json`, JSON.stringify(d,null,2));
}
async function exportPermission() {
  if (!state.selection) return alert("Select feature first");
  const out = await fetchJson("/api/permissions/export", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({layer:state.selection.layer, source_id:state.selection.id, description:"ui export"})});
  toast(out.ok ? "Permission exported" : "Export failed");
}

async function start() {
  css();
  state.manifest = await loadManifest();
  initMap();
  render();
  await refreshSystem();
  await loadSurveys();
  await loadLayers();
  render();
}

Object.assign(window, {
  setLeft,setRight,toggleLeft,toggleRight,refreshSystem,setActiveSurvey,loadSelectedSurvey,loadSurveys,
  toggleLayer,toggleLabels,startDraw,createSurvey,createObject,saveSelection,deleteSelection,
  exportLayer,exportData,exportDocument,exportPermission
});

start().catch(e => {
  console.error(e);
  alert(e.message || e);
});
"""

def run(cmd: list[str], required: bool = True) -> None:
    print("[RUN] " + " ".join(str(x) for x in cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if required and result.returncode != 0:
        raise SystemExit(result.returncode)

def main() -> None:
    print("[1/5] write minimal professional UI")
    SHELL.parent.mkdir(parents=True, exist_ok=True)
    BOOT.parent.mkdir(parents=True, exist_ok=True)
    SHELL.write_text(SHELL_HTML, encoding="utf-8")
    MANIFEST.write_text(MANIFEST_JSON, encoding="utf-8")
    BOOT.write_text(UI_BOOT, encoding="utf-8")

    print("[2/5] restart")
    run([sys.executable, "scripts/system_control.py", "restart"])

    print("[3/5] verify UI files")
    if "large" in BOOT.read_text(encoding="utf-8").lower():
        print("[WARN] UI file contains word 'large', check manually if needed")
    print("[OK] UI files written")

    print("[4/5] checkpoint")
    if (ROOT / "apply_checkpoint_bundle.py").exists():
        run([sys.executable, "apply_checkpoint_bundle.py", "minimal-professional-ui-stage1", "--no-push"], required=False)
    else:
        print("[WARN] checkpoint skipped")

    print("[5/5] complete")
    print("[PHASE COMPLETE]")
    print("minimal professional UI applied")

if __name__ == "__main__":
    main()