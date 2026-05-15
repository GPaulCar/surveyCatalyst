
const state = {
  manifest: null,
  surveys: [],
  layers: [],
  activeSurveyId: null,
  activeLeft: "survey",
  activeRight: "layers",
  activeDetailsChild: "properties",
  leftOpen: true,
  rightOpen: true,
  selection: {
    type: null,
    surveyId: null,
    objectId: null,
    feature: null,
    properties: null
  },
  layerIndex: new Map(),
  system: { api: false, db: false },
  admin: {
    services: {},
    logs: [],
    selectedLog: "",
    logMode: "tail",
    logQuery: "",
    logLines: 200,
    logOutput: [],
    logStatus: "",
    actionStatus: ""
  },
  labelVisibility: true,
  activeBasemap: "osm",
  activeLayerRegion: "auto",
  autoLayerRegion: "global",
  layerEfficiency: null,
  lookupData: null,
  measure: {
    active: false,
    meters: 0
  },
  grid: {
    enabled: false,
    cellMeters: 100
  },
  focusMode: "viewport",
  activeStatesViewport: ["de_by"],
  activeStatesSurvey: [],
  identifyRequestSeq: 0,
  permissionCandidates: [],
  permissionRequests: [],
  permissionStatus: "",
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
let measureSource, measureLayer, measureInteraction;
let gridSource, gridLayer;
let stateBoundarySource, stateBoundaryLayer;
let measureGeomListener = null;
let contextTileLayers = {};
let baseLayer = null;
let layerEfficiencyTimer = null;
const LAYER_EFFICIENCY_IDLE_MS = 2800;

const I18N = {
  en: {
    app_name: "SurveyCatalyst",
    api: "API",
    db: "DB",
    tab_survey: "Survey",
    tab_create: "Create",
    tab_edit: "Edit",
    tab_export: "Export",
    tab_manage: "Admin",
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
    measure: "Measure",
    clear_measure: "Clear",
    measure_hint: "Click to add points. Double-click to finish.",
    measure_distance: "Distance",
    focus: "Focus",
    focus_viewport: "Viewport",
    focus_survey: "Survey",
    active_states: "Active states",
    grid: "Grid",
    grid_size_m: "m",
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
    service_controls: "Service controls",
    api_service: "API service",
    database_service: "Database service",
    all_services: "All services",
    start: "Start",
    stop: "Stop",
    restart: "Restart",
    logs: "Logs",
    log_file: "Log file",
    tail: "Tail",
    search: "Search",
    search_logs: "Search logs",
    clear_screen: "Clear screen",
    lines: "Lines",
    query: "Search text",
    output: "Output",
    load_logs: "Load logs",
    no_logs_loaded: "No logs loaded.",
    no_log_output: "No log output.",
    action_scheduled: "Action scheduled",
    action_complete: "Action complete",
    log_loaded: "Log loaded",
    legal_restrictions: "Legal restrictions",
    legal_high: "High",
    legal_protected: "Protected",
    legal_verify: "Verify",
    legal_restriction_notice: "Restriction display is a planning aid. Verify current permission and law before fieldwork.",
    legal_restriction_layer: "Legal restriction layer",
    visible: "Visible",
    available_context_layers: "Available context layers",
    active_planning_scope: "Active planning scope",
    records: "Records",
    title: "Title",
    draw_boundary: "Draw boundary",
    create: "Create",
    survey_hint: "Creates a new survey from the drawn boundary, then makes it active.",
    create_workflow_hint: "Workflow: 1) Enter survey name. 2) Draw boundary. 3) Create survey. 4) Add objects inside active survey.",
    create_survey_locked_hint: "Boundary creation is disabled while a survey is active. Clear active survey first in the Survey tab.",
    draw_survey_boundary_blocked: "Clear active survey before drawing a new survey boundary",
    draw_object_requires_active_survey: "Set an active survey before drawing objects",
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
    permission_workflow: "Permission workflow",
    ownership_notice: "Owner details are not sourced from map data. Add the lawful ownership source/contact details before sending requests.",
    load_permission_candidates: "Load parcels",
    load_requests: "Load requests",
    permission_candidates: "Parcel candidates",
    permission_requests: "Permission requests",
    no_permission_candidates: "No parcel candidates loaded.",
    no_permission_requests: "No permission requests recorded.",
    owner_name: "Owner name",
    owner_contact: "Owner contact",
    request_notes: "Request notes",
    create_request: "Create request",
    candidate_overlap: "Overlap",
    request_created: "Permission request created",
    permission_candidates_loaded: "parcel candidate(s) loaded",
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
    details_properties: "Properties",
    details_lookup: "Lookup",
    lookup_request: "Lookup Context",
    lookup_pending: "Looking up context sources...",
    lookup_none: "No lookup data loaded.",
    lookup_open_wikipedia: "Open Wikipedia",
    lookup_open_osm: "Open OSM",
    lookup_sources: "Sources",
    lookup_location: "Location",
    lookup_wikipedia: "Wikipedia",
    lookup_osm: "OSM / Nominatim",
    identify_results: "Identify results",
    no_identify_results: "No identify results.",
    identify_pending: "Identifying visible layers...",
    identify_raw: "Raw response",
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
    archive: "Archive",
    archive_survey: "Archive survey",
    delete_survey: "Delete survey",
    archive_object: "Archive object",
    confirm_archive_survey: "Archive this survey?",
    confirm_delete_survey: "Delete this survey and all of its objects?",
    confirm_archive_object: "Archive this survey object?",
    confirm_delete_object: "Delete this survey object?",
    survey_archived: "Survey archived",
    survey_deleted: "Survey deleted",
    object_archived: "Object archived",
    object_deleted: "Object deleted",
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
    no: "No",
    none: "None",
    on: "ON",
    off: "OFF",
    language: "Language",
    language_english: "English",
    language_german: "German",
    layer_efficiency: "Layer load",
    layer_efficiency_pending: "Layer load: measuring...",
    layer_efficiency_light: "light",
    layer_efficiency_medium: "medium",
    layer_efficiency_heavy: "heavy",
    count_service_backed: "service",
    count_registry_only: "registry",
    count_not_loaded: "not loaded",
    region_state: "Region / state",
    loaded_features: "feature(s) loaded",
    unnamed_survey: "Unnamed survey",
    hit: "Hit",
    feature: "Feature",
    save_failed: "Save failed",
    request_failed: "Request failed",
    basemap_identify_note: "Basemap tiles do not expose feature attributes through a standard identify protocol.",
    selection_type_survey: "Survey",
    selection_type_object: "Object",
    selection_type_feature: "Feature",
    selection_type_identify: "Identify result",
    object_types: {
      note: "Note",
      findspot: "Findspot",
      track: "Track",
      polygon: "Polygon"
    },
    layer_regions: {
      auto: "Auto from map",
      all: "All regions",
      global: "General / Global",
      de_by: "Bavaria",
      de_bw: "Baden-Württemberg",
      de_he: "Hesse",
      de_th: "Thuringia",
      de_sn: "Saxony",
      eu: "Europe",
      international: "International",
      derived: "Analysis / Derived"
    },
    layer_groups: {
      survey: "Survey layers",
      legal_permission: "Legal & permission",
      archaeology: "Archaeology & heritage",
      historical_context: "Historical roads & places",
      hydrology_terrain: "Hydrology & terrain",
      access_infrastructure: "Access & infrastructure",
      remote_sensing: "Remote sensing",
      detection_intelligence: "Detection intelligence",
      base_maps: "Basemaps",
      other: "Other"
    },
    layer_names: {
      osm_standard_tiles: "Standard Map / OSM",
      esri_world_imagery_tiles: "Satellite / Esri World Imagery",
      esri_world_topo_tiles: "Topographic / Esri World Topo Map",
      carto_light_all_tiles: "Carto Light / Positron",
      carto_dark_all_tiles: "Carto Dark / Dark Matter",
      roman_roads_osm: "Roman roads (OSM)",
      roman_roads_curated: "Roman roads (curated)",
      roman_roads_confidence: "Roman roads (confidence)",
      parcel_boundaries: "Parcel boundaries",
      protection_buffers: "Protection buffers",
      field_names: "Field names",
      legal_restricted_areas: "No Metal Detecting / Legal Restrictions",
      rivers_streams: "Rivers and streams",
      waterbodies: "Waterbodies",
      floodplains: "Floodplains",
      old_creeks: "Old creeks",
      old_channels: "Old channels",
      wetland_history: "Wetland history",
      geonames_points: "GeoNames / place points",
      surveys: "Surveys",
      survey_objects: "Survey objects"
    },
    layer_terms: {
      aisber: "AISBer",
      alkis: "ALKIS",
      atkis: "ATKIS",
      bgr: "BGR",
      dai: "DAI",
      dem: "DEM",
      dop: "DOP",
      eea: "EEA",
      esri: "Esri",
      ffh: "FFH",
      gis: "GIS",
      geonames: "GeoNames",
      gibs: "GIBS",
      isric: "ISRIC",
      lidar: "LiDAR",
      modis: "MODIS",
      nasa: "NASA",
      nrw: "NRW",
      osm: "OSM",
      ph: "pH",
      spa: "SPA",
      tk25: "TK25",
      unesco: "UNESCO",
      wdpca: "WDPA",
      wfs: "WFS",
      wms: "WMS",
      wmts: "WMTS",
      wrb: "WRB"
    },
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
    tab_manage: "Admin",
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
    measure: "Messen",
    clear_measure: "Zurücksetzen",
    measure_hint: "Klicken um Punkte zu setzen. Doppelklick zum Beenden.",
    measure_distance: "Distanz",
    focus: "Fokus",
    focus_viewport: "Viewport",
    focus_survey: "Umfrage",
    active_states: "Aktive Regionen",
    grid: "Raster",
    grid_size_m: "m",
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
    service_controls: "Dienststeuerung",
    api_service: "API-Dienst",
    database_service: "Datenbankdienst",
    all_services: "Alle Dienste",
    start: "Starten",
    stop: "Stoppen",
    restart: "Neustart",
    logs: "Protokolle",
    log_file: "Protokolldatei",
    tail: "Tail",
    search: "Suche",
    search_logs: "Protokolle suchen",
    clear_screen: "Ausgabe leeren",
    lines: "Zeilen",
    query: "Suchtext",
    output: "Ausgabe",
    load_logs: "Protokolle laden",
    no_logs_loaded: "Keine Protokolle geladen.",
    no_log_output: "Keine Protokollausgabe.",
    action_scheduled: "Aktion geplant",
    action_complete: "Aktion abgeschlossen",
    log_loaded: "Protokoll geladen",
    legal_restrictions: "Rechtliche Einschränkungen",
    legal_high: "Hoch",
    legal_protected: "Geschützt",
    legal_verify: "Prüfen",
    legal_restriction_notice: "Die Restriktionsanzeige ist eine Planungshilfe. Prüfen Sie aktuelle Genehmigungen und Rechtslage vor der Feldarbeit.",
    legal_restriction_layer: "Ebene rechtlicher Einschränkungen",
    visible: "Sichtbar",
    available_context_layers: "Verfügbare Kontext-Ebenen",
    active_planning_scope: "Aktiver Planungsbereich",
    records: "Datensätze",
    title: "Titel",
    draw_boundary: "Grenze zeichnen",
    create: "Erstellen",
    survey_hint: "Erstellt eine neue Umfrage aus der gezeichneten Grenze und setzt sie danach aktiv.",
    create_workflow_hint: "Ablauf: 1) Umfragename eingeben. 2) Grenze zeichnen. 3) Umfrage erstellen. 4) Objekte innerhalb der aktiven Umfrage hinzufügen.",
    create_survey_locked_hint: "Grenzenerstellung ist deaktiviert, solange eine Umfrage aktiv ist. Aktive Umfrage zuerst im Tab Umfrage aufheben.",
    draw_survey_boundary_blocked: "Aktive Umfrage aufheben, bevor eine neue Umfragegrenze gezeichnet wird",
    draw_object_requires_active_survey: "Aktive Umfrage festlegen, bevor Objekte gezeichnet werden",
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
    permission_workflow: "Berechtigungsablauf",
    ownership_notice: "Eigentümerdaten stammen nicht aus den Kartendaten. Erfassen Sie die rechtmäßige Quelle und Kontaktdaten, bevor Anfragen versendet werden.",
    load_permission_candidates: "Flurstücke laden",
    load_requests: "Anfragen laden",
    permission_candidates: "Flurstück-Kandidaten",
    permission_requests: "Berechtigungsanfragen",
    no_permission_candidates: "Keine Flurstück-Kandidaten geladen.",
    no_permission_requests: "Keine Berechtigungsanfragen erfasst.",
    owner_name: "Eigentümername",
    owner_contact: "Eigentümerkontakt",
    request_notes: "Notizen zur Anfrage",
    create_request: "Anfrage erstellen",
    candidate_overlap: "Überlappung",
    request_created: "Berechtigungsanfrage erstellt",
    permission_candidates_loaded: "Flurstück-Kandidat(en) geladen",
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
    details_properties: "Attribute",
    details_lookup: "Nachschlagen",
    lookup_request: "Kontext nachschlagen",
    lookup_pending: "Kontextquellen werden abgefragt...",
    lookup_none: "Keine Nachschlage-Daten geladen.",
    lookup_open_wikipedia: "Wikipedia öffnen",
    lookup_open_osm: "OSM öffnen",
    lookup_sources: "Quellen",
    lookup_location: "Ort",
    lookup_wikipedia: "Wikipedia",
    lookup_osm: "OSM / Nominatim",
    identify_results: "Identifizierung",
    no_identify_results: "Keine Identifizierungsergebnisse.",
    identify_pending: "Sichtbare Ebenen werden identifiziert...",
    identify_raw: "Rohantwort",
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
    archive: "Archivieren",
    archive_survey: "Umfrage archivieren",
    delete_survey: "Umfrage löschen",
    archive_object: "Objekt archivieren",
    confirm_archive_survey: "Diese Umfrage archivieren?",
    confirm_delete_survey: "Diese Umfrage und alle zugehörigen Objekte löschen?",
    confirm_archive_object: "Dieses Umfrageobjekt archivieren?",
    confirm_delete_object: "Dieses Umfrageobjekt löschen?",
    survey_archived: "Umfrage archiviert",
    survey_deleted: "Umfrage gelöscht",
    object_archived: "Objekt archiviert",
    object_deleted: "Objekt gelöscht",
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
    none: "Keine",
    on: "EIN",
    off: "AUS",
    language: "Sprache",
    language_english: "Englisch",
    language_german: "Deutsch",
    layer_efficiency: "Ebenenlast",
    layer_efficiency_pending: "Ebenenlast: wird gemessen...",
    layer_efficiency_light: "gering",
    layer_efficiency_medium: "mittel",
    layer_efficiency_heavy: "hoch",
    count_service_backed: "Dienst",
    count_registry_only: "Registrierung",
    count_not_loaded: "nicht geladen",
    region_state: "Region / Bundesland",
    loaded_features: "Objekt(e) geladen",
    unnamed_survey: "Unbenannte Umfrage",
    hit: "Treffer",
    feature: "Objekt",
    save_failed: "Speichern fehlgeschlagen",
    request_failed: "Anfrage fehlgeschlagen",
    basemap_identify_note: "Basiskarten-Kacheln stellen keine Objektattribute über ein Standard-Identify-Protokoll bereit.",
    selection_type_survey: "Umfrage",
    selection_type_object: "Objekt",
    selection_type_feature: "Objekt",
    selection_type_identify: "Identifizierung",
    object_types: {
      note: "Notiz",
      findspot: "Fundstelle",
      track: "Track",
      polygon: "Polygon"
    },
    layer_regions: {
      auto: "Automatisch nach Karte",
      all: "Alle Regionen",
      global: "Allgemein / Global",
      de_by: "Bayern",
      de_bw: "Baden-Württemberg",
      de_he: "Hessen",
      de_th: "Thüringen",
      de_sn: "Sachsen",
      eu: "Europa",
      international: "International",
      derived: "Analyse / Abgeleitet"
    },
    layer_groups: {
      survey: "Umfrageebenen",
      legal_permission: "Recht & Genehmigung",
      archaeology: "Archäologie & Denkmalpflege",
      historical_context: "Historische Wege & Orte",
      hydrology_terrain: "Hydrologie & Gelände",
      access_infrastructure: "Zugang & Infrastruktur",
      remote_sensing: "Fernerkundung",
      detection_intelligence: "Erkennungsdaten",
      base_maps: "Basiskarten",
      other: "Sonstige"
    },
    layer_names: {
      "Parcel boundaries": "Flurstücksgrenzen",
      "Protection buffers": "Schutzpuffer",
      "Field names": "Flurnamen",
      "No Metal Detecting / Legal Restrictions": "Metallsuche verboten / rechtliche Einschränkungen",
      "Rivers and streams": "Flüsse und Bäche",
      Waterbodies: "Gewässerflächen",
      Floodplains: "Überschwemmungsflächen",
      "Old creeks": "Historische Bäche",
      "Old channels": "Historische Kanäle",
      "Wetland history": "Historische Feuchtgebiete",
      "GeoNames / place points": "GeoNames / Ortsnamenpunkte",
      Surveys: "Umfragen",
      "Survey Objects": "Umfrageobjekte",
      osm_standard_tiles: "Standardkarte / OSM",
      esri_world_imagery_tiles: "Satellit / Esri World Imagery",
      esri_world_topo_tiles: "Topografisch / Esri World Topo Map",
      carto_light_all_tiles: "Carto Hell / Positron",
      carto_dark_all_tiles: "Carto Dunkel / Dark Matter",
      roman_roads_osm: "Römische Straßen (OSM)",
      roman_roads_curated: "Römische Straßen (kuratiert)",
      roman_roads_confidence: "Römische Straßen (Konfidenz)",
      parcel_boundaries: "Flurstücksgrenzen",
      protection_buffers: "Schutzpuffer",
      field_names: "Flurnamen",
      legal_restricted_areas: "Metallsuche verboten / rechtliche Einschränkungen",
      rivers_streams: "Flüsse und Bäche",
      waterbodies: "Gewässerflächen",
      floodplains: "Überschwemmungsflächen",
      old_creeks: "Historische Bäche",
      old_channels: "Historische Kanäle",
      wetland_history: "Historische Feuchtgebiete",
      geonames_points: "GeoNames / Ortsnamenpunkte",
      surveys: "Umfragen",
      survey_objects: "Umfrageobjekte",
      osm_rivers: "Flüsse (OSM)",
      osm_streams: "Bäche und Gräben (OSM)",
      osm_wetlands: "Feuchtgebiete (OSM)",
      osm_roads: "Straßennetz (OSM)",
      osm_tracks_paths: "Wege, Pfade und Zufahrten (OSM)",
      osm_railways: "Eisenbahnen (OSM)",
      osm_archaeological_sites: "Archäologische Fundstellen (OSM)",
      osm_roman_roads: "Römische Straßen (OSM)",
      osm_burial_tumulus_sites: "Grabhügel und Tumuli (OSM)",
      osm_historic_cemeteries: "Historische Friedhöfe (OSM)",
      hessen_denkx_ground_monuments: "Hessen DenkX Bodendenkmale",
      hessen_area_monuments: "Hessen Flächendenkmale",
      hessen_limes_core_zone: "Hessen Limes Kernzone",
      hessen_limes_buffer_zone: "Hessen Limes Pufferzone",
      eea_european_main_rivers: "Europäische Hauptflüsse (EUA)",
      eea_potential_flood_prone_area: "Potenziell hochwassergefährdete Flächen (EUA)",
      eea_natura2000_habitats_directive: "Natura 2000 FFH-Gebiete (EUA)",
      eea_natura2000_birds_directive: "Natura 2000 Vogelschutzgebiete (EUA)",
      dai_barrington_atlas_roman_roads: "DAI Barrington-Atlas römische Straßen",
      dai_aurelian_wall_rome: "DAI Aurelianische Mauer Rom",
      dai_jazira_archaeological_sites: "DAI Jazira archäologische Fundstellen",
      dai_gadara_archaeological_sites: "DAI Gadara archäologische Fundstellen",
      dai_gadara_tombs: "DAI Gadara Gräber",
      derived_distance_to_osm_roads: "Abstand zu OSM-Straßen",
      derived_distance_to_roman_roads: "Abstand zu römischen Straßen",
      derived_distance_to_waterways: "Abstand zu Gewässern",
      derived_floodplain_edge_distance: "Abstand zu Überschwemmungsflächenrändern",
      derived_slope_accessibility_index: "Hangneigungs- und Zugänglichkeitsindex",
      derived_lidar_microrelief_anomaly: "LiDAR-Mikrorelief-Anomalien",
      derived_agricultural_candidate_zones: "Landwirtschaftliche Suchflächen"
    },
    layer_terms: {
      access: "Zugang",
      accessibility: "Zugänglichkeit",
      agricultural: "landwirtschaftliche",
      aisber: "AISBer",
      alkis: "ALKIS",
      ancient: "antike",
      anomaly: "Anomalien",
      archaeological: "archäologische",
      archaeology: "Archäologie",
      area: "Fläche",
      areas: "Flächen",
      atkis: "ATKIS",
      atlas: "Atlas",
      aurelian: "Aurelianische",
      axis: "Achsen",
      barrington: "Barrington",
      bgr: "BGR",
      birds: "Vogelschutz",
      buffer: "Puffer",
      burial: "Gräber",
      cadastre: "Kataster",
      cadastral: "Kataster",
      candidate: "Such",
      cemeteries: "Friedhöfe",
      channels: "Kanäle",
      clay: "Ton",
      cloudless: "wolkenfrei",
      copernicus: "Copernicus",
      core: "Kern",
      corine: "CORINE",
      creeks: "Bäche",
      dai: "DAI",
      damage: "Schäden",
      dark: "Dunkel",
      dem: "DGM",
      derived: "abgeleitete",
      directive: "Richtlinie",
      distance: "Abstand",
      dop: "DOP",
      earth: "Earth",
      edge: "Rand",
      eea: "EUA",
      elevation: "Höhenmodell",
      esri: "Esri",
      european: "europäische",
      ffh: "FFH",
      field: "Flur",
      flood: "Hochwasser",
      floodplain: "Überschwemmungsfläche",
      floodplains: "Überschwemmungsflächen",
      flowing: "Fließ",
      geonames: "GeoNames",
      geoscientific: "geowissenschaftliche",
      geology: "Geologie",
      gibs: "GIBS",
      global: "globale",
      ground: "Boden",
      habitats: "Habitate",
      hessen: "Hessen",
      hillshade: "Schummerung",
      historic: "historische",
      historical: "historische",
      imagery: "Bilddaten",
      index: "Index",
      infrastructure: "Infrastruktur",
      isric: "ISRIC",
      land: "Land",
      landscape: "Landschaftsschutz",
      lidar: "LiDAR",
      limes: "Limes",
      line: "Linie",
      list: "Liste",
      map: "Karte",
      maps: "Karten",
      microrelief: "Mikrorelief",
      mineral: "Mineral",
      modern: "moderne",
      monuments: "Denkmale",
      moor: "Moor",
      nasa: "NASA",
      natural: "Natur",
      nature: "Natur",
      nrw: "NRW",
      old: "historische",
      osm: "OSM",
      park: "Park",
      paths: "Pfade",
      ph: "pH",
      places: "Orte",
      polygons: "Polygone",
      populated: "Siedlungs",
      potential: "potenziell",
      probability: "Wahrscheinlichkeit",
      prone: "gefährdet",
      protection: "Schutz",
      reserves: "Reservate",
      resources: "Rohstoffe",
      rivers: "Flüsse",
      roads: "Straßen",
      roman: "römische",
      sensing: "Fernerkundung",
      sentinel2: "Sentinel-2",
      settlements: "Siedlungen",
      sites: "Fundstellen",
      slope: "Hangneigung",
      soil: "Boden",
      soilgrids: "SoilGrids",
      spa: "Vogelschutz",
      streams: "Bäche",
      surface: "Oberfläche",
      swamp: "Sumpf",
      tiles: "Kacheln",
      tk25: "TK25",
      topographic: "topografische",
      topsoil: "Oberboden",
      trace: "Spuren",
      tracks: "Wege",
      truedop: "TrueDOP",
      types: "Typen",
      unesco: "UNESCO",
      urban: "Stadt",
      use: "Nutzung",
      water: "Gewässer",
      waterbodies: "Gewässerflächen",
      waterways: "Gewässer",
      wdpca: "WDPA",
      wetland: "Feuchtgebiet",
      wetlands: "Feuchtgebiete",
      wfs: "WFS",
      wms: "WMS",
      wmts: "WMTS",
      world: "Welt",
      wrb: "WRB",
      zone: "Zone",
      zones: "Zonen"
    },
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

function tMap(group, key, fallback = "") {
  const pack = I18N[state.lang]?.[group] || {};
  const english = I18N.en[group] || {};
  return pack[key] ?? english[key] ?? fallback ?? key;
}

function tLayerRegion(id) {
  const region = LAYER_REGIONS.find(item => item.id === id);
  return tMap("layer_regions", id, region?.label || id);
}

function tLayerGroup(id) {
  return tMap("layer_groups", id, LAYER_GROUP_TITLES[id] || id.replaceAll("_", " "));
}

function layerNameLookup(key) {
  if (!key) return "";
  return tMap("layer_names", String(key), "");
}

function titleCaseToken(token) {
  const raw = String(token || "");
  if (!raw) return "";
  if (/^[A-Z0-9]{2,}$/.test(raw)) return raw;
  return raw.slice(0, 1).toUpperCase() + raw.slice(1).toLowerCase();
}

function humanLayerName(value) {
  return String(value || "")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .split(" ")
    .filter(Boolean)
    .map(titleCaseToken)
    .join(" ");
}

function derivedLayerName(value) {
  const tokens = String(value || "")
    .replace(/[()/]+/g, " ")
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .split(" ")
    .filter(Boolean);
  if (!tokens.length) return "";
  return tokens.map(token => tMap("layer_terms", token.toLowerCase(), titleCaseToken(token))).join(" ");
}

function tLayerName(layerOrKey, fallback = "") {
  const layer = typeof layerOrKey === "object" && layerOrKey !== null ? layerOrKey : null;
  const key = String(layer?.layer_key || layer?.layer || layer?.registry_layer || layer?.service_layer || layerOrKey || "");
  const raw = String(fallback || layer?.layer_name || layer?.title || key || "");
  const basemapKey = key.startsWith("basemap:") ? key.split(":")[1] : "";
  if (basemapKey && BASEMAPS[basemapKey]) return tBasemap(basemapKey, "label");
  return layerNameLookup(key)
    || layerNameLookup(raw)
    || (state.lang === "de" ? derivedLayerName(raw || key) : humanLayerName(raw || key));
}

function selectionLayerLabel(selection = state.selection) {
  const p = selection?.properties || {};
  return tLayerName({
    layer_key: p.layer_key || p.layer || p.registry_layer || p.service_layer || selectionLayerKey(selection),
    layer_name: p.layer_name || p.layer || selectionLayerKey(selection),
    service_layer: p.service_layer
  });
}

function tObjectType(type) {
  return tMap("object_types", type, type);
}

function selectionTypeLabel(type) {
  return type ? t(`selection_type_${type}`, type) : t("none");
}

function serviceTargetLabel(target) {
  return {
    all: t("all_services"),
    api: t("api_service"),
    database: t("database_service")
  }[target] || target;
}

function messageText(message) {
  if (!message) return "";
  if (typeof message === "string") return message;
  if (message.key === "admin_action_pending") {
    return `${serviceTargetLabel(message.target)}: ${t(message.action, message.action)}...`;
  }
  if (message.key === "logs_loaded_count") {
    return `${message.count} ${t("logs")}`;
  }
  if (message.key === "log_loaded_count") {
    return `${t("log_loaded")}: ${message.returned}/${message.total}`;
  }
  if (message.key === "permission_candidates_loaded_count") {
    return `${message.count} ${t("permission_candidates_loaded")}`;
  }
  return t(message.key, message.key || "");
}

function tTab(id, fallback) {
  return t(`tab_${id}`, fallback || fallbackTabTitle(id));
}

function fallbackTabTitle(id) {
  return ({survey:"Survey", create:"Create", edit:"Edit", export:"Export", manage:"Admin", plan:"Plan", layers:"Layers", basemap:"Basemap", details:"Details", region:"Region", notes:"Notes"})[id] || id;
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

const LAYER_REGIONS = [
  {id:"auto", label:"Auto from map"},
  {id:"all", label:"All regions"},
  {id:"global", label:"General / Global"},
  {id:"de_by", label:"Bavaria"},
  {id:"de_bw", label:"Baden-Württemberg"},
  {id:"de_he", label:"Hesse"},
  {id:"de_th", label:"Thuringia"},
  {id:"de_sn", label:"Saxony"},
  {id:"eu", label:"Europe"},
  {id:"international", label:"International"},
  {id:"derived", label:"Analysis / Derived"}
];

const STATE_VIEW_EXTENTS = [
  {id:"de_bw", minLon:7.45, minLat:47.50, maxLon:10.55, maxLat:49.80},
  {id:"de_he", minLon:7.75, minLat:49.35, maxLon:10.30, maxLat:51.70},
  {id:"de_th", minLon:9.85, minLat:50.20, maxLon:12.70, maxLat:51.65},
  {id:"de_sn", minLon:11.85, minLat:50.10, maxLon:15.10, maxLat:51.70},
  {id:"de_by", minLon:8.85, minLat:47.20, maxLon:13.90, maxLat:50.65}
];
const STATE_BOUNDARY_LAYER_KEY = "state_boundaries_de";

const LAYER_GROUP_ORDER = [
  "survey",
  "legal_permission",
  "archaeology",
  "historical_context",
  "hydrology_terrain",
  "access_infrastructure",
  "remote_sensing",
  "detection_intelligence",
  "base_maps",
  "other"
];

const LAYER_GROUP_TITLES = {
  survey: "Survey layers",
  legal_permission: "Legal & permission",
  archaeology: "Archaeology & heritage",
  historical_context: "Historical roads & places",
  hydrology_terrain: "Hydrology & terrain",
  access_infrastructure: "Access & infrastructure",
  remote_sensing: "Remote sensing",
  detection_intelligence: "Detection intelligence",
  base_maps: "Basemaps",
  other: "Other"
};

function layerRegionLabel(id) {
  return tLayerRegion(id);
}

function intersectsExtent(a, b) {
  return a.minLon <= b.maxLon && a.maxLon >= b.minLon && a.minLat <= b.maxLat && a.maxLat >= b.minLat;
}

function stateIdsFromExtent4326(extent4326) {
  if (!extent4326) return ["de_by"];
  if (stateBoundarySource && map) {
    const projection = map.getView().getProjection();
    const extentProj = ol.proj.transformExtent(extent4326, "EPSG:4326", projection);
    const states = new Set();
    stateBoundarySource.forEachFeatureIntersectingExtent(extentProj, feature => {
      const id = normalizeStateId(feature.get("state_id"));
      if (id) states.add(id);
    });
    if (states.size) return Array.from(states);
  }
  const box = {minLon: extent4326[0], minLat: extent4326[1], maxLon: extent4326[2], maxLat: extent4326[3]};
  const ids = STATE_VIEW_EXTENTS.filter(ext => intersectsExtent(ext, box)).map(ext => ext.id);
  return ids.length ? ids : ["de_by"];
}

function normalizeStateId(value) {
  const text = String(value || "").toLowerCase().trim();
  if (!text) return "";
  if (text === "de-by" || text === "by" || text.includes("bayern") || text.includes("bavaria")) return "de_by";
  if (text === "de-bw" || text === "bw" || text.includes("baden")) return "de_bw";
  if (text === "de-he" || text === "he" || text.includes("hessen") || text.includes("hesse")) return "de_he";
  if (text === "de-th" || text === "th" || text.includes("thüringen") || text.includes("thuringia")) return "de_th";
  if (text === "de-sn" || text === "sn" || text.includes("sachsen") || text.includes("saxony")) return "de_sn";
  return text;
}

async function loadStateBoundaryLayer() {
  if (!map || !stateBoundarySource) return;
  try {
    const payload = await fetchJson(`/api/layers/${STATE_BOUNDARY_LAYER_KEY}/geojson?limit=500`);
    const fmt = new ol.format.GeoJSON();
    const features = fmt.readFeatures(payload, {featureProjection: map.getView().getProjection()});
    stateBoundarySource.clear();
    features.forEach(feature => {
      const p = feature.getProperties() || {};
      const mapped = normalizeStateId(
        p.state_id || p.state || p.state_code || p.iso || p.iso_code || p.name || p.NAME_1 || p.admin
      );
      if (mapped) feature.set("state_id", mapped);
    });
    stateBoundarySource.addFeatures(features);
  } catch (error) {
    console.warn("state boundary layer unavailable", error);
    stateBoundarySource.clear();
  }
}

function currentMapStates() {
  if (!map) return ["de_by"];
  const view = map.getView();
  const size = map.getSize();
  if (!view || !size) return ["de_by"];
  const extent = view.calculateExtent(size);
  const extent4326 = ol.proj.transformExtent(extent, view.getProjection(), "EPSG:4326");
  return stateIdsFromExtent4326(extent4326);
}

function effectiveLayerRegion() {
  const ids = activeFocusStateIds();
  return ids[0] || "de_by";
}

function activeFocusStateIds() {
  if (state.focusMode === "survey" && state.activeStatesSurvey.length) return state.activeStatesSurvey;
  if (state.activeLayerRegion === "all") return ["all"];
  if (state.activeLayerRegion === "auto") return state.activeStatesViewport.length ? state.activeStatesViewport : ["de_by"];
  return [state.activeLayerRegion];
}

function activeFocusStateLabel() {
  const ids = activeFocusStateIds();
  if (ids.includes("all")) return tLayerRegion("all");
  return ids.map(layerRegionLabel).join(", ");
}

function syncAutoLayerRegion() {
  const nextStates = currentMapStates();
  const nextPrimary = nextStates[0] || "de_by";
  const changed = JSON.stringify(nextStates) !== JSON.stringify(state.activeStatesViewport);
  state.activeStatesViewport = nextStates;
  if (state.autoLayerRegion === nextPrimary && !changed) return;
  state.autoLayerRegion = nextPrimary;
  if (state.activeLayerRegion === "auto" && state.activeRight === "layers") render();
}

function surveyBoundaryFeatureForActiveSurvey() {
  if (!surveySource || !state.activeSurveyId) return null;
  const features = surveySource.getFeatures();
  return features.find(feature => {
    const props = plainFeatureProperties(feature);
    return props.feature_role === "survey_boundary" && String(props.survey_id ?? props.id ?? "") === String(state.activeSurveyId);
  }) || null;
}

function syncSurveyFocusStates() {
  if (!state.activeSurveyId) {
    state.activeStatesSurvey = [];
    if (state.focusMode === "survey") state.focusMode = "viewport";
    return;
  }
  const feature = surveyBoundaryFeatureForActiveSurvey();
  if (!feature) return;
  const geometry = feature.getGeometry?.();
  if (!geometry) return;
  const extent4326 = ol.proj.transformExtent(
    geometry.getExtent(),
    map.getView().getProjection(),
    "EPSG:4326"
  );
  state.activeStatesSurvey = stateIdsFromExtent4326(extent4326);
  state.focusMode = "survey";
}

function layerText(layer) {
  const md = layer?.metadata || {};
  return [
    layer?.layer_key,
    layer?.layer_name,
    layer?.source_table,
    md.coverage,
    md.description,
    md.notes,
    md.source_provider,
    md.service_url,
    md.endpoint_url,
    md.region_scope
  ].filter(Boolean).join(" ").toLowerCase();
}

function layerRegion(layer) {
  if (layer?.layer_group === "survey") return "survey";
  const md = layer?.metadata || {};
  const text = layerText(layer);

  if (text.includes("bavaria") || text.includes("bayern") || text.includes("de_by") || text.includes("gdiserv.bayern")) return "de_by";
  if (text.includes("baden") || text.includes("wuerttemberg") || text.includes("württemberg") || text.includes("de_bw")) return "de_bw";
  if (text.includes("hessen") || text.includes("geoportal.hessen")) return "de_he";
  if (text.includes("thuringia") || text.includes("thüringen") || text.includes("thueringen") || text.includes("de_th")) return "de_th";
  if (text.includes("saxony") || text.includes("sachsen") || text.includes("de_sn")) return "de_sn";
  if (String(md.region_scope || "").toLowerCase() === "eu" || text.includes("european") || text.includes("copernicus")) return "eu";
  if (text.includes("derived") || String(md.region_scope || "").toLowerCase() === "local") return "derived";
  if (text.includes("dainst") || text.includes("jazira") || text.includes("gadara") || text.includes("yemen") || text.includes("rome")) return "international";
  return "global";
}

function layerVisibleForRegion(layer, region) {
  if (region === "all") return true;
  const ownRegion = layerRegion(layer);
  if (ownRegion === "survey") return true;
  if (region === "global") return ownRegion === "global" || ownRegion === "eu" || ownRegion === "derived";
  return ownRegion === region || ownRegion === "global" || ownRegion === "eu" || ownRegion === "derived";
}

function layerVisibleForFocus(layer, regions) {
  const regionIds = Array.isArray(regions) ? regions : [regions];
  if (regionIds.includes("all")) return true;
  return regionIds.some(region => layerVisibleForRegion(layer, region));
}

function visibleContextLayers() {
  return (state.layers || []).filter(layer => !!layer.is_visible);
}

function layerComplexityWeight(layer) {
  const text = `${layer?.layer_key || ""} ${layer?.layer_name || ""}`.toLowerCase();
  if (text.includes("parcel") || text.includes("protection") || text.includes("restricted") || text.includes("flood")) return 1.5;
  if (text.includes("river") || text.includes("water") || text.includes("stream") || text.includes("road") || text.includes("track")) return 1.2;
  if (text.includes("survey")) return 1.0;
  return 1.1;
}

function efficiencyBucket(score) {
  if (score >= 22) return "heavy";
  if (score >= 12) return "medium";
  return "light";
}

function computeLayerEfficiency() {
  if (!map) return null;
  const zoom = Number(map.getView()?.getZoom?.() ?? 0);
  const visibleLayers = visibleContextLayers();
  const complexity = visibleLayers.reduce((sum, layer) => sum + layerComplexityWeight(layer), 0);
  const zoomFactor = 0.7 + Math.max(0, Math.min(zoom, 22)) / 10;
  const score = Math.round((complexity * zoomFactor + 1) * 10) / 10;
  const bucket = efficiencyBucket(score);
  return {
    zoom: Math.round(zoom * 10) / 10,
    visible: visibleLayers.length,
    total: (state.layers || []).length,
    score,
    bucket,
    pending: false
  };
}

function layerEfficiencyText() {
  const info = state.layerEfficiency;
  if (!info || info.pending) return t("layer_efficiency_pending");
  return `${t("layer_efficiency")}: ${t(`layer_efficiency_${info.bucket}`)} z${info.zoom} (${info.visible}/${info.total})`;
}

function formatMeasureDistance(meters) {
  const value = Number(meters) || 0;
  return value >= 1000 ? `${(value / 1000).toFixed(2)} km` : `${Math.round(value)} m`;
}

function measureText() {
  if (!state.measure?.meters) return t("measure");
  return `${t("measure_distance")}: ${formatMeasureDistance(state.measure.meters)}`;
}

function scheduleLayerEfficiencyUpdate() {
  if (layerEfficiencyTimer) clearTimeout(layerEfficiencyTimer);
  state.layerEfficiency = {...(state.layerEfficiency || {}), pending: true};
  render();
  layerEfficiencyTimer = setTimeout(() => {
    state.layerEfficiency = computeLayerEfficiency();
    render();
  }, LAYER_EFFICIENCY_IDLE_MS);
}

function layerWorkflowGroup(layer) {
  if (layer?.layer_group === "survey") return "survey";
  if (layer?.layer_group === "base") return "base_maps";

  const text = layerText(layer);
  const category = String(layer?.metadata?.category || "").toLowerCase();
  const subgroup = String(layer?.metadata?.subgroup || "").toLowerCase();

  if (category.includes("legal") || subgroup.includes("legal") || subgroup.includes("permission") || text.includes("parcel") || text.includes("protection")) return "legal_permission";
  if (category.includes("archaeology") || subgroup.includes("archaeological") || text.includes("monument") || text.includes("unesco") || text.includes("burial") || text.includes("tomb")) return "archaeology";
  if (subgroup.includes("roman") || subgroup.includes("historical") || subgroup.includes("place_names") || text.includes("field names") || text.includes("geonames")) return "historical_context";
  if (subgroup.includes("hydrology") || subgroup.includes("water") || category.includes("terrain") || text.includes("soil") || text.includes("geology") || text.includes("elevation") || text.includes("hillshade") || text.includes("slope")) return "hydrology_terrain";
  if (category.includes("infrastructure") || subgroup.includes("roads") || subgroup.includes("railways") || subgroup.includes("settlements") || text.includes("access")) return "access_infrastructure";
  if (category.includes("remote_sensing") || subgroup.includes("imagery") || subgroup.includes("photography") || text.includes("orthophoto") || text.includes("sentinel") || text.includes("modis")) return "remote_sensing";
  if (category.includes("detection_intelligence") || text.includes("derived")) return "detection_intelligence";
  return "other";
}

function sortedLayerGroups(groups) {
  return Object.keys(groups).sort((a, b) => {
    const ai = LAYER_GROUP_ORDER.indexOf(a);
    const bi = LAYER_GROUP_ORDER.indexOf(b);
    const ar = ai === -1 ? 999 : ai;
    const br = bi === -1 ? 999 : bi;
    return ar === br ? a.localeCompare(b) : ar - br;
  });
}

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

function emptySelection() {
  return {
    type: null,
    surveyId: null,
    objectId: null,
    feature: null,
    properties: null
  };
}

function hasSelection() {
  return Boolean(
    state.selection?.feature ||
    state.selection?.type === "survey" ||
    state.selection?.type === "object" ||
    state.selection?.type === "identify"
  );
}

function hasEditableSelection() {
  return state.selection?.type === "survey" || state.selection?.type === "object";
}

function selectionTitle(selection = state.selection) {
  const p = selection?.properties || {};
  if (selection?.type === "survey") {
    return String(p.title || (selection.surveyId ? `${t("survey")} ${selection.surveyId}` : t("survey")));
  }
  if (selection?.type === "object") {
    return String(p.title || p.name || p.type || (selection.objectId ? `${t("object")} ${selection.objectId}` : t("object")));
  }
  if (selection?.type === "identify") {
    const primary = identifyPrimaryResult(selection);
    const props = primary?.properties || {};
    return String(props.title || props.name || props.label || primary?.title || tLayerName(primary, selectionLayerKey(selection)) || t("feature"));
  }
  return String(
    p.title ||
    p.name ||
    p.label ||
    p.type ||
    p.layer_name ||
    p.layer ||
    p.layer_key ||
    p.source_id ||
    p.id ||
    t("feature")
  );
}

function compactReadableValue(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  if (/^https?:\/\//i.test(text)) return "";
  return text.length > 56 ? `${text.slice(0, 53)}...` : text;
}

function topbarSelectionSummary(selection = state.selection) {
  if (!hasSelection()) return t("none");
  const id = compactReadableValue(selectionRecordId(selection));
  if (id) return id;
  return t("none");
}

function selectionLayerKey(selection = state.selection) {
  const p = selection?.properties || {};
  if (selection?.type === "identify") {
    return String(p.layer || p.layer_key || p.source_table || p.registry_layer || p.service_layer || "");
  }
  return String(p.layer || p.layer_key || p.source_table || p.registry_layer || p.source || "");
}

function selectionRecordId(selection = state.selection) {
  if (selection?.type === "object") return selection.objectId || "";
  if (selection?.type === "survey") return selection.surveyId || "";
  if (selection?.type === "identify") {
    const p = identifyPrimaryProperties(selection);
    return String(p.source_id || p.id || p.feature_id || p.object_id || "");
  }
  const p = selection?.properties || {};
  return String(p.source_id || p.id || p.object_id || p.feature_id || "");
}

function identifyResults(selection = state.selection) {
  return Array.isArray(selection?.identifyResults) ? selection.identifyResults : [];
}

function identifyPrimaryResult(selection = state.selection) {
  return identifyResults(selection)[0] || null;
}

function identifyPrimaryProperties(selection = state.selection) {
  const primary = identifyPrimaryResult(selection);
  return primary?.properties || {};
}

function plainFeatureProperties(feature) {
  if (!feature) return {};
  const props = {...feature.getProperties()};
  delete props.geometry;
  return props;
}

function formatPropValue(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function selectionFromFeature(feature) {
  if (!feature) return emptySelection();

  const props = plainFeatureProperties(feature);
  const role = String(props.feature_role || "");
  const type = role === "survey_boundary" ? "survey" : role === "survey_object" ? "object" : "feature";

  const surveyId = String(props.survey_id ?? (type === "survey" ? props.id : "") ?? "") || null;
  const objectId = type === "object" ? (String(props.id ?? props.object_id ?? "") || null) : null;

  return {
    type,
    surveyId,
    objectId,
    feature,
    properties: props
  };
}

function identifySelectionFromResults(results, context = {}) {
  const hits = Array.isArray(results) ? results.filter(Boolean) : [];
  if (!hits.length) return emptySelection();

  const primary = hits[0];
  const properties = primary?.properties || {};
  return {
    type: "identify",
    surveyId: null,
    objectId: null,
    feature: null,
    identifyResults: hits,
    identifyContext: context,
    properties: {
      ...properties,
      layer: primary.layer_key || properties.layer || properties.layer_key || "",
      layer_key: primary.layer_key || properties.layer_key || "",
      layer_name: primary.layer_name || properties.layer_name || "",
      service_layer: primary.service_layer || properties.service_layer || "",
      service_url: primary.service_url || properties.service_url || "",
      source_type: primary.source_type || properties.source_type || "WMS",
      info_format: primary.info_format || "",
      content_type: primary.content_type || "",
      identify_count: hits.length
    }
  };
}

function syncTabsForSelection() {
  if (!hasSelection()) return;
  state.activeLeft = "edit";
  state.activeRight = "details";
  state.leftOpen = true;
  state.rightOpen = true;
}

function paintSelectionFeature(feature) {
  if (!selectionSource) return;
  selectionSource.clear();
  if (feature) selectionSource.addFeature(feature.clone());
}

function setSelectionState(selection, options = {}) {
  const next = selection?.feature || selection?.type ? selection : emptySelection();
  state.selection = next;
  state.lookupData = null;
  state.activeDetailsChild = "properties";
  paintSelectionFeature(next.feature);

  if (next.surveyId) {
    state.activeSurveyId = String(next.surveyId);
    state.focusMode = "survey";
    syncSurveyFocusStates();
  }
  if (options.switchTabs !== false) {
    syncTabsForSelection();
  }

  console.log("SELECTION", state.selection);
  if (options.render !== false) render();
}

function setSelection(feature, options = {}) {
  setSelectionState(selectionFromFeature(feature), options);
}

function clearSelection(options = {}) {
  setSelectionState(emptySelection(), options);
}

function editableFeature() {
  if (!selectionSource) return null;
  const fs = selectionSource.getFeatures();
  return fs.length ? fs[0] : null;
}

function startGeometryEdit() {
  if (!hasEditableSelection()) {
    alert(t("select_feature_first"));
    return;
  }
  if (!editableFeature()) {
    alert(t("no_editable_geometry_found"));
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
  if (!hasEditableSelection()) {
    alert(t("select_feature_first"));
    return;
  }

  const edited = editableFeature();
  if (!edited) {
    alert(t("no_editable_geometry_found"));
    return;
  }

  const selection = state.selection;
  const props = {...(selection.properties || {})};

  try {
    if (selection.type === "survey") {
      const values = readSurveyEditValues(props);
      await fetchJson(`/api/surveys/${selection.surveyId}`, {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          geometry: toGeoJSONGeometry(edited),
          title: values.title,
          status: values.status,
          metadata: values.metadata
        })
      });
      await loadSurveys({autoSelect:false});
      await loadSurveyFeatures(selection.surveyId, false);
    } else {
      const id = selectedSurveyObjectId();
      if (!id) {
        alert(t("selected_feature_no_id"));
        return;
      }

      const values = readObjectEditValues(props);
      await fetchJson(`/api/survey-objects/${id}`, {
        method: "PATCH",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          geometry: toGeoJSONGeometry(edited),
          type: values.type,
          properties: values.properties,
          title: values.title,
          annotation: values.annotation,
          details: values.details,
          is_active: props.is_active !== false
        })
      });

      await loadSurveyFeatures(selection.surveyId, false);
    }

    stopGeometryEdit(false);
    render();
    toast(t("geometry_saved"));
  } catch (error) {
    console.error("saveGeometryEdit failed", error);
    alert(t("geometry_save_failed") + ": " + (error?.message || error));
  }
}

function resetSelectedGeometry() {
  if (!hasEditableSelection() || !state.selection.feature) {
    alert(t("select_feature_first"));
    return;
  }
  selectionSource.clear();
  selectionSource.addFeature(state.selection.feature.clone());
  toast(t("geometry_reset"));
}

function zoomToSelection() {
  const feature = state.selection?.feature || findLoadedSelectionFeature();
  const geometry = feature?.getGeometry?.();
  if (!geometry) return alert(t("select_feature_first"));
  map.getView().fit(geometry.getExtent(), {padding:[42,42,42,42], maxZoom:18});
}

function detailsChildTab(id) {
  state.activeDetailsChild = id === "lookup" ? "lookup" : "properties";
  render();
}

function selectionLookupContext(selection = state.selection) {
  const props = selection?.properties || {};
  const primary = identifyPrimaryProperties(selection);
  const title = String(
    props.title || props.name || props.label || props.place || primary.title || primary.name || ""
  ).trim();

  let lon = Number(props.click_lon ?? primary.click_lon ?? props.lon ?? props.lng ?? primary.lon ?? primary.lng);
  let lat = Number(props.click_lat ?? primary.click_lat ?? props.lat ?? primary.lat);

  if ((!Number.isFinite(lon) || !Number.isFinite(lat)) && map) {
    const feature = selection?.feature || findLoadedSelectionFeature(selection);
    const geometry = feature?.getGeometry?.();
    if (geometry) {
      const extent = geometry.getExtent();
      const center = ol.extent.getCenter(extent);
      [lon, lat] = ol.proj.toLonLat(center);
    }
  }

  return {
    title,
    lon: Number.isFinite(lon) ? lon : null,
    lat: Number.isFinite(lat) ? lat : null
  };
}

function tokeniseLookupText(text) {
  return String(text || "")
    .toLowerCase()
    .replace(/[^a-z0-9\u00c0-\u024f]+/g, " ")
    .split(" ")
    .map(s => s.trim())
    .filter(Boolean)
    .filter(s => s.length >= 3)
    .filter(s => !["und", "der", "die", "das", "for", "and", "the", "von", "bei", "mit"].includes(s));
}

function scoreWikiCandidateTitle(title, referenceText) {
  const titleTokens = new Set(tokeniseLookupText(title));
  const refTokens = new Set(tokeniseLookupText(referenceText));
  if (!titleTokens.size || !refTokens.size) return 0;
  let score = 0;
  titleTokens.forEach(tok => {
    if (refTokens.has(tok)) score += 1;
  });
  return score;
}

async function loadLookupData() {
  if (!hasSelection()) return alert(t("select_feature_first"));
  const context = selectionLookupContext();
  if (!context.title && (!Number.isFinite(context.lon) || !Number.isFinite(context.lat))) {
    return alert(t("request_failed"));
  }

  state.lookupData = {pending: true, context};
  render();

  const wikiHost = state.lang === "de" ? "de.wikipedia.org" : "en.wikipedia.org";
  const hasCoords = Number.isFinite(context.lon) && Number.isFinite(context.lat);
  const wikiGeoSearchUrl = hasCoords
    ? `https://${wikiHost}/w/api.php?action=query&list=geosearch&gscoord=${encodeURIComponent(String(context.lat))}%7C${encodeURIComponent(String(context.lon))}&gsradius=2000&gslimit=5&format=json&origin=*`
    : null;
  const wikiTitleSearchUrl = context.title
    ? `https://${wikiHost}/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(context.title)}&srlimit=3&format=json&origin=*`
    : null;
  const osmUrl = (Number.isFinite(context.lon) && Number.isFinite(context.lat))
    ? `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${encodeURIComponent(String(context.lat))}&lon=${encodeURIComponent(String(context.lon))}&zoom=16&addressdetails=1`
    : null;

  try {
    let osm = null;
    if (osmUrl) {
      const reverse = await fetch(osmUrl, {cache: "no-store"}).then(r => r.json());
      osm = {
        displayName: reverse?.display_name || "",
        url: Number.isFinite(context.lon) && Number.isFinite(context.lat)
          ? `https://www.openstreetmap.org/?mlat=${encodeURIComponent(String(context.lat))}&mlon=${encodeURIComponent(String(context.lon))}#map=16/${encodeURIComponent(String(context.lat))}/${encodeURIComponent(String(context.lon))}`
          : ""
      };
    }

    let wiki = null;
    const candidates = [];

    if (wikiGeoSearchUrl) {
      const geoSearch = await fetch(wikiGeoSearchUrl, {cache: "no-store"}).then(r => r.json());
      const nearby = Array.isArray(geoSearch?.query?.geosearch) ? geoSearch.query.geosearch : [];
      nearby.forEach(item => {
        const title = String(item?.title || "").trim();
        if (title) candidates.push(title);
      });
    }

    if (wikiTitleSearchUrl) {
      const titleSearch = await fetch(wikiTitleSearchUrl, {cache: "no-store"}).then(r => r.json());
      const matches = Array.isArray(titleSearch?.query?.search) ? titleSearch.query.search : [];
      matches.forEach(item => {
        const title = String(item?.title || "").trim();
        if (title) candidates.push(title);
      });
    }

    const seen = new Set();
    const uniqueCandidates = candidates.filter(title => {
      const key = title.toLowerCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
    const referenceText = `${context.title || ""} ${osm?.displayName || ""}`;
    let wikiTitle = null;
    let bestScore = 0;
    uniqueCandidates.forEach(title => {
      const score = scoreWikiCandidateTitle(title, referenceText);
      if (score > bestScore) {
        bestScore = score;
        wikiTitle = title;
      }
    });

    if (wikiTitle) {
      const summaryUrl = `https://${wikiHost}/api/rest_v1/page/summary/${encodeURIComponent(wikiTitle)}`;
      const summary = await fetch(summaryUrl, {cache: "no-store"}).then(r => r.json());
      if (bestScore >= 2) {
        wiki = {
          title: summary?.title || wikiTitle,
          extract: summary?.extract || "",
          url: summary?.content_urls?.desktop?.page || `https://${wikiHost}/wiki/${encodeURIComponent(wikiTitle)}`
        };
      }
    }

    state.lookupData = {pending: false, context, wiki, osm};
  } catch (error) {
    state.lookupData = {pending: false, context, error: String(error?.message || error)};
  }
  render();
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
      display:flex;
      align-items:center;
      gap:8px;
      width:100%;
      min-width:0;
      min-height:36px;
      padding:5px 10px;
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
      gap:8px;
      min-width:0;
      flex:1 1 auto;
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
      gap:4px;
      flex-wrap:nowrap;
      margin-left:6px;
      justify-content:flex-start;
      min-width:0;
      overflow-x:auto;
      scrollbar-width:thin;
      color:#475467;
      font-size:10px;
    }
    .top-meta span {
      display:inline-flex;
      align-items:center;
      min-height:19px;
      padding:0 6px;
      border:1px solid #dbe2ea;
      border-radius:4px;
      background:#fff;
      white-space:nowrap;
      flex:0 0 auto;
    }
    .top-meta span.eff {
      border-color:#bfd6ff;
      background:#eef4ff;
      color:#1e3a8a;
      font-weight:600;
    }
    .topbar-actions {
      display:flex;
      align-items:center;
      gap:5px;
      flex-wrap:nowrap;
      flex:0 0 auto;
    }
    .topbar-actions button,
    .topbar-actions select,
    .topbar-actions input {
      height:23px;
      padding:0 8px;
      border-radius:4px;
      border-color:#cbd5e1;
      background:#ffffff;
      color:#1f2937;
      box-shadow:none;
    }
    .topbar-actions select {
      appearance:none;
      min-width:92px;
      width:auto;
      padding-right:8px;
    }
    .topbar-actions input {
      width:76px;
      min-width:76px;
      margin:0;
      font-size:11px;
    }
    .topbar-actions .tab {
      height:23px;
      padding:0 8px;
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
      top:50px;
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
      padding:10px 10px 8px;
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
      margin:8px 2px 2px;
      padding:0 2px;
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
    .detail-child-tabs {
      display:flex;
      gap:4px;
      margin:0 0 8px;
    }
    .detail-child-tabs .tab {
      margin:0;
      height:25px;
      line-height:23px;
      border-color:#cbd5e1;
      background:#fff;
      color:#334155;
    }
    .detail-child-tabs .tab.active {
      color:#172033;
      border-color:#a9c4ee;
      background:#eaf2ff;
    }
    .lookup-links a {
      display:inline-block;
      margin-right:8px;
      color:#1f5fbf;
      text-decoration:none;
      font-weight:600;
    }
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
    button:disabled,
    .tab:disabled,
    select:disabled,
    input:disabled,
    textarea:disabled {
      opacity:.5;
      cursor:not-allowed;
      background:#f1f5f9 !important;
      border-color:#d0d7e2 !important;
      color:#94a3b8 !important;
      box-shadow:none !important;
    }
    button:disabled:hover,
    .tab:disabled:hover {
      background:#f1f5f9 !important;
      border-color:#d0d7e2 !important;
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
    .layer-region-controls {
      display:grid;
      grid-template-columns:minmax(0, 1fr) auto;
      gap:8px;
      align-items:end;
      padding:0 0 8px;
      margin:0 0 8px;
      border-bottom:1px solid #e5e7eb;
    }
    .layer-region-controls select {
      margin-bottom:0;
    }
    .layer-region-meta {
      color:var(--muted);
      font-size:10px;
      line-height:13px;
      white-space:nowrap;
      padding-bottom:7px;
    }
    .admin-service-grid {
      display:grid;
      grid-template-columns:1fr;
      gap:7px;
    }
    .admin-service-card {
      border:1px solid #e2e8f0;
      border-radius:5px;
      padding:8px;
      background:#fbfcfe;
    }
    .admin-service-head {
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:8px;
      margin-bottom:7px;
    }
    .admin-service-title {
      font-size:11px;
      font-weight:750;
      color:#1f2937;
    }
    .admin-actions {
      display:flex;
      flex-wrap:wrap;
      gap:5px;
    }
    .admin-actions button {
      margin:0;
      height:24px;
    }
    .admin-log-controls {
      display:grid;
      grid-template-columns:minmax(0, 1fr) 82px;
      gap:6px;
      align-items:end;
    }
    .admin-log-controls select,
    .admin-log-controls input {
      margin-bottom:0;
    }
    .admin-log-output {
      height:220px;
      overflow:auto;
      white-space:pre-wrap;
      word-break:break-word;
      padding:8px;
      border:1px solid #cbd5e1;
      border-radius:5px;
      background:#0f172a;
      color:#dbeafe;
      font-family:Consolas, "Courier New", monospace;
      font-size:10px;
      line-height:14px;
    }
    .legal-legend {
      display:grid;
      grid-template-columns:repeat(3, minmax(0, 1fr));
      gap:5px;
      margin-top:7px;
    }
    .legal-legend span {
      display:flex;
      align-items:center;
      gap:5px;
      font-size:10px;
      color:#475467;
      min-width:0;
    }
    .legal-swatch {
      width:10px;
      height:10px;
      border-radius:2px;
      flex:0 0 auto;
    }
    .permission-row {
      display:grid;
      grid-template-columns:minmax(0, 1fr) auto;
      gap:8px;
      align-items:center;
      padding:7px 0;
      border-bottom:1px solid #eef2f7;
    }
    .permission-row:last-child { border-bottom:0; }
    .permission-main {
      min-width:0;
      display:flex;
      flex-direction:column;
      gap:2px;
    }
    .permission-main strong {
      font-size:11px;
      line-height:14px;
      color:#1f2937;
      white-space:nowrap;
      overflow:hidden;
      text-overflow:ellipsis;
    }
    .permission-meta {
      font-size:10px;
      color:var(--muted);
      line-height:13px;
      white-space:nowrap;
      overflow:hidden;
      text-overflow:ellipsis;
    }
    .permission-row button {
      margin:0;
      height:24px;
      white-space:nowrap;
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
      white-space:pre-wrap;
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
  if (!res.ok) throw new Error(data?.error?.message || data?.detail || text || `${t("request_failed")} ${res.status}`);
  return data;
}

async function loadManifest() {
  try {
    return await fetchJson("/static/ui_manifest.json?ts=" + Date.now());
  } catch {
    return {
      left: [{id:"survey",title:"Survey"},{id:"create",title:"Create"},{id:"edit",title:"Edit"},{id:"export",title:"Export"},{id:"manage",title:"Admin"},{id:"plan",title:"Plan"}],
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

  measureSource = new ol.source.Vector();
  measureLayer = new ol.layer.Vector({
    source: measureSource,
    style: [
      new ol.style.Style({
        stroke: new ol.style.Stroke({color: "#0ea5e9", width: 3, lineDash: [8, 6]})
      }),
      new ol.style.Style({
        image: new ol.style.Circle({
          radius: 4,
          fill: new ol.style.Fill({color: "#0ea5e9"}),
          stroke: new ol.style.Stroke({color: "#fff", width: 1})
        })
      })
    ]
  });

  gridSource = new ol.source.Vector();
  gridLayer = new ol.layer.Vector({
    source: gridSource,
    style: new ol.style.Style({
      stroke: new ol.style.Stroke({color: "rgba(15,23,42,0.28)", width: 1})
    })
  });
  gridLayer.setZIndex(19);

  stateBoundarySource = new ol.source.Vector();
  stateBoundaryLayer = new ol.layer.Vector({
    source: stateBoundarySource,
    style: new ol.style.Style({
      stroke: new ol.style.Stroke({color: "rgba(100,116,139,0.75)", width: 2}),
      fill: new ol.style.Fill({color: "rgba(100,116,139,0.03)"})
    })
  });
  stateBoundaryLayer.setZIndex(5);

  map.addLayer(surveyLayer);
  map.addLayer(stateBoundaryLayer);
  map.addLayer(drawLayer);
  map.addLayer(measureLayer);
  map.addLayer(gridLayer);
  map.addLayer(selectionLayer);
  setBasemap(state.activeBasemap);
  syncAutoLayerRegion();
  loadStateBoundaryLayer();

  map.on("singleclick", async e => {
    if (state.measure.active) return;
    const seq = ++state.identifyRequestSeq;
    let hit = null;
    map.forEachFeatureAtPixel(e.pixel, f => {
      hit = f;
      return true;
    }, {
      hitTolerance: 6,
      layerFilter: layer => layer !== selectionLayer && layer !== drawLayer && layer !== measureLayer && layer !== gridLayer && layer !== stateBoundaryLayer
    });
    if (hit) {
      setSelection(hit);
      console.log("SELECTION", state.selection);
      return;
    }

    try {
      toast(t("identify_pending"), 800);
      const identify = await identifyVisibleLayers(e);
      if (seq !== state.identifyRequestSeq) return;
      const hits = Array.isArray(identify?.hits) ? identify.hits : [];
      if (hits.length) {
        setSelectionState(identifySelectionFromResults(hits, {
          coordinate: e.coordinate,
          pixel: e.pixel
        }));
      } else {
        clearSelection();
      }
      console.log("SELECTION", state.selection);
    } catch (error) {
      if (seq !== state.identifyRequestSeq) return;
      console.error("identifyVisibleLayers failed", error);
      clearSelection();
    }
  });
  map.on("moveend", () => {
    syncAutoLayerRegion();
    scheduleLayerEfficiencyUpdate();
    updateGridLayer();
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

function legalRestrictionSeverity(feature) {
  const fields = [
    feature.get("legal_severity"),
    feature.get("restriction_level"),
    feature.get("severity"),
    feature.get("restriction_label"),
    feature.get("metal_detecting_status"),
    feature.get("category"),
    feature.get("siteprotectionclassification"),
    feature.get("designationasstring"),
    feature.get("name")
  ].filter(Boolean).join(" ").toLowerCase();

  if (fields.includes("high") || fields.includes("prohibit") || fields.includes("verbot") || fields.includes("bodendenkmal") || fields.includes("archaeolog")) return "high";
  if (fields.includes("medium") || fields.includes("protected") || fields.includes("restricted") || fields.includes("denkmal") || fields.includes("cultural")) return "medium";
  return "verify";
}

function legalRestrictionStyle(feature, gt) {
  const severity = legalRestrictionSeverity(feature);
  const palette = {
    high: {stroke:"#b42318", fill:"rgba(180,35,24,.28)"},
    medium: {stroke:"#ea580c", fill:"rgba(234,88,12,.20)"},
    verify: {stroke:"#d97706", fill:"rgba(217,119,6,.14)"}
  }[severity];

  if (gt.includes("POINT")) {
    return new ol.style.Style({
      image:new ol.style.Circle({
        radius:5,
        fill:new ol.style.Fill({color:palette.stroke}),
        stroke:new ol.style.Stroke({color:"#fff",width:1})
      })
    });
  }
  if (gt.includes("LINE")) {
    return new ol.style.Style({stroke:new ol.style.Stroke({color:palette.stroke,width:2})});
  }
  return new ol.style.Style({
    stroke:new ol.style.Stroke({color:palette.stroke,width:1.4}),
    fill:new ol.style.Fill({color:palette.fill})
  });
}

function makeStyle(layer) {
  return feature => {
    const key = layer.layer_key || "";
    const color = layerColour(key);
    const gt = (feature.getGeometry()?.getType?.() || "").toUpperCase();
    const name = feature.get("name") || feature.get("title") || feature.get("place") || "";
    const styles = [];

    if (key === "legal_restricted_areas" || key.startsWith("legal_")) {
      return legalRestrictionStyle(feature, gt);
    }

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

function findLoadedSelectionFeature(selection = state.selection) {
  if (!selection?.type || !surveySource) return null;
  const features = surveySource.getFeatures();
  return features.find(feature => {
    const props = plainFeatureProperties(feature);
    if (selection.type === "survey") {
      return props.feature_role === "survey_boundary" && String(props.survey_id ?? props.id ?? "") === String(selection.surveyId);
    }
    return props.feature_role === "survey_object"
      && String(props.survey_id ?? "") === String(selection.surveyId)
      && String(props.id ?? props.object_id ?? "") === String(selection.objectId);
  }) || null;
}

function syncSelectionFeatureFromSurveySource(options = {}) {
  if (!hasSelection()) return;
  const feature = findLoadedSelectionFeature();
  if (!feature) {
    if (options.clearMissingForSurveyId && state.selection.type === "object" && String(options.clearMissingForSurveyId) === String(state.selection.surveyId)) {
      clearSelection({switchTabs:false, render:false});
      return;
    }
    paintSelectionFeature(state.selection.feature);
    return;
  }
  setSelection(feature, {...options, switchTabs:false, render:false});
}

function selectSurveyById(idValue, options = {}) {
  const id = String(idValue || "");
  if (!id) {
    clearSelection(options);
    return;
  }

  const feature = findLoadedSelectionFeature({
    type: "survey",
    surveyId: id,
    objectId: null,
    feature: null,
    properties: null
  });
  if (feature) {
    setSelection(feature, options);
    return;
  }

  const survey = surveyRows().find(row => surveyId(row) === id);
  const metadata = survey?.metadata || {};
  setSelectionState({
    type: "survey",
    surveyId: id,
    objectId: null,
    feature: null,
    properties: survey ? {
      id,
      survey_id: id,
      title: surveyName(survey),
      status: surveyStatus(survey),
      layer_key: survey.layer_key || `survey_${id}`,
      expedition_id: survey.expedition_id ?? null,
      object_count: survey.object_count ?? survey.feature_count ?? survey.objects?.length ?? null,
      feature_role: "survey_boundary",
      metadata,
      annotation: metadata.annotation || "",
      details: metadata.details || ""
    } : {
      id,
      survey_id: id,
      title: `Survey ${id}`,
      status: "",
      layer_key: `survey_${id}`,
      feature_role: "survey_boundary",
      metadata: {},
      annotation: "",
      details: ""
    }
  }, options);
}

async function refreshSystem() {
  try {
    const payload = await fetchJson("/api/admin/system/status");
    state.admin.services = payload?.services || {};
    state.system = {
      api:!!state.admin.services.api?.running,
      db:!!state.admin.services.database?.running
    };
  } catch {
    try {
      const r = await fetch("/health", {cache:"no-store"});
      state.system = {api:r.ok, db:false};
    } catch {
      state.system = {api:false, db:false};
    }
  }
  render();
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function serviceInfo(key) {
  return state.admin.services?.[key] || {};
}

async function controlAdminService(target, action) {
  state.admin.actionStatus = {key: "admin_action_pending", target, action};
  render();
  try {
    const payload = await fetchJson(`/api/admin/system/${target}/${action}`, {method:"POST"});
    state.admin.actionStatus = {key: payload?.scheduled ? "action_scheduled" : "action_complete"};
    if (payload?.status) {
      state.admin.services = payload.status;
      state.system = {
        api:!!state.admin.services.api?.running,
        db:!!state.admin.services.database?.running
      };
    }
    render();
    toast(messageText(state.admin.actionStatus));
    await sleep(payload?.scheduled ? 1800 : 300);
    await refreshSystem();
  } catch (error) {
    state.admin.actionStatus = String(error?.message || error);
    render();
    alert(state.admin.actionStatus);
  }
}

async function loadAdminLogs(showToast = false) {
  try {
    const payload = await fetchJson("/api/admin/log-files");
    state.admin.logs = Array.isArray(payload?.logs) ? payload.logs : [];
    if (!state.admin.selectedLog && state.admin.logs.length) {
      const preferred = state.admin.logs.find(l => l.name === "api.err.log")
        || state.admin.logs.find(l => l.name === "admin_control.log")
        || state.admin.logs[0];
      state.admin.selectedLog = preferred.name;
    }
    state.admin.logStatus = {key: "logs_loaded_count", count: state.admin.logs.length};
    render();
    if (showToast) toast(messageText(state.admin.logStatus));
  } catch (error) {
    state.admin.logStatus = String(error?.message || error);
    render();
  }
}

function readAdminLogControls() {
  state.admin.selectedLog = document.getElementById("adminLogSelect")?.value || state.admin.selectedLog || "";
  state.admin.logMode = document.getElementById("adminLogMode")?.value || state.admin.logMode || "tail";
  state.admin.logQuery = document.getElementById("adminLogQuery")?.value || "";
  const lineValue = Number(document.getElementById("adminLogLines")?.value || state.admin.logLines || 200);
  state.admin.logLines = Number.isFinite(lineValue) ? Math.max(1, Math.min(lineValue, 1000)) : 200;
}

async function viewAdminLog(mode) {
  readAdminLogControls();
  if (mode) state.admin.logMode = mode;
  if (!state.admin.selectedLog) {
    state.admin.logStatus = {key: "no_logs_loaded"};
    render();
    return;
  }
  const params = new URLSearchParams({
    name: state.admin.selectedLog,
    mode: state.admin.logMode,
    lines: String(state.admin.logLines),
    q: state.admin.logQuery || ""
  });
  try {
    const payload = await fetchJson(`/api/admin/logs?${params.toString()}`);
    state.admin.logOutput = Array.isArray(payload?.lines) ? payload.lines : [];
    state.admin.logStatus = {
      key: "log_loaded_count",
      returned: payload?.returned ?? state.admin.logOutput.length,
      total: payload?.total_lines ?? "-"
    };
    render();
  } catch (error) {
    state.admin.logStatus = String(error?.message || error);
    render();
    alert(state.admin.logStatus);
  }
}

function clearAdminLogOutput() {
  state.admin.logOutput = [];
  state.admin.logStatus = "";
  render();
}

window.loadSurveys = async function loadSurveys(options = {}) {
  const autoSelect = options?.autoSelect !== false;
  try {
    const payload = await fetchJson("/api/surveys");
    state.surveys = normaliseSurveyPayload(payload);
    state.surveyLoadError = "";

    if (state.activeSurveyId && !state.surveys.some(s => surveyId(s) === String(state.activeSurveyId))) {
      state.activeSurveyId = null;
    }
    if (hasSelection() && state.selection.surveyId && !state.surveys.some(s => surveyId(s) === String(state.selection.surveyId))) {
      clearSelection({switchTabs:false, render:false});
    }

    if (autoSelect && !state.activeSurveyId && state.surveys.length) {
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
  await loadStateBoundaryLayer();
  state.layerEfficiency = computeLayerEfficiency();
  render();
}

function identifyLayerCandidates() {
  return (state.layers || []).filter(layer => {
    const md = layer?.metadata || {};
    const sourceType = String(md.source_type || "").toUpperCase();
    return !!layer.is_visible && ["WMS", "WMTS", "XYZ"].includes(sourceType) && (md.service_url || md.endpoint_url);
  }).map(layer => layer.layer_key);
}

function identifyActiveBasemapContext(event) {
  const basemap = BASEMAPS[state.activeBasemap];
  if (!basemap || !map) return null;
  const basemapLabel = tBasemap(state.activeBasemap, "label") || basemap.label || state.activeBasemap;
  const view = map.getView();
  const zoom = Math.max(0, Math.min(22, Math.round(view?.getZoom?.() ?? 0)));
  const [lon, lat] = ol.proj.toLonLat(event.coordinate);
  const latRad = Math.max(Math.min(lat, 85.05112878), -85.05112878) * Math.PI / 180;
  const tileX = Math.floor((lon + 180) / 360 * Math.pow(2, zoom));
  const tileY = Math.floor((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2 * Math.pow(2, zoom));
  const sampleTileUrl = basemap.url
    .replace("{z}", String(zoom))
    .replace("{x}", String(tileX))
    .replace("{y}", String(tileY))
    .replace("{a-c}", "a");

  return {
    layer_key: `basemap:${state.activeBasemap}`,
    layer_name: basemapLabel,
    source_type: "XYZ",
    service_url: basemap.url,
    service_layer: state.activeBasemap,
    status: "ok",
    content_type: "application/json",
    info_format: "tile-context",
    identify_kind: "basemap_tile_context",
    title: basemapLabel,
    properties: {
      layer_key: `basemap:${state.activeBasemap}`,
      layer_name: basemapLabel,
      source_type: "XYZ",
      service_url: basemap.url,
      service_layer: state.activeBasemap,
      tile_z: zoom,
      tile_x: tileX,
      tile_y: tileY,
      click_lon: lon,
      click_lat: lat,
      sample_tile_url: sampleTileUrl,
      note: t("basemap_identify_note"),
    },
    raw: {
      layer_key: `basemap:${state.activeBasemap}`,
      service_url: basemap.url,
      sample_tile_url: sampleTileUrl,
      tile_z: zoom,
      tile_x: tileX,
      tile_y: tileY,
      click_lon: lon,
      click_lat: lat,
    }
  };
}

async function identifyVisibleLayers(event) {
  const mapSize = map?.getSize?.();
  const extent = map?.getView?.().calculateExtent?.(mapSize);
  const coordinate = event?.coordinate ? ol.proj.toLonLat(event.coordinate) : null;
  if (!mapSize || !extent || !coordinate) return null;
  const layerKeys = identifyLayerCandidates();
  if (!layerKeys.length) return null;

  const payload = {
    layer_keys: layerKeys,
    bbox: ol.proj.transformExtent(extent, map.getView().getProjection(), "EPSG:4326"),
    size: [Math.round(mapSize[0]), Math.round(mapSize[1])],
    pixel: [Math.round(event.pixel[0]), Math.round(event.pixel[1])],
    limit: 5
  };

  const response = await fetchJson("/api/layers/identify", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });

  const hits = Array.isArray(response?.hits) ? response.hits.slice() : [];
  const basemapHit = identifyActiveBasemapContext(event);
  if (basemapHit) hits.push(basemapHit);
  return {...response, hits};
}

async function loadSurveyFeatures(id, zoom=false) {
  const geo = await fetchJson(`/api/surveys/${id}/features?limit=20000`);
  const fmt = new ol.format.GeoJSON();
  const fs = fmt.readFeatures(geo, {featureProjection:map.getView().getProjection()});
  surveySource.clear();
  surveySource.addFeatures(fs);
  syncSelectionFeatureFromSurveySource({clearMissingForSurveyId:id});
  if (state.activeSurveyId && String(state.activeSurveyId) === String(id)) {
    syncSurveyFocusStates();
  }

  if (zoom && fs.length) {
    const ext = ol.extent.createEmpty();
    fs.forEach(f => ol.extent.extend(ext, f.getGeometry().getExtent()));
    map.getView().fit(ext, {padding:[36,36,36,36], maxZoom:18});
  }

  toast(`${fs.length} ${t("loaded_features")}`);
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
          <button class="tab ${state.measure.active ? "active" : ""}" onclick="toggleMeasure()" title="${esc(t("measure_hint"))}">${esc(t("measure"))}</button>
          ${state.measure.meters > 0 ? `<button class="tab" onclick="clearMeasure()">${esc(t("clear_measure"))}</button>` : ""}
          <button class="tab ${state.grid.enabled ? "active" : ""}" onclick="toggleGrid()">${esc(t("grid"))}</button>
          <input type="number" min="10" step="10" value="${esc(state.grid.cellMeters)}" onchange="setGridSizeMeters(this.value)" aria-label="${esc(t("grid"))}" title="${esc(t("grid"))}">
          <select id="languageSelect" onchange="setLanguage(this.value)" aria-label="${esc(t("language"))}" title="${esc(t("language"))}">
            <option value="en" ${state.lang === "en" ? "selected" : ""}>${esc(t("language_english"))}</option>
            <option value="de" ${state.lang === "de" ? "selected" : ""}>${esc(t("language_german"))}</option>
          </select>
        </div>
      </div>
      <div class="top-meta">
        <span><span class="status-dot ${state.system.api ? "on" : ""}"></span>${esc(t("api"))}</span>
        <span>${esc(t("db"))} ${esc(state.system.db ? t("on") : t("off"))}</span>
        <span>${esc(titleFor("left", state.activeLeft))} / ${esc(titleFor("right", state.activeRight))}</span>
        <span>${esc(t("focus"))}: ${esc(state.focusMode === "survey" ? t("focus_survey") : t("focus_viewport"))}</span>
        <span>${esc(t("active_states"))}: ${esc(activeFocusStateLabel())}</span>
        <span>${esc(t("survey"))}: ${esc(survey?.title || state.activeSurveyId || t("none"))}</span>
        <span>${esc(t("selection"))}: ${esc(topbarSelectionSummary())}</span>
        <span>${esc(measureText())}</span>
        <span>${esc(t("grid"))}: ${esc(state.grid.enabled ? `${state.grid.cellMeters}${t("grid_size_m")}` : t("off"))}</span>
        <span class="eff">${esc(layerEfficiencyText())}</span>
      </div>
    </div>
  `;
}

function panel(id, side, title, sub, body) {
  const el = document.getElementById(id);
  el.className = `panel ${side === "left" ? (state.leftOpen ? "" : "closed-left") : (state.rightOpen ? "" : "closed-right")}`;
  const toggle = side === "left"
    ? `<button class="tab toggle" onclick="toggleLeft()">${esc(state.leftOpen ? t("hide") : t("show"))}</button>`
    : `<button class="tab toggle" onclick="toggleRight()">${esc(state.rightOpen ? t("hide") : t("show"))}</button>`;
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
  if (state.activeLeft === "plan") return planBody();
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
  if (state.activeRight === "notes") return `<div class="section"><div class="section-title">${esc(t("scratch_notes"))}</div><textarea placeholder="${esc(t("scratch_space"))}"></textarea><button onclick="toast(t('save'))">${esc(t("save"))}</button></div>`;
  return "";
}

function surveyRows() {
  return Array.isArray(state.surveys) ? state.surveys : [];
}

function surveyId(survey) {
  return String(survey?.id ?? survey?.survey_id ?? survey?.key ?? survey?.name ?? "");
}

function surveyName(survey) {
  return String(survey?.title ?? survey?.name ?? survey?.label ?? survey?.survey_name ?? surveyId(survey) ?? t("unnamed_survey"));
}

function surveyStatus(survey) {
  return String(survey?.status ?? survey?.state ?? "active");
}

function layerObjectCount(layer) {
  const kind = String(layer?.count_kind ?? layer?.metadata?.count_kind ?? "");
  if (kind === "service_backed") return t("count_service_backed");
  if (kind === "registry_only") return t("count_registry_only");
  if (kind === "not_loaded") return t("count_not_loaded");
  const label = layer?.count_label ?? layer?.metadata?.count_label;
  if (label !== undefined && label !== null && label !== "") return label;
  const direct = layer?.object_count ?? layer?.feature_count ?? layer?.metadata?.object_count ?? layer?.metadata?.feature_count;
  if (direct !== undefined && direct !== null && direct !== "") return direct;
  const key = String(layer?.layer_key || "");
  if (key.startsWith("survey_")) {
    const survey = surveyRows().find(s => String(s?.layer_key || "") === key);
    if (survey && survey.object_count !== undefined && survey.object_count !== null) return survey.object_count;
  }
  return null;
}

function permissionCandidateLabel(candidate) {
  const p = candidate?.properties || {};
  return String(
    p.name ||
    p.label ||
    p.parcel_id ||
    p.flurstueck ||
    p.ref ||
    (p.landuse && `${p.landuse} #${candidate?.feature_id || ""}`) ||
    candidate?.source_id ||
    `#${candidate?.feature_id || ""}`
  );
}

function formatArea(value) {
  const n = Number(value || 0);
  if (!Number.isFinite(n) || n <= 0) return "-";
  if (n >= 10000) return `${(n / 10000).toFixed(2)} ha`;
  return `${Math.round(n)} m2`;
}

function activeSurveyRecord() {
  const active = String(state.activeSurveyId || "");
  return surveyRows().find(s => surveyId(s) === active) || null;
}

function selectedSurveyObjectId() {
  return state.selection?.type === "object" ? state.selection.objectId || "" : "";
}

function readSurveyEditValues(props = state.selection?.properties || {}) {
  const metadata = {...(props.metadata || {})};
  const annotation = document.getElementById("editSurveyAnnotation")?.value ?? metadata.annotation ?? props.annotation ?? "";
  const details = document.getElementById("editSurveyDetails")?.value ?? metadata.details ?? props.details ?? "";
  metadata.annotation = annotation;
  metadata.details = details;
  return {
    title: document.getElementById("editSurveyTitle")?.value || props.title || null,
    status: document.getElementById("editSurveyStatus")?.value || props.status || null,
    annotation,
    details,
    metadata
  };
}

function readObjectEditValues(props = state.selection?.properties || {}) {
  const type = document.getElementById("editObjectType")?.value || props.type || "note";
  const title = document.getElementById("editObjectTitle")?.value || null;
  const annotation = document.getElementById("editObjectAnnotation")?.value || "";
  const details = document.getElementById("editObjectDetails")?.value || "";
  return {
    type,
    title,
    annotation,
    details,
    properties: {
      ...props,
      type,
      title,
      note: annotation,
      annotation,
      details
    }
  };
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
      <div class="row"><span>${esc(t("selected"))}</span><strong>${esc(active ? surveyName(active) : t("none"))}</strong></div>
      <div class="row"><span>${esc(t("status"))}</span><strong>${esc(active ? surveyStatus(active) : "-")}</strong></div>
      <div class="row"><span>${esc(t("id"))}</span><strong>${esc(active ? surveyId(active) : "-")}</strong></div>
      <div class="row"><span>${esc(t("objects"))}</span><strong>${esc(active ? (active.object_count ?? active.feature_count ?? active.objects?.length ?? "-") : "-")}</strong></div>
      ${active ? `
        <button onclick="archiveActiveSurvey()">${esc(t("archive_survey"))}</button>
        <button class="danger" onclick="deleteActiveSurvey()">${esc(t("delete_survey"))}</button>
      ` : ""}
      <div class="hint">${esc(t("survey_context_hint"))}</div>
    </div>
  `;
}

function planBody() {
  const active = activeSurveyRecord();
  const contextLayers = (state.layers || []).filter(layer => layer.layer_group === "context");
  const legalLayer = (state.layers || []).find(layer => layer.layer_key === "legal_restricted_areas");
  return `
    <div class="section">
      <div class="section-title">${esc(t("active_planning_scope"))}</div>
      <div class="row"><span>${esc(t("survey"))}</span><strong>${esc(active ? surveyName(active) : t("no_survey_selected"))}</strong></div>
      <div class="row"><span>${esc(t("id"))}</span><strong>${esc(active ? surveyId(active) : "-")}</strong></div>
      <div class="row"><span>${esc(t("selection"))}</span><strong>${esc(selectionTitle())}</strong></div>
    </div>
    <div class="section">
      <div class="section-title">${esc(t("legal_restriction_layer"))}</div>
      <div class="row"><span>${esc(t("visible"))}</span><strong>${esc(legalLayer?.is_visible ? t("yes") : t("no"))}</strong></div>
      <div class="row"><span>${esc(t("records"))}</span><strong>${esc(legalLayer?.object_count ?? legalLayer?.feature_count ?? 0)}</strong></div>
      <div class="hint">${esc(t("legal_restriction_notice"))}</div>
    </div>
    <div class="section">
      <div class="section-title">${esc(t("available_context_layers"))}</div>
      <div class="row"><span>${esc(t("layers"))}</span><strong>${esc(contextLayers.length)}</strong></div>
      <button onclick="setRight('layers')">${esc(t("layers"))}</button>
      <button onclick="setRight('details')">${esc(t("details"))}</button>
    </div>
  `;
}

function manageBody() {
  const api = serviceInfo("api");
  const db = serviceInfo("database");
  const logOptions = (state.admin.logs || []).map(log => {
    const sizeKb = Math.max(1, Math.round((log.size || 0) / 1024));
    return `<option value="${esc(log.name)}" ${log.name === state.admin.selectedLog ? "selected" : ""}>${esc(log.name)} (${sizeKb} KB)</option>`;
  }).join("");
  const output = (state.admin.logOutput || []).length
    ? esc((state.admin.logOutput || []).join("\n"))
    : esc(t("no_log_output"));
  return `
    <div class="section">
      <div class="section-title">${esc(t("service_controls"))}</div>
      <div class="admin-service-grid">
        ${adminServiceCard("all", t("all_services"), state.system.api && state.system.db, null)}
        ${adminServiceCard("api", t("api_service"), !!api.running, api)}
        ${adminServiceCard("database", t("database_service"), !!db.running, db)}
      </div>
      <button onclick="refreshSystem()">${esc(t("refresh"))}</button>
      ${state.admin.actionStatus ? `<div class="hint">${esc(messageText(state.admin.actionStatus))}</div>` : ""}
    </div>
    <div class="section">
      <div class="section-title">${esc(t("logs"))}</div>
      <label>${esc(t("log_file"))}</label>
      <select id="adminLogSelect" onchange="readAdminLogControls()">
        ${logOptions || `<option value="">${esc(t("no_logs_loaded"))}</option>`}
      </select>
      <div class="admin-log-controls">
        <div>
          <label>${esc(t("search"))}</label>
          <input id="adminLogQuery" value="${esc(state.admin.logQuery)}" placeholder="${esc(t("query"))}">
        </div>
        <div>
          <label>${esc(t("lines"))}</label>
          <input id="adminLogLines" type="number" min="1" max="1000" value="${esc(state.admin.logLines)}">
        </div>
      </div>
      <select id="adminLogMode" onchange="readAdminLogControls()">
        <option value="tail" ${state.admin.logMode === "tail" ? "selected" : ""}>${esc(t("tail"))}</option>
        <option value="search" ${state.admin.logMode === "search" ? "selected" : ""}>${esc(t("search_logs"))}</option>
      </select>
      <button class="primary" onclick="viewAdminLog('tail')">${esc(t("tail"))}</button>
      <button onclick="viewAdminLog('search')">${esc(t("search"))}</button>
      <button onclick="loadAdminLogs(true)">${esc(t("load_logs"))}</button>
      <button onclick="clearAdminLogOutput()">${esc(t("clear_screen"))}</button>
      ${state.admin.logStatus ? `<div class="hint">${esc(messageText(state.admin.logStatus))}</div>` : ""}
    </div>
    <div class="section">
      <div class="section-title">${esc(t("output"))}</div>
      <pre class="admin-log-output">${output}</pre>
    </div>
    <div class="section">
      <div class="section-title">${esc(t("legal_restrictions"))}</div>
      <div class="hint">${esc(t("legal_restriction_notice"))}</div>
      <div class="legal-legend">
        <span><i class="legal-swatch" style="background:#b42318"></i>${esc(t("legal_high"))}</span>
        <span><i class="legal-swatch" style="background:#ea580c"></i>${esc(t("legal_protected"))}</span>
        <span><i class="legal-swatch" style="background:#d97706"></i>${esc(t("legal_verify"))}</span>
      </div>
    </div>
  `;
}

function adminServiceCard(target, title, running, detail) {
  const stateText = running ? t("on") : t("off");
  const port = detail?.port ? `:${detail.port}` : "";
  const pid = detail?.pid ? ` pid ${detail.pid}` : "";
  return `
    <div class="admin-service-card">
      <div class="admin-service-head">
        <div class="admin-service-title">${esc(title)}${esc(port)}${esc(pid)}</div>
        <span class="badge ${running ? "on" : ""}">${esc(stateText)}</span>
      </div>
      <div class="admin-actions">
        <button class="primary" onclick="controlAdminService('${esc(target)}','start')">${esc(t("start"))}</button>
        <button onclick="controlAdminService('${esc(target)}','restart')">${esc(t("restart"))}</button>
        <button class="danger" onclick="controlAdminService('${esc(target)}','stop')">${esc(t("stop"))}</button>
      </div>
    </div>
  `;
}

function createBody() {
  const active = activeSurveyRecord();
  const hasActiveSurvey = !!state.activeSurveyId;
  const surveyBoundaryDisabled = hasActiveSurvey ? "disabled" : "";
  return `
    <div class="section">
      <div class="section-title">${esc(t("survey"))}</div>
      <input id="createSurveyTitle" placeholder="${esc(t("title"))}">
      <input id="createSurveyStatus" value="active" placeholder="${esc(t("status"))}">
      <button ${surveyBoundaryDisabled} onclick="startSurveyBoundaryDraw()">${esc(t("draw_boundary"))}</button>
      <button class="primary" onclick="createSurvey()">${esc(t("create"))}</button>
      <div class="hint">${esc(t("survey_hint"))}</div>
      <div class="hint">${esc(t("create_workflow_hint"))}</div>
      ${hasActiveSurvey ? `<div class="hint">${esc(t("create_survey_locked_hint"))}</div>` : ""}
    </div>
    <div class="section">
      <div class="section-title">${esc(t("active_survey"))}</div>
      <div class="row"><span>${esc(t("selected"))}</span><strong>${esc(active ? surveyName(active) : t("none"))}</strong></div>
      <div class="row"><span>${esc(t("status"))}</span><strong>${esc(active ? surveyStatus(active) : "-")}</strong></div>
      <div class="row"><span>${esc(t("id"))}</span><strong>${esc(active ? surveyId(active) : "-")}</strong></div>
    </div>
    <div class="section">
      <div class="section-title">${esc(t("object"))}</div>
      <select id="createObjectType">
        <option value="note">${esc(tObjectType("note"))}</option>
        <option value="findspot">${esc(tObjectType("findspot"))}</option>
        <option value="track">${esc(tObjectType("track"))}</option>
        <option value="polygon">${esc(tObjectType("polygon"))}</option>
      </select>
      <input id="createObjectTitle" placeholder="${esc(t("object_title"))}">
      <textarea id="createObjectNote" placeholder="${esc(t("notes"))}"></textarea>
      <button onclick="startObjectDraw('point')">${esc(t("point"))}</button>
      <button onclick="startObjectDraw('line')">${esc(t("line"))}</button>
      <button onclick="startObjectDraw('polygon')">${esc(t("polygon"))}</button>
      <button class="primary" onclick="createObject()">${esc(t("create"))}</button>
    </div>
  `;
}

function editBody() {
  console.log("SELECTION", state.selection);
  if (!hasSelection()) {
    return `<div class="section"><div class="section-title">${esc(t("selection"))}</div><div class="hint">${esc(t("click_feature"))}</div></div>`;
  }
  if (state.selection.type === "survey") return surveyEditBody();
  if (state.selection.type === "object") return objectEditBody();
  if (state.selection.type === "identify") return identifyBody();
  return genericFeatureBody();
}

function surveyEditBody() {
  const selection = state.selection;
  const p = selection.properties || {};
  const metadata = p.metadata || {};
  const annotation = p.annotation ?? metadata.annotation ?? "";
  const details = p.details ?? metadata.details ?? "";
  const objectCount = p.object_count ?? p.feature_count ?? p.objects?.length ?? "-";

  return `
    <div class="section">
      <div class="section-title">${esc(t("survey"))}</div>
      <div class="row"><span>${esc(t("id"))}</span><strong>${esc(selection.surveyId || "-")}</strong></div>
      <div class="row"><span>${esc(t("objects"))}</span><strong>${esc(objectCount)}</strong></div>
      <input id="editSurveyTitle" value="${esc(p.title || "")}" placeholder="${esc(t("title"))}">
      <input id="editSurveyStatus" value="${esc(p.status || "")}" placeholder="${esc(t("status"))}">
      <textarea id="editSurveyAnnotation" placeholder="${esc(t("notes"))}">${esc(annotation)}</textarea>
      <textarea id="editSurveyDetails" placeholder="${esc(t("details"))}">${esc(details)}</textarea>
      <button class="primary" onclick="saveSelection()">${esc(t("save"))}</button>
      <button onclick="zoomToSelection()">${esc(t("zoom"))}</button>
    </div>
    <div class="section">
      <div class="section-title">${esc(t("draw_boundary"))}</div>
      <button onclick="startGeometryEdit()">${esc(t("edit_geometry"))}</button>
      <button onclick="saveGeometryEdit()">${esc(t("save_geometry"))}</button>
      <button onclick="resetSelectedGeometry()">${esc(t("reset_geometry"))}</button>
      <button onclick="stopGeometryEdit()">${esc(t("stop_edit"))}</button>
      <div class="hint">${esc(t("geometry_hint"))}</div>
    </div>
  `;
}

function objectEditBody() {
  const selection = state.selection;
  const p = selection.properties || {};
  return `
    <div class="section">
      <div class="section-title">${esc(t("selected_object"))}</div>
      <div class="row"><span>${esc(t("id"))}</span><strong>${esc(selection.objectId || "-")}</strong></div>
      <div class="row"><span>${esc(t("survey"))}</span><strong>${esc(selection.surveyId || "-")}</strong></div>
      <input id="editObjectType" value="${esc(p.type || "note")}" placeholder="${esc(t("object"))}">
      <input id="editObjectTitle" value="${esc(p.title || "")}" placeholder="${esc(t("title"))}">
      <textarea id="editObjectAnnotation" placeholder="${esc(t("notes"))}">${esc(p.annotation || p.note || "")}</textarea>
      <textarea id="editObjectDetails" placeholder="${esc(t("details"))}">${esc(p.details || "")}</textarea>

      <button class="primary" onclick="saveSelection()">${esc(t("save_attributes"))}</button>
      <button onclick="startGeometryEdit()">${esc(t("edit_geometry"))}</button>
      <button onclick="saveGeometryEdit()">${esc(t("save_geometry"))}</button>
      <button onclick="resetSelectedGeometry()">${esc(t("reset_geometry"))}</button>
      <button onclick="stopGeometryEdit()">${esc(t("stop_edit"))}</button>
      <button onclick="archiveSelection()">${esc(t("archive_object"))}</button>
      <button class="danger" onclick="deleteSelection()">${esc(t("delete"))}</button>

      <div class="hint">${esc(t("geometry_hint"))}</div>
    </div>
  `;
}

function genericFeatureBody() {
  const selection = state.selection;
  const p = selection.properties || {};
  return `
    <div class="section">
      <div class="section-title">${esc(t("selected"))}</div>
      <div class="row"><span>${esc(t("layer"))}</span><strong>${esc(selectionLayerLabel(selection) || "-")}</strong></div>
      <div class="row"><span>${esc(t("id"))}</span><strong>${esc(selectionRecordId(selection) || "-")}</strong></div>
      <div class="row"><span>${esc(t("status"))}</span><strong>${esc(selectionTypeLabel(selection?.type))}</strong></div>
      <div class="hint">${esc(t("click_feature"))}</div>
    </div>
    <div class="section">
      <div class="section-title">${esc(t("details"))}</div>
      <div class="props">${Object.keys(p).sort().map(k => `<div class="prop"><div class="prop-k">${esc(k)}</div><div class="prop-v">${esc(formatPropValue(p[k]))}</div></div>`).join("")}</div>
    </div>
  `;
}

function identifyBody() {
  const selection = state.selection;
  const hits = identifyResults(selection);
  return `
    <div class="section">
      <div class="section-title">${esc(t("identify_results"))}</div>
      <div class="row"><span>${esc(t("layer"))}</span><strong>${esc(selectionLayerLabel(selection) || "-")}</strong></div>
      <div class="row"><span>${esc(t("id"))}</span><strong>${esc(selectionRecordId(selection) || "-")}</strong></div>
      <div class="row"><span>${esc(t("status"))}</span><strong>${esc(selectionTypeLabel(selection?.type))}</strong></div>
    </div>
    ${hits.length ? hits.map((hit, index) => {
      const props = hit.properties || {};
      const rows = Object.keys(props).sort().map(k => `<div class="prop"><div class="prop-k">${esc(k)}</div><div class="prop-v">${esc(formatPropValue(props[k]))}</div></div>`).join("");
      const raw = hit.raw && typeof hit.raw === "object" ? `<div class="props">${Object.keys(hit.raw).sort().filter(k => k !== "properties").map(k => `<div class="prop"><div class="prop-k">${esc(k)}</div><div class="prop-v">${esc(formatPropValue(hit.raw[k]))}</div></div>`).join("")}</div>` : "";
      return `
        <div class="section">
          <div class="section-title">${esc(tLayerName(hit) || `${t("hit")} ${index + 1}`)}</div>
          <div class="row"><span>${esc(t("title"))}</span><strong>${esc(hit.title || props.title || props.name || "-")}</strong></div>
          <div class="row"><span>${esc(t("layer"))}</span><strong>${esc(tLayerName(hit) || "-")}</strong></div>
          <div class="row"><span>${esc(t("status"))}</span><strong>${esc(hit.info_format || hit.content_type || "-")}</strong></div>
          <div class="props">${rows || `<div class="hint">${esc(t("no_identify_results"))}</div>`}</div>
          ${hit.raw && typeof hit.raw === "string" ? `<div class="hint">${esc(t("identify_raw"))}</div><div class="props"><div class="prop"><div class="prop-k">${esc(t("identify_raw"))}</div><div class="prop-v">${esc(hit.raw)}</div></div></div>` : raw}
        </div>
      `;
    }).join("") : `<div class="section"><div class="hint">${esc(t("no_identify_results"))}</div></div>`}
  `;
}

function permissionWorkflowBody() {
  const candidates = state.permissionCandidates || [];
  const requests = state.permissionRequests || [];
  return `
    <div class="section">
      <div class="section-title">${esc(t("permission_workflow"))}</div>
      <div class="hint">${esc(t("ownership_notice"))}</div>
      <input id="permissionOwnerName" placeholder="${esc(t("owner_name"))}">
      <input id="permissionOwnerContact" placeholder="${esc(t("owner_contact"))}">
      <textarea id="permissionNotes" placeholder="${esc(t("request_notes"))}"></textarea>
      <button class="primary" onclick="loadPermissionCandidates()">${esc(t("load_permission_candidates"))}</button>
      <button onclick="loadPermissionRequests()">${esc(t("load_requests"))}</button>
      ${state.permissionStatus ? `<div class="hint">${esc(messageText(state.permissionStatus))}</div>` : ""}
    </div>
    <div class="section">
      <div class="section-title">${esc(t("permission_candidates"))}</div>
      ${candidates.length ? candidates.map(candidate => `
        <div class="permission-row">
          <div class="permission-main">
            <strong>${esc(permissionCandidateLabel(candidate))}</strong>
            <span class="permission-meta">${esc(tLayerName(candidate.layer))} - ${esc(t("candidate_overlap"))}: ${esc(formatArea(candidate.overlap_area_m2))} - ${esc(t("id"))}: ${esc(candidate.source_id || candidate.feature_id)}</span>
          </div>
          <button onclick="createPermissionRequest(${Number(candidate.feature_id)})">${esc(t("create_request"))}</button>
        </div>
      `).join("") : `<div class="hint">${esc(t("no_permission_candidates"))}</div>`}
    </div>
    <div class="section">
      <div class="section-title">${esc(t("permission_requests"))}</div>
      ${requests.length ? requests.map(request => `
        <div class="permission-row">
          <div class="permission-main">
            <strong>${esc(permissionCandidateLabel({properties: request.properties, source_id: request.source_id, feature_id: request.feature_id}))}</strong>
            <span class="permission-meta">${esc(request.status)} - ${esc(t("id"))}: ${esc(request.id)} - ${esc(request.owner_name || request.owner_contact || "-")}</span>
          </div>
        </div>
      `).join("") : `<div class="hint">${esc(t("no_permission_requests"))}</div>`}
    </div>
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
    ${permissionWorkflowBody()}
  `;
}

function layersBody() {
  const groups = {};
  const activeRegions = activeFocusStateIds();
  const visibleLayers = state.layers.filter(layer => layerVisibleForFocus(layer, activeRegions));
  const regionOptions = LAYER_REGIONS.map(regionOption => {
    const selected = regionOption.id === state.activeLayerRegion ? "selected" : "";
    const label = regionOption.id === "auto"
      ? `${tLayerRegion(regionOption.id)}: ${activeFocusStateLabel()}`
      : tLayerRegion(regionOption.id);
    return `<option value="${esc(regionOption.id)}" ${selected}>${esc(label)}</option>`;
  }).join("");

  visibleLayers.forEach(l => {
    const g = layerWorkflowGroup(l);
    if (!groups[g]) groups[g] = [];
    groups[g].push(l);
  });
  const hasLayers = Object.keys(groups).length > 0;
  const total = state.layers.length;
  const shown = visibleLayers.length;

  return `
    <div class="layer-region-controls">
      <div>
        <label>${esc(t("region_state"))}</label>
        <select id="layerRegionSelect" onchange="setLayerRegion(this.value)">
          ${regionOptions}
        </select>
      </div>
      <div class="layer-region-meta">${esc(shown)} / ${esc(total)}</div>
    </div>
    <div class="layer-toolbar">
      <label class="layer-toggle"><input type="checkbox" ${state.labelVisibility ? "checked" : ""} onchange="toggleLabels(this.checked)"> <span>${esc(t("point_labels"))}</span></label>
      <button onclick="loadLayers()">${esc(t("load_layers"))}</button>
    </div>
    ${hasLayers ? sortedLayerGroups(groups).map(g => `
      <div class="section">
        <div class="section-title">${esc(tLayerGroup(g))}</div>
        ${groups[g].map(l => `
          <label class="layer-row">
            <input type="checkbox" ${l.is_visible ? "checked" : ""} onchange="toggleLayer('${esc(l.layer_key)}', this.checked)">
            <div class="layer-row-main">
              <span class="layer-name">${esc(tLayerName(l))}</span>
              <span class="layer-count">${esc(layerObjectCount(l) ?? "registry")}</span>
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

function detailsLookupBody() {
  const lookup = state.lookupData;
  const context = selectionLookupContext();
  const hasPoint = Number.isFinite(context.lon) && Number.isFinite(context.lat);
  const coordText = hasPoint ? `${context.lat.toFixed(5)}, ${context.lon.toFixed(5)}` : "-";
  return `
    <div class="section">
      <div class="section-title">${esc(t("lookup_sources"))}</div>
      <button onclick="loadLookupData()">${esc(t("lookup_request"))}</button>
      ${lookup?.pending ? `<div class="hint">${esc(t("lookup_pending"))}</div>` : ""}
      ${lookup?.error ? `<div class="hint">${esc(t("request_failed"))}: ${esc(lookup.error)}</div>` : ""}
      <div class="row"><span>${esc(t("lookup_location"))}</span><strong>${esc(coordText)}</strong></div>
      ${lookup?.wiki?.url ? `
      <div class="lookup-links">
        ${lookup?.wiki?.url ? `<a href="${esc(lookup.wiki.url)}" target="_blank" rel="noopener noreferrer">${esc(t("lookup_open_wikipedia"))}</a>` : ""}
      </div>` : ""}
    </div>
    ${lookup?.wiki ? `
    <div class="section">
      <div class="section-title">${esc(t("lookup_wikipedia"))}</div>
      <div class="row"><span>${esc(t("title"))}</span><strong>${esc(lookup.wiki.title || "-")}</strong></div>
      <div class="hint">${esc(lookup.wiki.extract || "-")}</div>
    </div>` : ""}
    ${lookup?.osm ? `
    <div class="section">
      <div class="section-title">${esc(t("lookup_osm"))}</div>
      <div class="hint">${esc(lookup.osm.displayName || "-")}</div>
    </div>` : ""}
    ${!lookup ? `<div class="section"><div class="hint">${esc(t("lookup_none"))}</div></div>` : ""}
  `;
}

function detailsBody() {
  if (!hasSelection()) return `<div class="section"><div class="hint">${esc(t("click_feature"))}</div></div>`;
  const tabs = `
    <div class="detail-child-tabs">
      <button class="tab ${state.activeDetailsChild === "properties" ? "active" : ""}" onclick="detailsChildTab('properties')">${esc(t("details_properties"))}</button>
      <button class="tab ${state.activeDetailsChild === "lookup" ? "active" : ""}" onclick="detailsChildTab('lookup')">${esc(t("details_lookup"))}</button>
    </div>
  `;
  if (state.activeDetailsChild === "lookup") return tabs + detailsLookupBody();
  const selection = state.selection;
  if (selection.type === "identify") return tabs + identifyBody();
  const p = selection.properties || {};
  return tabs + `
    <div class="section">
      <div class="section-title">${esc(selectionTitle())}</div>
      <div class="hint">${esc(t("layer"))}: ${esc(selectionLayerLabel(selection) || "-")}<br>${esc(t("id"))}: ${esc(selectionRecordId(selection) || "-")}<br>${esc(t("status"))}: ${esc(selectionTypeLabel(selection?.type))}</div>
    </div>
    <div class="props">${Object.keys(p).sort().map(k => `<div class="prop"><div class="prop-k">${esc(k)}</div><div class="prop-v">${esc(formatPropValue(p[k]))}</div></div>`).join("")}</div>
  `;
}

function regionBody() {
  return `
    <div class="section"><div class="section-title">${esc(t("region"))}</div>
      <div class="row"><span>${esc(t("layers"))}</span><strong>${state.layers.length}</strong></div>
      <div class="row"><span>${esc(t("survey"))}</span><strong>${esc(state.activeSurveyId || t("none"))}</strong></div>
      <div class="row"><span>${esc(t("focus"))}</span><strong>${esc(state.focusMode === "survey" ? t("focus_survey") : t("focus_viewport"))}</strong></div>
      <div class="row"><span>${esc(t("active_states"))}</span><strong>${esc(activeFocusStateLabel())}</strong></div>
      <div class="row"><span>${esc(t("selection"))}</span><strong>${hasSelection() ? esc(t("yes")) : esc(t("no"))}</strong></div>
    </div>
  `;
}

function render() {
  const leftScroll = document.getElementById("left-panel")?.querySelector(".panel-body")?.scrollTop ?? 0;
  const rightScroll = document.getElementById("right-panel")?.querySelector(".panel-body")?.scrollTop ?? 0;
  css();
  topbar();
  panel("left-panel", "left", titleFor("left", state.activeLeft), subtitleFor(state.activeLeft), leftBody());
  panel("right-panel", "right", titleFor("right", state.activeRight), subtitleFor(state.activeRight), rightBody());
  requestAnimationFrame(() => {
    const leftBody = document.getElementById("left-panel")?.querySelector(".panel-body");
    const rightBody = document.getElementById("right-panel")?.querySelector(".panel-body");
    if (leftBody) leftBody.scrollTop = leftScroll;
    if (rightBody) rightBody.scrollTop = rightScroll;
  });
}

function titleFor(side, id) {
  const tabs = side === "left" ? state.manifest.left : state.manifest.right;
  const tab = tabs.find(t => t.id === id);
  return tTab(id, tab?.title || id);
}

function subtitleFor(id) {
  return {
    survey:t("survey_context"),
    manage:t("service_controls"),
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


function setLeft(id){
  state.activeLeft = id;
  state.leftOpen = true;
  render();
  if (id === "manage" && !state.admin.logs.length) loadAdminLogs(false);
}
function setRight(id){ state.activeRight = id; state.rightOpen = true; render(); }
function toggleLeft(){ state.leftOpen = !state.leftOpen; render(); }
function toggleRight(){ state.rightOpen = !state.rightOpen; render(); }

function setActiveSurveyContext(value) {
  state.activeSurveyId = value || null;
  state.permissionCandidates = [];
  state.permissionRequests = [];
  state.permissionStatus = "";
  const survey = activeSurveyRecord();
  toast(survey ? `${t("survey_set")}: ${surveyName(survey)}` : t("no_survey_selected"));
  if (state.activeSurveyId) {
    state.focusMode = "survey";
    selectSurveyById(state.activeSurveyId);
    syncSurveyFocusStates();
  } else {
    state.focusMode = "viewport";
    state.activeStatesSurvey = [];
    clearSelection();
  }
}

function setActiveSurvey() {
  const value = document.getElementById("surveyContextSelect")?.value || document.getElementById("surveySelect")?.value || null;
  setActiveSurveyContext(value);
}


async function loadSelectedSurvey(zoom) {
  if (!state.activeSurveyId) return alert(t("select_survey_first"));
  await loadSurveyFeatures(state.activeSurveyId, zoom);
  syncSurveyFocusStates();
  if (state.selection?.type === "survey" && String(state.selection.surveyId) === String(state.activeSurveyId)) {
    render();
  }
}

async function archiveActiveSurvey() {
  const survey = activeSurveyRecord();
  if (!survey) return alert(t("select_survey_first"));
  if (!confirm(`${t("confirm_archive_survey")} ${surveyName(survey)}`)) return;

  await fetchJson(`/api/surveys/${surveyId(survey)}/archive`, {method:"POST"});
  surveySource.clear();
  clearSelection({switchTabs:false, render:false});
  state.activeSurveyId = null;
  state.focusMode = "viewport";
  state.activeStatesSurvey = [];
  state.permissionCandidates = [];
  state.permissionRequests = [];
  state.permissionStatus = "";
  await loadSurveys({autoSelect:false});
  await loadLayers();
  render();
  toast(t("survey_archived"));
}

async function deleteActiveSurvey() {
  const survey = activeSurveyRecord();
  if (!survey) return alert(t("select_survey_first"));
  if (!confirm(`${t("confirm_delete_survey")} ${surveyName(survey)}`)) return;

  await fetchJson(`/api/surveys/${surveyId(survey)}`, {method:"DELETE"});
  surveySource.clear();
  drawSource.clear();
  clearSelection({switchTabs:false, render:false});
  state.activeSurveyId = null;
  state.focusMode = "viewport";
  state.activeStatesSurvey = [];
  state.permissionCandidates = [];
  state.permissionRequests = [];
  state.permissionStatus = "";
  await loadSurveys({autoSelect:false});
  await loadLayers();
  render();
  toast(t("survey_deleted"));
}

function toggleLayer(key, value) {
  const l = state.layerIndex.get(key);
  if (l) l.is_visible = !!value;
  if (contextTileLayers[key]) contextTileLayers[key].setVisible(!!value);
  scheduleLayerEfficiencyUpdate();
  toast(value ? t("layer_shown") : t("layer_hidden"));
}

function toggleLabels(value) {
  state.labelVisibility = !!value;
  syncContextLayers();
  toast(value ? t("labels_on") : t("labels_off"));
}

function setLayerRegion(value) {
  state.activeLayerRegion = LAYER_REGIONS.some(region => region.id === value) ? value : "auto";
  if (state.activeLayerRegion === "auto") state.autoLayerRegion = currentMapRegion();
  render();
}

function setBasemap(key) {
  const next = BASEMAPS[key] ? key : "osm";
  state.activeBasemap = next;
  if (baseLayer) baseLayer.setSource(createBasemapSource(next));
  scheduleLayerEfficiencyUpdate();
  render();
}

function stopMeasureInteraction() {
  if (measureInteraction) {
    map.removeInteraction(measureInteraction);
    measureInteraction = null;
  }
  if (measureGeomListener) {
    ol.Observable.unByKey(measureGeomListener);
    measureGeomListener = null;
  }
}

function clearMeasure() {
  stopMeasureInteraction();
  if (measureSource) measureSource.clear();
  state.measure.active = false;
  state.measure.meters = 0;
  render();
}

function setMeasureDistance(geometry) {
  if (!geometry) {
    state.measure.meters = 0;
    render();
    return;
  }
  state.measure.meters = ol.sphere.getLength(geometry, {projection: map.getView().getProjection()}) || 0;
  render();
}

function toggleMeasure() {
  if (!map || !measureSource) return;
  if (state.measure.active) {
    clearMeasure();
    return;
  }

  clearMeasure();
  state.measure.active = true;
  measureInteraction = new ol.interaction.Draw({source: measureSource, type: "LineString"});
  measureInteraction.on("drawstart", evt => {
    if (measureGeomListener) {
      ol.Observable.unByKey(measureGeomListener);
      measureGeomListener = null;
    }
    measureGeomListener = evt.feature.getGeometry().on("change", e => setMeasureDistance(e.target));
  });
  measureInteraction.on("drawend", evt => {
    setMeasureDistance(evt.feature.getGeometry());
    stopMeasureInteraction();
    state.measure.active = false;
    render();
  });
  map.addInteraction(measureInteraction);
  toast(t("measure_hint"));
  render();
}

function clampGridSize(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 100;
  return Math.max(10, Math.min(50000, Math.round(n)));
}

function updateGridLayer() {
  if (!map || !gridSource) return;
  gridSource.clear();
  if (!state.grid.enabled) return;

  const view = map.getView();
  const size = map.getSize();
  if (!view || !size) return;
  const extent = view.calculateExtent(size);
  if (!extent) return;

  const cell = clampGridSize(state.grid.cellMeters);
  state.grid.cellMeters = cell;

  const minX = extent[0], minY = extent[1], maxX = extent[2], maxY = extent[3];
  const startX = Math.floor(minX / cell) * cell;
  const startY = Math.floor(minY / cell) * cell;
  const cols = Math.ceil((maxX - startX) / cell);
  const rows = Math.ceil((maxY - startY) / cell);
  const maxLines = 450;
  if ((cols + rows) > maxLines) return;

  const features = [];
  for (let x = startX; x <= maxX + cell; x += cell) {
    features.push(new ol.Feature(new ol.geom.LineString([[x, minY], [x, maxY]])));
  }
  for (let y = startY; y <= maxY + cell; y += cell) {
    features.push(new ol.Feature(new ol.geom.LineString([[minX, y], [maxX, y]])));
  }
  gridSource.addFeatures(features);
}

function setGridSizeMeters(value) {
  state.grid.cellMeters = clampGridSize(value);
  render();
  updateGridLayer();
}

function toggleGrid() {
  state.grid.enabled = !state.grid.enabled;
  render();
  updateGridLayer();
}

function startSurveyBoundaryDraw() {
  if (state.activeSurveyId) return alert(t("draw_survey_boundary_blocked"));
  startDraw("polygon");
}

function startObjectDraw(type) {
  if (!state.activeSurveyId) return alert(t("draw_object_requires_active_survey"));
  startDraw(type);
}

function startDraw(type) {
  if (state.measure.active || state.measure.meters > 0) clearMeasure();
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
  if (state.activeSurveyId) return alert(t("draw_survey_boundary_blocked"));
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
    selectSurveyById(state.activeSurveyId, {render:false});
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
  await loadSurveys();
  await loadSurveyFeatures(state.activeSurveyId, false);
  toast(t("object_created"));
}

async function saveSelection() {
  if (!hasEditableSelection()) return alert(t("select_feature_first"));
  return state.selection.type === "survey" ? saveSurveySelection() : saveObjectSelection();
}

async function saveSurveySelection() {
  const selection = state.selection;
  const values = readSurveyEditValues(selection.properties || {});
  try {
    await fetchJson(`/api/surveys/${selection.surveyId}`, {
      method:"PATCH",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        title:values.title,
        status:values.status,
        metadata:values.metadata
      })
    });

    await loadSurveys({autoSelect:false});
    await loadSurveyFeatures(selection.surveyId, false);
    render();
    toast(t("saved"));
  } catch (error) {
    console.error("saveSurveySelection failed", error);
    alert(t("save_failed") + ": " + (error?.message || error));
  }
}

async function saveObjectSelection() {
  const id = selectedSurveyObjectId();
  if (!id) return alert(t("selected_feature_no_id"));

  const selection = state.selection;
  const values = readObjectEditValues(selection.properties || {});

  try {
    const payload = {
      type:values.type,
      properties:values.properties,
      title:values.title,
      annotation:values.annotation,
      details:values.details,
      is_active:selection.properties?.is_active !== false
    };

    await fetchJson(`/api/survey-objects/${id}`, {
      method:"PATCH",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify(payload)
    });

    await loadSurveyFeatures(selection.surveyId, false);
    render();
    toast(t("saved"));
  } catch (error) {
    console.error("saveObjectSelection failed", error);
    alert(t("save_failed") + ": " + (error?.message || error));
  }
}

async function deleteSelection() {
  if (state.selection?.type !== "object") return alert(t("select_object_first"));
  const id = selectedSurveyObjectId();
  if (!id) return alert(t("selected_feature_no_id"));
  if (!confirm(t("confirm_delete_object"))) return;
  const surveyId = state.selection.surveyId || state.activeSurveyId;
  await fetchJson(`/api/survey-objects/${id}`, {method:"DELETE"});
  clearSelection({switchTabs:false, render:false});
  await loadSurveys();
  if (surveyId) await loadSurveyFeatures(surveyId, false);
  toast(t("object_deleted"));
}

async function archiveSelection() {
  if (state.selection?.type !== "object") return alert(t("select_object_first"));
  const id = selectedSurveyObjectId();
  if (!id) return alert(t("selected_feature_no_id"));
  if (!confirm(t("confirm_archive_object"))) return;
  const surveyId = state.selection.surveyId || state.activeSurveyId;
  await fetchJson(`/api/survey-objects/${id}`, {
    method:"PATCH",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({is_active:false})
  });
  clearSelection({switchTabs:false, render:false});
  await loadSurveys();
  if (surveyId) await loadSurveyFeatures(surveyId, false);
  toast(t("object_archived"));
}

function downloadText(name, content, mimeType = "application/json") {
  const blob = new Blob([content], {type:mimeType});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function getCurrentMapImageDataUrl() {
  try {
    const canvas = map.getViewport().querySelector("canvas");
    if (!canvas) return null;
    return canvas.toDataURL("image/png");
  } catch {
    return null;
  }
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

function buildPrintableDocumentHtml(doc, mapImageDataUrl) {
  const survey = doc.survey || {};
  const objects = Array.isArray(doc.objects) ? doc.objects : [];
  const rows = objects.map(obj => {
    const properties = obj.properties ? `<pre>${esc(JSON.stringify(obj.properties, null, 2))}</pre>` : "";
    const details = [
      obj.details ? `<div><strong>${esc(t("details"))}:</strong> ${esc(obj.details)}</div>` : "",
      obj.annotation ? `<div><strong>${esc(t("annotation"))}:</strong> ${esc(obj.annotation)}</div>` : "",
      properties,
    ].filter(Boolean).join("");
    return `<tr><td>${esc(obj.id)}</td><td>${esc(obj.type || "")}</td><td>${esc(obj.title || "")}</td><td>${esc(obj.is_active ? t("active") : t("archived"))}</td><td>${details}</td></tr>`;
  }).join("");
  const mapSection = mapImageDataUrl ? `<h2>${esc(t("map"))}</h2><img src="${mapImageDataUrl}" style="max-width:100%;border:1px solid #ccc;">` : "";
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Survey ${esc(survey.id)} ${esc(t("document"))}</title><style>body{font-family:Arial,sans-serif;margin:24px;line-height:1.4;} table{width:100%;border-collapse:collapse;} th,td{border:1px solid #ccc;padding:8px;vertical-align:top;} h1,h2{margin:16px 0 8px;} pre{white-space:pre-wrap;word-break:break-word;}</style></head><body><h1>${esc(t("survey"))} ${esc(survey.id)} - ${esc(survey.title || "")}</h1><p><strong>${esc(t("status"))}:</strong> ${esc(survey.status || "")}<br><strong>${esc(t("layer_key"))}:</strong> ${esc(survey.layer_key || "")}<br><strong>${esc(t("expedition"))}:</strong> ${esc(survey.expedition_id || "")}</p><h2>${esc(t("summary"))}</h2><p><strong>${esc(t("total_objects"))}:</strong> ${esc(doc.summary?.object_count || 0)}<br><strong>${esc(t("active_objects"))}:</strong> ${esc(doc.summary?.active_count || 0)}<br><strong>${esc(t("archived_objects"))}:</strong> ${esc(doc.summary?.archived_count || 0)}</p>${mapSection}<h2>${esc(t("survey_metadata"))}</h2><pre>${esc(JSON.stringify(survey.metadata || {}, null, 2))}</pre><h2>${esc(t("objects"))}</h2><table><thead><tr><th>${esc(t("id"))}</th><th>${esc(t("type"))}</th><th>${esc(t("title"))}</th><th>${esc(t("status"))}</th><th>${esc(t("details"))}</th></tr></thead><tbody>${rows}</tbody></table></body></html>`;
}

async function exportDocument() {
  if (!state.activeSurveyId) return alert(t("set_active_survey_first"));
  const d = await fetchJson(`/api/surveys/${state.activeSurveyId}/export/document.json?include_geometry=false&include_properties=true`);
  const html = buildPrintableDocumentHtml(d, getCurrentMapImageDataUrl());
  downloadText(`survey_${state.activeSurveyId}_document.html`, html, "text/html");
}
async function exportPermission() {
  if (!hasSelection()) return alert(t("select_feature_first"));
  const p = state.selection.properties || {};
  const out = await fetchJson("/api/permissions/export", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      layer:selectionLayerKey(),
      source_id:p.source_id || selectionRecordId(),
      feature_id:p.id || selectionRecordId(),
      description:"ui export"
    })
  });
  toast(out.ok ? t("permission_exported") : t("export_failed"));
}

async function loadPermissionCandidates() {
  if (!state.activeSurveyId) return alert(t("set_active_survey_first"));
  const payload = await fetchJson(`/api/surveys/${state.activeSurveyId}/permission-candidates?limit=25`);
  state.permissionCandidates = Array.isArray(payload?.candidates) ? payload.candidates : [];
  state.permissionStatus = {key: "permission_candidates_loaded_count", count: state.permissionCandidates.length};
  render();
  toast(messageText(state.permissionStatus));
}

async function loadPermissionRequests(showToast = true) {
  if (!state.activeSurveyId) return alert(t("set_active_survey_first"));
  const payload = await fetchJson(`/api/surveys/${state.activeSurveyId}/permission-requests`);
  state.permissionRequests = Array.isArray(payload?.requests) ? payload.requests : [];
  if (showToast) toast(`${state.permissionRequests.length} ${t("permission_requests")}`);
  render();
}

async function createPermissionRequest(featureId) {
  if (!state.activeSurveyId) return alert(t("set_active_survey_first"));
  const candidate = (state.permissionCandidates || []).find(c => Number(c.feature_id) === Number(featureId));
  if (!candidate) return alert(t("select_feature_first"));
  const ownerName = document.getElementById("permissionOwnerName")?.value || "";
  const ownerContact = document.getElementById("permissionOwnerContact")?.value || "";
  const notes = document.getElementById("permissionNotes")?.value || "";
  const out = await fetchJson("/api/permissions/requests", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      survey_id:Number(state.activeSurveyId),
      feature_id:candidate.feature_id,
      layer:candidate.layer,
      source_id:candidate.source_id,
      status:"draft",
      owner_name:ownerName,
      owner_contact:ownerContact,
      notes
    })
  });
  if (out?.request) {
    state.permissionRequests = [out.request, ...(state.permissionRequests || [])];
  }
  state.permissionStatus = {key: "request_created"};
  render();
  toast(messageText(state.permissionStatus));
}

async function start() {
  css();
  state.manifest = await loadManifest();
  document.documentElement.lang = state.lang || "en";
  initMap();
  render();
  await refreshSystem();
  await loadAdminLogs(false);
  await loadSurveys();
  await loadLayers();
  render();
}

Object.assign(window, {
  startGeometryEdit,stopGeometryEdit,saveGeometryEdit,resetSelectedGeometry,zoomToSelection,
  toggleMeasure,clearMeasure,toggleGrid,setGridSizeMeters,
  detailsChildTab,loadLookupData,
  setLanguage,setLeft,setRight,toggleLeft,toggleRight,refreshSystem,setActiveSurvey,setActiveSurveyContext,loadSelectedSurvey,loadSurveys,loadLayers,loadSurveyFeatures,
  controlAdminService,loadAdminLogs,readAdminLogControls,viewAdminLog,clearAdminLogOutput,
  toggleLayer,toggleLabels,setLayerRegion,startDraw,startSurveyBoundaryDraw,startObjectDraw,setBasemap,createSurvey,createObject,saveSelection,archiveSelection,deleteSelection,archiveActiveSurvey,deleteActiveSurvey,
  exportLayer,exportData,exportDocument,exportPermission,loadPermissionCandidates,loadPermissionRequests,createPermissionRequest
});

start().catch(e => {
  console.error(e);
  alert(e.message || e);
});
