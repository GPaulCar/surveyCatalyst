from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend
from data.ingestion.providers.blfd import BLfDProvider


LAYER_KEY = "legal_restricted_areas"


def ensure_registry(projected: int) -> None:
    metadata = {
        "source_key": "blfd",
        "subgroup": "legal_permission",
        "always_show": True,
        "severity_field": "legal_severity",
        "projected": projected,
        "description": (
            "Protected and restricted areas where metal detecting may be prohibited "
            "or require explicit permission. Verify current legal status before fieldwork."
        ),
    }
    conn = build_backend().connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO layers_registry (
                    layer_key, layer_name, layer_group, source_table, geometry_type,
                    is_user_selectable, is_visible, opacity, sort_order, metadata
                )
                VALUES (
                    %s, 'No Metal Detecting / Legal Restrictions', 'context', 'legal.restricted_areas',
                    'GEOMETRY', TRUE, TRUE, 0.72, 230, %s::jsonb
                )
                ON CONFLICT (layer_key) DO UPDATE
                SET layer_name = EXCLUDED.layer_name,
                    layer_group = EXCLUDED.layer_group,
                    source_table = EXCLUDED.source_table,
                    geometry_type = EXCLUDED.geometry_type,
                    is_user_selectable = TRUE,
                    is_visible = TRUE,
                    opacity = EXCLUDED.opacity,
                    sort_order = EXCLUDED.sort_order,
                    metadata = layers_registry.metadata || EXCLUDED.metadata,
                    updated_at = NOW()
                """,
                (LAYER_KEY, json.dumps(metadata)),
            )
        conn.commit()
    finally:
        conn.close()


def main() -> int:
    provider = BLfDProvider()
    provider.ensure_target_table()
    projected = provider.project_to_external_features()
    ensure_registry(projected)
    print(f"[DONE] restored {projected} features for '{LAYER_KEY}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
