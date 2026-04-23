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
        "sort_order": 310,
        "metadata": {
            "subgroup": "historic_water",
            "phase": "phase_4",
            "description": "Historic or inferred creeks",
        },
    },
    {
        "layer_key": "old_channels",
        "layer_name": "Old channels",
        "geometry_type": "LINESTRING",
        "sort_order": 311,
        "metadata": {
            "subgroup": "historic_water",
            "phase": "phase_4",
            "description": "Historic or inferred river channels",
        },
    },
    {
        "layer_key": "wetland_history",
        "layer_name": "Wetland history",
        "geometry_type": "POLYGON",
        "sort_order": 312,
        "metadata": {
            "subgroup": "historic_water",
            "phase": "phase_4",
            "description": "Historic wetland, marsh, or damp ground areas",
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

    print("[DONE] historic water layers registered")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
