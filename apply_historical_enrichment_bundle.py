from pathlib import Path

ROOT = Path.cwd()

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
        "layer_key": "old_creeks",
        "layer_name": "Old creeks",
        "geometry_type": "LINESTRING",
        "sort_order": 330,
        "metadata": {
            "subgroup": "historical_water",
            "description": "Historic or inferred creek and stream channels"
        },
    },
    {
        "layer_key": "old_channels",
        "layer_name": "Old channels",
        "geometry_type": "LINESTRING",
        "sort_order": 331,
        "metadata": {
            "subgroup": "historical_water",
            "description": "Historic, abandoned, intermittent, or canalised water channels"
        },
    },
    {
        "layer_key": "wetland_history",
        "layer_name": "Wetland history",
        "geometry_type": "POLYGON",
        "sort_order": 332,
        "metadata": {
            "subgroup": "historical_water",
            "description": "Historic wetland / marsh / damp-ground proxy areas"
        },
    },
    {
        "layer_key": "field_names",
        "layer_name": "Field names",
        "geometry_type": "POINT",
        "sort_order": 340,
        "metadata": {
            "subgroup": "place_names",
            "description": "OSM locality, field-name, hamlet, farm and named-place proxy layer"
        },
    },
    {
        "layer_key": "geonames_points",
        "layer_name": "GeoNames / place points",
        "geometry_type": "POINT",
        "sort_order": 341,
        "metadata": {
            "subgroup": "place_names",
            "description": "Place-name enrichment points from open sources"
        },
    },
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

    print("[DONE] historical + enrichment layers registered")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''

INGEST_SCRIPT = r'''from __future__ import annotations

import json
import sys
import time
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
RAW_DIR = ROOT / "workspace" / "downloads" / "raw" / "osm"
RAW_DIR.mkdir(parents=True, exist_ok=True)

BBOX = (47.20, 8.95, 50.65, 13.95)

CONFIG = {
    "old_creeks": {
        "kind": "line",
        "source_table": "osm_historical_old_creeks",
        "query": f"""
[out:json][timeout:300];
(
  way["waterway"~"stream|ditch|drain"]["name"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["waterway"]["intermittent"="yes"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["waterway"]["seasonal"="yes"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out tags geom;
""",
    },
    "old_channels": {
        "kind": "line",
        "source_table": "osm_historical_old_channels",
        "query": f"""
[out:json][timeout:300];
(
  way["waterway"~"canal|ditch|drain"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["historic"~"canal|waterway"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["man_made"~"canal|drain"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out tags geom;
""",
    },
    "wetland_history": {
        "kind": "polygon",
        "source_table": "osm_historical_wetland_history",
        "query": f"""
[out:json][timeout:300];
(
  way["natural"="wetland"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["wetland"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  way["landuse"~"meadow|grass"]["wetland"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out tags geom;
""",
    },
    "field_names": {
        "kind": "point",
        "source_table": "osm_field_names_proxy",
        "query": f"""
[out:json][timeout:300];
(
  node["place"~"locality|hamlet|isolated_dwelling|farm"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  node["name"]["historic"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  node["name"]["landuse"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out tags geom;
""",
    },
    "geonames_points": {
        "kind": "point",
        "source_table": "osm_geonames_proxy",
        "query": f"""
[out:json][timeout:300];
(
  node["place"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  node["historic"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
  node["tourism"~"attraction|viewpoint|museum"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out tags geom;
""",
    },
}

def layer_count(layer_key: str) -> int:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM external_features WHERE layer = %s", (layer_key,))
            row = cur.fetchone()
            return int(row[0] or 0)
    finally:
        conn.close()

def fetch(query: str, name: str) -> tuple[dict, Path]:
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "surveyCatalyst/historical-enrichment"},
        method="POST",
    )

    last_error = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            out = RAW_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            out.write_text(json.dumps(payload), encoding="utf-8")
            return payload, out
        except Exception as exc:
            last_error = exc
            print(f"[WARN] {name} attempt {attempt} failed: {exc}")
            if attempt < 3:
                time.sleep(3 * attempt)
    raise last_error  # type: ignore[misc]

def close_ring(coords):
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords

def element_to_feature(element: dict, kind: str) -> dict | None:
    tags = element.get("tags") or {}

    if kind == "point":
        lat = element.get("lat")
        lon = element.get("lon")
        if lat is None or lon is None:
            return None
        geometry = {"type": "Point", "coordinates": [lon, lat]}
    else:
        geom = element.get("geometry") or []
        coords = [[p["lon"], p["lat"]] for p in geom if "lon" in p and "lat" in p]

        if kind == "polygon":
            if len(coords) < 3:
                return None
            geometry = {"type": "Polygon", "coordinates": [close_ring(coords)]}
        else:
            if len(coords) < 2:
                return None
            geometry = {"type": "LineString", "coordinates": coords}

    props = {
        "name": tags.get("name"),
        "historic": tags.get("historic"),
        "place": tags.get("place"),
        "waterway": tags.get("waterway"),
        "wetland": tags.get("wetland"),
        "natural": tags.get("natural"),
        "landuse": tags.get("landuse"),
        "source": "osm_overpass_historical_enrichment",
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

def ingest_layer(layer_key: str, cfg: dict) -> None:
    current = layer_count(layer_key)
    if current > 0:
        print(f"[SKIP] {layer_key}: already loaded ({current})")
        return

    print(f"[INFO] downloading {layer_key}")
    payload, saved = fetch(cfg["query"], layer_key)
    print(f"[INFO] raw saved to {saved}")

    seen = set()
    features = []
    elements = payload.get("elements") or []

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

def main() -> int:
    for layer_key, cfg in CONFIG.items():
        ingest_layer(layer_key, cfg)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
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
    ROOT / "scripts" / "build_historical_enrichment_layers.py": BUILD_SCRIPT,
    ROOT / "scripts" / "ingest_historical_enrichment_osm.py": INGEST_SCRIPT,
    ROOT / "scripts" / "layer_counts.py": LAYER_COUNTS,
}

for path, content in files.items():
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[OK] wrote {path}")

print("[DONE] historical + enrichment bundle applied")