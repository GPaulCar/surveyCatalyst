from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BAVARIA_BBOX = (47.20, 8.95, 50.65, 13.95)
LAYER_KEY = "roman_roads_osm"

RAW_OUTPUT_DIR = ROOT / "workspace" / "downloads" / "raw" / "osm"
RAW_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


QUERY = f"""
[out:json][timeout:180];
(
  way["historic"="road"]({BAVARIA_BBOX[0]},{BAVARIA_BBOX[1]},{BAVARIA_BBOX[2]},{BAVARIA_BBOX[3]});
  relation["historic"="road"]({BAVARIA_BBOX[0]},{BAVARIA_BBOX[1]},{BAVARIA_BBOX[2]},{BAVARIA_BBOX[3]});
  way["name"~"Romer|Römer|Roman",i]({BAVARIA_BBOX[0]},{BAVARIA_BBOX[1]},{BAVARIA_BBOX[2]},{BAVARIA_BBOX[3]});
);
out tags geom;
"""

def fetch_overpass() -> dict:
    from datetime import datetime
    data = urllib.parse.urlencode({"data": QUERY}).encode("utf-8")
    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "surveyCatalyst/phase2-dual-roman-roads"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_file = RAW_OUTPUT_DIR / f"roman_roads_osm_{stamp}.json"
    raw_file.write_text(json.dumps(payload), encoding="utf-8")
    return payload

def element_to_geojson(element: dict) -> dict | None:
    geom = element.get("geometry") or []
    if len(geom) < 2:
        return None
    coords = [[point["lon"], point["lat"]] for point in geom if "lon" in point and "lat" in point]
    if len(coords) < 2:
        return None
    tags = element.get("tags") or {}
    name_blob = " ".join(str(v) for v in tags.values())
    historic = str(tags.get("historic", "")).lower()
    confidence = "candidate"
    if "roman" in name_blob.lower() or "römer" in name_blob.lower() or "romer" in name_blob.lower():
        confidence = "named"
    if historic == "road":
        confidence = "historic_road"
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coords},
        "properties": {
            "osm_type": element.get("type"),
            "osm_id": element.get("id"),
            "source": "osm_overpass",
            "name": tags.get("name"),
            "historic": tags.get("historic"),
            "highway": tags.get("highway"),
            "ref": tags.get("ref"),
            "confidence": confidence,
            "all_tags": tags,
        },
    }

def ensure_registry(cur) -> None:
    cur.execute(
        """
        INSERT INTO layers_registry (
            layer_key, layer_name, layer_group, source_table, geometry_type,
            is_user_selectable, is_visible, opacity, sort_order, metadata
        )
        VALUES (
            %s, %s, 'context', 'external_features', 'LINESTRING',
            TRUE, FALSE, 1.0, 120,
            %s::jsonb
        )
        ON CONFLICT (layer_key) DO UPDATE
        SET layer_name = EXCLUDED.layer_name,
            layer_group = EXCLUDED.layer_group,
            source_table = EXCLUDED.source_table,
            geometry_type = EXCLUDED.geometry_type,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
        """,
        (
            LAYER_KEY,
            "Roman roads (OSM)",
            json.dumps({
                "subgroup": "historical",
                "phase": "phase_2",
                "description": "OSM baseline Roman-road candidates for Bavaria",
            }),
        ),
    )

def load_features(features: list[dict]) -> int:
    backend = build_backend()
    conn = backend.connect()
    inserted = 0
    try:
        with conn.cursor() as cur:
            ensure_registry(cur)
            cur.execute("DELETE FROM external_features WHERE layer = %s", (LAYER_KEY,))
            for feat in features:
                geometry = feat["geometry"]
                properties = feat["properties"]
                source_id = str(properties.get("osm_id") or "")
                cur.execute(
                    """
                    INSERT INTO external_features (layer, geom, properties, source_table, source_id)
                    VALUES (
                        %s,
                        ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326),
                        %s::jsonb,
                        %s,
                        %s
                    )
                    """,
                    (
                        LAYER_KEY,
                        json.dumps(geometry),
                        json.dumps(properties),
                        "osm_overpass",
                        source_id,
                    ),
                )
                inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted

def main() -> None:
    print("[INFO] downloading OSM Roman-road candidates for Bavaria")
    raw = fetch_overpass()
    elements = raw.get("elements") or []
    seen = set()
    features = []
    for element in elements:
        feature = element_to_geojson(element)
        if not feature:
            continue
        key = (feature["properties"].get("osm_type"), feature["properties"].get("osm_id"))
        if key in seen:
            continue
        seen.add(key)
        features.append(feature)
    count = load_features(features)
    print(f"[DONE] loaded {count} OSM Roman-road features into layer '{LAYER_KEY}'")

if __name__ == "__main__":
    main()
