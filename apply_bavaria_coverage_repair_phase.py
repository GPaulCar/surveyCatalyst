from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

OVERPASS_URL = "https://overpass.kumi.systems/api/interpreter"
RAW_DIR = ROOT / "workspace" / "downloads" / "raw" / "osm" / "bavaria_repair"
RAW_DIR.mkdir(parents=True, exist_ok=True)

BAVARIA_TILES = [
    (47.20, 8.95, 48.35, 10.60),
    (47.20, 10.60, 48.35, 12.25),
    (47.20, 12.25, 48.35, 13.95),
    (48.35, 8.95, 49.50, 10.60),
    (48.35, 10.60, 49.50, 12.25),
    (48.35, 12.25, 49.50, 13.95),
    (49.50, 8.95, 50.65, 10.60),
    (49.50, 10.60, 50.65, 12.25),
    (49.50, 12.25, 50.65, 13.95),
]

CONFIG = {
    "field_names": {
        "kind": "point",
        "source_table": "osm_bavaria_field_names_area_repair",
        "queries": [
            """
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  node["place"~"locality|hamlet|isolated_dwelling|farm"](area.searchArea);
  node["name"]["historic"](area.searchArea);
  node["name"]["landuse"](area.searchArea);
);
out tags;
"""
        ],
    },
    "geonames_points": {
        "kind": "point",
        "source_table": "osm_bavaria_geonames_area_repair",
        "queries": [
            """
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  node["place"](area.searchArea);
  node["historic"](area.searchArea);
  node["tourism"~"attraction|viewpoint|museum"](area.searchArea);
);
out tags;
"""
        ],
    },
    "old_creeks": {
        "kind": "line",
        "source_table": "osm_bavaria_old_creeks_area_repair",
        "queries": [
            """
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  way["waterway"~"stream|ditch|drain"]["name"](area.searchArea);
  way["waterway"]["intermittent"="yes"](area.searchArea);
  way["waterway"]["seasonal"="yes"](area.searchArea);
);
out tags geom;
"""
        ],
    },
    "old_channels": {
        "kind": "line",
        "source_table": "osm_bavaria_old_channels_area_repair",
        "queries": [
            """
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  way["waterway"~"canal|ditch|drain"](area.searchArea);
  way["historic"~"canal|waterway"](area.searchArea);
  way["man_made"~"canal|drain"](area.searchArea);
);
out tags geom;
"""
        ],
    },
    "wetland_history": {
        "kind": "polygon",
        "source_table": "osm_bavaria_wetland_history_area_repair",
        "queries": [],
    },
    "floodplains": {
        "kind": "polygon",
        "source_table": "osm_bavaria_floodplains_area_repair",
        "queries": [],
    },
    "parcel_boundaries": {
        "kind": "polygon",
        "source_table": "osm_bavaria_parcel_proxy_area_repair",
        "queries": [],
    },
}

for s, w, n, e in BAVARIA_TILES:
    CONFIG["wetland_history"]["queries"].append(f"""
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  way["natural"="wetland"](area.searchArea)({s},{w},{n},{e});
  way["wetland"](area.searchArea)({s},{w},{n},{e});
);
out tags geom;
""")
    CONFIG["floodplains"]["queries"].append(f"""
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  way["natural"="wetland"](area.searchArea)({s},{w},{n},{e});
  way["wetland"](area.searchArea)({s},{w},{n},{e});
);
out tags geom;
""")
    CONFIG["parcel_boundaries"]["queries"].append(f"""
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  way["landuse"](area.searchArea)({s},{w},{n},{e});
  way["amenity"](area.searchArea)({s},{w},{n},{e});
  way["leisure"](area.searchArea)({s},{w},{n},{e});
);
out tags geom;
""")

LAYER_REGISTRY = [
    ("field_names", "Field names", "POINT", 340, "place_names"),
    ("geonames_points", "GeoNames / place points", "POINT", 341, "place_names"),
    ("old_creeks", "Old creeks", "LINESTRING", 330, "historical_water"),
    ("old_channels", "Old channels", "LINESTRING", 331, "historical_water"),
    ("wetland_history", "Wetland history", "POLYGON", 332, "historical_water"),
    ("floodplains", "Floodplains", "POLYGON", 302, "hydrology"),
    ("parcel_boundaries", "Parcel boundaries (OSM proxy)", "POLYGON", 220, "permission"),
]

def run(cmd: list[str], required: bool = True) -> int:
    print("[RUN] " + " ".join(cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if required and result.returncode != 0:
        raise SystemExit(result.returncode)
    return result.returncode

def fetch(query: str, layer_key: str, part: int | None = None) -> dict:
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "surveyCatalyst/bavaria-coverage-repair"},
        method="POST",
    )

    last_error = None
    for attempt in range(1, 6):
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        time.sleep(2)  # <-- throttle between successful calls
        return payload

    except Exception as exc:
        last_error = exc
        wait = 10 * attempt  # exponential backoff
        print(f"[WARN] {layer_key} attempt {attempt} failed: {exc} -> waiting {wait}s")
        time.sleep(3)

    raise last_error

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
        geom = {"type": "Point", "coordinates": [lon, lat]}
    else:
        raw_geom = element.get("geometry") or []
        coords = [[p["lon"], p["lat"]] for p in raw_geom if "lon" in p and "lat" in p]

        if kind == "polygon":
            if len(coords) < 3:
                return None
            geom = {"type": "Polygon", "coordinates": [close_ring(coords)]}
        else:
            if len(coords) < 2:
                return None
            geom = {"type": "LineString", "coordinates": coords}

    props = {
        "name": tags.get("name"),
        "place": tags.get("place"),
        "historic": tags.get("historic"),
        "waterway": tags.get("waterway"),
        "natural": tags.get("natural"),
        "wetland": tags.get("wetland"),
        "landuse": tags.get("landuse"),
        "amenity": tags.get("amenity"),
        "leisure": tags.get("leisure"),
        "source": "osm_bavaria_area_repair",
        "osm_type": element.get("type"),
        "osm_id": element.get("id"),
        "all_tags": tags,
    }

    return {"type": "Feature", "geometry": geom, "properties": props}

def register_layers() -> None:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            for key, name, geom_type, order, subgroup in LAYER_REGISTRY:
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
                        key,
                        name,
                        geom_type,
                        order,
                        json.dumps({
                            "subgroup": subgroup,
                            "coverage": "bavaria_admin_area_DE_BY",
                            "repair_phase": "bavaria_coverage_repair",
                        }),
                    ),
                )
        conn.commit()
    finally:
        conn.close()

def load_layer(layer_key: str, cfg: dict, features: list[dict]) -> int:
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
                if cfg["kind"] == "polygon":
                    geom_expr = "ST_Multi(ST_Force2D(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))))"
                cur.execute(
                    f"""
                    INSERT INTO external_features (layer, geom, properties, source_table, source_id)
                    VALUES (%s, {geom_expr}, %s::jsonb, %s, %s)
                    """,
                    (
                        layer_key,
                        json.dumps(feat["geometry"]),
                        json.dumps(props),
                        cfg["source_table"],
                        source_id,
                    ),
                )
                inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted

def ingest_layer(layer_key: str, cfg: dict) -> int:
    print(f"[INFO] repairing coverage for {layer_key}")
    seen = set()
    features = []
    total_source = 0

    for idx, query in enumerate(cfg["queries"], start=1):
        payload = fetch(query, layer_key, idx if len(cfg["queries"]) > 1 else None)
        elements = payload.get("elements") or []
        total_source += len(elements)

        for element in elements:
            feature = element_to_feature(element, cfg["kind"])
            if not feature:
                continue
            key = (feature["properties"].get("osm_type"), feature["properties"].get("osm_id"))
            if key in seen:
                continue
            seen.add(key)
            features.append(feature)

    inserted = load_layer(layer_key, cfg, features)
    print(f"[DONE] {layer_key}: source={total_source} loaded={inserted}")
    return inserted

def layer_counts() -> dict[str, int]:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT layer, COUNT(*) FROM external_features GROUP BY layer ORDER BY layer")
            return {str(layer): int(count) for layer, count in cur.fetchall()}
    finally:
        conn.close()

def clear_tile_cache() -> None:
    cache = ROOT / ".cache" / "mvt"
    if cache.exists():
        shutil.rmtree(cache, ignore_errors=True)
    cache.mkdir(parents=True, exist_ok=True)
    print("[OK] cleared MVT tile cache")

def checkpoint() -> None:
    if (ROOT / "apply_checkpoint_bundle.py").exists():
        run([sys.executable, "apply_checkpoint_bundle.py", "bavaria-coverage-repair-stage1", "--no-push"], required=False)
    else:
        print("[WARN] checkpoint skipped: apply_checkpoint_bundle.py not found")

def main() -> None:
    print("[1/7] register Bavaria-area layers")
    register_layers()

    print("[2/7] reload affected OSM layers using Bavaria admin area")
    results = {}
    for layer_key, cfg in CONFIG.items():
        results[layer_key] = ingest_layer(layer_key, cfg)

    print("[3/7] verify counts")
    counts = layer_counts()
    for layer_key in CONFIG:
        count = counts.get(layer_key, 0)
        print(f"{layer_key}: {count}")
        if count <= 0:
            raise SystemExit(f"[FAIL] {layer_key} has no data")

    print("[4/7] clear tile cache")
    clear_tile_cache()

    print("[5/7] restart system")
    run([sys.executable, "scripts/system_control.py", "restart"])

    print("[6/7] checkpoint")
    checkpoint()

    print("[7/7] phase complete")
    print("[PHASE COMPLETE]")
    print("Bavaria coverage repair completed")
    print("Affected layers are now sourced through the Bavaria admin area, not arbitrary rectangular-only coverage.")

if __name__ == "__main__":
    main()