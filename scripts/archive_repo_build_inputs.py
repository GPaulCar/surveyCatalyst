from __future__ import annotations

import argparse
import fnmatch
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
DEFAULT_OUT = ROOT / "zip" / "archive"


@dataclass(frozen=True)
class BundleSpec:
    name: str
    roots: list[Path]
    include_globs: list[str]


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


def is_maintenance_script(path: Path) -> bool:
    if path.suffix.lower() not in {".py", ".ps1", ".cmd", ".sh"}:
        return False
    if path.name in RUNTIME_SCRIPT_ALLOWLIST:
        return False
    if path.parent.name == "sql":
        return False
    return True


def collect_files(spec: BundleSpec) -> list[Path]:
    files: list[Path] = []
    for root in spec.roots:
        if not root.exists():
            continue
        for base, _, names in os.walk(root):
            for name in names:
                full = Path(base) / name
                rel = full.relative_to(ROOT)
                rel_text = rel.as_posix()
                if any(fnmatch.fnmatch(rel_text, g) for g in spec.include_globs):
                    files.append(full)
    files.sort()
    return files


def zip_selected(files: list[Path], out_zip: Path) -> None:
    import zipfile

    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.relative_to(ROOT).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive maintenance/build scripts and ingested source datasets.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT), help="Output directory for archive bundles.")
    parser.add_argument("--prune", action="store_true", help="Delete archived source files after successful archive.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    maintenance_files = [
        p for p in SCRIPTS_DIR.iterdir() if p.is_file() and is_maintenance_script(p)
    ]
    maintenance_files.sort()

    specs = [
        BundleSpec(
            name="maintenance_scripts",
            roots=[SCRIPTS_DIR],
            include_globs=[],
        ),
        BundleSpec(
            name="source_datasets",
            roots=[
                ROOT / "workspace" / "downloads" / "raw",
                ROOT / "workspace" / "downloads" / "curated",
                ROOT / "workspace" / "osm_ingest_engine" / "raw",
                ROOT / "workspace" / "data_gaps_field_names_geonames" / "raw",
                ROOT / "downloads",
                ROOT / "exports_full",
            ],
            include_globs=[
                "workspace/downloads/raw/*",
                "workspace/downloads/raw/**/*",
                "workspace/downloads/curated/*",
                "workspace/downloads/curated/**/*",
                "workspace/osm_ingest_engine/raw/*",
                "workspace/osm_ingest_engine/raw/**/*",
                "workspace/data_gaps_field_names_geonames/raw/*",
                "workspace/data_gaps_field_names_geonames/raw/**/*",
                "downloads/*",
                "downloads/**/*",
                "exports_full/*",
                "exports_full/**/*",
            ],
        ),
    ]

    results: dict[str, dict] = {}

    # Maintenance scripts bundle from explicit selection, not by glob
    maintenance_zip = out_dir / f"maintenance_scripts_{stamp}.zip"
    zip_selected(maintenance_files, maintenance_zip)
    results["maintenance_scripts"] = {
        "zip": str(maintenance_zip),
        "file_count": len(maintenance_files),
        "total_bytes": sum(p.stat().st_size for p in maintenance_files),
        "files": [str(p.relative_to(ROOT)).replace("\\", "/") for p in maintenance_files],
    }

    # Dataset bundle(s)
    dataset_files = collect_files(specs[1])
    datasets_zip = out_dir / f"source_datasets_{stamp}.zip"
    zip_selected(dataset_files, datasets_zip)
    results["source_datasets"] = {
        "zip": str(datasets_zip),
        "file_count": len(dataset_files),
        "total_bytes": sum(p.stat().st_size for p in dataset_files),
        "files_sample": [str(p.relative_to(ROOT)).replace("\\", "/") for p in dataset_files[:200]],
    }

    if args.prune:
        for p in maintenance_files + dataset_files:
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(ROOT),
        "pruned": bool(args.prune),
        "bundles": results,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / f"archive_manifest_{stamp}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, "manifest": str(manifest_path), "bundles": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
