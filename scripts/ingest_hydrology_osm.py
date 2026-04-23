from __future__ import annotations

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
BBOX = (47.20, 8.95, 50.65, 13.95)  # south, west, north, east

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
        "geometry_type": "LINESTRING",
        "source_table": "osm_hydrology_rivers_streams",
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
        "geometry_type": "POLYGON",
        "source_table": "osm_hydrology_waterbodies",
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
        "geometry_type": "POLYGON",
        "source_table": "osm_hydrology_floodplains",
    },
}

def fetch_overpass(query: str, name: str) -> tuple[dict, Path]:
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "surveyCatalyst/auto-hydro-ingest"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    out = RAW_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    return payload, out

def close_ring(coords: list[list[float]]) -> list[list[float]]:
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords

def element_to_feature(element: dict, layer_key: str) -> dict | None:
    tags = element.get("tags") or {}
    geom = element.get("geometry") or []
    if len(geom) < 2:
        return None

    coords = [[point["lon"], point["lat"]] for point in geom if "lon" in point and "lat" in point]
    if layer_key in {"waterbodies", "floodplains"}:
        if len(coords) < 3:
            return None
        coords = close_ring(coords)
        geometry = {"type": "Polygon", "coordinates": [coords]}
    else:
        if len(coords) < 2:
            return None
        geometry = {"type": "LineString", "coordinates": coords}

    properties = {
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
    return {"type": "Feature", "geometry": geometry, "properties": properties}

def load_features(layer_key: str, source_table: str, features: list[dict]) -> int:
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
                if layer_key in {"waterbodies", "floodplains"}:
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
    summary = []
    for layer_key, cfg in LAYER_CONFIG.items():
        print(f"[INFO] downloading {layer_key}")
        payload, saved = fetch_overpass(cfg["query"], layer_key)
        print(f"[INFO] raw saved to {saved}")
        elements = payload.get("elements") or []
        features = []
        seen = set()
        for element in elements:
            feature = element_to_feature(element, layer_key)
            if not feature:
                continue
            key = (feature["properties"].get("osm_type"), feature["properties"].get("osm_id"))
            if key in seen:
                continue
            seen.add(key)
            features.append(feature)

        inserted = load_features(layer_key, cfg["source_table"], features)
        summary.append((layer_key, len(elements), inserted))
        print(f"[DONE] {layer_key}: source={len(elements)} loaded={inserted}")

    print("[SUMMARY]")
    for layer_key, source_count, inserted in summary:
        print(f"  {layer_key}: source={source_count} loaded={inserted}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
