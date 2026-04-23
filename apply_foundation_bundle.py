from pathlib import Path

ROOT = Path.cwd()

APP_PY = ROOT / "src" / "api" / "app.py"
APP_DIR = ROOT / "app"
STATIC_DIR = APP_DIR / "static"

SHELL_HTML = APP_DIR / "openlayers_map_shell.html"
UI_BOOT = STATIC_DIR / "ui_boot.js"
UI_MANIFEST = STATIC_DIR / "ui_manifest.json"

# -----------------------------
# 1. PATCH API (serve shell + static)
# -----------------------------
def patch_api():
    text = APP_PY.read_text(encoding="utf-8")

    if "StaticFiles" not in text:
        text = text.replace(
            "from fastapi.responses import HTMLResponse, JSONResponse, Response",
            "from fastapi.responses import HTMLResponse, JSONResponse, Response\nfrom fastapi.staticfiles import StaticFiles"
        )

    if 'app.mount("/static"' not in text:
        text = text.replace(
            'app = FastAPI(title="surveyCatalyst API", version="0.5.0")',
            'app = FastAPI(title="surveyCatalyst API", version="0.5.0")\napp.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")'
        )

    text = text.replace(
        'APP_HTML = BASE_DIR / "app" / "openlayers_map.html"',
        'APP_HTML = BASE_DIR / "app" / "openlayers_map_shell.html"'
    )

    APP_PY.write_text(text, encoding="utf-8")
    print("[OK] API patched")


# -----------------------------
# 2. SHELL HTML
# -----------------------------
def write_shell():
    SHELL_HTML.parent.mkdir(parents=True, exist_ok=True)

    SHELL_HTML.write_text("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>SurveyCatalyst</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ol@latest/ol.css">
<style>
html,body{margin:0;height:100%;}
#map{position:absolute;inset:0;}
#ui-root{position:absolute;inset:0;pointer-events:none;}
</style>
</head>
<body>

<div id="map"></div>
<div id="ui-root">
  <div id="left-panel"></div>
  <div id="right-panel"></div>
  <div id="selection-banner"></div>
</div>

<script src="https://cdn.jsdelivr.net/npm/ol@latest/dist/ol.js"></script>
<script src="/static/ui_boot.js"></script>

</body>
</html>
""", encoding="utf-8")

    print("[OK] shell written")


# -----------------------------
# 3. MANIFEST
# -----------------------------
def write_manifest():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    UI_MANIFEST.write_text("""{
  "left_tabs": [
    {"id":"manage","title":"Manage"},
    {"id":"create","title":"Create"},
    {"id":"edit","title":"Edit"},
    {"id":"export","title":"Export"}
  ],
  "right_tabs": [
    {"id":"layers","title":"Layers"},
    {"id":"hierarchy","title":"Hierarchy"},
    {"id":"details","title":"Details"}
  ]
}""", encoding="utf-8")

    print("[OK] manifest written")


# -----------------------------
# 4. UI BOOT (MAP + BUTTONS + LAYERS + SELECTION)
# -----------------------------
def write_boot():
    UI_BOOT.write_text(r"""
const state = { surveys: [], layers: [], activeSurveyId:null };

let map;
let surveyLayer;
let surveySource;

function initMap(){
  map = new ol.Map({
    target:'map',
    layers:[new ol.layer.Tile({source:new ol.source.OSM()})],
    view:new ol.View({
      center:ol.proj.fromLonLat([11,48]),
      zoom:7
    })
  });

  surveySource = new ol.source.Vector();
  surveyLayer = new ol.layer.Vector({source:surveySource});
  map.addLayer(surveyLayer);

  map.on('singleclick', e=>{
    map.forEachFeatureAtPixel(e.pixel,f=>{
      alert("Selected feature id: " + (f.get("id")||"unknown"));
    });
  });
}

async function fetchJson(url){
  const r = await fetch(url);
  return await r.json();
}

async function loadSurveys(){
  state.surveys = await fetchJson("/api/surveys");
  render();
}

async function loadLayers(){
  state.layers = await fetchJson("/api/layers");
}

async function loadSurveyFeatures(id, zoom=false){
  const geo = await fetchJson(`/api/surveys/${id}/features`);
  const fmt = new ol.format.GeoJSON();
  const feats = fmt.readFeatures(geo,{featureProjection:map.getView().getProjection()});
  surveySource.clear();
  surveySource.addFeatures(feats);

  if(zoom && feats.length){
    const ext = ol.extent.createEmpty();
    feats.forEach(f=>ol.extent.extend(ext,f.getGeometry().getExtent()));
    map.getView().fit(ext);
  }
}

function render(){
  const left = document.getElementById("left-panel");

  left.innerHTML = `
    <div style="background:white;padding:10px;width:300px;">
      <h3>Surveys</h3>
      <select id="surveySelect">
        <option value="">Select</option>
        ${state.surveys.map(s=>`<option value="${s.id}">${s.title||s.id}</option>`).join("")}
      </select>
      <br><br>
      <button onclick="setActive()">Set Active</button>
      <button onclick="refreshSurveys()">Refresh</button>
      <button onclick="zoom()">Zoom</button>
      <button onclick="load()">Load</button>
    </div>
  `;
}

function setActive(){
  const sel = document.getElementById("surveySelect").value;
  state.activeSurveyId = sel;
}

function refreshSurveys(){
  loadSurveys();
}

function zoom(){
  if(!state.activeSurveyId) return alert("select survey");
  loadSurveyFeatures(state.activeSurveyId,true);
}

function load(){
  if(!state.activeSurveyId) return alert("select survey");
  loadSurveyFeatures(state.activeSurveyId,false);
}

async function start(){
  initMap();
  await loadSurveys();
  await loadLayers();
}

start();
""", encoding="utf-8")

    print("[OK] ui_boot written")


# -----------------------------
# MAIN
# -----------------------------
def main():
    patch_api()
    write_shell()
    write_manifest()
    write_boot()
    print("\n[DONE] FOUNDATION COMPLETE")


if __name__ == "__main__":
    main()