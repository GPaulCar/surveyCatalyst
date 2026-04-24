from pathlib import Path

ROOT = Path.cwd()
TARGET = ROOT / "scripts" / "stable_osm_ingest_engine.py"

CODE = r'''
from __future__ import annotations

import json
import random
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

OVERPASS_ENDPOINTS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

WORK_DIR = ROOT / "workspace" / "osm_ingest_engine"
RAW_DIR = WORK_DIR / "raw"
STATE_DIR = WORK_DIR / "state"
RAW_DIR.mkdir(parents=True, exist_ok=True)
STATE_DIR.mkdir(parents=True, exist_ok=True)

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

JOBS = {
    "field_names": {
        "kind": "point",
        "source_table": "osm_bavaria_field_names_stable",
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
        "source_table": "osm_bavaria_geonames_stable",
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
        "source_table": "osm_bavaria_old_creeks_stable",
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
        "source_table": "osm_bavaria_old_channels_stable",
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
        "source_table": "osm_bavaria_wetland_history_stable",
        "queries": [],
    },
    "floodplains": {
        "kind": "polygon",
        "source_table": "osm_bavaria_floodplains_stable",
        "queries": [],
    },
    "parcel_boundaries": {
        "kind": "polygon",
        "source_table": "osm_bavaria_parcel_proxy_stable",
        "queries": [],
    },
}

for s, w, n, e in BAVARIA_TILES:
    bbox = f"{s},{w},{n},{e}"
    JOBS["wetland_history"]["queries"].append(f"""
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  way["natural"="wetland"](area.searchArea)({bbox});
  way["wetland"](area.searchArea)({bbox});
);
out tags geom;
""")
    JOBS["floodplains"]["queries"].append(f"""
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  way["natural"="wetland"](area.searchArea)({bbox});
  way["wetland"](area.searchArea)({bbox});
);
out tags geom;
""")
    JOBS["parcel_boundaries"]["queries"].append(f"""
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  way["landuse"](area.searchArea)({bbox});
  way["amenity"](area.searchArea)({bbox});
  way["leisure"](area.searchArea)({bbox});
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

def state_path(job_name: str) -> Path:
    return STATE_DIR / f"{job_name}.json"

def load_state(job_name: str) -> dict:
    path = state_path(job_name)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"completed_parts": [], "failed_parts": [], "raw_files": [], "started_at": datetime.now().isoformat()}

def save_state(job_name: str, state: dict) -> None:
    state["updated_at"] = datetime.now().isoformat()
    state_path(job_name).write_text(json.dumps(state, indent=2), encoding="utf-8")

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
                            "engine": "stable_osm_ingest_engine",
                        }),
                    ),
                )
        conn.commit()
    finally:
        conn.close()

def fetch_query(job_name: str, query: str, part: int) -> Path:
    payload = urllib.parse.urlencode({"data": query}).encode("utf-8")
    last_error = None

    for attempt in range(1, 9):
        endpoint = OVERPASS_ENDPOINTS[(attempt - 1) % len(OVERPASS_ENDPOINTS)]
        wait = min(180, 8 * attempt + random.randint(0, 8))

        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"User-Agent": "surveyCatalyst/stable-osm-ingest-engine"},
            method="POST",
        )

        try:
            print(f"[FETCH] {job_name} part={part} attempt={attempt} endpoint={endpoint}")
            with urllib.request.urlopen(req, timeout=600) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            out = RAW_DIR / f"{job_name}_part{part}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            out.write_text(json.dumps(data), encoding="utf-8")
            print(f"[OK] saved {out}")
            time.sleep(5)
            return out

        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in (429, 502, 503, 504):
                print(f"[WARN] rate/server error {exc.code}; wait {wait}s")
                time.sleep(wait)
                continue
            raise

        except Exception as exc:
            last_error = exc
            print(f"[WARN] fetch failed: {exc}; wait {wait}s")
            time.sleep(wait)

    raise RuntimeError(f"failed to fetch {job_name} part {part}: {last_error}")

def close_ring(coords: list[list[float]]) -> list[list[float]]:
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
        "source": "osm_stable_bavaria_area_ingest",
        "osm_type": element.get("type"),
        "osm_id": element.get("id"),
        "all_tags": tags,
    }

    return {"type": "Feature", "geometry": geom, "properties": props}

def collect_features(raw_files: list[str], kind: str) -> list[dict]:
    seen = set()
    features = []

    for raw_file in raw_files:
        doc = json.loads(Path(raw_file).read_text(encoding="utf-8"))
        for element in doc.get("elements") or []:
            feat = element_to_feature(element, kind)
            if not feat:
                continue
            key = (feat["properties"].get("osm_type"), feat["properties"].get("osm_id"))
            if key in seen:
                continue
            seen.add(key)
            features.append(feat)

    return features

def load_features(layer_key: str, cfg: dict, features: list[dict]) -> int:
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

def run_job(job_name: str) -> int:
    if job_name not in JOBS:
        raise SystemExit(f"unknown job: {job_name}")

    cfg = JOBS[job_name]
    state = load_state(job_name)
    completed = set(state.get("completed_parts") or [])
    raw_files = list(state.get("raw_files") or [])

    for idx, query in enumerate(cfg["queries"], start=1):
        if idx in completed:
            print(f"[SKIP] {job_name} part={idx} already fetched")
            continue

        try:
            raw = fetch_query(job_name, query, idx)
            raw_files.append(str(raw))
            completed.add(idx)
            state["completed_parts"] = sorted(completed)
            state["raw_files"] = raw_files
            save_state(job_name, state)

        except Exception as exc:
            print(f"[FAIL] {job_name} part={idx}: {exc}")
            failed = state.get("failed_parts") or []
            if idx not in failed:
                failed.append(idx)
            state["failed_parts"] = sorted(failed)
            save_state(job_name, state)
            raise

    print(f"[LOAD] {job_name}")
    features = collect_features(raw_files, cfg["kind"])
    inserted = load_features(job_name, cfg, features)

    state["loaded_count"] = inserted
    state["completed_at"] = datetime.now().isoformat()
    save_state(job_name, state)

    print(f"[DONE] {job_name}: loaded={inserted}")
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
    print("[OK] cleared MVT cache")

def run_phase() -> None:
    print("[1/5] register layers")
    register_layers()

    print("[2/5] run stable OSM jobs")
    results = {}
    for job_name in JOBS:
        results[job_name] = run_job(job_name)

    print("[3/5] verify counts")
    counts = layer_counts()
    for job_name in JOBS:
        count = counts.get(job_name, 0)
        print(f"{job_name}: {count}")
        if count <= 0:
            raise SystemExit(f"[FAIL] {job_name} has zero rows")

    print("[4/5] clear tile cache")
    clear_tile_cache()

    print("[5/5] complete")
    print("[PHASE COMPLETE]")
    print("Stable OSM ingest completed. Restart the system if the UI is already open.")

def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage:")
        print("  python scripts/stable_osm_ingest_engine.py bavaria_coverage_repair")
        print("  python scripts/stable_osm_ingest_engine.py job <layer_key>")
        print("  python scripts/stable_osm_ingest_engine.py counts")
        return 1

    command = argv[1]

    if command == "bavaria_coverage_repair":
        run_phase()
        return 0

    if command == "job":
        if len(argv) != 3:
            print("Usage: python scripts/stable_osm_ingest_engine.py job <layer_key>")
            return 1
        register_layers()
        run_job(argv[2])
        clear_tile_cache()
        return 0

    if command == "counts":
        for layer, count in layer_counts().items():
            print(f"{layer}: {count}")
        return 0

    print(f"unknown command: {command}")
    return 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
'''

def main() -> None:
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(CODE, encoding="utf-8")
    print(f"[OK] wrote {TARGET}")
    print("[DONE] stable OSM ingest engine installed")

if __name__ == "__main__":
    main()