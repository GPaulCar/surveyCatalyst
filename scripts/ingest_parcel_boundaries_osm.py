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

LAYER_KEY = "parcel_boundaries"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Start with a smaller reliable test area around Upper Bavaria / Munich region.
# Expand later once confirmed working.
BBOX = (48.00, 11.00, 48.50, 11.80)  # south, west, north, east

RAW_DIR = ROOT / "workspace" / "downloads" / "raw" / "osm"
RAW_DIR.mkdir(parents=True, exist_ok=True)

QUERY = f"""
[out:json][timeout:180];
(
  way["landuse"~"farmland|meadow|grass|orchard|vineyard"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
);
out tags geom;
"""

def fetch_overpass() -> tuple[dict, Path]:
    from datetime import datetime

    data = urllib.parse.urlencode({"data": QUERY}).encode("utf-8")
    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "surveyCatalyst/phase3-auto-parcels"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    out = RAW_DIR / f"parcel_boundaries_osm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    return payload, out

def close_ring(coords: list[list[float]]) -> list[list[float]]:
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    return coords

def element_to_feature(element: dict) -> dict | None:
    tags = element.get("tags") or {}
    geom = element.get("geometry") or []
    if len(geom) < 3:
        return None

    coords = [[point["lon"], point["lat"]] for point in geom if "lon" in point and "lat" in point]
    if len(coords) < 3:
        return None

    coords = close_ring(coords)

    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [coords]},
        "properties": {
            "name": tags.get("name"),
            "landuse": tags.get("landuse"),
            "source": "osm_overpass_proxy",
            "osm_type": element.get("type"),
            "osm_id": element.get("id"),
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
            %s, %s, 'context', 'external_features', 'POLYGON',
            TRUE, FALSE, 1.0, 210,
            %s::jsonb
        )
        ON CONFLICT (layer_key) DO UPDATE
        SET layer_name = EXCLUDED.layer_name,
            layer_group = EXCLUDED.layer_group,
            source_table = EXCLUDED.source_table,
            geometry_type = EXCLUDED.geometry_type,
            metadata = EXCLUDED.metadata,
            sort_order = EXCLUDED.sort_order,
            updated_at = NOW()
        """,
        (
            LAYER_KEY,
            "Parcel boundaries (OSM proxy)",
            json.dumps({
                "subgroup": "legal_permission",
                "phase": "phase_3_1",
                "description": "OSM proxy parcel-like boundaries for workflow testing",
                "source_quality": "proxy_not_official_cadastral",
                "bbox_test": BBOX,
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
                props = feat["properties"]
                source_id = str(props.get("osm_id") or "")
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
                        json.dumps(feat["geometry"]),
                        json.dumps(props),
                        "osm_parcel_proxy",
                        source_id,
                    ),
                )
                inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted

def main() -> int:
    print("[INFO] downloading OSM parcel-like proxy features for test area")
    payload, saved = fetch_overpass()
    print(f"[INFO] raw download saved to {saved}")

    elements = payload.get("elements") or []
    features = []
    seen = set()

    for element in elements:
        feature = element_to_feature(element)
        if not feature:
            continue
        key = (feature["properties"].get("osm_type"), feature["properties"].get("osm_id"))
        if key in seen:
            continue
        seen.add(key)
        features.append(feature)

    inserted = load_features(features)
    print(f"[INFO] source elements: {len(elements)}")
    print(f"[DONE] loaded {inserted} parcel proxy features into layer '{LAYER_KEY}'")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())