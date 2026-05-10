from __future__ import annotations

import json
import sys
import time
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
    FROM tmp_roman_roads_curated
),
osm AS (
    SELECT id, geom, properties
    FROM tmp_roman_roads_osm
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
    WHERE EXISTS (
        SELECT 1
        FROM tmp_roman_roads_paired_curated pc
        WHERE pc.id = c.id
    )

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
    WHERE NOT EXISTS (
        SELECT 1
        FROM tmp_roman_roads_paired_curated pc
        WHERE pc.id = c.id
    )

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
    WHERE NOT EXISTS (
        SELECT 1
        FROM tmp_roman_roads_paired_osm po
        WHERE po.id = o.id
    )
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

def prepare_work_tables(cur) -> tuple[int, int]:
    print("[INFO] preparing projected Roman roads work tables", flush=True)
    cur.execute("DROP TABLE IF EXISTS tmp_roman_roads_curated")
    cur.execute("DROP TABLE IF EXISTS tmp_roman_roads_osm")
    cur.execute(
        """
        CREATE TEMP TABLE tmp_roman_roads_curated ON COMMIT DROP AS
        WITH normalized AS (
            SELECT
                id,
                CASE
                    WHEN ST_XMin(geom) < -180
                      OR ST_XMax(geom) > 180
                      OR ST_YMin(geom) < -90
                      OR ST_YMax(geom) > 90
                    THEN ST_Transform(ST_SetSRID(geom, 3857), 4326)
                    ELSE geom
                END AS geom,
                properties
            FROM external_features
            WHERE layer = 'roman_roads_curated'
              AND geom IS NOT NULL
        )
        SELECT
            id,
            geom,
            ST_Transform(geom, 25832) AS geom_m,
            properties
        FROM normalized
        WHERE ST_XMin(geom) >= -180
          AND ST_XMax(geom) <= 180
          AND ST_YMin(geom) >= -90
          AND ST_YMax(geom) <= 90
        """
    )
    cur.execute(
        """
        CREATE TEMP TABLE tmp_roman_roads_osm ON COMMIT DROP AS
        SELECT
            id,
            geom,
            ST_Transform(geom, 25832) AS geom_m,
            properties
        FROM external_features
        WHERE layer = 'roman_roads_osm'
          AND geom IS NOT NULL
          AND ST_XMin(geom) >= -180
          AND ST_XMax(geom) <= 180
          AND ST_YMin(geom) >= -90
          AND ST_YMax(geom) <= 90
        """
    )
    cur.execute("CREATE INDEX tmp_roman_roads_curated_geom_m_idx ON tmp_roman_roads_curated USING GIST (geom_m)")
    cur.execute("CREATE INDEX tmp_roman_roads_osm_geom_m_idx ON tmp_roman_roads_osm USING GIST (geom_m)")
    cur.execute("ANALYZE tmp_roman_roads_curated")
    cur.execute("ANALYZE tmp_roman_roads_osm")
    cur.execute("SELECT COUNT(*) FROM tmp_roman_roads_curated")
    curated_count = int(cur.fetchone()[0] or 0)
    cur.execute("SELECT COUNT(*) FROM tmp_roman_roads_osm")
    osm_count = int(cur.fetchone()[0] or 0)
    print(f"[INFO] roman roads work tables: curated={curated_count} osm={osm_count}", flush=True)
    return curated_count, osm_count

def prepare_pair_tables(cur) -> tuple[int, int]:
    print("[INFO] matching Roman roads within 50m using projected indexes", flush=True)
    cur.execute("DROP TABLE IF EXISTS tmp_roman_roads_paired_curated")
    cur.execute("DROP TABLE IF EXISTS tmp_roman_roads_paired_osm")
    cur.execute(
        """
        CREATE TEMP TABLE tmp_roman_roads_paired_curated ON COMMIT DROP AS
        SELECT DISTINCT c.id
        FROM tmp_roman_roads_curated c
        JOIN tmp_roman_roads_osm o
          ON c.geom_m && ST_Expand(o.geom_m, 50.0)
         AND ST_DWithin(c.geom_m, o.geom_m, 50.0)
        """
    )
    cur.execute(
        """
        CREATE TEMP TABLE tmp_roman_roads_paired_osm ON COMMIT DROP AS
        SELECT DISTINCT o.id
        FROM tmp_roman_roads_osm o
        JOIN tmp_roman_roads_curated c
          ON o.geom_m && ST_Expand(c.geom_m, 50.0)
         AND ST_DWithin(o.geom_m, c.geom_m, 50.0)
        """
    )
    cur.execute("CREATE INDEX tmp_roman_roads_paired_curated_id_idx ON tmp_roman_roads_paired_curated (id)")
    cur.execute("CREATE INDEX tmp_roman_roads_paired_osm_id_idx ON tmp_roman_roads_paired_osm (id)")
    cur.execute("ANALYZE tmp_roman_roads_paired_curated")
    cur.execute("ANALYZE tmp_roman_roads_paired_osm")
    cur.execute("SELECT COUNT(*) FROM tmp_roman_roads_paired_curated")
    paired_curated = int(cur.fetchone()[0] or 0)
    cur.execute("SELECT COUNT(*) FROM tmp_roman_roads_paired_osm")
    paired_osm = int(cur.fetchone()[0] or 0)
    print(f"[INFO] Roman roads matched within 50m: curated={paired_curated} osm={paired_osm}", flush=True)
    return paired_curated, paired_osm

def main() -> int:
    started = time.monotonic()
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            ensure_registry(cur)
            curated_count, osm_count = prepare_work_tables(cur)
            prepare_pair_tables(cur)
            cur.execute("DELETE FROM external_features WHERE layer = %s", (LAYER_KEY,))
            print("[INFO] rebuilding Roman roads confidence rows", flush=True)
            cur.execute(SQL, (LAYER_KEY,))
            inserted = cur.rowcount
            print(f"[INFO] inserted {inserted} confidence rows", flush=True)
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

    print(f"[DONE] rebuilt Roman roads confidence layer in {time.monotonic() - started:.1f}s")
    if not rows:
        print("[INFO] no confidence features were created")
    else:
        for bucket, count in rows:
            print(f"[INFO] {bucket}: {count}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
