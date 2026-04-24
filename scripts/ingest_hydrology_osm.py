from __future__ import annotations

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

# Bavaria-ish overall area
FULL_BBOX = (47.20, 8.95, 50.65, 13.95)  # south, west, north, east

LAYER_CONFIG = {
    "rivers_streams": {
        "source_table": "osm_hydrology_rivers_streams",
        "kind": "line",
        "queries": [
            f"""
[out:json][timeout:300];
(
  way["waterway"~"river|stream|ditch|canal|drain"]({FULL_BBOX[0]},{FULL_BBOX[1]},{FULL_BBOX[2]},{FULL_BBOX[3]});
);
out tags geom;
"""
        ],
    },
    "waterbodies": {
        "source_table": "osm_hydrology_waterbodies",
        "kind": "polygon",
        "queries": [
            f"""
[out:json][timeout:300];
(
  way["natural"="water"]({FULL_BBOX[0]},{FULL_BBOX[1]},{FULL_BBOX[2]},{FULL_BBOX[3]});
  way["water"]({FULL_BBOX[0]},{FULL_BBOX[1]},{FULL_BBOX[2]},{FULL_BBOX[3]});
);
out tags geom;
"""
        ],
    },
    "floodplains": {
        "source_table": "osm_hydrology_floodplains",
        "kind": "polygon",
        # Split into smaller tiles to avoid 504s
        "queries": [
            """
[out:json][timeout:300];
(
  way["natural"="wetland"](47.20,8.95,48.40,10.60);
  way["wetland"](47.20,8.95,48.40,10.60);
);
out tags geom;
""",
            """
[out:json][timeout:300];
(
  way["natural"="wetland"](47.20,10.60,48.40,12.30);
  way["wetland"](47.20,10.60,48.40,12.30);
);
out tags geom;
""",
            """
[out:json][timeout:300];
(
  way["natural"="wetland"](47.20,12.30,48.40,13.95);
  way["wetland"](47.20,12.30,48.40,13.95);
);
out tags geom;
""",
            """
[out:json][timeout:300];
(
  way["natural"="wetland"](48.40,8.95,49.50,10.60);
  way["wetland"](48.40,8.95,49.50,10.60);
);
out tags geom;
""",
            """
[out:json][timeout:300];
(
  way["natural"="wetland"](48.40,10.60,49.50,12.30);
  way["wetland"](48.40,10.60,49.50,12.30);
);
out tags geom;
""",
            """
[out:json][timeout:300];
(
  way["natural"="wetland"](48.40,12.30,49.50,13.95);
  way["wetland"](48.40,12.30,49.50,13.95);
);
out tags geom;
""",
            """
[out:json][timeout:300];
(
  way["natural"="wetland"](49.50,8.95,50.65,10.60);
  way["wetland"](49.50,8.95,50.65,10.60);
);
out tags geom;
""",
            """
[out:json][timeout:300];
(
  way["natural"="wetland"](49.50,10.60,50.65,12.30);
  way["wetland"](49.50,10.60,50.65,12.30);
);
out tags geom;
""",
            """
[out:json][timeout:300];
(
  way["natural"="wetland"](49.50,12.30,50.65,13.95);
  way["wetland"](49.50,12.30,50.65,13.95);
);
out tags geom;
""",
        ],
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

def fetch(query: str, name: str, part: int | None = None) -> tuple[dict, Path]:
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "surveyCatalyst/hydrology-pipeline"},
        method="POST",
    )

    last_error = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            suffix = f"_part{part}" if part is not None else ""
            out = RAW_DIR / f"{name}{suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            out.write_text(json.dumps(payload), encoding="utf-8")
            return payload, out
        except Exception as exc:
            last_error = exc
            print(f"[WARN] {name}{f' part {part}' if part is not None else ''} attempt {attempt} failed: {exc}")
            if attempt < 3:
                time.sleep(3 * attempt)

    raise last_error  # type: ignore[misc]

def close_ring(coords: list[list[float]]) -> list[list[float]]:
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

def ingest_layer(layer_key: str, cfg: dict) -> None:
    current = layer_count(layer_key)
    if current > 0:
        print(f"[SKIP] {layer_key}: already loaded ({current})")
        return

    all_elements: list[dict] = []
    saved_files: list[Path] = []

    queries = cfg["queries"]
    for idx, query in enumerate(queries, start=1):
        part = idx if len(queries) > 1 else None
        print(f"[INFO] downloading {layer_key}{f' part {idx}/{len(queries)}' if part is not None else ''}")
        payload, saved = fetch(query, layer_key, part=part)
        saved_files.append(saved)
        print(f"[INFO] raw saved to {saved}")
        all_elements.extend(payload.get("elements") or [])

    seen = set()
    features = []
    for element in all_elements:
        feature = element_to_feature(element, cfg["kind"])
        if not feature:
            continue
        key = (feature["properties"].get("osm_type"), feature["properties"].get("osm_id"))
        if key in seen:
            continue
        seen.add(key)
        features.append(feature)

    inserted = load_features(layer_key, cfg["source_table"], cfg["kind"], features)
    print(f"[DONE] {layer_key}: source={len(all_elements)} loaded={inserted}")

def main() -> int:
    for layer_key, cfg in LAYER_CONFIG.items():
        ingest_layer(layer_key, cfg)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())