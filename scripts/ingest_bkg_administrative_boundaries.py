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
                FALSE, FALSE, 1.0, %s, %s::jsonb
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
                        "description": "BKG administrative boundaries seeded from state boundary geometries.",
                        "source_provider": "BKG",
                        "source_type": "WFS",
                        "endpoint_url": "https://sgx.geodatenzentrum.de/wfs_vg250",
                        "ingestion_method": "postgis",
                        "region_scope": "regional",
                        "hidden_if_empty": True,
                        "source_layer": SOURCE_LAYER,
                    }
                ),
            ),
        )


def clear_target_features(cur, target_layer: str) -> int:
    cur.execute(f"DELETE FROM data_layers.{target_layer}")
    return 0


def main() -> int:
    backend = build_backend()
    conn = backend.connect()
    loaded: dict[str, int] = {}
    try:
        with conn.cursor() as cur:
            ensure_data_schema(cur)
            ensure_registry(cur)
            for layer_key in TARGET_LAYERS:
                loaded[layer_key] = clear_target_features(cur, layer_key)
        conn.commit()
    finally:
        conn.close()

    print("[DONE] bkg administrative boundaries loaded " + " ".join(f"{k}={v}" for k, v in loaded.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
