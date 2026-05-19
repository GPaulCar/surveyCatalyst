from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assessment" / "output"

RUNTIME_SCRIPT_ALLOWLIST = {
    "run_ops_cycle.py",
    "run_app.py",
    "run_api.py",
    "start_api_managed.py",
    "system_control.py",
    "service_control.py",
    "update_from_git.py",
    "update_from_git.cmd",
    "run_migrations.py",
}

PURGE_DIRS = [
    ROOT / "workspace" / "downloads" / "raw",
    ROOT / "workspace" / "downloads" / "curated",
    ROOT / "workspace" / "osm_ingest_engine" / "raw",
    ROOT / "workspace" / "data_gaps_field_names_geonames" / "raw",
    ROOT / "downloads",
    ROOT / "exports_full",
]


def remove_file(path: Path, removed: list[str]) -> None:
    if path.exists() and path.is_file():
        path.unlink(missing_ok=True)
        removed.append(str(path.relative_to(ROOT)).replace("\\", "/"))


def purge_tree(path: Path, removed: list[str]) -> None:
    if not path.exists():
        return
    for base, _, files in os.walk(path):
        for name in files:
            p = Path(base) / name
            p.unlink(missing_ok=True)
            removed.append(str(p.relative_to(ROOT)).replace("\\", "/"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Purge repository to runtime-only footprint after git pull.")
    parser.add_argument("--yes", action="store_true", help="Execute purge. Without this, script runs as plan only.")
    args = parser.parse_args()

    removed: list[str] = []
    planned: list[str] = []

    script_files = [p for p in (ROOT / "scripts").iterdir() if p.is_file()]
    for p in script_files:
        if p.name in RUNTIME_SCRIPT_ALLOWLIST or p.suffix.lower() == ".sql":
            continue
        planned.append(str(p.relative_to(ROOT)).replace("\\", "/"))
        if args.yes:
            remove_file(p, removed)

    for d in PURGE_DIRS:
        planned.append(str(d.relative_to(ROOT)).replace("\\", "/") + "/**/*")
        if args.yes:
            purge_tree(d, removed)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if args.yes else "plan",
        "planned_entries": planned,
        "removed_files_count": len(removed),
        "removed_files_sample": removed[:500],
    }
    out = OUT_DIR / f"runtime_purge_{stamp}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(out), "mode": report["mode"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
