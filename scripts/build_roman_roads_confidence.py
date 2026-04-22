from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

LAYER_KEY = "roman_roads_confidence"

SQL = r"""
WITH
curated AS (
    SELECT id, geom, properties
    FROM external_features
    WHERE layer = 'roman_roads_curated'
),
osm AS (
    SELECT id, geom, properties
    FROM external_features
    WHERE layer = 'roman_roads_osm'
),
paired_curated AS (
    SELECT DISTINCT c.id
    FROM curated c
    JOIN osm o
      ON ST_DWithin(c.geom::geography, o.geom::geography, 50.0)
),
paired_osm AS (
    SELECT DISTINCT o.id
    FROM osm o
    JOIN curated c
      ON ST_DWithin(c.geom::geography, o.geom::geography, 50.0)
),
confidence_rows AS (
    SELECT
        c.geom,
        jsonb_build_object(
            'confidence_case', 'both_overlap',
            'confidence_rank', 3,
            'label', 'Roman roads (both sources)',
            'source_a', 'roman_roads_curated',
            'source_b', 'roman_roads_osm',
            'source_properties', c.properties
        ) AS properties,
        'derived_roman_roads_confidence'::text AS source_table,
        ('curated_' || c.id::text) AS source_id
    FROM curated c
    WHERE c.id IN (SELECT id FROM paired_curated)

    UNION ALL

    SELECT
        c.geom,
        jsonb_build_object(
            'confidence_case', 'curated_only',
            'confidence_rank', 2,
            'label', 'Roman roads (curated only)',
            'source_a', 'roman_roads_curated',
            'source_properties', c.properties
        ) AS properties,
        'derived_roman_roads_confidence'::text AS source_table,
        ('curated_' || c.id::text) AS source_id
    FROM curated c
    WHERE c.id NOT IN (SELECT id FROM paired_curated)

    UNION ALL

    SELECT
        o.geom,
        jsonb_build_object(
            'confidence_case', 'osm_only',
            'confidence_rank', 1,
            'label', 'Roman roads (OSM only)',
            'source_a', 'roman_roads_osm',
            'source_properties', o.properties
        ) AS properties,
        'derived_roman_roads_confidence'::text AS source_table,
        ('osm_' || o.id::text) AS source_id
    FROM osm o
    WHERE o.id NOT IN (SELECT id FROM paired_osm)
)
INSERT INTO external_features (layer, geom, properties, source_table, source_id)
SELECT
    %s,
    geom,
    properties,
    source_table,
    source_id
FROM confidence_rows;
"""

def ensure_registry(cur) -> None:
    cur.execute(
        """
        INSERT INTO layers_registry (
            layer_key, layer_name, layer_group, source_table, geometry_type,
            is_user_selectable, is_visible, opacity, sort_order, metadata
        )
        VALUES (
            %s, %s, 'context', 'external_features', 'LINESTRING',
            TRUE, FALSE, 1.0, 122,
            %s::jsonb
        )
        ON CONFLICT (layer_key) DO UPDATE
        SET layer_name = EXCLUDED.layer_name,
            layer_group = EXCLUDED.layer_group,
            source_table = EXCLUDED.source_table,
            geometry_type = EXCLUDED.geometry_type,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
        """,
        (
            LAYER_KEY,
            "Roman roads (confidence)",
            json.dumps({
                "subgroup": "historical",
                "phase": "phase_2_5",
                "description": "Derived Roman roads confidence layer comparing curated and OSM sources",
                "legend": {
                    "both_overlap": "very strong",
                    "curated_only": "strong",
                    "osm_only": "candidate"
                }
            }),
        ),
    )

def main() -> int:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            ensure_registry(cur)
            cur.execute("DELETE FROM external_features WHERE layer = %s", (LAYER_KEY,))
            cur.execute(SQL, (LAYER_KEY,))
            cur.execute(
                """
                SELECT
                    properties->>'confidence_case' AS bucket,
                    COUNT(*)
                FROM external_features
                WHERE layer = %s
                GROUP BY bucket
                ORDER BY bucket
                """,
                (LAYER_KEY,),
            )
            rows = cur.fetchall()
        conn.commit()
    finally:
        conn.close()

    print("[DONE] rebuilt Roman roads confidence layer")
    if not rows:
        print("[INFO] no confidence features were created")
    else:
        for bucket, count in rows:
            print(f"[INFO] {bucket}: {count}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
