from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class LayerSpec:
    key: str
    group: str
    ops: dict[str, list[list[str]]]


LAYER_SPECS: dict[str, LayerSpec] = {
    "state_boundaries_de": LayerSpec(
        key="state_boundaries_de",
        group="reference",
        ops={
            "acquire": [["ingest_state_boundaries_de.py"]],
            "visualize": [["run_api.py"]],
        },
    ),
    "bkg_administrative_boundaries": LayerSpec(
        key="bkg_administrative_boundaries",
        group="reference",
        ops={
            "acquire": [["ingest_bkg_administrative_boundaries.py"]],
            "visualize": [["run_api.py"]],
        },
    ),
    "parcel_boundaries": LayerSpec(
        key="parcel_boundaries",
        group="legal_permission",
        ops={
            "acquire": [["ingest_parcel_boundaries_osm.py"]],
            "generate": [["build_phase_3_parcel_permission.py"]],
            "visualize": [["run_api.py"]],
        },
    ),
    "roman_roads_osm": LayerSpec(
        key="roman_roads_osm",
        group="historical_context",
        ops={
            "acquire": [["ingest_roman_roads_osm.py"]],
            "generate": [["build_roman_roads_confidence.py"]],
            "visualize": [["run_api.py"]],
        },
    ),
    "hydrology_osm": LayerSpec(
        key="hydrology_osm",
        group="hydrology_terrain",
        ops={
            "acquire": [["ingest_hydrology_osm.py"]],
            "generate": [["build_bundle_hydrology_core.py"], ["build_hydrology_protection_layers.py"]],
            "visualize": [["run_api.py"]],
        },
    ),
    "historical_enrichment_osm": LayerSpec(
        key="historical_enrichment_osm",
        group="historical_context",
        ops={
            "acquire": [["ingest_historical_enrichment_osm.py"]],
            "generate": [["build_historical_enrichment_layers.py"]],
            "visualize": [["run_api.py"]],
        },
    ),
}


def run_python(script_name: str, args: list[str]) -> int:
    cmd = [sys.executable, "-u", str(ROOT / "scripts" / script_name), *args]
    print(f"[RUN] {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    return proc.returncode


def run_steps(commands: list[list[str]]) -> int:
    for command in commands:
        script = command[0]
        args = command[1:]
        code = run_python(script, args)
        if code != 0:
            return code
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Bavaria layer pipeline operations independently.")
    parser.add_argument("--all", action="store_true", help="Run all configured layers.")
    parser.add_argument("--group", action="append", default=[], help="Layer group to run (repeatable).")
    parser.add_argument("--layer", action="append", default=[], help="Layer key to run (repeatable).")
    parser.add_argument(
        "--op",
        action="append",
        default=[],
        choices=["acquire", "process", "generate", "register", "visualize", "reload"],
        help="Operation stage(s) to run in order.",
    )
    return parser.parse_args()


def target_layers(args: argparse.Namespace) -> list[LayerSpec]:
    if args.all:
        return list(LAYER_SPECS.values())

    selected: list[LayerSpec] = []
    group_set = set(args.group or [])
    layer_set = set(args.layer or [])
    for spec in LAYER_SPECS.values():
        if spec.key in layer_set or spec.group in group_set:
            selected.append(spec)
    return selected


def main() -> int:
    args = parse_args()
    ops = args.op or ["acquire", "generate"]
    layers = target_layers(args)
    if not layers:
        print("[ERROR] no layers selected. Use --all, --group, or --layer.", flush=True)
        return 2

    for spec in layers:
        print(f"\n[LAYER] {spec.key} ({spec.group})", flush=True)
        for op in ops:
            if op == "reload":
                sequence = spec.ops.get("acquire", []) + spec.ops.get("generate", [])
            else:
                sequence = spec.ops.get(op, [])
            if not sequence:
                print(f"[SKIP] {spec.key} op={op} (no command configured)", flush=True)
                continue
            code = run_steps(sequence)
            if code != 0:
                print(f"[FAIL] {spec.key} op={op} exit={code}", flush=True)
                return code
            print(f"[OK] {spec.key} op={op}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
