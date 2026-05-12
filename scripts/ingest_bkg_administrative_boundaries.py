from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend


SOURCE_LAYER = "state_boundaries_de"
RAW_STATE_GLOB = "state_boundaries_de_*.json"
TARGET_LAYERS = {
    "bkg_vg250_boundaries": {
        "layer_name": "BKG VG250 boundaries",
        "sort_order": 32,
    },
    "bkg_vg25_boundaries": {
        "layer_name": "BKG VG25 boundaries",
        "sort_order": 34,
    },
}


def _state_bounds_features_from_raw() -> list[dict]:
    raw_dir = ROOT / "workspace" / "downloads" / "raw" / "osm"
    candidates = sorted(raw_dir.glob(RAW_STATE_GLOB))
    if not candidates:
        return []

    latest = candidates[-1]
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        return []

    features: list[dict] = []
    for element in payload.get("elements") or []:
        if element.get("type") != "relation":
            continue
        bounds = element.get("bounds") or {}
        minlat = bounds.get("minlat")
        minlon = bounds.get("minlon")
        maxlat = bounds.get("maxlat")
        maxlon = bounds.get("maxlon")
        if None in (minlat, minlon, maxlat, maxlon):
            continue
        geometry = {
            "type": "Polygon",
            "coordinates": [[
                [minlon, minlat],
                [maxlon, minlat],
                [maxlon, maxlat],
                [minlon, maxlat],
                [minlon, minlat],
            ]],
        }
        tags = element.get("tags") or {}
        features.append(
            {
                "geometry": geometry,
                "properties": {
                    "source": "osm_overpass_relation_bounds_proxy",
                    "source_layer": SOURCE_LAYER,
                    "osm_id": element.get("id"),
                    "state_id": tags.get("ISO3166-2"),
                    "name": tags.get("name"),
                    "admin_level": tags.get("admin_level"),
                    "bounds_proxy": True,
                },
            }
        )
    return features


def ensure_data_schema(cur) -> None:
    cur.execute("CREATE SCHEMA IF NOT EXISTS data_layers")
    for layer_key in TARGET_LAYERS:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS data_layers.{layer_key} (
                id SERIAL PRIMARY KEY,
                geom GEOMETRY,
                properties JSONB NOT NULL DEFAULT '{{}}'::jsonb
            )
            """
        )
        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{layer_key}_geom_gist
            ON data_layers.{layer_key}
            USING GIST (geom)
            """
        )


def ensure_registry(cur) -> None:
    for layer_key, spec in TARGET_LAYERS.items():
        cur.execute(
            """
            INSERT INTO layers_registry (
                layer_key, layer_name, layer_group, source_table, geometry_type,
                is_user_selectable, is_visible, opacity, sort_order, metadata
            )
            VALUES (
                %s, %s, 'context', %s, 'MULTIPOLYGON',
                TRUE, TRUE, 1.0, %s, %s::jsonb
            )
            ON CONFLICT (layer_key) DO UPDATE
            SET layer_name = EXCLUDED.layer_name,
                layer_group = EXCLUDED.layer_group,
                source_table = EXCLUDED.source_table,
                geometry_type = EXCLUDED.geometry_type,
                is_user_selectable = EXCLUDED.is_user_selectable,
                is_visible = EXCLUDED.is_visible,
                opacity = EXCLUDED.opacity,
                sort_order = EXCLUDED.sort_order,
                metadata = EXCLUDED.metadata,
                updated_at = NOW()
            """,
            (
                layer_key,
                spec["layer_name"],
                f"data_layers.{layer_key}",
                spec["sort_order"],
                json.dumps(
                    {
                        "category": "Administrative",
                        "subcategory": "Boundaries",
                        "subgroup": "boundaries",
                        "description": "BKG administrative boundary proxy seeded from Bavaria state boundaries until the official source is wired.",
                        "source_provider": "BKG",
                        "source_type": "WFS",
                        "endpoint_url": "https://sgx.geodatenzentrum.de/wfs_vg250",
                        "ingestion_method": "postgis",
                        "region_scope": "regional",
                        "always_show": True,
                        "proxy_source_layer": SOURCE_LAYER,
                    }
                ),
            ),
        )


def copy_source_features(cur, target_layer: str) -> int:
    cur.execute(f"DELETE FROM data_layers.{target_layer}")
    cur.execute(
        f"""
        INSERT INTO data_layers.{target_layer} (geom, properties)
        SELECT
            geom,
            jsonb_build_object(
                'registry_layer', %s,
                'proxy_source_layer', %s,
                'state_id', properties->>'state_id',
                'name', properties->>'name',
                'admin_level', properties->>'admin_level',
                'source', properties->>'source',
                'osm_id', properties->>'osm_id',
                'all_tags', properties->'all_tags'
            )
        FROM external_features
        WHERE layer = %s
          AND geom IS NOT NULL
        """,
        (target_layer, SOURCE_LAYER, SOURCE_LAYER),
    )
    return cur.rowcount


def load_proxy_bounds(cur, target_layer: str, features: list[dict]) -> int:
    cur.execute(f"DELETE FROM data_layers.{target_layer}")
    inserted = 0
    for feature in features:
        cur.execute(
            f"""
            INSERT INTO data_layers.{target_layer} (geom, properties)
            VALUES (
                ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326),
                %s::jsonb
            )
            """,
            (json.dumps(feature["geometry"]), json.dumps(feature["properties"])),
        )
        inserted += 1
    return inserted


def main() -> int:
    backend = build_backend()
    conn = backend.connect()
    loaded: dict[str, int] = {}
    try:
        with conn.cursor() as cur:
            ensure_data_schema(cur)
            ensure_registry(cur)
            cur.execute("SELECT COUNT(*) FROM external_features WHERE layer = %s", (SOURCE_LAYER,))
            source_count = int((cur.fetchone() or [0])[0] or 0)
            if source_count > 0:
                for layer_key in TARGET_LAYERS:
                    loaded[layer_key] = copy_source_features(cur, layer_key)
            else:
                fallback_features = _state_bounds_features_from_raw()
                if not fallback_features:
                    raise RuntimeError(
                        f"Source layer {SOURCE_LAYER} has no features and no raw state boundary fallback was found"
                    )
                for layer_key in TARGET_LAYERS:
                    loaded[layer_key] = load_proxy_bounds(cur, layer_key, fallback_features)
        conn.commit()
    finally:
        conn.close()

    print("[DONE] bkg administrative boundaries loaded " + " ".join(f"{k}={v}" for k, v in loaded.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
