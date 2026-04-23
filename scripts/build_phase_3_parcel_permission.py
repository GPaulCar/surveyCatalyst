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
        "layer_key": "parcel_boundaries",
        "layer_name": "Parcel boundaries",
        "geometry_type": "POLYGON",
        "sort_order": 210,
        "metadata": {
            "subgroup": "legal_permission",
            "phase": "phase_3",
            "description": "Parcel boundary polygons for land identification and permission workflow"
        },
    },
    {
        "layer_key": "parcel_identifiers",
        "layer_name": "Parcel identifiers",
        "geometry_type": "POINT",
        "sort_order": 211,
        "metadata": {
            "subgroup": "legal_permission",
            "phase": "phase_3",
            "description": "Parcel identifier reference points or centroids"
        },
    },
    {
        "layer_key": "protection_buffers",
        "layer_name": "Protection buffers",
        "geometry_type": "POLYGON",
        "sort_order": 212,
        "metadata": {
            "subgroup": "legal_permission",
            "phase": "phase_3",
            "description": "Protection and legal buffer areas"
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
            "description": "Field-name polygons or parcel naming references"
        },
    },
    {
        "layer_key": "land_access_routes",
        "layer_name": "Land access routes",
        "geometry_type": "LINESTRING",
        "sort_order": 214,
        "metadata": {
            "subgroup": "legal_permission",
            "phase": "phase_3",
            "description": "Rights of way, access routes, or permission access references"
        },
    },
]

def ensure_workspace() -> None:
    for rel in [
        "workspace/permissions",
        "workspace/permissions/requests",
        "workspace/permissions/reference_exports",
        "workspace/downloads/curated/parcels",
        "workspace/downloads/curated/legal",
    ]:
        (ROOT / rel).mkdir(parents=True, exist_ok=True)

def main() -> int:
    ensure_workspace()
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
                        layer_group = EXCLUDED.layer_group,
                        source_table = EXCLUDED.source_table,
                        geometry_type = EXCLUDED.geometry_type,
                        metadata = EXCLUDED.metadata,
                        sort_order = EXCLUDED.sort_order,
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

    print("[DONE] phase 3 parcel / permission foundation registered")
    for spec in LAYER_SPECS:
        print(f"[INFO] registered {spec['layer_key']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
