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
        "layer_key": "protection_buffers",
        "layer_name": "Protection buffers",
        "geometry_type": "POLYGON",
        "sort_order": 212,
        "metadata": {
            "subgroup": "legal_permission",
            "phase": "phase_3",
            "description": "Structured protection and legal buffer polygons",
        },
    },
    {
        "layer_key": "field_names",
        "layer_name": "Field names",
        "geometry_type": "POLYGON",
        "sort_order": 213,
        "metadata": {
            "subgroup": "legal_permission",
            "phase": "phase_3",
            "description": "Structured field-name polygons or references",
        },
    },
    {
        "layer_key": "geonames_points",
        "layer_name": "GeoNames points",
        "geometry_type": "POINT",
        "sort_order": 320,
        "metadata": {
            "subgroup": "enrichment",
            "phase": "phase_5",
            "description": "GeoNames or place-name reference points",
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

    print("[DONE] legal + enrichment layers registered")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
