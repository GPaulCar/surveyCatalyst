from pathlib import Path

ROOT = Path.cwd()

DATA_QUALITY = r'''from __future__ import annotations

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
'''

RESET_REBUILD = r'''from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

REQUIRED_SCRIPTS = [
    "scripts/system_control.py",
    "scripts/build_hydrology_protection_layers.py",
    "scripts/ingest_hydrology_osm.py",
    "scripts/fetch_protection_buffers_source.py",
    "scripts/load_protection_buffers_geojson.py",
    "scripts/stable_osm_ingest_engine.py",
    "scripts/data_quality_pass.py",
    "scripts/layer_counts.py",
]

REQUIRED_LAYERS = [
    "rivers_streams",
    "waterbodies",
    "floodplains",
    "protection_buffers",
    "parcel_boundaries",
    "field_names",
    "geonames_points",
    "old_creeks",
    "old_channels",
    "wetland_history",
]

PROTECTION_GEOJSON = ROOT / "workspace" / "downloads" / "curated" / "protection_buffers" / "protection_buffers_merged.geojson"


def run(cmd: list[str], required: bool = True) -> int:
    print("[RUN] " + " ".join(str(x) for x in cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if required and result.returncode != 0:
        raise SystemExit(result.returncode)
    return result.returncode


def require_files() -> None:
    missing = [p for p in REQUIRED_SCRIPTS if not (ROOT / p).exists()]
    if missing:
        print("[FAIL] missing required scripts:")
        for p in missing:
            print(f"  - {p}")
        raise SystemExit(1)


def reset_imported_data_only() -> None:
    print("[RESET] imported/context data only")
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE external_features RESTART IDENTITY")
        conn.commit()
    finally:
        conn.close()

    # Do not touch surveys, survey_objects, user-created records, or workspace exports.
    print("[OK] external_features truncated")


def clear_runtime_state() -> None:
    print("[RESET] cache and ingest state")

    for path in [
        ROOT / ".cache" / "mvt",
        ROOT / "workspace" / "osm_ingest_engine",
    ]:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True, exist_ok=True)
        print(f"[OK] reset {path}")


def counts() -> dict[str, int]:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT layer, COUNT(*)
                FROM external_features
                GROUP BY layer
                ORDER BY layer
            """)
            return {str(layer): int(count) for layer, count in cur.fetchall()}
    finally:
        conn.close()


def verify_counts() -> None:
    print("[VERIFY] layer counts")
    c = counts()
    for layer in sorted(c):
        print(f"{layer}: {c[layer]}")

    missing = []
    zero = []
    for layer in REQUIRED_LAYERS:
        if layer not in c:
            missing.append(layer)
        elif c[layer] <= 0:
            zero.append(layer)

    if missing or zero:
        if missing:
            print("[FAIL] missing layers:")
            for layer in missing:
                print(f"  - {layer}")
        if zero:
            print("[FAIL] zero-count layers:")
            for layer in zero:
                print(f"  - {layer}")
        raise SystemExit(1)

    print("[OK] required layer counts verified")


def checkpoint() -> None:
    checkpoint_script = ROOT / "apply_checkpoint_bundle.py"
    if checkpoint_script.exists():
        run([sys.executable, str(checkpoint_script), "full-rebuild-quality-stage1", "--no-push"], required=False)
    else:
        print("[WARN] checkpoint skipped: apply_checkpoint_bundle.py not found")


def main() -> None:
    print("[PHASE] reset + full imported-data rebuild")
    print("[SCOPE] keeps surveys and user-created survey objects")
    print("[SCOPE] rebuilds imported/context layers from source")

    print("[1/10] preflight")
    require_files()

    print("[2/10] ensure services")
    run([sys.executable, "scripts/system_control.py", "restart"])

    print("[3/10] reset imported data")
    reset_imported_data_only()
    clear_runtime_state()

    print("[4/10] register hydrology/protection layers")
    run([sys.executable, "scripts/build_hydrology_protection_layers.py"])

    print("[5/10] fetch/load official protection source")
    run([sys.executable, "scripts/fetch_protection_buffers_source.py"])
    if not PROTECTION_GEOJSON.exists():
        raise SystemExit(f"[FAIL] missing protection source: {PROTECTION_GEOJSON}")
    run([sys.executable, "scripts/load_protection_buffers_geojson.py", str(PROTECTION_GEOJSON)])

    print("[6/10] ingest hydrology")
    run([sys.executable, "scripts/ingest_hydrology_osm.py"])

    print("[7/10] run stable Bavaria OSM rebuild")
    run([sys.executable, "scripts/stable_osm_ingest_engine.py", "bavaria_coverage_repair"])

    print("[8/10] data quality / dedup / simplification")
    run([sys.executable, "scripts/data_quality_pass.py"])

    print("[9/10] verify counts and restart")
    verify_counts()
    run([sys.executable, "scripts/system_control.py", "restart"])

    print("[10/10] checkpoint")
    checkpoint()

    print("[PHASE COMPLETE]")
    print("full imported-data rebuild complete")
    print("surveys/user data preserved")
    print("context/imported layers rebuilt, deduplicated, simplified, indexed")


if __name__ == "__main__":
    main()
'''

def main() -> None:
    (ROOT / "scripts").mkdir(parents=True, exist_ok=True)

    (ROOT / "scripts" / "data_quality_pass.py").write_text(DATA_QUALITY, encoding="utf-8")
    print("[OK] wrote scripts/data_quality_pass.py")

    (ROOT / "reset_and_full_rebuild.py").write_text(RESET_REBUILD, encoding="utf-8")
    print("[OK] wrote reset_and_full_rebuild.py")

    print("[DONE] rebuild + data-quality phase installed")


if __name__ == "__main__":
    main()