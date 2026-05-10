from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BAVARIA_BBOX = "8.95,47.20,13.95,50.65"


@dataclass
class StepResult:
    name: str
    ok: bool
    skipped: bool = False
    command: str = ""
    message: str = ""


def script_path(name: str) -> Path:
    return ROOT / "scripts" / name


def run_step(name: str, args: list[str], *, optional: bool = False) -> StepResult:
    cmd = [sys.executable, "-u", str(script_path(name)), *args]
    command_label = f"{name} {' '.join(args)}".rstrip()
    print(f"[RUN] {command_label}", flush=True)
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    except FileNotFoundError as exc:
        return StepResult(
            name=name,
            ok=False,
            skipped=optional,
            command=" ".join(cmd),
            message=f"python not available: {exc}",
        )

    if proc.returncode == 0:
        print(f"[DONE] {name}", flush=True)
        return StepResult(name=name, ok=True, command=" ".join(cmd), message="ok")

    if optional:
        print(f"[SKIP] {name}: exit {proc.returncode}", flush=True)
        return StepResult(name=name, ok=True, skipped=True, command=" ".join(cmd), message=f"skipped (exit {proc.returncode})")

    print(f"[FAIL] {name}: exit {proc.returncode}", flush=True)
    return StepResult(
        name=name,
        ok=False,
        command=" ".join(cmd),
        message=f"failed with exit code {proc.returncode}",
    )


def add_geojson_steps(results: list[StepResult], args: argparse.Namespace) -> None:
    geojson_jobs = [
        ("load_field_names_geojson.py", args.field_names, True),
        ("load_geonames_geojson.py", args.geonames, True),
        ("load_old_creeks_geojson.py", args.old_creeks, True),
        ("load_old_channels_geojson.py", args.old_channels, True),
        ("load_wetland_history_geojson.py", args.wetland_history, True),
        ("load_rivers_streams_geojson.py", args.rivers_streams, True),
        ("load_waterbodies_geojson.py", args.waterbodies, True),
        ("load_floodplains_geojson.py", args.floodplains, True),
        ("load_parcel_boundaries_geojson.py", args.parcel_boundaries, True),
        ("load_protection_buffers_geojson.py", args.protection_buffers, True),
        ("load_roman_roads_curated.py", args.roman_roads_curated, True),
    ]

    for script_name, value, optional in geojson_jobs:
        if not value:
            results.append(
                StepResult(
                    name=script_name,
                    ok=True,
                    skipped=True,
                    message="not provided",
                )
            )
            continue
        results.append(run_step(script_name, [str(Path(value).resolve())], optional=optional))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Populate supported layers in one pass.")
    parser.add_argument(
        "--bbox",
        default=BAVARIA_BBOX,
        help=f"First-pass bbox as min_lon,min_lat,max_lon,max_lat. Defaults to Bavaria ({BAVARIA_BBOX}).",
    )
    parser.add_argument("--max-records-per-layer", type=int, default=5000, help="Use 0 for no cap.")
    parser.add_argument("--all-records", action="store_true", help="Disable the per-layer cap during master registry load.")
    parser.add_argument("--force", action="store_true", help="Reload vector layers even if rows already exist.")
    parser.add_argument("--include-osm", action="store_true", default=True, help="Include OSM-based registry layers.")
    parser.add_argument("--skip-registry-sync", action="store_true")
    parser.add_argument("--skip-master-load", action="store_true")
    parser.add_argument("--skip-provider-loads", action="store_true")
    parser.add_argument("--skip-special-loads", action="store_true")
    parser.add_argument("--skip-derived-loads", action="store_true")
    parser.add_argument("--skip-geojson-loads", action="store_true")
    parser.add_argument("--field-names")
    parser.add_argument("--geonames")
    parser.add_argument("--old-creeks")
    parser.add_argument("--old-channels")
    parser.add_argument("--wetland-history")
    parser.add_argument("--rivers-streams")
    parser.add_argument("--waterbodies")
    parser.add_argument("--floodplains")
    parser.add_argument("--parcel-boundaries")
    parser.add_argument("--protection-buffers")
    parser.add_argument("--roman-roads-curated")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    results: list[StepResult] = []

    if not args.skip_registry_sync:
        results.append(run_step("import_layer_registry_master.py", []))

    if not args.skip_master_load:
        master_args = [
            "run",
            "--bbox",
            args.bbox,
        ]
        if args.all_records:
            master_args.append("--all-records")
        else:
            master_args.extend(["--max-records-per-layer", str(args.max_records_per_layer)])
        if args.force:
            master_args.append("--force")
        if args.include_osm:
            master_args.append("--include-osm")
        results.append(run_step("load_master_registry_data.py", master_args))

    if not args.skip_provider_loads:
        for source_key in ("blfd", "itiner_e", "viabundus", "gesis"):
            provider_args = [source_key]
            if args.force:
                provider_args.append("--force")
            results.append(run_step("run_ingestion_source.py", provider_args))

    if not args.skip_special_loads:
        for script_name in (
            "ingest_hydrology_osm.py",
            "ingest_historical_enrichment_osm.py",
            "ingest_parcel_boundaries_osm.py",
            "ingest_roman_roads_osm.py",
            "restore_legal_restricted_layer.py",
        ):
            results.append(run_step(script_name, []))

    if not args.skip_derived_loads:
        for script_name in (
            "build_bundle_hydrology_core.py",
            "build_historical_enrichment_layers.py",
            "build_hydrology_protection_layers.py",
            "build_phase_3_parcel_permission.py",
            "build_roman_roads_confidence.py",
        ):
            results.append(run_step(script_name, []))

    if not args.skip_geojson_loads:
        add_geojson_steps(results, args)

    total = len(results)
    ok = sum(1 for r in results if r.ok)
    skipped = sum(1 for r in results if r.skipped)
    failed = total - ok

    print("\n[SUMMARY]")
    print(f"steps={total} ok={ok} skipped={skipped} failed={failed}")
    for result in results:
        status = "SKIP" if result.skipped else "OK" if result.ok else "FAIL"
        print(f"{status} {result.name}: {result.message}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
