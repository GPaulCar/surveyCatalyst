from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend


SIMPLIFY_RULES = {
    "parcel_boundaries": 0.00001,
    "rivers_streams": 0.000005,
    "waterbodies": 0.00002,
    "floodplains": 0.00002,
    "wetland_history": 0.00002,
    "old_creeks": 0.000005,
    "old_channels": 0.000005,
    "field_names": 0.0,
    "geonames_points": 0.0,
    "protection_buffers": 0.0,
    "legal_restricted_areas": 0.0,
    "roman_roads_osm": 0.000005,
    "roman_roads_confidence": 0.000005,
}


def main() -> int:
    backend = build_backend()
    conn = backend.connect()

    try:
        with conn.cursor() as cur:
            print("[DQ] remove null/empty geometries")
            cur.execute("""
                DELETE FROM external_features
                WHERE geom IS NULL OR ST_IsEmpty(geom)
            """)

            print("[DQ] force valid 2D geometries")
            cur.execute("""
                UPDATE external_features
                SET geom = ST_Force2D(ST_MakeValid(geom))
                WHERE geom IS NOT NULL
                  AND (
                    NOT ST_IsValid(geom)
                    OR ST_NDims(geom) > 2
                  )
            """)

            print("[DQ] deduplicate by layer/source/source_id")
            cur.execute("""
                DELETE FROM external_features a
                USING external_features b
                WHERE a.id > b.id
                  AND a.layer = b.layer
                  AND COALESCE(a.source_table, '') = COALESCE(b.source_table, '')
                  AND COALESCE(a.source_id, '') <> ''
                  AND COALESCE(a.source_id, '') = COALESCE(b.source_id, '')
            """)

            print("[DQ] deduplicate remaining by layer + geometry hash")
            cur.execute("""
                DELETE FROM external_features a
                USING external_features b
                WHERE a.id > b.id
                  AND a.layer = b.layer
                  AND COALESCE(a.source_id, '') = ''
                  AND COALESCE(b.source_id, '') = ''
                  AND md5(ST_AsEWKB(a.geom)::text) = md5(ST_AsEWKB(b.geom)::text)
            """)

            print("[DQ] simplify configured layers")
            for layer, tolerance in SIMPLIFY_RULES.items():
                if tolerance <= 0:
                    continue
                cur.execute(
                    """
                    UPDATE external_features
                    SET geom = ST_Force2D(ST_SimplifyPreserveTopology(geom, %s))
                    WHERE layer = %s
                      AND geom IS NOT NULL
                      AND GeometryType(geom) NOT IN ('POINT', 'MULTIPOINT')
                    """,
                    (tolerance, layer),
                )

            print("[DQ] final validity pass")
            cur.execute("""
                UPDATE external_features
                SET geom = ST_Force2D(ST_MakeValid(geom))
                WHERE geom IS NOT NULL
                  AND NOT ST_IsValid(geom)
            """)

            print("[DQ] ensure spatial index")
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_external_features_geom_gist
                ON external_features
                USING GIST (geom)
            """)

        conn.commit()
    finally:
        conn.close()

    print("[DQ] analyse table")
    conn = backend.connect()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("ANALYZE external_features")
    finally:
        conn.close()

    print("[DQ COMPLETE]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
