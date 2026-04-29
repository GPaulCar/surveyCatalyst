
const state = {
  manifest: null,
  surveys: [],
  layers: [],
  activeSurveyId: null,
  activeLeft: "survey",
  activeRight: "layers",
  leftOpen: true,
  rightOpen: true,
  selection: null,
  layerIndex: new Map(),
  system: { api: false, db: false },
  labelVisibility: true,
  activeBasemap: "osm",
  lang: (() => {
    const saved = (typeof localStorage !== "undefined" && localStorage.getItem("surveyCatalyst.lang")) || "";
    if (saved === "de" || saved === "en") return saved;
    const nav = (navigator.language || navigator.userLanguage || "en").toLowerCase();
    return nav.startsWith("de") ? "de" : "en";
  })()
};

let map;
let surveySource, surveyLayer;
let selectionSource, selectionLayer;
let drawSource, drawLayer, drawInteraction;
let contextTileLayers = {};
let baseLayer = null;

const I18N = {
  en: {
    app_name: "SurveyCatalyst",
    api: "API",
    db: "DB",
    tab_survey: "Survey",
    tab_create: "Create",
    tab_edit: "Edit",
    tab_export: "Export",
    tab_manage: "Manage",
    tab_plan: "Plan",
    tab_layers: "Layers",
    tab_basemap: "Basemap",
    tab_details: "Details",
    tab_region: "Region",
    tab_notes: "Notes",
    survey: "Survey",
    selection: "Selection",
    surveys: "Surveys",
    layers: "Layers",
    hide_surveys: "Hide Surveys",
    show_surveys: "Show Surveys",
    hide_layers: "Hide Layers",
    show_layers: "Show Layers",
    lang_en: "EN",
    lang_de: "DE",
    active_survey: "Active survey",
    select_survey: "Select survey",
    refresh: "Refresh",
    load: "Load",
    zoom: "Zoom",
    survey_context: "Survey context",
    selected: "Selected",
    status: "Status",
    id: "ID",
    objects: "Objects",
    survey_context_hint: "This tab only selects the active survey context. Creation and editing remain separate workflows.",
    system: "System",
    title: "Title",
    draw_boundary: "Draw boundary",
    create: "Create",
    survey_hint: "Creates a new survey from the drawn boundary, then makes it active.",
    object: "Object",
    object_title: "Object title",
    notes: "Notes",
    point: "Point",
    line: "Line",
    polygon: "Polygon",
    active_survey_hint: "Active survey",
    select_object_hint: "Select a survey object first.",
    selected_object: "Selected object",
    save_attributes: "Save attributes",
    edit_geometry: "Edit geometry",
    save_geometry: "Save geometry",
    reset_geometry: "Reset geometry",
    stop_edit: "Stop edit",
    geometry_hint: "Geometry edit mode supports moving vertices, reshaping polygons, and adding points to line/polygon segments.",
    survey_export: "Survey export",
    data: "Data",
    document: "Document",
    permission: "Permission",
    export_selected: "Export selected",
    point_labels: "Point labels",
    basemaps: "Basemaps",
    basemap_hint: "Choose a background map. The active basemap stays in place while survey layers remain on top.",
    basemap_footer: "Switching basemaps keeps the current survey layers and view in place.",
    click_feature: "Click a map feature to inspect it.",
    layer: "Layer",
    load_layers: "Reload layers",
    no_layers_loaded: "No layers loaded.",
    region: "Region",
    details: "Feature inspection",
    scratch_notes: "Scratch notes",
    planning_context: "Planning context",
    workspace_controls: "Workspace controls",
    outputs: "Outputs",
    map_layers: "Map layers",
    base_map: "Base map",
    summary: "Summary",
    scratch_space: "Scratch space",
    no_surveys_loaded: "No surveys loaded. Click Refresh.",
    survey_load_error: "Survey load error",
    loaded_records: "survey record(s) loaded.",
    survey_set: "Survey set",
    no_survey_selected: "No survey selected",
    select_survey_first: "Select a survey first",
    select_feature_first: "Select a feature first",
    select_object_first: "Select an object first",
    enter_title: "Enter a title",
    draw_boundary_first: "Draw a boundary first",
    set_active_survey_first: "Set an active survey first",
    no_editable_geometry_found: "No editable geometry found",
    selected_feature_no_id: "Selected feature cannot be edited; no survey object id",
    geometry_edit_on: "Geometry edit on. Drag vertices; click segments to add points.",
    geometry_edit_off: "Geometry edit off",
    geometry_saved: "Geometry saved",
    geometry_reset: "Geometry reset",
    geometry_save_failed: "Geometry save failed",
    layer_shown: "Layer shown",
    layer_hidden: "Layer hidden",
    labels_on: "Labels on",
    labels_off: "Labels off",
    survey_created: "Survey created",
    object_created: "Object created",
    saved: "Saved",
    deleted: "Deleted",
    permission_exported: "Permission exported",
    export_failed: "Export failed",
    geometry_captured: "Geometry captured",
    save: "Save",
    active: "Active",
    other: "Other",
    group: "Group",
    show: "Show",
    hide: "Hide",
    delete: "Delete",
    yes: "Yes",
    no: "No"
    ,
    basemaps: {
      osm: {
        label: "Standard Map / OSM",
        description: "General-purpose street map with roads, place names, and cartographic detail from OpenStreetMap.",
        sourceNote: "Community-maintained street and place data"
      },
      satellite: {
        label: "Satellite / ESRI World Imagery",
        description: "High-resolution aerial and satellite imagery for inspecting roofs, terrain, boundaries, and land cover.",
        sourceNote: "Imagery basemap"
      },
      topo: {
        label: "Topographic / ESRI World Topo Map",
        description: "Topographic reference map with terrain context, contours, and labelled features for planning work.",
        sourceNote: "Topo reference basemap"
      },
      streets: {
        label: "ESRI Streets",
        description: "Clean road-oriented map designed for navigation, street context, and quick situational reference.",
        sourceNote: "Road and place-name basemap"
      },
      cartoLight: {
        label: "Carto Light / Positron",
        description: "Minimal light basemap that keeps attention on survey overlays, labels, and selected features.",
        sourceNote: "Neutral cartographic background"
      },
      cartoDark: {
        label: "Carto Dark / Dark Matter",
        description: "Dark-toned basemap that improves contrast for bright overlays and low-light visual environments.",
        sourceNote: "Dark contrast basemap"
      }
    }
  },
  de: {
    app_name: "SurveyCatalyst",
    api: "API",
    db: "DB",
    tab_survey: "Umfrage",
    tab_create: "Erstellen",
    tab_edit: "Bearbeiten",
    tab_export: "Export",
    tab_manage: "Verwalten",
    tab_plan: "Planung",
    tab_layers: "Ebenen",
    tab_basemap: "Basiskarte",
    tab_details: "Details",
    tab_region: "Region",
    tab_notes: "Notizen",
    survey: "Umfrage",
    selection: "Auswahl",
    surveys: "Umfragen",
    layers: "Ebenen",
    hide_surveys: "Umfragen ausblenden",
    show_surveys: "Umfragen anzeigen",
    hide_layers: "Ebenen ausblenden",
    show_layers: "Ebenen anzeigen",
    lang_en: "EN",
    lang_de: "DE",
    active_survey: "Aktive Umfrage",
    select_survey: "Umfrage auswählen",
    refresh: "Aktualisieren",
    load: "Laden",
    zoom: "Zoomen",
    survey_context: "Umgebung der Umfrage",
    selected: "Ausgewählt",
    status: "Status",
    id: "ID",
    objects: "Objekte",
    survey_context_hint: "Dieser Tab wählt nur die aktive Umfrage aus. Erstellen und Bearbeiten bleiben getrennte Arbeitsabläufe.",
    system: "System",
    title: "Titel",
    draw_boundary: "Grenze zeichnen",
    create: "Erstellen",
    survey_hint: "Erstellt eine neue Umfrage aus der gezeichneten Grenze und setzt sie danach aktiv.",
    object: "Objekt",
    object_title: "Objekttitel",
    notes: "Notizen",
    point: "Punkt",
    line: "Linie",
    polygon: "Polygon",
    active_survey_hint: "Aktive Umfrage",
    select_object_hint: "Bitte zuerst ein Umfrageobjekt auswählen.",
    selected_object: "Ausgewähltes Objekt",
    save_attributes: "Attribute speichern",
    edit_geometry: "Geometrie bearbeiten",
    save_geometry: "Geometrie speichern",
    reset_geometry: "Geometrie zurücksetzen",
    stop_edit: "Bearbeitung stoppen",
    geometry_hint: "Der Geometriebearbeitungsmodus unterstützt das Verschieben von Knoten, das Umformen von Polygonen und das Hinzufügen von Punkten an Linien- und Polygonsegmenten.",
    survey_export: "Export der Umfrage",
    data: "Daten",
    document: "Dokument",
    permission: "Berechtigung",
    export_selected: "Auswahl exportieren",
    point_labels: "Punktbeschriftungen",
    basemaps: "Basiskarten",
    basemap_hint: "Wählen Sie eine Hintergrundkarte. Die aktive Basiskarte bleibt sichtbar, während die Umfrageebenen darüber liegen.",
    basemap_footer: "Der Wechsel der Basiskarte verändert die aktuellen Umfrageebenen und die Ansicht nicht.",
    click_feature: "Klicken Sie ein Kartenobjekt an, um es zu prüfen.",
    layer: "Ebene",
    load_layers: "Ebenen neu laden",
    no_layers_loaded: "Keine Ebenen geladen.",
    region: "Region",
    details: "Objektprüfung",
    scratch_notes: "Notizen",
    planning_context: "Planungskontext",
    workspace_controls: "Arbeitsbereich",
    outputs: "Ausgaben",
    map_layers: "Kartenebenen",
    base_map: "Basiskarte",
    summary: "Zusammenfassung",
    scratch_space: "Arbeitsnotizen",
    no_surveys_loaded: "Keine Umfragen geladen. Auf Aktualisieren klicken.",
    survey_load_error: "Fehler beim Laden der Umfragen",
    loaded_records: "Umfrageeintrag(e) geladen.",
    survey_set: "Umfrage gesetzt",
    no_survey_selected: "Keine Umfrage ausgewählt",
    select_survey_first: "Bitte zuerst eine Umfrage auswählen",
    select_feature_first: "Bitte zuerst ein Objekt auswählen",
    select_object_first: "Bitte zuerst ein Objekt auswählen",
    enter_title: "Bitte einen Titel eingeben",
    draw_boundary_first: "Bitte zuerst eine Grenze zeichnen",
    set_active_survey_first: "Bitte zuerst eine aktive Umfrage festlegen",
    no_editable_geometry_found: "Keine bearbeitbare Geometrie gefunden",
    selected_feature_no_id: "Ausgewähltes Objekt kann nicht bearbeitet werden; keine Umfrageobjekt-ID",
    geometry_edit_on: "Geometriebearbeitung aktiv. Knoten ziehen; Segmente anklicken, um Punkte hinzuzufügen.",
    geometry_edit_off: "Geometriebearbeitung aus",
    geometry_saved: "Geometrie gespeichert",
    geometry_reset: "Geometrie zurückgesetzt",
    geometry_save_failed: "Fehler beim Speichern der Geometrie",
    layer_shown: "Ebene angezeigt",
    layer_hidden: "Ebene ausgeblendet",
    labels_on: "Beschriftungen an",
    labels_off: "Beschriftungen aus",
    survey_created: "Umfrage erstellt",
    object_created: "Objekt erstellt",
    saved: "Gespeichert",
    deleted: "Gelöscht",
    permission_exported: "Berechtigung exportiert",
    export_failed: "Export fehlgeschlagen",
    geometry_captured: "Geometrie erfasst",
    save: "Speichern",
    active: "Aktiv",
    other: "Sonstige",
    group: "Gruppe",
    show: "Anzeigen",
    hide: "Ausblenden",
    delete: "Löschen",
    yes: "Ja",
    no: "Nein",
    basemaps: {
      osm: {
        label: "Standardkarte / OSM",
        description: "Allgemeine Straßenkarte mit Wegen, Ortsnamen und kartografischen Details aus OpenStreetMap.",
        sourceNote: "Gemeinschaftlich gepflegte Straßen- und Ortsdaten"
      },
      satellite: {
        label: "Satellit / ESRI World Imagery",
        description: "Hochauflösende Luft- und Satellitenbilder zum Prüfen von Dächern, Gelände, Grenzen und Landbedeckung.",
        sourceNote: "Bildbasiskarte"
      },
      topo: {
        label: "Topografisch / ESRI World Topo Map",
        description: "Topografische Referenzkarte mit Geländekontext, Höhenlinien und beschrifteten Merkmalen für die Planung.",
        sourceNote: "Topografische Referenzkarte"
      },
      streets: {
        label: "ESRI Straßen",
        description: "Straßenorientierte Karte für Navigation, Ortsbezug und schnellen Überblick.",
        sourceNote: "Straßen- und Ortsnamenkarte"
      },
      cartoLight: {
        label: "Carto Hell / Positron",
        description: "Zurückhaltende helle Basiskarte, die den Fokus auf Überlagerungen und Beschriftungen lässt.",
        sourceNote: "Neutrale kartografische Hintergrundkarte"
      },
      cartoDark: {
        label: "Carto Dunkel / Dark Matter",
        description: "Dunkle Basiskarte mit hohem Kontrast für helle Überlagerungen und schwach beleuchtete Umgebungen.",
        sourceNote: "Dunkle Kontrast-Basiskarte"
      }
    }
  }
};

function langPack() {
  return I18N[state.lang] || I18N.en;
}

function t(key, fallback = "") {
  const pack = langPack();
  return pack[key] ?? I18N.en[key] ?? fallback ?? key;
}

function tBasemap(key, field) {
  const entry = I18N[state.lang]?.basemaps?.[key]?.[field];
  return entry ?? I18N.en.basemaps?.[key]?.[field] ?? BASEMAPS[key]?.[field] ?? "";
}

function tTab(id, fallback) {
  return t(`tab_${id}`, fallback || fallbackTabTitle(id));
}

function fallbackTabTitle(id) {
  return ({survey:"Survey", create:"Create", edit:"Edit", export:"Export", manage:"Manage", plan:"Plan", layers:"Layers", basemap:"Basemap", details:"Details", region:"Region", notes:"Notes"})[id] || id;
}

function setLanguage(lang) {
  const next = I18N[lang] ? lang : "en";
  state.lang = next;
  if (typeof localStorage !== "undefined") localStorage.setItem("surveyCatalyst.lang", next);
  document.documentElement.lang = next;
  render();
}

const BASEMAPS = {
  osm: {
    label: "Standard Map / OSM",
    description: "General-purpose street map with roads, place names, and cartographic detail from OpenStreetMap.",
    url: "https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attributions: "© OpenStreetMap contributors",
    sourceNote: "Community-maintained street and place data"
  },
  satellite: {
    label: "Satellite / ESRI World Imagery",
    description: "High-resolution aerial and satellite imagery for inspecting roofs, terrain, boundaries, and land cover.",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attributions: "Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
    sourceNote: "Imagery basemap"
  },
  topo: {
    label: "Topographic / ESRI World Topo Map",
    description: "Topographic reference map with terrain context, contours, and labelled features for planning work.",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
    attributions: "Tiles © Esri",
    sourceNote: "Topo reference basemap"
  },
  streets: {
    label: "ESRI Streets",
    description: "Clean road-oriented map designed for navigation, street context, and quick situational reference.",
    url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
    attributions: "Tiles © Esri",
    sourceNote: "Road and place-name basemap"
  },
  cartoLight: {
    label: "Carto Light / Positron",
    description: "Minimal light basemap that keeps attention on survey overlays, labels, and selected features.",
    url: "https://{a-c}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
    attributions: "© OpenStreetMap contributors © CARTO",
    sourceNote: "Neutral cartographic background"
  },
  cartoDark: {
    label: "Carto Dark / Dark Matter",
    description: "Dark-toned basemap that improves contrast for bright overlays and low-light visual environments.",
    url: "https://{a-c}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
    attributions: "© OpenStreetMap contributors © CARTO",
    sourceNote: "Dark contrast basemap"
  }
};

function createBasemapSource(key) {
  const entry = BASEMAPS[key] || BASEMAPS.osm;
  return new ol.source.XYZ({
    url: entry.url,
    attributions: entry.attributions,
    crossOrigin: "anonymous"
  });
}

let modifyInteraction = null;
let snapInteraction = null;

function editableFeature() {
  if (!selectionSource) return null;
  const fs = selectionSource.getFeatures();
  return fs.length ? fs[0] : null;
}

function startGeometryEdit() {
  if (!state.selection) {
    alert(t("select_feature_first"));
    return;
  }

  stopGeometryEdit(false);

  modifyInteraction = new ol.interaction.Modify({
    source: selectionSource
  });

  snapInteraction = new ol.interaction.Snap({
    source: selectionSource
  });

  map.addInteraction(modifyInteraction);
  map.addInteraction(snapInteraction);

  toast(t("geometry_edit_on"));
}

function stopGeometryEdit(showToast = true) {
  if (modifyInteraction) {
    map.removeInteraction(modifyInteraction);
    modifyInteraction = null;
  }
  if (snapInteraction) {
    map.removeInteraction(snapInteraction);
    snapInteraction = null;
  }
  if (showToast) toast(t("geometry_edit_off"));
}

async function saveGeometryEdit() {
  if (!state.selection) {
    alert(t("select_object_first"));
    return;
  }

  const edited = editableFeature();
  if (!edited) {
    alert(t("no_editable_geometry_found"));
    return;
  }

  const id = state.selection.properties.id;
  if (!id) {
    alert(t("selected_feature_no_id"));
    return;
  }

  const props = {...state.selection.properties};
  const title = document.getElementById("editTitle")?.value || props.title || null;
  const note = document.getElementById("editNote")?.value || props.note || props.annotation || "";

  props.title = title;
  props.note = note;
  props.annotation = note;

  try {
    await fetchJson(`/api/survey-objects/${id}`, {
      method: "PATCH",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        geometry: toGeoJSONGeometry(edited),
        type: props.type || "note",
        properties: props,
        title,
        annotation: note,
        details: props.details || null,
        is_active: true
      })
    });

    stopGeometryEdit(false);

    if (state.activeSurveyId) {
      await loadSurveyFeatures(state.activeSurveyId, false);
    }

    toast(t("geometry_saved"));
  } catch (error) {
    console.error("saveGeometryEdit failed", error);
    alert(t("geometry_save_failed") + ": " + (error?.message || error));
  }
}

function resetSelectedGeometry() {
  if (!state.selection || !state.selection.feature) {
    alert(t("select_feature_first"));
    return;
  }
  selectionSource.clear();
  selectionSource.addFeature(state.selection.feature.clone());
  toast(t("geometry_reset"));
}


function esc(v) {
  return String(v ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function apiUrl(url) {
  try {
    const u = new URL(url, window.location.origin);
    if (u.pathname.startsWith("/api/") || u.pathname === "/health") {
      u.searchParams.set("lang", state.lang || "en");
    }
    return u.pathname + u.search + u.hash;
  } catch {
    return url;
  }
}

function css() {
  if (document.getElementById("minimalUiCss")) return;
  const style = document.createElement("style");
  style.id = "minimalUiCss";
  style.textContent = `
    :root {
      --bg: #f4f6f8;
      --panel: #ffffff;
      --panel-2: #f8fafc;
      --line: #d7dde5;
      --line-strong: #b8c2d0;
      --text: #172033;
      --muted: #667085;
      --accent: #1f5fbf;
      --accent-soft: #e8f1ff;
      --danger: #b42318;
      --topbar: #f8fafc;
    }
    html, body {
      margin: 0;
      height: 100%;
      overflow: hidden;
      font-family: Segoe UI, Inter, Arial, sans-serif;
      font-size: 12px;
      color: var(--text);
      background: var(--bg);
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
      top:0;
      left:0;
      right:0;
      transform:none;
      z-index:40;
      pointer-events:auto;
    }
    .topbar {
      display:grid;
      grid-template-columns:minmax(0, 1fr) auto;
      align-items:center;
      gap:14px;
      width:100%;
      min-width:0;
      min-height:44px;
      padding:7px 14px;
      box-sizing:border-box;
      border-radius:0;
      color:#172033;
      background:var(--topbar);
      border-bottom:1px solid var(--line-strong);
      box-shadow:0 1px 4px rgba(15,23,42,.10);
    }
    .topbar-left {
      display:flex;
      align-items:center;
      gap:14px;
      min-width:0;
      flex-wrap:wrap;
    }
    .brand {
      display:flex;
      align-items:center;
      gap:7px;
      font-size:13px;
      font-weight:750;
      letter-spacing:0;
      flex:0 0 auto;
    }
    .mark {
      width:15px;
      height:15px;
      border-radius:3px;
      background:var(--accent);
      box-shadow:inset 0 0 0 1px rgba(255,255,255,.28);
    }
    .top-meta {
      display:flex;
      gap:6px;
      flex-wrap:wrap;
      margin-left:auto;
      justify-content:flex-end;
      color:#475467;
      font-size:10px;
    }
    .top-meta span {
      display:inline-flex;
      align-items:center;
      min-height:21px;
      padding:0 7px;
      border:1px solid #dbe2ea;
      border-radius:4px;
      background:#fff;
      white-space:nowrap;
    }
    .topbar-actions {
      display:flex;
      align-items:center;
      gap:6px;
      flex-wrap:wrap;
    }
    .topbar-actions button,
    .topbar-actions select {
      height:25px;
      padding:0 9px;
      border-radius:4px;
      border-color:#cbd5e1;
      background:#ffffff;
      color:#1f2937;
      box-shadow:none;
    }
    .topbar-actions select {
      appearance:none;
      min-width:120px;
      padding-right:10px;
    }
    .topbar-actions .tab {
      height:25px;
      padding:0 10px;
      border-color:#cbd5e1;
      background:#ffffff;
      color:#1f2937;
      box-shadow:none;
    }
    .topbar-actions .tab:hover {
      background:#f1f5f9;
      border-color:#94a3b8;
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
    .tab {
      height:26px;
      padding:0 9px;
      border:1px solid transparent;
      border-radius:4px;
      background:transparent;
      color:#475467;
      font-size:11px;
      font-weight:700;
      line-height:24px;
      letter-spacing:0;
      cursor:pointer;
      box-shadow:none;
    }
    .tab.active {
      color:var(--accent);
      background:var(--accent-soft);
      border-color:#b9d3ff;
    }
    .tab.toggle {
      height:25px;
      color:#344054;
      background:#fff;
      border-color:#cbd5e1;
    }
    .panel {
      position:absolute;
      top:54px;
      bottom:14px;
      width:352px;
      z-index:30;
      pointer-events:auto;
      background:var(--panel);
      border:1px solid #c7d0dc;
      border-radius:6px;
      box-shadow:0 10px 24px rgba(15,23,42,.13);
      overflow:hidden;
      display:flex;
      flex-direction:column;
      transition:transform .18s ease, opacity .18s ease;
    }
    #left-panel { left:16px; }
    #right-panel { right:16px; width:392px; }
    .panel.closed-left { transform:translateX(-380px); opacity:0; }
    .panel.closed-right { transform:translateX(420px); opacity:0; }
    .panel-head {
      padding:10px 10px 0;
      box-sizing:border-box;
      border-bottom:1px solid var(--line);
      background:var(--panel-2);
    }
    .panel-head-main {
      display:flex;
      align-items:flex-start;
      justify-content:space-between;
      gap:10px;
    }
    .panel-title {
      font-size:12px;
      font-weight:750;
      line-height:16px;
      letter-spacing:0;
    }
    .panel-sub {
      color:var(--muted);
      font-size:10px;
      margin-top:1px;
      line-height:13px;
    }
    .panel-tabs {
      display:flex;
      flex-wrap:nowrap;
      gap:2px;
      margin:8px -10px 0;
      padding:0 10px;
      border-top:1px solid #e4e9f0;
      overflow-x:auto;
    }
    .panel-tabs .tab {
      flex:0 0 auto;
      white-space:nowrap;
      border-radius:4px 4px 0 0;
      border-color:transparent;
      height:29px;
      line-height:27px;
      margin-bottom:-1px;
    }
    .panel-tabs .tab.active {
      color:#172033;
      background:#fff;
      border-color:var(--line);
      border-bottom-color:#fff;
    }
    .panel-body {
      padding:11px 12px;
      overflow:auto;
      flex:1;
      background:#fff;
    }
    .section {
      margin-bottom:11px;
      padding:0 0 10px;
      border-bottom:1px solid #e5e7eb;
    }
    .section:last-child { border-bottom:0; }
    .section-title {
      font-size:10px;
      font-weight:700;
      color:#344054;
      margin:0 0 8px 0;
      text-transform:uppercase;
      letter-spacing:.03em;
    }
    .basemap-grid {
      display:grid;
      grid-template-columns:repeat(2, minmax(0, 1fr));
      gap:6px;
    }
    .basemap-btn {
      width:100%;
      margin:0;
      height:auto;
      min-height:78px;
      padding:8px 10px;
      text-align:left;
      border-radius:5px;
      line-height:1.2;
      display:flex;
      flex-direction:column;
      gap:4px;
      justify-content:flex-start;
      white-space:normal;
      overflow:visible;
    }
    .basemap-btn .basemap-title {
      font-size:11px;
      font-weight:700;
      color:inherit;
      line-height:14px;
    }
    .basemap-btn .basemap-desc {
      font-size:10px;
      font-weight:500;
      color:inherit;
      opacity:.86;
      line-height:14px;
    }
    .basemap-btn .basemap-meta {
      font-size:9px;
      color:inherit;
      opacity:.72;
      line-height:12px;
    }
    label {
      font-size:11px;
      color:#344054;
    }
    select, input, textarea {
      width:100%;
      box-sizing:border-box;
      height:30px;
      border:1px solid #cbd5e1;
      border-radius:4px;
      background:#fff;
      color:#111827;
      padding:4px 8px;
      font-size:12px;
      margin:4px 0 6px 0;
      outline:none;
    }
    select:focus, input:focus, textarea:focus {
      border-color:#7aa7e8;
      box-shadow:0 0 0 2px rgba(31,95,191,.12);
    }
    textarea {
      height:62px;
      resize:vertical;
      line-height:16px;
    }
    button {
      height:28px;
      border:1px solid #cbd5e1;
      border-radius:4px;
      padding:0 10px;
      margin:0 4px 5px 0;
      background:#f8fafc;
      color:#1f2937;
      font-size:11px;
      font-weight:650;
      cursor:pointer;
    }
    button:hover {
      background:#eef2f7;
      border-color:#94a3b8;
    }
    .panel-head button {
      margin:0;
    }
    .panel-head .tab {
      margin:0;
    }
    button.primary {
      border-color:var(--accent);
      background:var(--accent);
      color:white;
    }
    button.primary:hover {
      background:#184f9f;
      border-color:#184f9f;
    }
    button.danger {
      border-color:var(--danger);
      background:var(--danger);
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
      min-height:24px;
      margin:0;
      border-bottom:1px solid #f0f3f7;
    }
    .row:last-child {
      border-bottom:0;
    }
    .row strong {
      font-weight:700;
      color:#111827;
      text-align:right;
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
      display:flex;
      align-items:center;
      gap:8px;
      width:100%;
      min-height:28px;
      padding:4px 0;
      border-bottom:1px solid #eef2f7;
    }
    .layer-row:last-child { border-bottom:0; }
    .layer-row input {
      width:auto;
      height:auto;
      margin:0;
      flex:0 0 auto;
    }
    .layer-row-main {
      flex:1;
      min-width:0;
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:10px;
    }
    .layer-name {
      font-size:11px;
      font-weight:600;
      color:#1f2937;
      line-height:14px;
      word-break:break-word;
      min-width:0;
      white-space:nowrap;
      overflow:hidden;
      text-overflow:ellipsis;
    }
    .layer-count {
      flex:0 0 auto;
      font-size:10px;
      font-weight:700;
      color:#344054;
      background:#f1f5f9;
      border:1px solid #dbe2ea;
      border-radius:4px;
      padding:1px 6px;
      white-space:nowrap;
      min-width:24px;
      text-align:center;
    }
    .layer-toolbar {
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:8px;
      padding:0 0 8px;
      margin:0 0 8px;
      border-bottom:1px solid #e5e7eb;
    }
    .layer-toggle {
      display:flex;
      align-items:center;
      gap:6px;
      min-width:0;
      margin:0;
      font-size:11px;
      font-weight:600;
      color:#344054;
    }
    .layer-toggle input {
      width:auto;
      height:auto;
      margin:0;
    }
    .layer-toolbar button {
      flex:0 0 auto;
      margin:0;
      height:24px;
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
  const res = await fetch(apiUrl(url), opts);
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
      left: [{id:"survey",title:"Survey"},{id:"create",title:"Create"},{id:"edit",title:"Edit"},{id:"export",title:"Export"},{id:"manage",title:"Manage"},{id:"plan",title:"Plan"}],
      right: [{id:"layers",title:"Layers"},{id:"basemap",title:"Basemap"},{id:"details",title:"Details"},{id:"region",title:"Region"},{id:"notes",title:"Notes"}]
    };
  }
}

function initMap() {
  baseLayer = new ol.layer.Tile({
    source: createBasemapSource(state.activeBasemap)
  });

  map = new ol.Map({
    target:"map",
    layers:[baseLayer],
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
  setBasemap(state.activeBasemap);

  map.on("singleclick", e => {
    let hit = null;
    map.forEachFeatureAtPixel(e.pixel, f => {
      hit = f;
      return true;
    });
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

window.loadSurveys = async function loadSurveys() {
  try {
    const payload = await fetchJson("/api/surveys");
    state.surveys = normaliseSurveyPayload(payload);
    state.surveyLoadError = "";

    if (state.activeSurveyId && !state.surveys.some(s => surveyId(s) === String(state.activeSurveyId))) {
      state.activeSurveyId = null;
    }

    if (!state.activeSurveyId && state.surveys.length) {
      state.activeSurveyId = surveyId(state.surveys[0]);
    }
  } catch (error) {
    state.surveyLoadError = String(error?.message || error);
    console.error("loadSurveys failed", error);
  }
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
      <div class="topbar-left">
        <div class="brand"><span class="mark"></span>${esc(t("app_name", "SurveyCatalyst"))}</div>
        <div class="topbar-actions">
          <button class="tab" onclick="toggleLeft()">${esc(state.leftOpen ? t("hide_surveys") : t("show_surveys"))}</button>
          <button class="tab" onclick="toggleRight()">${esc(state.rightOpen ? t("hide_layers") : t("show_layers"))}</button>
          <button class="tab" onclick="setLanguage('en')">${t("lang_en")}</button>
          <button class="tab" onclick="setLanguage('de')">${t("lang_de")}</button>
        </div>
      </div>
      <div class="top-meta">
        <span><span class="status-dot ${state.system.api ? "on" : ""}"></span>${esc(t("api"))}</span>
        <span>${esc(t("db"))} ${state.system.db ? "ON" : "OFF"}</span>
        <span>${esc(titleFor("left", state.activeLeft))} / ${esc(titleFor("right", state.activeRight))}</span>
        <span>${esc(t("survey"))}: ${esc(survey?.title || state.activeSurveyId || "none")}</span>
        <span>${esc(t("selection"))}: ${esc(state.selection?.title || "none")}</span>
      </div>
    </div>
  `;
}

function panel(id, side, title, sub, body) {
  const el = document.getElementById(id);
  el.className = `panel ${side === "left" ? (state.leftOpen ? "" : "closed-left") : (state.rightOpen ? "" : "closed-right")}`;
  const toggle = side === "left"
    ? `<button class="tab toggle" onclick="toggleLeft()">${state.leftOpen ? "Hide" : "Show"}</button>`
    : `<button class="tab toggle" onclick="toggleRight()">${state.rightOpen ? "Hide" : "Show"}</button>`;
  el.innerHTML = `
    <div class="panel-head">
      <div class="panel-head-main">
        <div>
          <div class="panel-title">${esc(title)}</div>
          <div class="panel-sub">${esc(sub)}</div>
        </div>
        ${toggle}
      </div>
      <div class="panel-tabs">${panelTabs(side)}</div>
    </div>
    <div class="panel-body">${body}</div>
  `;
}

function panelTabs(side) {
  const tabs = side === "left" ? (state.manifest?.left || []) : (state.manifest?.right || []);
  return tabs.map(t => {
    const active = side === "left" ? state.activeLeft === t.id : state.activeRight === t.id;
    const click = side === "left" ? `setLeft('${esc(t.id)}')` : `setRight('${esc(t.id)}')`;
    return `<button class="tab ${active ? "active" : ""}" onclick="${click}">${esc(tTab(t.id, t.title))}</button>`;
  }).join("");
}

function leftBody() {
  if (state.activeLeft === "survey") return surveyBody();
  if (state.activeLeft === "manage") return manageBody();
  if (state.activeLeft === "plan") return `<div class="section"><div class="section-title">${esc(t("planning_context"))}</div><div class="hint">${esc(t("planning_context"))}</div></div>`;
  if (state.activeLeft === "create") return createBody();
  if (state.activeLeft === "edit") return editBody();
  if (state.activeLeft === "export") return exportBody();
  return "";
}


function rightBody() {
  if (state.activeRight === "layers") return layersBody();
  if (state.activeRight === "basemap") return basemapBody();
  if (state.activeRight === "details") return detailsBody();
  if (state.activeRight === "region") return regionBody();
  if (state.activeRight === "notes") return `<div class="section"><div class="section-title">${esc(t("scratch_notes"))}</div><textarea placeholder="${esc(t("scratch_space"))}"></textarea><button onclick="toast('${esc(t("save"))}')">${esc(t("save"))}</button></div>`;
  return "";
}

function surveyRows() {
  return Array.isArray(state.surveys) ? state.surveys : [];
}

function surveyId(survey) {
  return String(survey?.id ?? survey?.survey_id ?? survey?.key ?? survey?.name ?? "");
}

function surveyName(survey) {
  return String(survey?.title ?? survey?.name ?? survey?.label ?? survey?.survey_name ?? surveyId(survey) ?? "Unnamed survey");
}

function surveyStatus(survey) {
  return String(survey?.status ?? survey?.state ?? "active");
}

function layerObjectCount(layer) {
  const direct = layer?.object_count ?? layer?.feature_count ?? layer?.metadata?.object_count ?? layer?.metadata?.feature_count;
  if (direct !== undefined && direct !== null && direct !== "") return direct;
  const key = String(layer?.layer_key || "");
  if (key.startsWith("survey_")) {
    const survey = surveyRows().find(s => String(s?.layer_key || "") === key);
    if (survey && survey.object_count !== undefined && survey.object_count !== null) return survey.object_count;
  }
  return null;
}

function activeSurveyRecord() {
  const active = String(state.activeSurveyId || "");
  return surveyRows().find(s => surveyId(s) === active) || null;
}

function normaliseSurveyPayload(payload) {
  if (Array.isArray(payload)) return payload;
  if (payload && Array.isArray(payload.surveys)) return payload.surveys;
  if (payload && Array.isArray(payload.items)) return payload.items;
  if (payload && Array.isArray(payload.data)) return payload.data;
  if (payload && Array.isArray(payload.results)) return payload.results;
  return [];
}

function surveyBody() {
  const rows = surveyRows();
  const active = activeSurveyRecord();
  const activeId = String(state.activeSurveyId || "");

  const options = rows.map(survey => {
    const id = surveyId(survey);
    return `<option value="${esc(id)}" ${id === activeId ? "selected" : ""}>${esc(surveyName(survey))}</option>`;
  }).join("");

  const message = state.surveyLoadError
    ? `<div class="hint">${esc(t("survey_load_error"))}: ${esc(state.surveyLoadError)}</div>`
    : rows.length
      ? `<div class="hint">${esc(rows.length)} ${esc(t("loaded_records"))}</div>`
      : `<div class="hint">${esc(t("no_surveys_loaded"))}</div>`;

  return `
    <div class="section">
      <div class="section-title">${esc(t("active_survey"))}</div>
      <select id="surveyContextSelect" onchange="setActiveSurveyContext(this.value)">
        <option value="">${esc(t("select_survey"))}</option>
        ${options}
      </select>
      <button onclick="loadSurveys()">${esc(t("refresh"))}</button>
      <button class="primary" onclick="loadSelectedSurvey(false)">${esc(t("load"))}</button>
      <button onclick="loadSelectedSurvey(true)">${esc(t("zoom"))}</button>
      ${message}
    </div>
    <div class="section">
      <div class="section-title">${esc(t("survey_context"))}</div>
      <div class="row"><span>${esc(t("selected"))}</span><strong>${esc(active ? surveyName(active) : "none")}</strong></div>
      <div class="row"><span>${esc(t("status"))}</span><strong>${esc(active ? surveyStatus(active) : "-")}</strong></div>
      <div class="row"><span>${esc(t("id"))}</span><strong>${esc(active ? surveyId(active) : "-")}</strong></div>
      <div class="row"><span>${esc(t("objects"))}</span><strong>${esc(active ? (active.object_count ?? active.feature_count ?? active.objects?.length ?? "-") : "-")}</strong></div>
      <div class="hint">${esc(t("survey_context_hint"))}</div>
    </div>
  `;
}

function manageBody() {
  return `
    <div class="section">
      <div class="section-title">${esc(t("system"))}</div>
      <div class="row"><span>${esc(t("api"))}</span><span class="badge ${state.system.api ? "on" : ""}">${state.system.api ? "ON" : "OFF"}</span></div>
      <div class="row"><span>${esc(t("db"))}</span><span class="badge ${state.system.db ? "on" : ""}">${state.system.db ? "ON" : "OFF"}</span></div>
      <button onclick="refreshSystem()">${esc(t("refresh"))}</button>
    </div>
  `;
}

function createBody() {
  const active = activeSurveyRecord();
  return `
    <div class="section">
      <div class="section-title">${esc(t("survey"))}</div>
      <input id="createSurveyTitle" placeholder="${esc(t("title"))}">
      <input id="createSurveyStatus" value="active" placeholder="${esc(t("status"))}">
      <button onclick="startDraw('polygon')">${esc(t("draw_boundary"))}</button>
      <button class="primary" onclick="createSurvey()">${esc(t("create"))}</button>
      <div class="hint">${esc(t("survey_hint"))}</div>
    </div>
    <div class="section">
      <div class="section-title">${esc(t("active_survey"))}</div>
      <div class="row"><span>${esc(t("selected"))}</span><strong>${esc(active ? surveyName(active) : "none")}</strong></div>
      <div class="row"><span>${esc(t("status"))}</span><strong>${esc(active ? surveyStatus(active) : "-")}</strong></div>
      <div class="row"><span>${esc(t("id"))}</span><strong>${esc(active ? surveyId(active) : "-")}</strong></div>
    </div>
    <div class="section">
      <div class="section-title">${esc(t("object"))}</div>
      <select id="createObjectType"><option value="note">note</option><option value="findspot">findspot</option><option value="track">track</option><option value="polygon">polygon</option></select>
      <input id="createObjectTitle" placeholder="${esc(t("object_title"))}">
      <textarea id="createObjectNote" placeholder="${esc(t("notes"))}"></textarea>
      <button onclick="startDraw('point')">${esc(t("point"))}</button>
      <button onclick="startDraw('line')">${esc(t("line"))}</button>
      <button onclick="startDraw('polygon')">${esc(t("polygon"))}</button>
      <button class="primary" onclick="createObject()">${esc(t("create"))}</button>
    </div>
  `;
}

function editBody() {
  const survey = activeSurveyRecord();
  const p = state.selection?.properties || {};
  return `
    <div class="section">
      <div class="section-title">${esc(t("active_survey"))}</div>
      <div class="row"><span>${esc(t("selected"))}</span><strong>${esc(survey ? surveyName(survey) : "none")}</strong></div>
      <div class="row"><span>${esc(t("status"))}</span><strong>${esc(survey ? surveyStatus(survey) : "-")}</strong></div>
      <div class="row"><span>${esc(t("id"))}</span><strong>${esc(survey ? surveyId(survey) : "-")}</strong></div>
      <div class="row"><span>${esc(t("objects"))}</span><strong>${esc(survey ? (survey.object_count ?? survey.feature_count ?? survey.objects?.length ?? "-") : "-")}</strong></div>
      <div class="hint">${esc(t("select_object_hint"))}</div>
    </div>
    ${state.selection ? `
    <div class="section">
      <div class="section-title">${esc(t("selected_object"))}</div>
      <input id="editTitle" value="${esc(p.title || state.selection.title || "")}" placeholder="${esc(t("title"))}">
      <textarea id="editNote" placeholder="${esc(t("notes"))}">${esc(p.note || p.annotation || "")}</textarea>

      <button class="primary" onclick="saveSelection()">${esc(t("save_attributes"))}</button>
      <button onclick="startGeometryEdit()">${esc(t("edit_geometry"))}</button>
      <button onclick="saveGeometryEdit()">${esc(t("save_geometry"))}</button>
      <button onclick="resetSelectedGeometry()">${esc(t("reset_geometry"))}</button>
      <button onclick="stopGeometryEdit()">${esc(t("stop_edit"))}</button>
      <button class="danger" onclick="deleteSelection()">${esc(t("delete"))}</button>

      <div class="hint">
        ${esc(t("geometry_hint"))}
      </div>
    </div>
    ` : `<div class="section"><div class="hint">${esc(t("select_object_hint"))}</div></div>`}
  `;
}

function exportBody() {
  return `
    <div class="section">
      <div class="section-title">${esc(t("survey_export"))}</div>
      <button class="primary" onclick="exportLayer()">GeoJSON</button>
      <button onclick="exportData()">${esc(t("data"))}</button>
      <button onclick="exportDocument()">${esc(t("document"))}</button>
    </div>
    <div class="section">
      <div class="section-title">${esc(t("permission"))}</div>
      <button class="primary" onclick="exportPermission()">${esc(t("export_selected"))}</button>
      <div class="hint">${esc(t("click_feature"))}</div>
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
  const hasLayers = Object.keys(groups).length > 0;

  return `
    <div class="layer-toolbar">
      <label class="layer-toggle"><input type="checkbox" ${state.labelVisibility ? "checked" : ""} onchange="toggleLabels(this.checked)"> <span>${esc(t("point_labels"))}</span></label>
      <button onclick="loadLayers()">${esc(t("load_layers"))}</button>
    </div>
    ${hasLayers ? Object.keys(groups).sort().map(g => `
      <div class="section">
        <div class="section-title">${esc(g === "other" ? t("other") : g.replaceAll("_"," "))}</div>
        ${groups[g].map(l => `
          <label class="layer-row">
            <input type="checkbox" ${l.is_visible ? "checked" : ""} onchange="toggleLayer('${esc(l.layer_key)}', this.checked)">
            <div class="layer-row-main">
              <span class="layer-name">${esc(l.layer_name || l.layer_key)}</span>
              <span class="layer-count">${esc(layerObjectCount(l) ?? 0)}</span>
            </div>
          </label>
        `).join("")}
      </div>
    `).join("") : `<div class="section"><div class="hint">${esc(t("no_layers_loaded"))}</div></div>`}
  `;
}

function basemapBody() {
  return `
    <div class="section">
      <div class="section-title">${esc(t("basemaps"))}</div>
      <div class="hint">${esc(t("basemap_hint"))}</div>
      <div class="basemap-grid">
        ${Object.entries(BASEMAPS).map(([key, entry]) => `
          <button class="basemap-btn ${state.activeBasemap === key ? "primary" : ""}" onclick="setBasemap('${esc(key)}')">
            <span class="basemap-title">${esc(tBasemap(key, "label"))}${state.activeBasemap === key ? " • " + esc(t("active")) : ""}</span>
            <span class="basemap-desc">${esc(tBasemap(key, "description"))}</span>
            <span class="basemap-meta">${esc(tBasemap(key, "sourceNote") || entry.attributions || "")}</span>
          </button>
        `).join("")}
      </div>
      <div class="hint">${esc(t("basemap_footer"))}</div>
    </div>
  `;
}

function detailsBody() {
  if (!state.selection) return `<div class="section"><div class="hint">${esc(t("click_feature"))}</div></div>`;
  const p = state.selection.properties || {};
  return `
    <div class="section">
      <div class="section-title">${esc(state.selection.title)}</div>
      <div class="hint">${esc(t("layer"))}: ${esc(state.selection.layer)}<br>${esc(t("id"))}: ${esc(state.selection.id)}</div>
    </div>
    <div class="props">${Object.keys(p).sort().map(k => `<div class="prop"><div class="prop-k">${esc(k)}</div><div class="prop-v">${esc(p[k])}</div></div>`).join("")}</div>
  `;
}

function regionBody() {
  return `
    <div class="section"><div class="section-title">${esc(t("region"))}</div>
      <div class="row"><span>${esc(t("layers"))}</span><strong>${state.layers.length}</strong></div>
      <div class="row"><span>${esc(t("survey"))}</span><strong>${esc(state.activeSurveyId || "none")}</strong></div>
      <div class="row"><span>${esc(t("selection"))}</span><strong>${state.selection ? esc(t("yes")) : esc(t("no"))}</strong></div>
    </div>
  `;
}

function render() {
  css();
  topbar();
  panel("left-panel", "left", titleFor("left", state.activeLeft), subtitleFor(state.activeLeft), leftBody());
  panel("right-panel", "right", titleFor("right", state.activeRight), subtitleFor(state.activeRight), rightBody());
}

function titleFor(side, id) {
  const tabs = side === "left" ? state.manifest.left : state.manifest.right;
  const tab = tabs.find(t => t.id === id);
  return tTab(id, tab?.title || id);
}

function subtitleFor(id) {
  return {
    survey:t("survey_context"),
    manage:t("workspace_controls"),
    plan:t("planning_context"),
    create:t("survey_hint"),
    edit:t("select_object_hint"),
    export:t("outputs"),
    layers:t("map_layers"),
    basemap:t("base_map"),
    details:t("details"),
    region:t("summary"),
    notes:t("scratch_space")
  }[id] || "";
}


function setLeft(id){ state.activeLeft = id; state.leftOpen = true; render(); }
function setRight(id){ state.activeRight = id; state.rightOpen = true; render(); }
function toggleLeft(){ state.leftOpen = !state.leftOpen; render(); }
function toggleRight(){ state.rightOpen = !state.rightOpen; render(); }

function setActiveSurveyContext(value) {
  state.activeSurveyId = value || null;
  const survey = activeSurveyRecord();
  toast(survey ? `${t("survey_set")}: ${surveyName(survey)}` : t("no_survey_selected"));
  render();
}

function setActiveSurvey() {
  const value = document.getElementById("surveyContextSelect")?.value || document.getElementById("surveySelect")?.value || null;
  setActiveSurveyContext(value);
}


async function loadSelectedSurvey(zoom) {
  if (!state.activeSurveyId) return alert(t("select_survey_first"));
  await loadSurveyFeatures(state.activeSurveyId, zoom);
}

function toggleLayer(key, value) {
  const l = state.layerIndex.get(key);
  if (l) l.is_visible = !!value;
  if (contextTileLayers[key]) contextTileLayers[key].setVisible(!!value);
  toast(value ? t("layer_shown") : t("layer_hidden"));
}

function toggleLabels(value) {
  state.labelVisibility = !!value;
  syncContextLayers();
  toast(value ? t("labels_on") : t("labels_off"));
}

function setBasemap(key) {
  const next = BASEMAPS[key] ? key : "osm";
  state.activeBasemap = next;
  if (baseLayer) baseLayer.setSource(createBasemapSource(next));
  render();
}

function startDraw(type) {
  if (drawInteraction) map.removeInteraction(drawInteraction);
  drawSource.clear();
  const olType = type === "point" ? "Point" : type === "line" ? "LineString" : "Polygon";
  drawInteraction = new ol.interaction.Draw({source:drawSource, type:olType});
  drawInteraction.on("drawend", () => {
    map.removeInteraction(drawInteraction);
    drawInteraction = null;
    toast(t("geometry_captured"));
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
  if (!title) return alert(t("enter_title"));
  if (!f) return alert(t("draw_boundary_first"));
  const result = await fetchJson("/api/surveys", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({expedition_id:null,title,status,geometry:toGeoJSONGeometry(f),metadata:{}})});
  drawSource.clear();
  await loadSurveys();
  if (result?.survey_id) {
    state.activeSurveyId = String(result.survey_id);
    await loadSurveyFeatures(state.activeSurveyId, true);
  }
  render();
  toast(t("survey_created"));
}

async function createObject() {
  if (!state.activeSurveyId) return alert(t("set_active_survey_first"));
  const f = drawnFeature();
  if (!f) return alert(t("draw_boundary_first"));
  const type = document.getElementById("createObjectType")?.value || "note";
  const title = document.getElementById("createObjectTitle")?.value || null;
  const note = document.getElementById("createObjectNote")?.value || "";
  await fetchJson(`/api/surveys/${state.activeSurveyId}/objects`, {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({expedition_id:null,type,geometry:toGeoJSONGeometry(f),properties:{note},title,annotation:note,details:null})});
  drawSource.clear();
  await loadSurveyFeatures(state.activeSurveyId, false);
  toast(t("object_created"));
}

async function saveSelection() {
  if (!state.selection) return alert(t("select_object_first"));
  const id = state.selection.properties.id;
  if (!id) return alert(t("selected_feature_no_id"));

  const title = document.getElementById("editTitle")?.value || null;
  const note = document.getElementById("editNote")?.value || "";
  const props = {...state.selection.properties, title, note, annotation: note};

  try {
    await fetchJson(`/api/survey-objects/${id}`, {
      method:"PATCH",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        geometry:toGeoJSONGeometry(state.selection.feature),
        type:props.type || "note",
        properties:props,
        title,
        annotation:note,
        details:props.details || null,
        is_active:true
      })
    });

    if (state.activeSurveyId) {
      await loadSurveyFeatures(state.activeSurveyId, false);
    }
    toast(t("saved"));
  } catch (error) {
    console.error("saveSelection failed", error);
    alert(t("saved") + " failed: " + (error?.message || error));
  }
}

async function deleteSelection() {
  if (!state.selection) return alert(t("select_object_first"));
  const id = state.selection.properties.id;
  if (!id) return alert(t("selected_feature_no_id"));
  await fetchJson(`/api/survey-objects/${id}`, {method:"DELETE"});
  setSelection(null);
  if (state.activeSurveyId) await loadSurveyFeatures(state.activeSurveyId, false);
  toast(t("deleted"));
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
  if (!state.activeSurveyId) return alert(t("set_active_survey_first"));
  const d = await fetchJson(`/api/surveys/${state.activeSurveyId}/export/layer.geojson`);
  downloadText(`survey_${state.activeSurveyId}_layer.geojson`, JSON.stringify(d,null,2));
}
async function exportData() {
  if (!state.activeSurveyId) return alert(t("set_active_survey_first"));
  const d = await fetchJson(`/api/surveys/${state.activeSurveyId}/export/data.json`);
  downloadText(`survey_${state.activeSurveyId}_data.json`, JSON.stringify(d,null,2));
}
async function exportDocument() {
  if (!state.activeSurveyId) return alert(t("set_active_survey_first"));
  const d = await fetchJson(`/api/surveys/${state.activeSurveyId}/export/document.json`);
  downloadText(`survey_${state.activeSurveyId}_document.json`, JSON.stringify(d,null,2));
}
async function exportPermission() {
  if (!state.selection) return alert(t("select_feature_first"));
  const out = await fetchJson("/api/permissions/export", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({layer:state.selection.layer, source_id:state.selection.id, description:"ui export"})});
  toast(out.ok ? t("permission_exported") : t("export_failed"));
}

async function start() {
  css();
  state.manifest = await loadManifest();
  document.documentElement.lang = state.lang || "en";
  initMap();
  render();
  await refreshSystem();
  await loadSurveys();
  await loadLayers();
  render();
}

Object.assign(window, {
  startGeometryEdit,stopGeometryEdit,saveGeometryEdit,resetSelectedGeometry,
  setLeft,setRight,toggleLeft,toggleRight,refreshSystem,setActiveSurvey,setActiveSurveyContext,loadSelectedSurvey,loadSurveys,loadLayers,loadSurveyFeatures,
  toggleLayer,toggleLabels,startDraw,setBasemap,createSurvey,createObject,saveSelection,deleteSelection,
  exportLayer,exportData,exportDocument,exportPermission
});

start().catch(e => {
  console.error(e);
  alert(e.message || e);
});
