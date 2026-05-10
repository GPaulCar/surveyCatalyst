from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from layers.master_registry_data_loader import MasterRegistryDataLoader


BAVARIA_BBOX = "8.95,47.20,13.95,50.65"


def parse_bbox(value: str | None) -> tuple[float, float, float, float] | None:
    if not value:
        return None
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("bbox must be min_lon,min_lat,max_lon,max_lat")
    try:
        min_lon, min_lat, max_lon, max_lat = (float(part) for part in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("bbox values must be numeric") from exc
    if min_lon >= max_lon or min_lat >= max_lat:
        raise argparse.ArgumentTypeError("bbox must be min_lon,min_lat,max_lon,max_lat")
    return min_lon, min_lat, max_lon, max_lat


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan or load master registry vector layers into external_features."
    )
    parser.add_argument("command", choices=("plan", "run"))
    parser.add_argument(
        "--include-osm",
        action="store_true",
        help="Allow OSM Overpass layers. Requires --bbox to avoid unbounded global queries.",
    )
    parser.add_argument(
        "--bbox",
        type=parse_bbox,
        help="Bounding box for OSM and ArcGIS REST loads as min_lon,min_lat,max_lon,max_lat.",
    )
    parser.add_argument(
        "--bavaria",
        action="store_true",
        help=f"Use Bavaria bbox ({BAVARIA_BBOX}) when --bbox is not provided.",
    )
    parser.add_argument(
        "--max-records-per-layer",
        type=int,
        default=5000,
        help="Upper bound per loadable layer. Use 0 for no cap. Defaults to 5000.",
    )
    parser.add_argument(
        "--all-records",
        action="store_true",
        help="Disable the per-layer record cap and page until each service stops returning rows.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing rows for each selected layer before loading.",
    )
    parser.add_argument(
        "--layer",
        dest="layers",
        action="append",
        help="Layer name to include. Can be repeated.",
    )
    parser.add_argument(
        "--source-type",
        dest="source_types",
        action="append",
        choices=("WFS", "REST", "OSM", "FILE"),
        help="Source type to include. Can be repeated.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    loader = MasterRegistryDataLoader()
    layer_names = set(args.layers or []) or None
    source_types = set(args.source_types or []) or None
    bbox = args.bbox or (parse_bbox(BAVARIA_BBOX) if args.bavaria else None)
    max_records_per_layer = 0 if args.all_records else args.max_records_per_layer
    if max_records_per_layer < 0:
        raise SystemExit("--max-records-per-layer must be 0 or greater")

    if args.command == "plan":
        result = loader.plan(
            include_osm=args.include_osm,
            bbox=bbox,
            layer_names=layer_names,
            source_types=source_types,
        )
    else:
        result = loader.load_all(
            force=args.force,
            include_osm=args.include_osm,
            bbox=bbox,
            max_records_per_layer=max_records_per_layer,
            layer_names=layer_names,
            source_types=source_types,
        )

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
