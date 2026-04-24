from pathlib import Path
import base64

ROOT = Path.cwd()

UI_BOOT = r'''const state = {
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
'''

BUILD_SCRIPT = r'''from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

LAYER_SPECS = [
    {
        "layer_key": "rivers_streams",
        "layer_name": "Rivers and streams",
        "geometry_type": "LINESTRING",
        "sort_order": 300,
        "metadata": {
            "subgroup": "hydrology",
            "phase": "hardening_bundle",
            "description": "Current rivers, streams, canals, drains"
        }
    },
    {
        "layer_key": "waterbodies",
        "layer_name": "Waterbodies",
        "geometry_type": "POLYGON",
        "sort_order": 301,
        "metadata": {
            "subgroup": "hydrology",
            "phase": "hardening_bundle",
            "description": "Current lakes, ponds, water polygons"
        }
    },
    {
        "layer_key": "floodplains",
        "layer_name": "Floodplains",
        "geometry_type": "POLYGON",
        "sort_order": 302,
        "metadata": {
            "subgroup": "hydrology",
            "phase": "hardening_bundle",
            "description": "Wetland/floodplain proxy polygons"
        }
    },
    {
        "layer_key": "protection_buffers",
        "layer_name": "Protection buffers",
        "geometry_type": "POLYGON",
        "sort_order": 212,
        "metadata": {
            "subgroup": "legal_permission",
            "phase": "hardening_bundle",
            "description": "Protection and legal buffer polygons"
        }
    }
]

def main() -> int:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            for spec in LAYER_SPECS:
                cur.execute(
                    """
                    INSERT INTO layers_registry (
                        layer_key, layer_name, layer_group, source_table, geometry_type,
                        is_user_selectable, is_visible, opacity, sort_order, metadata
                    )
                    VALUES (
                        %s, %s, 'context', 'external_features', %s,
                        TRUE, FALSE, 1.0, %s, %s::jsonb
                    )
                    ON CONFLICT (layer_key) DO UPDATE
                    SET layer_name = EXCLUDED.layer_name,
                        geometry_type = EXCLUDED.geometry_type,
                        sort_order = EXCLUDED.sort_order,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    (
                        spec["layer_key"],
                        spec["layer_name"],
                        spec["geometry_type"],
                        spec["sort_order"],
                        json.dumps(spec["metadata"]),
                    ),
                )
        conn.commit()
    finally:
        conn.close()
    print("[DONE] hydrology + protection layers registered")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''

INGEST_HYDRO = r'''from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BBOX = (47.20, 8.95, 50.65, 13.95)

RAW_DIR = ROOT / "workspace" / "downloads" / "raw" / "osm"
RAW_DIR.mkdir(parents=True, exist_ok=True)

LAYER_CONFIG = {
    "rivers_streams": {
        "query": f"""
[out:json][timeout:300];
(
  way["waterway"~"river|stream|ditch|canal|drain"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out tags geom;
""",
        "source_table": "osm_hydrology_rivers_streams",
        "kind": "line",
    },
    "waterbodies": {
        "query": f"""
[out:json][timeout:300];
(
  way["natural"="water"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["water"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out tags geom;
""",
        "source_table": "osm_hydrology_waterbodies",
        "kind": "polygon",
    },
    "floodplains": {
        "query": f"""
[out:json][timeout:300];
(
  way["natural"="wetland"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["wetland"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out tags geom;
""",
        "source_table": "osm_hydrology_floodplains",
        "kind": "polygon",
    },
}

def fetch(query: str, name: str) -> tuple[dict, Path]:
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "surveyCatalyst/hydro-bundle"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    out = RAW_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    return payload, out

def close_ring(coords):
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords

def element_to_feature(element: dict, kind: str) -> dict | None:
    tags = element.get("tags") or {}
    geom = element.get("geometry") or []
    coords = [[p["lon"], p["lat"]] for p in geom if "lon" in p and "lat" in p]
    if kind == "polygon":
        if len(coords) < 3:
            return None
        coords = close_ring(coords)
        geometry = {"type": "Polygon", "coordinates": [coords]}
    else:
        if len(coords) < 2:
            return None
        geometry = {"type": "LineString", "coordinates": coords}

    props = {
        "name": tags.get("name"),
        "waterway": tags.get("waterway"),
        "natural": tags.get("natural"),
        "water": tags.get("water"),
        "wetland": tags.get("wetland"),
        "source": "osm_overpass_auto_hydrology",
        "osm_type": element.get("type"),
        "osm_id": element.get("id"),
        "all_tags": tags,
    }
    return {"type": "Feature", "geometry": geometry, "properties": props}

def load_features(layer_key: str, source_table: str, kind: str, features: list[dict]) -> int:
    backend = build_backend()
    conn = backend.connect()
    inserted = 0
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM external_features WHERE layer = %s", (layer_key,))
            for feat in features:
                props = feat["properties"]
                source_id = str(props.get("osm_id") or "")
                geom_expr = "ST_Force2D(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))"
                if kind == "polygon":
                    geom_expr = "ST_Multi(ST_Force2D(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)))"
                cur.execute(
                    f"""
                    INSERT INTO external_features (layer, geom, properties, source_table, source_id)
                    VALUES (
                        %s,
                        {geom_expr},
                        %s::jsonb,
                        %s,
                        %s
                    )
                    """,
                    (
                        layer_key,
                        json.dumps(feat["geometry"]),
                        json.dumps(props),
                        source_table,
                        source_id,
                    ),
                )
                inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted

def main() -> int:
    for layer_key, cfg in LAYER_CONFIG.items():
        print(f"[INFO] downloading {layer_key}")
        payload, saved = fetch(cfg["query"], layer_key)
        print(f"[INFO] raw saved to {saved}")
        elements = payload.get("elements") or []
        seen = set()
        features = []
        for element in elements:
            feature = element_to_feature(element, cfg["kind"])
            if not feature:
                continue
            key = (feature["properties"].get("osm_type"), feature["properties"].get("osm_id"))
            if key in seen:
                continue
            seen.add(key)
            features.append(feature)
        inserted = load_features(layer_key, cfg["source_table"], cfg["kind"], features)
        print(f"[DONE] {layer_key}: source={len(elements)} loaded={inserted}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''

LOAD_PROTECTION = r'''from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

LAYER_KEY = "protection_buffers"
SOURCE_TABLE = "protection_buffers_import"

def iter_features(doc: dict):
    if doc.get("type") == "FeatureCollection":
        for feat in doc.get("features") or []:
            yield feat
    elif doc.get("type") == "Feature":
        yield doc
    else:
        raise ValueError("Input must be GeoJSON Feature or FeatureCollection")

def pick_source_id(props: dict, fallback: int) -> str:
    props = props or {}
    for key in ("id", "identifier", "source_id", "name", "ref"):
        value = props.get(key)
        if value not in (None, ""):
            return str(value)
    return str(fallback)

def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python scripts/load_protection_buffers_geojson.py <full-path-to-geojson>")
        return 1

    path = Path(argv[1]).resolve()
    if not path.exists():
        print(f"[ERROR] file not found: {path}")
        return 1

    doc = json.loads(path.read_text(encoding="utf-8"))
    backend = build_backend()
    conn = backend.connect()
    inserted = 0
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM external_features WHERE layer = %s", (LAYER_KEY,))
            for idx, feat in enumerate(iter_features(doc), start=1):
                geom = feat.get("geometry")
                props = feat.get("properties") or {}
                if not geom:
                    continue
                cur.execute(
                    """
                    INSERT INTO external_features (layer, geom, properties, source_table, source_id)
                    VALUES (
                        %s,
                        ST_Multi(ST_Force2D(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))),
                        %s::jsonb,
                        %s,
                        %s
                    )
                    """,
                    (
                        LAYER_KEY,
                        json.dumps(geom),
                        json.dumps(props),
                        SOURCE_TABLE,
                        pick_source_id(props, idx),
                    ),
                )
                inserted += 1
        conn.commit()
    finally:
        conn.close()

    print(f"[DONE] loaded {inserted} features into layer '{LAYER_KEY}'")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
'''

LAYER_COUNTS = r'''from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

def main() -> int:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT layer, COUNT(*)
                FROM external_features
                GROUP BY layer
                ORDER BY layer
            """)
            for layer, count in cur.fetchall():
                print(f"{layer}: {count}")
    finally:
        conn.close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''

files = {
    ROOT / "app" / "static" / "ui_boot.js": UI_BOOT,
    ROOT / "scripts" / "build_hydrology_protection_layers.py": BUILD_SCRIPT,
    ROOT / "scripts" / "ingest_hydrology_osm.py": INGEST_HYDRO,
    ROOT / "scripts" / "load_protection_buffers_geojson.py": LOAD_PROTECTION,
    ROOT / "scripts" / "layer_counts.py": LAYER_COUNTS,
}

for path, content in files.items():
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[OK] wrote {path}")

print("[DONE] hardening + hydrology bundle applied")
print("Run:")
print("  python scripts/build_hydrology_protection_layers.py")
print("  python scripts/ingest_hydrology_osm.py")
print("  python scripts/system_control.py restart")
print("Protection buffers later:")
print('  python scripts/load_protection_buffers_geojson.py "<FULL_PATH_TO_PROTECTION_GEOJSON>"')