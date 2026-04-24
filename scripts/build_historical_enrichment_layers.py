from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

LAYER_SPECS = [
    {
        "layer_key": "old_creeks",
        "layer_name": "Old creeks",
        "geometry_type": "LINESTRING",
        "sort_order": 330,
        "metadata": {
            "subgroup": "historical_water",
            "description": "Historic or inferred creek and stream channels"
        },
    },
    {
        "layer_key": "old_channels",
        "layer_name": "Old channels",
        "geometry_type": "LINESTRING",
        "sort_order": 331,
        "metadata": {
            "subgroup": "historical_water",
            "description": "Historic, abandoned, intermittent, or canalised water channels"
        },
    },
    {
        "layer_key": "wetland_history",
        "layer_name": "Wetland history",
        "geometry_type": "POLYGON",
        "sort_order": 332,
        "metadata": {
            "subgroup": "historical_water",
            "description": "Historic wetland / marsh / damp-ground proxy areas"
        },
    },
    {
        "layer_key": "field_names",
        "layer_name": "Field names",
        "geometry_type": "POINT",
        "sort_order": 340,
        "metadata": {
            "subgroup": "place_names",
            "description": "OSM locality, field-name, hamlet, farm and named-place proxy layer"
        },
    },
    {
        "layer_key": "geonames_points",
        "layer_name": "GeoNames / place points",
        "geometry_type": "POINT",
        "sort_order": 341,
        "metadata": {
            "subgroup": "place_names",
            "description": "Place-name enrichment points from open sources"
        },
    },
]

def main() -> int:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            for spec in LAYER_SPECS:
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
                        spec["layer_key"],
                        spec["layer_name"],
                        spec["geometry_type"],
                        spec["sort_order"],
                        json.dumps(spec["metadata"]),
                    ),
                )
        conn.commit()
    finally:
        conn.close()

    print("[DONE] historical + enrichment layers registered")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
