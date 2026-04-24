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
        "layer_key": "rivers_streams",
        "layer_name": "Rivers and streams",
        "geometry_type": "LINESTRING",
        "sort_order": 300,
        "metadata": {
            "subgroup": "hydrology",
            "phase": "hardening_bundle",
            "description": "Current rivers, streams, canals, drains"
        }
    },
    {
        "layer_key": "waterbodies",
        "layer_name": "Waterbodies",
        "geometry_type": "POLYGON",
        "sort_order": 301,
        "metadata": {
            "subgroup": "hydrology",
            "phase": "hardening_bundle",
            "description": "Current lakes, ponds, water polygons"
        }
    },
    {
        "layer_key": "floodplains",
        "layer_name": "Floodplains",
        "geometry_type": "POLYGON",
        "sort_order": 302,
        "metadata": {
            "subgroup": "hydrology",
            "phase": "hardening_bundle",
            "description": "Wetland/floodplain proxy polygons"
        }
    },
    {
        "layer_key": "protection_buffers",
        "layer_name": "Protection buffers",
        "geometry_type": "POLYGON",
        "sort_order": 212,
        "metadata": {
            "subgroup": "legal_permission",
            "phase": "hardening_bundle",
            "description": "Protection and legal buffer polygons"
        }
    }
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
    print("[DONE] hydrology + protection layers registered")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
