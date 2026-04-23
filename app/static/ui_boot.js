
const state = {
  surveys: [],
  layers: [],
  activeSurveyId: null,
  selection: null,
  createMode: "point"
};

let map;
let surveySource, surveyLayer;
let selectionSource, selectionLayer;
let drawSource, drawLayer, drawInteraction;

function styleSurveyFeature(feature){
  const props = feature.getProperties();
  const role = props.feature_role || "";
  if (role === "survey_boundary") {
    return new ol.style.Style({
      stroke:new ol.style.Stroke({color:'#2563eb',width:3}),
      fill:new ol.style.Fill({color:'rgba(37,99,235,0.08)'})
    });
  }
  return new ol.style.Style({
    stroke:new ol.style.Stroke({color:'#0f766e',width:2}),
    fill:new ol.style.Fill({color:'rgba(15,118,110,0.14)'}),
    image:new ol.style.Circle({
      radius:6,
      fill:new ol.style.Fill({color:'#0f766e'}),
      stroke:new ol.style.Stroke({color:'#ffffff',width:2})
    })
  });
}

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
  surveyLayer = new ol.layer.Vector({
    source:surveySource,
    style:styleSurveyFeature
  });

  selectionSource = new ol.source.Vector();
  selectionLayer = new ol.layer.Vector({
    source:selectionSource,
    style:new ol.style.Style({
      stroke:new ol.style.Stroke({color:'#f59e0b',width:4}),
      fill:new ol.style.Fill({color:'rgba(245,158,11,0.2)'}),
      image:new ol.style.Circle({
        radius:8,
        fill:new ol.style.Fill({color:'#f59e0b'}),
        stroke:new ol.style.Stroke({color:'#ffffff',width:2})
      })
    })
  });

  drawSource = new ol.source.Vector();
  drawLayer = new ol.layer.Vector({
    source:drawSource,
    style:new ol.style.Style({
      stroke:new ol.style.Stroke({color:'#7c3aed',width:3}),
      fill:new ol.style.Fill({color:'rgba(124,58,237,0.15)'}),
      image:new ol.style.Circle({
        radius:6,
        fill:new ol.style.Fill({color:'#7c3aed'}),
        stroke:new ol.style.Stroke({color:'#ffffff',width:2})
      })
    })
  });

  map.addLayer(surveyLayer);
  map.addLayer(selectionLayer);
  map.addLayer(drawLayer);

  map.on('singleclick', e=>{
    let found = null;
    map.forEachFeatureAtPixel(e.pixel, f => {
      if (!found) found = f;
    });
    setSelection(found);
  });
}

function toGeoJSONGeometry(feature){
  const format = new ol.format.GeoJSON();
  const obj = JSON.parse(format.writeFeature(feature, {
    featureProjection: map.getView().getProjection(),
    dataProjection: 'EPSG:4326'
  }));
  return obj.geometry;
}

function setSelection(feature){
  selectionSource.clear();

  if(!feature){
    state.selection = null;
    render();
    return;
  }

  selectionSource.addFeature(feature.clone());

  const props = {...feature.getProperties()};
  delete props.geometry;

  state.selection = {
    feature,
    id: props.id || props.source_id || "unknown",
    layer: props.layer || props.layer_key || "",
    properties: props
  };

  render();
}

async function fetchJson(url, options){
  const r = await fetch(url, options);
  const data = await r.json();
  if (!r.ok) {
    throw new Error(data?.error?.message || data?.detail || "request failed");
  }
  return data;
}

async function loadSurveys(){
  state.surveys = await fetchJson("/api/surveys");
  render();
}

async function loadLayers(){
  state.layers = await fetchJson("/api/layers");
}

async function loadSurveyFeatures(id, zoom=false){
  const geo = await fetchJson(`/api/surveys/${id}/features?limit=20000`);
  const fmt = new ol.format.GeoJSON();
  const feats = fmt.readFeatures(geo,{featureProjection:map.getView().getProjection()});
  surveySource.clear();
  surveySource.addFeatures(feats);

  if(zoom && feats.length){
    const ext = ol.extent.createEmpty();
    feats.forEach(f=>ol.extent.extend(ext,f.getGeometry().getExtent()));
    map.getView().fit(ext, {padding:[40,40,40,40], maxZoom:18});
  }
}

function clearDrawInteraction(){
  if (drawInteraction) {
    map.removeInteraction(drawInteraction);
    drawInteraction = null;
  }
}

function startDraw(type){
  clearDrawInteraction();
  drawSource.clear();

  const olType = type === "point" ? "Point" : (type === "line" ? "LineString" : "Polygon");
  drawInteraction = new ol.interaction.Draw({
    source: drawSource,
    type: olType
  });

  drawInteraction.on("drawend", () => {
    clearDrawInteraction();
    render();
  });

  map.addInteraction(drawInteraction);
}

function selectedDrawFeature(){
  const feats = drawSource.getFeatures();
  return feats.length ? feats[0] : null;
}

async function createSurvey(){
  const titleEl = document.getElementById("createSurveyTitle");
  const statusEl = document.getElementById("createSurveyStatus");
  const feat = selectedDrawFeature();

  if (!titleEl || !titleEl.value.trim()) return alert("Enter survey title");
  if (!feat) return alert("Draw a survey boundary first");

  const payload = {
    expedition_id: null,
    title: titleEl.value.trim(),
    status: statusEl ? statusEl.value.trim() || "active" : "active",
    geometry: toGeoJSONGeometry(feat),
    metadata: {}
  };

  await fetchJson("/api/surveys", {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  drawSource.clear();
  await loadSurveys();
  alert("Survey created");
}

async function createObject(){
  const typeEl = document.getElementById("createObjectType");
  const titleEl = document.getElementById("createObjectTitle");
  const noteEl = document.getElementById("createObjectNote");
  const feat = selectedDrawFeature();

  if (!state.activeSurveyId) return alert("Set active survey first");
  if (!feat) return alert("Draw object geometry first");

  const payload = {
    expedition_id: null,
    type: typeEl ? typeEl.value : "note",
    geometry: toGeoJSONGeometry(feat),
    properties: { note: noteEl ? noteEl.value : "" },
    title: titleEl ? titleEl.value : null,
    annotation: noteEl ? noteEl.value : null,
    details: null
  };

  await fetchJson(`/api/surveys/${state.activeSurveyId}/objects`, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  drawSource.clear();
  await loadSurveyFeatures(state.activeSurveyId, false);
  alert("Object created");
}

async function saveSelection(){
  if (!state.selection) return alert("Select feature first");

  const feature = state.selection.feature;
  const props = {...state.selection.properties};

  const titleEl = document.getElementById("editTitle");
  const noteEl = document.getElementById("editNote");
  const activeEl = document.getElementById("editActive");

  props.title = titleEl ? titleEl.value : props.title;
  props.note = noteEl ? noteEl.value : props.note;

  const payload = {
    geometry: toGeoJSONGeometry(feature),
    type: props.type || "note",
    properties: props,
    title: titleEl ? titleEl.value : null,
    annotation: noteEl ? noteEl.value : null,
    details: null,
    is_active: activeEl ? !!activeEl.checked : true
  };

  const id = state.selection.properties.id;
  if (!id) return alert("Selected feature has no editable object id");

  await fetchJson(`/api/survey-objects/${id}`, {
    method: "PATCH",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });

  await loadSurveyFeatures(state.activeSurveyId, false);
  alert("Selection saved");
}

async function deleteSelection(){
  if (!state.selection) return alert("Select feature first");

  const id = state.selection.properties.id;
  if (!id) return alert("Selected feature has no editable object id");

  await fetchJson(`/api/survey-objects/${id}`, {
    method: "DELETE"
  });

  setSelection(null);
  await loadSurveyFeatures(state.activeSurveyId, false);
  alert("Selection deleted");
}

async function exportLayer(){
  if (!state.activeSurveyId) return alert("Set active survey first");
  const data = await fetchJson(`/api/surveys/${state.activeSurveyId}/export/layer.geojson`);
  downloadText(`survey_${state.activeSurveyId}_layer.geojson`, JSON.stringify(data, null, 2));
}

async function exportData(){
  if (!state.activeSurveyId) return alert("Set active survey first");
  const data = await fetchJson(`/api/surveys/${state.activeSurveyId}/export/data.json`);
  downloadText(`survey_${state.activeSurveyId}_data.json`, JSON.stringify(data, null, 2));
}

async function exportDocument(){
  if (!state.activeSurveyId) return alert("Set active survey first");
  const data = await fetchJson(`/api/surveys/${state.activeSurveyId}/export/document.json`);
  downloadText(`survey_${state.activeSurveyId}_document.json`, JSON.stringify(data, null, 2));
}

async function exportPermission(){
  if(!state.selection){
    alert("select feature first");
    return;
  }

  const payload = {
    layer: state.selection.layer,
    source_id: state.selection.id,
    description: "ui export"
  };

  const out = await fetchJson("/api/permissions/export", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify(payload)
  });

  alert(out.ok ? "Permission exported" : "Export failed");
}

function downloadText(filename, content){
  const blob = new Blob([content], {type:"application/json;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function leftPanelHtml(){
  return `
    <div style="background:white;padding:10px;width:340px;">
      <h3>Manage</h3>
      <select id="surveySelect" style="width:100%;">
        <option value="">Select</option>
        ${state.surveys.map(s=>`<option value="${s.id}" ${String(state.activeSurveyId)===String(s.id) ? "selected" : ""}>${s.title||s.id}</option>`).join("")}
      </select>
      <br><br>
      <button onclick="setActive()">Set Active</button>
      <button onclick="load()">Load</button>
      <button onclick="zoom()">Zoom</button>
      <hr>

      <h3>Create Survey</h3>
      <input id="createSurveyTitle" placeholder="Survey title" style="width:100%;margin-bottom:6px;">
      <input id="createSurveyStatus" placeholder="Status" value="active" style="width:100%;margin-bottom:6px;">
      <button onclick="startBoundaryDraw()">Draw boundary</button>
      <button onclick="createSurvey()">Create survey</button>
      <hr>

      <h3>Create Object</h3>
      <select id="createObjectType" style="width:100%;margin-bottom:6px;">
        <option value="note">note</option>
        <option value="findspot">findspot</option>
        <option value="track">track</option>
        <option value="polygon">polygon</option>
      </select>
      <input id="createObjectTitle" placeholder="Object title" style="width:100%;margin-bottom:6px;">
      <input id="createObjectNote" placeholder="Note" style="width:100%;margin-bottom:6px;">
      <button onclick="startPointDraw()">Point</button>
      <button onclick="startLineDraw()">Line</button>
      <button onclick="startPolygonDraw()">Polygon</button>
      <button onclick="createObject()">Create object</button>
      <hr>

      <h3>Export</h3>
      <button onclick="exportLayer()">GeoJSON</button>
      <button onclick="exportData()">Data</button>
      <button onclick="exportDocument()">Document</button>
      <button onclick="exportPermission()">Permission</button>
    </div>
  `;
}

function rightPanelHtml(){
  if(!state.selection){
    return `<div style="background:white;padding:10px;width:340px;"><h3>Details</h3>No selection</div>`;
  }

  const props = state.selection.properties;
  const editableTitle = props.title || "";
  const editableNote = props.note || props.annotation || "";

  return `
    <div style="background:white;padding:10px;width:340px;">
      <h3>Details</h3>
      <b>ID:</b> ${state.selection.id}<br>
      <b>Layer:</b> ${state.selection.layer}<br><br>

      <input id="editTitle" value="${String(editableTitle).replaceAll('"','&quot;')}" placeholder="Title" style="width:100%;margin-bottom:6px;">
      <input id="editNote" value="${String(editableNote).replaceAll('"','&quot;')}" placeholder="Note" style="width:100%;margin-bottom:6px;">
      <label><input id="editActive" type="checkbox" checked> Active</label>
      <br><br>
      <button onclick="saveSelection()">Save</button>
      <button onclick="deleteSelection()">Delete</button>

      <hr>
      <div style="max-height:320px;overflow:auto;">
        ${Object.keys(props).map(k=>`<div><b>${k}</b>: ${String(props[k])}</div>`).join("")}
      </div>
    </div>
  `;
}

function render(){
  document.getElementById("left-panel").innerHTML = leftPanelHtml();
  document.getElementById("right-panel").innerHTML = rightPanelHtml();
}

function setActive(){
  const sel = document.getElementById("surveySelect").value;
  state.activeSurveyId = sel || null;
}

function load(){
  if(!state.activeSurveyId) return alert("select survey");
  loadSurveyFeatures(state.activeSurveyId,false);
}

function zoom(){
  if(!state.activeSurveyId) return alert("select survey");
  loadSurveyFeatures(state.activeSurveyId,true);
}

function startBoundaryDraw(){ startDraw("polygon"); }
function startPointDraw(){ startDraw("point"); }
function startLineDraw(){ startDraw("line"); }
function startPolygonDraw(){ startDraw("polygon"); }

async function start(){
  initMap();
  await loadSurveys();
  await loadLayers();
  render();
}

start();
