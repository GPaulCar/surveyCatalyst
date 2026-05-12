from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend
import psycopg

LAYER_KEY = "parcel_boundaries"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Bavaria extent: south, west, north, east
BAVARIA_BBOX = (47.20, 8.95, 50.65, 13.95)

RAW_DIR = ROOT / "workspace" / "downloads" / "raw" / "osm"
RAW_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = RAW_DIR / "parcel_boundaries_osm_bavaria_state.json"

def bbox_tiles(bbox: tuple[float, float, float, float], lat_step: float = 0.5, lon_step: float = 0.5) -> list[tuple[float, float, float, float]]:
    min_lat, min_lon, max_lat, max_lon = bbox
    tiles: list[tuple[float, float, float, float]] = []
    lat = min_lat
    while lat < max_lat:
        next_lat = min(lat + lat_step, max_lat)
        lon = min_lon
        while lon < max_lon:
            next_lon = min(lon + lon_step, max_lon)
            tiles.append((lat, lon, next_lat, next_lon))
            lon = next_lon
        lat = next_lat
    return tiles


def overpass_query(bbox: tuple[float, float, float, float]) -> str:
    south, west, north, east = bbox
    return f"""
[out:json][timeout:240];
(
  way["landuse"~"farmland|meadow|grass|orchard|vineyard"]({south},{west},{north},{east});
);
out tags geom;
"""


def fetch_overpass_tile(bbox: tuple[float, float, float, float], retries: int = 7, base_delay: float = 3.0) -> tuple[dict, Path]:
    from datetime import datetime

    data = urllib.parse.urlencode({"data": overpass_query(bbox)}).encode("utf-8")
    req = urllib.request.Request(
        OVERPASS_URL,
        data=data,
        headers={"User-Agent": "surveyCatalyst/phase3-auto-parcels"},
        method="POST",
    )
    payload = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            status = getattr(exc, "code", None)
            retryable = status in (429, 500, 502, 503, 504)
            if attempt >= retries or not retryable:
                raise
            retry_after = 0.0
            header = exc.headers.get("Retry-After") if getattr(exc, "headers", None) else None
            if header:
                try:
                    retry_after = float(header)
                except ValueError:
                    retry_after = 0.0
            delay = max(retry_after, base_delay * (2 ** (attempt - 1)))
            print(f"[RETRY] overpass tile={bbox} status={status} attempt={attempt}/{retries} delay={delay:.1f}s", flush=True)
            time.sleep(delay)
        except urllib.error.URLError:
            if attempt >= retries:
                raise
            delay = base_delay * (2 ** (attempt - 1))
            print(f"[RETRY] overpass tile={bbox} network attempt={attempt}/{retries} delay={delay:.1f}s", flush=True)
            time.sleep(delay)
    if payload is None:
        raise RuntimeError(f"failed to fetch overpass tile after retries: {bbox}")

    south, west, north, east = bbox
    tile_tag = f"{south:.2f}_{west:.2f}_{north:.2f}_{east:.2f}".replace(".", "p")
    out = RAW_DIR / f"parcel_boundaries_osm_{tile_tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    return payload, out


def tile_tag_for_bbox(bbox: tuple[float, float, float, float]) -> str:
    south, west, north, east = bbox
    return f"{south:.2f}_{west:.2f}_{north:.2f}_{east:.2f}".replace(".", "p")


def load_cached_tile_elements(tile_tag: str) -> list[dict]:
    candidates = sorted(RAW_DIR.glob(f"parcel_boundaries_osm_{tile_tag}_*.json"))
    if not candidates:
        return []
    latest = candidates[-1]
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        return []
    return payload.get("elements") or []

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
            "Parcel boundaries (Bavaria)",
            json.dumps({
                "subgroup": "legal_permission",
                "phase": "phase_3_1",
                "description": "OSM parcel-like boundary proxy coverage for Bavaria",
                "source_quality": "proxy_not_official_cadastral",
                "coverage_bbox": BAVARIA_BBOX,
            }),
        ),
    )

def load_features(features: list[dict]) -> int:
    backend = build_backend()
    conn = backend.connect()
    inserted = 0
    skipped_invalid = 0
    try:
        with conn.cursor() as cur:
            ensure_registry(cur)
            cur.execute("DELETE FROM external_features WHERE layer = %s", (LAYER_KEY,))
            cur.execute(
                """
                SELECT ST_UnaryUnion(ST_Collect(geom))
                FROM external_features
                WHERE layer = 'state_boundaries_de'
                  AND (
                    (properties->>'state_id') = 'de_by'
                    OR lower(coalesce(properties->>'name','')) LIKE '%bayern%'
                    OR lower(coalesce(properties->>'name','')) LIKE '%bavaria%'
                  )
                """
            )
            bavaria_geom = cur.fetchone()[0]
            if not bavaria_geom:
                print("[WARN] Bavaria boundary geometry missing; falling back to Bavaria bbox clip.", flush=True)
                cur.execute(
                    """
                    SELECT ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                    """,
                    (BAVARIA_BBOX[1], BAVARIA_BBOX[0], BAVARIA_BBOX[3], BAVARIA_BBOX[2]),
                )
                bavaria_geom = cur.fetchone()[0]
            print(f"[INFO] loading {len(features)} parcel boundary features into PostGIS", flush=True)
            for index, feat in enumerate(features, start=1):
                props = feat["properties"]
                source_id = str(props.get("osm_id") or "")
                try:
                    cur.execute(
                        """
                        WITH src AS (
                          SELECT ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)) AS g
                        ),
                        bayern AS (
                          SELECT ST_MakeValid(%s::geometry) AS g
                        ),
                        clipped AS (
                          SELECT ST_CollectionExtract(
                                   ST_MakeValid(
                                     ST_Intersection(
                                       ST_Buffer(src.g, 0),
                                       ST_Buffer(bayern.g, 0)
                                     )
                                   ),
                                   3
                                 ) AS g
                          FROM src
                          CROSS JOIN bayern
                          WHERE ST_Intersects(src.g, bayern.g)
                        )
                        INSERT INTO external_features (layer, geom, properties, source_table, source_id)
                        SELECT
                          %s,
                          ST_Multi(ST_Force2D(g)),
                          %s::jsonb,
                          %s,
                          %s
                        FROM clipped
                        WHERE g IS NOT NULL AND NOT ST_IsEmpty(g)
                        """,
                        (
                            json.dumps(feat["geometry"]),
                            bavaria_geom,
                            LAYER_KEY,
                            json.dumps(props),
                            "osm_parcel_proxy",
                            source_id,
                        ),
                    )
                    inserted += cur.rowcount
                except psycopg.Error:
                    skipped_invalid += 1
                    continue
                if inserted % 1000 == 0:
                    print(f"[LOAD] {LAYER_KEY}: inserted {inserted}/{len(features)}", flush=True)
        conn.commit()
    finally:
        conn.close()
    if skipped_invalid:
        print(f"[WARN] skipped invalid geometries: {skipped_invalid}", flush=True)
    return inserted

def main() -> int:
    tiles = bbox_tiles(BAVARIA_BBOX, lat_step=0.5, lon_step=0.5)
    print(f"[INFO] downloading OSM parcel-like boundary data for Bavaria ({len(tiles)} tiles)")
    state = {"completed_tiles": []}
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            state = {"completed_tiles": []}
    completed = set(state.get("completed_tiles") or [])
    elements: list[dict] = []
    for idx, tile in enumerate(tiles, start=1):
      tile_key = ",".join(f"{value:.5f}" for value in tile)
      tile_tag = tile_tag_for_bbox(tile)
      if tile_key in completed:
          cached = load_cached_tile_elements(tile_tag)
          elements.extend(cached)
          print(f"[SKIP] tile {idx}/{len(tiles)} already completed: {tile}", flush=True)
          print(f"[INFO] cached tile elements: {len(cached)} (running total: {len(elements)})", flush=True)
          continue
      print(f"[FETCH] tile {idx}/{len(tiles)}: {tile}", flush=True)
      payload, saved = fetch_overpass_tile(tile)
      print(f"[INFO] raw download saved to {saved}")
      chunk = payload.get("elements") or []
      elements.extend(chunk)
      completed.add(tile_key)
      STATE_FILE.write_text(json.dumps({"completed_tiles": sorted(completed)}, indent=2), encoding="utf-8")
      print(f"[INFO] tile elements: {len(chunk)} (running total: {len(elements)})", flush=True)

    print(f"[INFO] source elements total: {len(elements)}", flush=True)
    features = []
    seen = set()

    for index, element in enumerate(elements, start=1):
        feature = element_to_feature(element)
        if not feature:
            continue
        key = (feature["properties"].get("osm_type"), feature["properties"].get("osm_id"))
        if key in seen:
            continue
        seen.add(key)
        features.append(feature)
        if index % 10000 == 0:
            print(f"[PARSE] {LAYER_KEY}: scanned {index}/{len(elements)} elements, features={len(features)}", flush=True)

    print(f"[INFO] parsed parcel boundary features: {len(features)}", flush=True)
    inserted = load_features(features)
    print(f"[DONE] loaded {inserted} parcel boundary features into layer '{LAYER_KEY}'")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
