from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
APP_PY = ROOT / "src" / "api" / "app.py"
SHELL = ROOT / "app" / "openlayers_map_shell.html"
BOOT = ROOT / "app" / "static" / "ui_boot.js"
MANIFEST = ROOT / "app" / "static" / "ui_manifest.json"

APP_HTML_LINE = 'APP_HTML = BASE_DIR / "app" / "openlayers_map_shell.html"'
STATIC_IMPORT = "from fastapi.staticfiles import StaticFiles"
STATIC_MOUNT = 'app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")'

SHELL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SurveyCatalyst</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ol@latest/ol.css">
</head>
<body>
  <div id="map"></div>
  <div id="ui-root">
    <div id="top-bar"></div>
    <div id="left-rail"></div>
    <div id="right-rail"></div>
    <div id="left-panel"></div>
    <div id="right-panel"></div>
    <div id="selection-banner"></div>
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

UI_BOOT = r'''
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
  layerFilter: ""
};

let map;
let surveySource, surveyLayer;
let selectionSource, selectionLayer;
let drawSource, drawLayer, drawInteraction;
let contextTileLayers = {};
let labelVisibility = true;

function css() {
  if (document.getElementById("surveyCatalystUiCss")) return;
  const style = document.createElement("style");
  style.id = "surveyCatalystUiCss";
  style.textContent = `
    html, body { margin:0; height:100%; overflow:hidden; font-family:Inter, Segoe UI, Arial, sans-serif; background:#0f172a; }
    #map { position:absolute; inset:0; z-index:0; }
    #ui-root { position:absolute; inset:0; z-index:20; pointer-events:none; }
    #top-bar { position:absolute; top:14px; left:50%; transform:translateX(-50%); min-width:520px; max-width:900px; pointer-events:auto; z-index:35; }
    .top-shell { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:11px 14px; border-radius:18px; background:rgba(15,23,42,.88); color:#fff; box-shadow:0 18px 42px rgba(15,23,42,.32); border:1px solid rgba(255,255,255,.12); backdrop-filter:blur(12px); }
    .brand { display:flex; align-items:center; gap:10px; font-weight:850; letter-spacing:.2px; }
    .brand-mark { width:30px; height:30px; border-radius:9px; background:linear-gradient(135deg,#38bdf8,#2563eb); box-shadow:0 8px 18px rgba(37,99,235,.45); }
    .top-meta { display:flex; gap:12px; align-items:center; font-size:12px; color:#cbd5e1; }
    .pill { display:inline-flex; align-items:center; gap:6px; padding:5px 9px; border-radius:999px; background:rgba(255,255,255,.1); color:#e2e8f0; }
    .dot { width:8px; height:8px; border-radius:999px; background:#22c55e; }
    #left-rail, #right-rail { position:absolute; top:50%; transform:translateY(-50%); display:flex; flex-direction:column; gap:8px; pointer-events:auto; z-index:32; }
    #left-rail { left:10px; } #right-rail { right:10px; }
    .rail-btn { width:44px; min-height:104px; border:1px solid rgba(148,163,184,.32); border-radius:15px; background:rgba(248,250,252,.92); color:#334155; box-shadow:0 12px 26px rgba(15,23,42,.14); font-weight:850; writing-mode:vertical-rl; text-orientation:mixed; cursor:pointer; backdrop-filter:blur(10px); }
    .rail-btn.active { background:#1d4ed8; color:#fff; border-color:#1d4ed8; }
    .rail-btn.close { background:#111827; color:#fff; min-height:72px; }
    .drawer { position:absolute; top:74px; bottom:18px; width:390px; background:rgba(248,250,252,.96); color:#0f172a; border:1px solid rgba(148,163,184,.38); border-radius:22px; box-shadow:0 24px 64px rgba(15,23,42,.22); backdrop-filter:blur(14px); pointer-events:auto; z-index:28; display:flex; flex-direction:column; overflow:hidden; transition:transform .22s ease, opacity .22s ease; }
    #left-panel { left:64px; } #right-panel { right:64px; width:430px; }
    .drawer.closed-left { transform:translateX(calc(-100% - 90px)); opacity:0; } .drawer.closed-right { transform:translateX(calc(100% + 90px)); opacity:0; }
    .drawer-head { padding:16px 18px 12px 18px; border-bottom:1px solid #dbe4ef; background:linear-gradient(180deg,#fff,#f8fafc); }
    .drawer-title { font-size:19px; font-weight:900; color:#0f172a; line-height:1.1; } .drawer-subtitle { color:#64748b; font-size:12px; margin-top:4px; }
    .drawer-body { padding:14px 16px 16px 16px; overflow:auto; flex:1; }
    .card { border:1px solid #e2e8f0; background:#fff; border-radius:16px; padding:13px; margin-bottom:12px; box-shadow:0 4px 14px rgba(15,23,42,.04); }
    .card h3 { margin:0 0 10px 0; font-size:14px; color:#0f172a; letter-spacing:.2px; }
    .row { display:flex; align-items:center; justify-content:space-between; gap:10px; margin:7px 0; }
    .muted { color:#64748b; font-size:12px; }
    select, input, textarea { box-sizing:border-box; width:100%; border:1px solid #cbd5e1; border-radius:11px; padding:9px 10px; background:#fff; color:#0f172a; outline:none; margin:4px 0 8px 0; }
    textarea { min-height:78px; resize:vertical; }
    button.action { border:0; border-radius:11px; padding:9px 12px; margin:0 6px 8px 0; background:#1d4ed8; color:#fff; font-weight:800; cursor:pointer; box-shadow:0 8px 16px rgba(37,99,235,.18); }
    button.action.secondary { background:#e2e8f0; color:#0f172a; box-shadow:none; } button.action.danger { background:#dc2626; }
    .status { display:inline-flex; align-items:center; gap:6px; padding:4px 9px; border-radius:999px; color:#fff; font-size:12px; font-weight:850; }
    .status.on { background:#16a34a; } .status.off { background:#dc2626; }
    .layer-row { display:grid; grid-template-columns:20px 1fr auto; gap:9px; align-items:start; padding:9px 0; border-bottom:1px solid #eef2f7; }
    .layer-row:last-child { border-bottom:0; } .layer-count { color:#64748b; font-size:11px; white-space:nowrap; }
    .section-title { font-size:12px; text-transform:uppercase; letter-spacing:.08em; color:#64748b; font-weight:900; margin:8px 0; }
    #selection-banner { position:absolute; display:none; left:50%; bottom:18px; transform:translateX(-50%); padding:12px 16px; border-radius:16px; background:#f59e0b; color:#111827; font-weight:900; pointer-events:auto; box-shadow:0 18px 38px rgba(15,23,42,.25); z-index:34; max-width:760px; }
    #toast { position:absolute; left:50%; top:74px; transform:translateX(-50%); display:none; pointer-events:none; background:rgba(15,23,42,.92); color:white; border-radius:12px; padding:10px 14px; z-index:36; font-weight:750; box-shadow:0 14px 28px rgba(15,23,42,.28); }
    .prop-table { font-size:12px; } .prop-row { display:grid; grid-template-columns:37% 1fr; gap:8px; border-top:1px solid #eef2f7; padding:7px 0; }
    .prop-key { font-weight:850; color:#334155; word-break:break-word; } .prop-val { color:#0f172a; word-break:break-word; }
  `;
  document.head.appendChild(style);
}

function toast(text, ms = 1700) { const el = document.getElementById("toast"); if (!el) return; if (!text) { el.style.display="none"; el.textContent=""; return; } el.textContent=text; el.style.display="block"; clearTimeout(window.__toastTimer); window.__toastTimer=setTimeout(()=>{el.style.display="none"; el.textContent="";},ms); }
function banner(text) { const el=document.getElementById("selection-banner"); if(!el) return; if(!text){el.style.display="none";el.textContent="";return;} el.style.display="block"; el.textContent=text; }
function esc(v) { return String(v ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;"); }
async function fetchJson(url, options) { const res=await fetch(url, options); const text=await res.text(); let data=null; try{data=text?JSON.parse(text):null;}catch{data=null;} if(!res.ok) throw new Error(data?.error?.message || data?.detail || text || `Request failed: ${res.status}`); return data; }
async function loadManifest() { try { return await fetchJson("/static/ui_manifest.json?ts=" + Date.now()); } catch { return {left:[{id:"manage",title:"Manage"},{id:"plan",title:"Plan"},{id:"create",title:"Create"},{id:"edit",title:"Edit"},{id:"export",title:"Export"}],right:[{id:"layers",title:"Layers"},{id:"details",title:"Details"},{id:"region",title:"Region"},{id:"notes",title:"Notes"}]}; } }

function topBar(){ const active=state.surveys.find(s=>String(s.id)===String(state.activeSurveyId)); const surveyLabel=active?(active.title||active.id):"No active survey"; document.getElementById("top-bar").innerHTML=`<div class="top-shell"><div class="brand"><div class="brand-mark"></div><div>SurveyCatalyst</div></div><div class="top-meta"><span class="pill"><span class="dot"></span>127.0.0.1:8000 online</span><span class="pill">Survey: ${esc(surveyLabel)}</span><span class="pill">Selection: ${state.selection ? esc(state.selection.title) : "none"}</span></div></div>`; }
function rail(){ const left=document.getElementById("left-rail"); const right=document.getElementById("right-rail"); const lt=state.manifest.left||state.manifest.left_tabs||[]; const rt=state.manifest.right||state.manifest.right_tabs||[]; left.innerHTML=`${lt.map(t=>`<button class="rail-btn ${state.activeLeft===t.id?"active":""}" data-left="${esc(t.id)}">${esc(t.title)}</button>`).join("")}<button class="rail-btn close" id="leftToggle">${state.leftOpen?"Hide":"Show"}</button>`; right.innerHTML=`${rt.map(t=>`<button class="rail-btn ${state.activeRight===t.id?"active":""}" data-right="${esc(t.id)}">${esc(t.title)}</button>`).join("")}<button class="rail-btn close" id="rightToggle">${state.rightOpen?"Hide":"Show"}</button>`; left.querySelectorAll("[data-left]").forEach(b=>b.onclick=()=>{state.activeLeft=b.dataset.left;state.leftOpen=true;render();}); right.querySelectorAll("[data-right]").forEach(b=>b.onclick=()=>{state.activeRight=b.dataset.right;state.rightOpen=true;render();}); document.getElementById("leftToggle").onclick=()=>{state.leftOpen=!state.leftOpen;render();}; document.getElementById("rightToggle").onclick=()=>{state.rightOpen=!state.rightOpen;render();}; }
function drawer(id, side, title, subtitle, body){ const el=document.getElementById(id); el.className=`drawer ${side==="left"?(state.leftOpen?"":"closed-left"):(state.rightOpen?"":"closed-right")}`; el.innerHTML=`<div class="drawer-head"><div class="drawer-title">${esc(title)}</div><div class="drawer-subtitle">${esc(subtitle)}</div></div><div class="drawer-body">${body}</div>`; }
function tabTitle(side,id){ const tabs=side==="left"?(state.manifest.left||state.manifest.left_tabs||[]):(state.manifest.right||state.manifest.right_tabs||[]); return tabs.find(t=>t.id===id)?.title||id; }
function tabSubtitle(side,id){ return {manage:"Survey, status and workspace control",plan:"Regional planning and suitability",create:"Create surveys and survey objects",edit:"Edit selected survey object",export:"Survey and permission outputs",layers:"Context, survey and analysis layers",details:"Selected feature inspection",region:"Regional analysis summary",notes:"Scratch planning notes"}[id]||""; }

function initMap(){ map=new ol.Map({target:"map",layers:[new ol.layer.Tile({source:new ol.source.OSM()})],view:new ol.View({center:ol.proj.fromLonLat([11,48]),zoom:7})}); surveySource=new ol.source.Vector(); surveyLayer=new ol.layer.Vector({source:surveySource,style:f=>{const role=f.get("feature_role"); if(role==="survey_boundary") return new ol.style.Style({stroke:new ol.style.Stroke({color:"#2563eb",width:3}),fill:new ol.style.Fill({color:"rgba(37,99,235,.08)"})}); return new ol.style.Style({stroke:new ol.style.Stroke({color:"#0f766e",width:2}),fill:new ol.style.Fill({color:"rgba(15,118,110,.14)"}),image:new ol.style.Circle({radius:6,fill:new ol.style.Fill({color:"#0f766e"}),stroke:new ol.style.Stroke({color:"#fff",width:2})})});}}); selectionSource=new ol.source.Vector(); selectionLayer=new ol.layer.Vector({source:selectionSource,style:new ol.style.Style({stroke:new ol.style.Stroke({color:"#f59e0b",width:4}),fill:new ol.style.Fill({color:"rgba(245,158,11,.2)"}),image:new ol.style.Circle({radius:8,fill:new ol.style.Fill({color:"#f59e0b"}),stroke:new ol.style.Stroke({color:"#fff",width:2})})})}); drawSource=new ol.source.Vector(); drawLayer=new ol.layer.Vector({source:drawSource,style:new ol.style.Style({stroke:new ol.style.Stroke({color:"#7c3aed",width:3}),fill:new ol.style.Fill({color:"rgba(124,58,237,.15)"}),image:new ol.style.Circle({radius:7,fill:new ol.style.Fill({color:"#7c3aed"}),stroke:new ol.style.Stroke({color:"#fff",width:2})})})}); map.addLayer(surveyLayer); map.addLayer(drawLayer); map.addLayer(selectionLayer); map.on("singleclick",evt=>{let found=null; map.forEachFeatureAtPixel(evt.pixel,f=>{if(!found) found=f;}); setSelection(found);}); }
function layerColour(key){ const k=(key||"").toLowerCase(); if(k.includes("river")||k.includes("water")||k.includes("flood")||k.includes("creek")||k.includes("channel")) return "#0284c7"; if(k.includes("protection")||k.includes("restricted")||k.includes("legal")) return "#ea580c"; if(k.includes("roman")) return "#7c2d12"; if(k.includes("parcel")) return "#64748b"; if(k.includes("field")||k.includes("geonames")||k.includes("place")) return "#111827"; return "#475569"; }
function makeVectorTileStyle(layer){ return function(feature){ const key=layer.layer_key||""; const gt=(feature.getGeometry()?.getType?.()||"").toUpperCase(); const color=layerColour(key); const name=feature.get("name")||feature.get("title")||feature.get("place")||""; const styles=[]; if(gt.includes("POINT")){ styles.push(new ol.style.Style({image:new ol.style.Circle({radius:4,fill:new ol.style.Fill({color}),stroke:new ol.style.Stroke({color:"#fff",width:1})})})); if(labelVisibility&&name) styles.push(new ol.style.Style({text:new ol.style.Text({text:String(name),font:"12px Segoe UI, Arial, sans-serif",fill:new ol.style.Fill({color:"#0f172a"}),stroke:new ol.style.Stroke({color:"#fff",width:3}),offsetY:-13})})); return styles;} if(gt.includes("LINE")) return new ol.style.Style({stroke:new ol.style.Stroke({color,width:key.includes("roman")?2.2:1.7})}); return new ol.style.Style({stroke:new ol.style.Stroke({color,width:1.3}),fill:new ol.style.Fill({color:key.includes("protection")||key.includes("restricted")?"rgba(234,88,12,.12)":"rgba(2,132,199,.08)"})});}; }
function syncContextLayers(){ for(const key of Object.keys(contextTileLayers)){ if(!state.layerIndex.has(key)){map.removeLayer(contextTileLayers[key]); delete contextTileLayers[key];}} for(const layer of state.layers){ if(!contextTileLayers[layer.layer_key]){ const vt=new ol.layer.VectorTile({visible:!!layer.is_visible,declutter:true,source:new ol.source.VectorTile({format:new ol.format.MVT(),url:`/api/layers/${layer.layer_key}/tiles/{z}/{x}/{y}.mvt`}),style:makeVectorTileStyle(layer)}); vt.set("layer_key",layer.layer_key); vt.setZIndex(10+(layer.sort_order||0)); contextTileLayers[layer.layer_key]=vt; map.addLayer(vt);} else { contextTileLayers[layer.layer_key].setVisible(!!layer.is_visible); contextTileLayers[layer.layer_key].setStyle(makeVectorTileStyle(layer)); contextTileLayers[layer.layer_key].setZIndex(10+(layer.sort_order||0)); } } }
function setSelection(feature){ selectionSource.clear(); if(!feature){state.selection=null;banner("");render();return;} selectionSource.addFeature(feature.clone()); const props={...feature.getProperties()}; delete props.geometry; state.selection={feature,id:props.source_id||props.id||"",layer:props.layer||props.layer_key||props.source_table||"",title:props.title||props.name||props.place||props.feature_role||"Selected feature",properties:props}; banner(`Selected: ${state.selection.layer||"feature"} | ${state.selection.id||state.selection.title}`); render(); }
async function refreshSystem(){ try{const r=await fetch("/health",{cache:"no-store"}); state.system={api:r.ok,db:r.ok};}catch{state.system={api:false,db:false};} render(); }
async function loadSurveys(){ state.surveys=await fetchJson("/api/surveys"); render(); }
async function loadLayers(){ const layers=await fetchJson("/api/layers"); state.layers=Array.isArray(layers)?layers:[]; state.layerIndex=new Map(state.layers.map(l=>[l.layer_key,l])); syncContextLayers(); render(); }
async function loadSurveyFeatures(id,zoom=false){ const geo=await fetchJson(`/api/surveys/${id}/features?limit=20000`); const fmt=new ol.format.GeoJSON(); const feats=fmt.readFeatures(geo,{featureProjection:map.getView().getProjection()}); surveySource.clear(); surveySource.addFeatures(feats); if(zoom&&feats.length){const ext=ol.extent.createEmpty(); feats.forEach(f=>ol.extent.extend(ext,f.getGeometry().getExtent())); map.getView().fit(ext,{padding:[40,40,40,40],maxZoom:18});} toast(`Loaded ${feats.length} survey features`); }

function manageBody(){ const opts=state.surveys.map(s=>`<option value="${esc(s.id)}" ${String(s.id)===String(state.activeSurveyId)?"selected":""}>${esc(s.title||s.id)}</option>`).join(""); const api=state.system?.api; const db=state.system?.db; return `<div class="card"><h3>System</h3><div class="row"><span>API</span><span class="status ${api?"on":"off"}">${api?"ON":"OFF"}</span></div><div class="row"><span>Database</span><span class="status ${db?"on":"off"}">${db?"ON":"OFF"}</span></div><button class="action secondary" onclick="refreshSystem()">Refresh</button><button class="action secondary" onclick="healthCheck()">Health</button></div><div class="card"><h3>Survey workspace</h3><select id="surveySelect"><option value="">Select survey</option>${opts}</select><button class="action" onclick="setActiveSurvey()">Set active</button><button class="action secondary" onclick="loadSelectedSurvey(false)">Load</button><button class="action secondary" onclick="loadSelectedSurvey(true)">Zoom to</button><button class="action secondary" onclick="loadSurveys()">Refresh</button><div class="muted">Active survey controls planning, editing and exports.</div></div>`; }
function planBody(){ return `<div class="card"><h3>Region planning</h3><div class="muted">Use context layers, hydrology, protection layers, Roman roads and parcels to identify survey areas.</div></div><div class="card"><h3>Recommended view stack</h3><div class="muted">1. Protection/restricted layers<br>2. Hydrology<br>3. Roman roads<br>4. Parcels<br>5. Survey objects</div></div>`; }
function createBody(){ return `<div class="card"><h3>Create survey</h3><input id="createSurveyTitle" placeholder="Survey title"><input id="createSurveyStatus" placeholder="Status" value="active"><button class="action secondary" onclick="startDraw('polygon')">Draw boundary</button><button class="action" onclick="createSurvey()">Create survey</button></div><div class="card"><h3>Create object</h3><select id="createObjectType"><option value="note">note</option><option value="findspot">findspot</option><option value="track">track</option><option value="polygon">polygon</option></select><input id="createObjectTitle" placeholder="Object title"><textarea id="createObjectNote" placeholder="Notes"></textarea><button class="action secondary" onclick="startDraw('point')">Point</button><button class="action secondary" onclick="startDraw('line')">Line</button><button class="action secondary" onclick="startDraw('polygon')">Polygon</button><button class="action" onclick="createObject()">Create object</button></div>`; }
function editBody(){ if(!state.selection) return `<div class="card"><h3>Edit</h3><div class="muted">Select a survey object first.</div></div>`; const p=state.selection.properties||{}; return `<div class="card"><h3>Edit selected object</h3><input id="editTitle" value="${esc(p.title||state.selection.title||"")}" placeholder="Title"><textarea id="editNote" placeholder="Notes">${esc(p.note||p.annotation||"")}</textarea><button class="action" onclick="saveSelection()">Save</button><button class="action danger" onclick="deleteSelection()">Delete</button><div class="muted">Only selected survey objects with an id can be edited.</div></div>`; }
function exportBody(){ return `<div class="card"><h3>Survey exports</h3><button class="action" onclick="exportLayer()">GeoJSON</button><button class="action secondary" onclick="exportData()">Data JSON</button><button class="action secondary" onclick="exportDocument()">Document JSON</button></div><div class="card"><h3>Permission export</h3><button class="action" onclick="exportPermission()">Export selected feature</button><div class="muted">Select a parcel or context feature first.</div></div>`; }
function layerBody(){ const q=(state.layerFilter||"").toLowerCase(); const layers=state.layers.filter(l=>!q||(l.layer_name||l.layer_key||"").toLowerCase().includes(q)); const groups={}; layers.forEach(l=>{const g=l.metadata?.subgroup||l.layer_group||"other"; if(!groups[g]) groups[g]=[]; groups[g].push(l);}); return `<div class="card"><h3>Layer controls</h3><input id="layerFilter" placeholder="Filter layers" value="${esc(state.layerFilter||"")}" oninput="state.layerFilter=this.value;render()"><label class="muted"><input type="checkbox" ${labelVisibility?"checked":""} onchange="toggleLabels(this.checked)"> Show point labels</label></div>${Object.keys(groups).sort().map(g=>`<div class="card"><div class="section-title">${esc(g.replaceAll("_"," "))}</div>${groups[g].map(l=>`<label class="layer-row"><input type="checkbox" ${l.is_visible?"checked":""} onchange="toggleLayer('${esc(l.layer_key)}', this.checked)"><span><strong>${esc(l.layer_name||l.layer_key)}</strong><br><span class="muted">${esc(l.geometry_type||"")}</span></span><span class="layer-count">${esc(l.layer_key)}</span></label>`).join("")}</div>`).join("")}`; }
function detailsBody(){ if(!state.selection) return `<div class="card"><h3>Selection</h3><div class="muted">Click a feature on the map.</div></div>`; const p=state.selection.properties||{}; return `<div class="card"><h3>Selected feature</h3><div><strong>${esc(state.selection.title)}</strong></div><div class="muted">Layer: ${esc(state.selection.layer)} | ID: ${esc(state.selection.id)}</div></div><div class="card prop-table">${Object.keys(p).sort().map(k=>`<div class="prop-row"><div class="prop-key">${esc(k)}</div><div class="prop-val">${esc(p[k])}</div></div>`).join("")}</div>`; }
function regionBody(){ return `<div class="card"><h3>Region analysis</h3><div class="row"><span>Registered layers</span><strong>${state.layers.length}</strong></div><div class="row"><span>Active survey</span><strong>${esc(state.activeSurveyId||"none")}</strong></div><div class="row"><span>Selected feature</span><strong>${state.selection?"yes":"no"}</strong></div></div><div class="card"><h3>Analysis guidance</h3><div class="muted">Toggle hydrology, protection, parcels and Roman roads to assess suitability before creating or editing survey data.</div></div>`; }
function notesBody(){ return `<div class="card"><h3>Scratch notes</h3><textarea id="scratchText" placeholder="Temporary planning note"></textarea><button class="action secondary" onclick="toast('Scratch notes UI placeholder')">Save note</button><div class="muted">Persistent scratch-note layer will be wired in the next data-entry pass.</div></div>`; }
function leftBody(){ return {manage:manageBody,plan:planBody,create:createBody,edit:editBody,export:exportBody}[state.activeLeft]?.() || ""; }
function rightBody(){ return {layers:layerBody,details:detailsBody,region:regionBody,notes:notesBody}[state.activeRight]?.() || ""; }
function render(){ css(); topBar(); rail(); drawer("left-panel","left",tabTitle("left",state.activeLeft),tabSubtitle("left",state.activeLeft),leftBody()); drawer("right-panel","right",tabTitle("right",state.activeRight),tabSubtitle("right",state.activeRight),rightBody()); }
function setActiveSurvey(){ const sel=document.getElementById("surveySelect"); state.activeSurveyId=sel?.value||null; toast(state.activeSurveyId?`Active survey ${state.activeSurveyId}`:"No active survey"); render(); }
async function loadSelectedSurvey(zoom){ if(!state.activeSurveyId) return alert("Select a survey first"); await loadSurveyFeatures(state.activeSurveyId, zoom); }
function toggleLayer(key,value){ const layer=state.layerIndex.get(key); if(layer) layer.is_visible=!!value; if(contextTileLayers[key]) contextTileLayers[key].setVisible(!!value); toast(`${value?"Shown":"Hidden"}: ${key}`); }
function toggleLabels(value){ labelVisibility=!!value; syncContextLayers(); toast(labelVisibility?"Labels on":"Labels off"); }
async function healthCheck(){ try{const r=await fetch("/health"); toast(r.ok?"127.0.0.1:8000 healthy":"Health check failed");}catch{toast("Health check failed");} }
function startDraw(type){ if(drawInteraction) map.removeInteraction(drawInteraction); drawSource.clear(); const olType=type==="point"?"Point":type==="line"?"LineString":"Polygon"; drawInteraction=new ol.interaction.Draw({source:drawSource,type:olType}); drawInteraction.on("drawend",()=>{map.removeInteraction(drawInteraction); drawInteraction=null; toast("Geometry captured");}); map.addInteraction(drawInteraction); }
function drawnFeature(){ return drawSource.getFeatures()[0]||null; }
function toGeoJSONGeometry(feature){ const fmt=new ol.format.GeoJSON(); return JSON.parse(fmt.writeFeature(feature,{featureProjection:map.getView().getProjection(),dataProjection:"EPSG:4326"})).geometry; }
async function createSurvey(){ const title=document.getElementById("createSurveyTitle")?.value?.trim(); const status=document.getElementById("createSurveyStatus")?.value?.trim()||"active"; const f=drawnFeature(); if(!title) return alert("Enter a survey title"); if(!f) return alert("Draw a boundary first"); await fetchJson("/api/surveys",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({expedition_id:null,title,status,geometry:toGeoJSONGeometry(f),metadata:{}})}); drawSource.clear(); await loadSurveys(); toast("Survey created"); }
async function createObject(){ if(!state.activeSurveyId) return alert("Set an active survey first"); const f=drawnFeature(); if(!f) return alert("Draw object geometry first"); const type=document.getElementById("createObjectType")?.value||"note"; const title=document.getElementById("createObjectTitle")?.value||null; const note=document.getElementById("createObjectNote")?.value||""; await fetchJson(`/api/surveys/${state.activeSurveyId}/objects`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({expedition_id:null,type,geometry:toGeoJSONGeometry(f),properties:{note},title,annotation:note,details:null})}); drawSource.clear(); await loadSurveyFeatures(state.activeSurveyId,false); toast("Object created"); }
async function saveSelection(){ if(!state.selection) return alert("Select a survey object first"); const id=state.selection.properties.id; if(!id) return alert("Selected feature has no editable object id"); const title=document.getElementById("editTitle")?.value||null; const note=document.getElementById("editNote")?.value||""; const props={...state.selection.properties,title,note}; await fetchJson(`/api/survey-objects/${id}`,{method:"PATCH",headers:{"Content-Type":"application/json"},body:JSON.stringify({geometry:toGeoJSONGeometry(state.selection.feature),type:props.type||"note",properties:props,title,annotation:note,details:null,is_active:true})}); await loadSurveyFeatures(state.activeSurveyId,false); toast("Selection saved"); }
async function deleteSelection(){ if(!state.selection) return alert("Select a survey object first"); const id=state.selection.properties.id; if(!id) return alert("Selected feature has no editable object id"); await fetchJson(`/api/survey-objects/${id}`,{method:"DELETE"}); setSelection(null); if(state.activeSurveyId) await loadSurveyFeatures(state.activeSurveyId,false); toast("Selection deleted"); }
function downloadText(filename,content){ const blob=new Blob([content],{type:"application/json;charset=utf-8"}); const url=URL.createObjectURL(blob); const a=document.createElement("a"); a.href=url; a.download=filename; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url); }
async function exportLayer(){ if(!state.activeSurveyId) return alert("Set active survey first"); const data=await fetchJson(`/api/surveys/${state.activeSurveyId}/export/layer.geojson`); downloadText(`survey_${state.activeSurveyId}_layer.geojson`,JSON.stringify(data,null,2)); }
async function exportData(){ if(!state.activeSurveyId) return alert("Set active survey first"); const data=await fetchJson(`/api/surveys/${state.activeSurveyId}/export/data.json`); downloadText(`survey_${state.activeSurveyId}_data.json`,JSON.stringify(data,null,2)); }
async function exportDocument(){ if(!state.activeSurveyId) return alert("Set active survey first"); const data=await fetchJson(`/api/surveys/${state.activeSurveyId}/export/document.json`); downloadText(`survey_${state.activeSurveyId}_document.json`,JSON.stringify(data,null,2)); }
async function exportPermission(){ if(!state.selection) return alert("Select feature first"); const out=await fetchJson("/api/permissions/export",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({layer:state.selection.layer,source_id:state.selection.id,description:"ui export"})}); toast(out.ok?"Permission exported":"Export failed"); }
async function start(){ css(); state.manifest=await loadManifest(); initMap(); render(); await refreshSystem(); await loadSurveys(); await loadLayers(); render(); }
window.refreshSystem=refreshSystem; window.healthCheck=healthCheck; window.setActiveSurvey=setActiveSurvey; window.loadSelectedSurvey=loadSelectedSurvey; window.loadSurveys=loadSurveys; window.toggleLayer=toggleLayer; window.toggleLabels=toggleLabels; window.createSurvey=createSurvey; window.createObject=createObject; window.saveSelection=saveSelection; window.deleteSelection=deleteSelection; window.exportLayer=exportLayer; window.exportData=exportData; window.exportDocument=exportDocument; window.exportPermission=exportPermission; window.startDraw=startDraw; window.state=state;
start().catch(err=>{console.error(err); alert(err.message||err);});
'''

def patch_api() -> None:
    if not APP_PY.exists():
        raise FileNotFoundError(APP_PY)
    text = APP_PY.read_text(encoding="utf-8")
    if STATIC_IMPORT not in text:
        text = text.replace("from fastapi.responses import HTMLResponse, JSONResponse, Response", "from fastapi.responses import HTMLResponse, JSONResponse, Response\nfrom fastapi.staticfiles import StaticFiles", 1)
    if 'APP_HTML = BASE_DIR / "app" / "openlayers_map.html"' in text:
        text = text.replace('APP_HTML = BASE_DIR / "app" / "openlayers_map.html"', APP_HTML_LINE, 1)
    elif APP_HTML_LINE not in text:
        text = text.replace("MVT_EXTENT = 4096", APP_HTML_LINE + "\nMVT_EXTENT = 4096", 1)
    if STATIC_MOUNT not in text:
        text = text.replace('app = FastAPI(title="surveyCatalyst API", version="0.5.0")', 'app = FastAPI(title="surveyCatalyst API", version="0.5.0")\n' + STATIC_MOUNT, 1)
    APP_PY.write_text(text, encoding="utf-8")
    print("[OK] API static/shell route verified")

def write_files() -> None:
    SHELL.parent.mkdir(parents=True, exist_ok=True)
    BOOT.parent.mkdir(parents=True, exist_ok=True)
    SHELL.write_text(SHELL_HTML, encoding="utf-8")
    BOOT.write_text(UI_BOOT, encoding="utf-8")
    MANIFEST.write_text(MANIFEST_JSON, encoding="utf-8")
    print("[OK] shell, manifest and UI boot written")

def run(cmd: list[str], required: bool = True) -> int:
    print("[RUN] " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if required and result.returncode != 0:
        raise SystemExit(result.returncode)
    return result.returncode

def main() -> None:
    print("[1/5] patch API route/static mount")
    patch_api()
    print("[2/5] write professional interface shell")
    write_files()
    print("[3/5] syntax check API")
    run([sys.executable, "-m", "py_compile", str(APP_PY)])
    print("[4/5] restart system")
    run([sys.executable, "scripts/system_control.py", "restart"])
    print("[5/5] checkpoint")
    if (ROOT / "apply_checkpoint_bundle.py").exists():
        run([sys.executable, "apply_checkpoint_bundle.py", "professional-interface-restore-stage1", "--no-push"], required=False)
    else:
        print("[WARN] apply_checkpoint_bundle.py not found; checkpoint skipped")
    print("[PHASE COMPLETE]")
    print("professional interface restored")

if __name__ == "__main__":
    main()
