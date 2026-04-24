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
    "rivers_streams": {"kind": "line", "source_table": "osm_rivers_streams", "queries": []},
    "waterbodies": {"kind": "polygon", "source_table": "osm_waterbodies", "queries": []},
    "floodplains": {"kind": "polygon", "source_table": "osm_floodplains", "queries": []},
    "parcel_boundaries": {"kind": "polygon", "source_table": "osm_parcel_proxy", "queries": []},

    "field_names": {
        "kind": "point",
        "source_table": "osm_field_names",
        "queries": ["""
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  node["place"~"hamlet|isolated_dwelling|farm"](area.searchArea);
  node["landuse"="farmland"](area.searchArea);
);
out tags;
"""]
    },

    "geonames_points": {
        "kind": "point",
        "source_table": "osm_geonames",
        "queries": ["""
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  node["place"](area.searchArea);
  node["natural"~"peak|hill"](area.searchArea);
  node["tourism"](area.searchArea);
  node["historic"](area.searchArea);
);
out tags;
"""]
    },

    "old_creeks": {
        "kind": "line",
        "source_table": "osm_old_creeks",
        "queries": ["""
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  way["waterway"~"stream|ditch|drain"](area.searchArea);
);
out tags geom;
"""]
    },

    "old_channels": {
        "kind": "line",
        "source_table": "osm_old_channels",
        "queries": ["""
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  way["waterway"~"canal|ditch|drain"](area.searchArea);
);
out tags geom;
"""]
    },

    "wetland_history": {"kind": "polygon", "source_table": "osm_wetlands", "queries": []},
}

# Tile-based queries
for s, w, n, e in BAVARIA_TILES:
    bbox = f"{s},{w},{n},{e}"

    JOBS["rivers_streams"]["queries"].append(f"""
[out:json][timeout:300];
way["waterway"~"river|stream|ditch|canal|drain"]({bbox});
out tags geom;
""")

    JOBS["waterbodies"]["queries"].append(f"""
[out:json][timeout:300];
way["natural"="water"]({bbox});
out tags geom;
""")

    JOBS["floodplains"]["queries"].append(f"""
[out:json][timeout:300];
way["natural"="wetland"]({bbox});
out tags geom;
""")

    JOBS["wetland_history"]["queries"].append(f"""
[out:json][timeout:300];
way["natural"="wetland"]({bbox});
out tags geom;
""")

    JOBS["parcel_boundaries"]["queries"].append(f"""
[out:json][timeout:300];
way["landuse"]({bbox});
out tags geom;
""")

def fetch(query, job, part):
    payload = urllib.parse.urlencode({"data": query}).encode()
    for attempt in range(1, 7):
        endpoint = OVERPASS_ENDPOINTS[attempt % len(OVERPASS_ENDPOINTS)]
        wait = 5 * attempt + random.randint(0, 5)

        try:
            print(f"[FETCH] {job} part={part} attempt={attempt}")
            with urllib.request.urlopen(endpoint, payload, timeout=600) as r:
                data = json.loads(r.read().decode())

            path = RAW_DIR / f"{job}_{part}.json"
            path.write_text(json.dumps(data))
            time.sleep(2)
            return path

        except urllib.error.HTTPError as e:
            print(f"[WARN] HTTP {e.code}, retrying in {wait}s")
            time.sleep(wait)

    raise RuntimeError(f"{job} part {part} failed")

def parse_geom(el, kind):
    if kind == "point":
        if "lat" not in el:
            return None
        return {"type": "Point", "coordinates": [el["lon"], el["lat"]]}

    coords = [[p["lon"], p["lat"]] for p in el.get("geometry", [])]

    if kind == "line" and len(coords) >= 2:
        return {"type": "LineString", "coordinates": coords}

    if kind == "polygon" and len(coords) >= 3:
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        return {"type": "Polygon", "coordinates": [coords]}

    return None

def load(job, cfg, files):
    backend = build_backend()
    conn = backend.connect()
    count = 0

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM external_features WHERE layer=%s", (job,))

            seen = set()

            for f in files:
                data = json.loads(Path(f).read_text())
                for el in data.get("elements", []):
                    key = (el.get("type"), el.get("id"))
                    if key in seen:
                        continue
                    seen.add(key)

                    geom = parse_geom(el, cfg["kind"])
                    if not geom:
                        continue

                    props = el.get("tags", {})
                    cur.execute(
                        """
                        INSERT INTO external_features (layer, geom, properties)
                        VALUES (%s, ST_SetSRID(ST_GeomFromGeoJSON(%s),4326), %s::jsonb)
                        """,
                        (job, json.dumps(geom), json.dumps(props)),
                    )
                    count += 1

        conn.commit()
    finally:
        conn.close()

    return count

def run_job(job):
    cfg = JOBS[job]
    files = []

    for i, q in enumerate(cfg["queries"], 1):
        files.append(fetch(q, job, i))

    print(f"[LOAD] {job}")
    c = load(job, cfg, files)
    print(f"[DONE] {job}: {c}")
    return c

def run_all():
    for job in JOBS:
        run_job(job)

    print("[COMPLETE]")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "bavaria_coverage_repair":
        run_all()
    elif len(sys.argv) == 3 and sys.argv[1] == "job":
        run_job(sys.argv[2])
    else:
        print("usage:")
        print("  python stable_osm_ingest_engine.py bavaria_coverage_repair")
        print("  python stable_osm_ingest_engine.py job <layer>")