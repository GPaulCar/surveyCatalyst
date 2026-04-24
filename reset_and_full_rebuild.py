from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

# ---- CONFIG ----

REQUIRED_SCRIPTS = [
    "scripts/system_control.py",
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

# ---- UTILS ----

def run(cmd: list[str], required: bool = True):
    print("[RUN] " + " ".join(str(x) for x in cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if required and result.returncode != 0:
        raise SystemExit(result.returncode)

def require_files():
    missing = [p for p in REQUIRED_SCRIPTS if not (ROOT / p).exists()]
    if missing:
        print("[FAIL] missing required scripts:")
        for p in missing:
            print(f"  - {p}")
        raise SystemExit(1)

def reset_imported_data():
    print("[RESET] external_features only (preserving surveys)")
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE external_features RESTART IDENTITY")
        conn.commit()
    finally:
        conn.close()

def clear_runtime_state():
    print("[RESET] cache + ingest state")

    for path in [
        ROOT / ".cache" / "mvt",
        ROOT / "workspace" / "osm_ingest_engine",
    ]:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True, exist_ok=True)
        print(f"[OK] reset {path}")

def counts():
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT layer, COUNT(*)
                FROM external_features
                GROUP BY layer
            """)
            return {str(layer): int(count) for layer, count in cur.fetchall()}
    finally:
        conn.close()

def verify_counts():
    print("[VERIFY] layer counts")
    c = counts()

    for k in sorted(c):
        print(f"{k}: {c[k]}")

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
            for m in missing:
                print(f"  - {m}")
        if zero:
            print("[FAIL] zero-count layers:")
            for z in zero:
                print(f"  - {z}")
        raise SystemExit(1)

    print("[OK] counts verified")

def checkpoint():
    script = ROOT / "apply_checkpoint_bundle.py"
    if script.exists():
        run([sys.executable, str(script), "full-rebuild-stable-stage1", "--no-push"], required=False)
    else:
        print("[WARN] checkpoint skipped")

# ---- MAIN ----

def main():
    print("[PHASE] FULL REBUILD (IMPORTED DATA ONLY)")
    print("[SAFE] surveys + user data preserved")

    print("\n[1/9] preflight")
    require_files()

    print("\n[2/9] restart services")
    run([sys.executable, "scripts/system_control.py", "restart"])

    print("\n[3/9] reset imported data")
    reset_imported_data()
    clear_runtime_state()

    print("\n[4/9] load protection buffers")
    if not PROTECTION_GEOJSON.exists():
        raise SystemExit(f"[FAIL] missing protection file: {PROTECTION_GEOJSON}")

    run([
        sys.executable,
        "scripts/load_protection_buffers_geojson.py",
        str(PROTECTION_GEOJSON)
    ])

    print("\n[5/9] ingest hydrology (stable engine)")
    run([sys.executable, "scripts/stable_osm_ingest_engine.py", "job", "rivers_streams"])
    run([sys.executable, "scripts/stable_osm_ingest_engine.py", "job", "waterbodies"])
    run([sys.executable, "scripts/stable_osm_ingest_engine.py", "job", "floodplains"])

    print("\n[6/9] ingest Bavaria enrichment (stable engine full)")
    run([sys.executable, "scripts/stable_osm_ingest_engine.py", "bavaria_coverage_repair"])

    print("\n[7/9] data quality pass")
    run([sys.executable, "scripts/data_quality_pass.py"])

    print("\n[8/9] verify + restart")
    verify_counts()
    run([sys.executable, "scripts/system_control.py", "restart"])

    print("\n[9/9] checkpoint")
    checkpoint()

    print("\n[COMPLETE]")
    print("clean rebuild complete")
    print("stable ingestion + deduplicated + simplified + indexed")

if __name__ == "__main__":
    main()