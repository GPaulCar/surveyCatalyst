from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import requests

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend


PRODUCTS = {
    "dgm1": {
        "layer_key": "bavaria_dgm1",
        "product_name": "Digitales Geländemodell 1m",
        "product_page": "https://www.geodaten.bayern.de/opengeodata/OpenDataDetail.html?pn=dgm1",
        "metalink_url": "https://www.geodaten.bayern.de/odd/a/dgm/dgm1/meta/metalink/09.meta4",
        "source_available": True,
        "notes": "Official Bavaria OpenData DGM1 metalink manifest.",
    },
    "dgm5": {
        "layer_key": "bavaria_dgm5",
        "product_name": "Digitales Geländemodell 5m",
        "product_page": "https://www.geodaten.bayern.de/opengeodata/OpenDataDetail.html?pn=dgm5",
        "metalink_url": None,
        "source_available": False,
        "notes": "Derived 5m terrain model. This repo tracks it as a registry layer; local raster derivation is not implemented yet.",
    },
}


@dataclass(frozen=True)
class AcquisitionResult:
    product: str
    layer_key: str
    manifest_path: str | None
    asset_dir: str | None
    metalink_url: str | None
    source_available: bool
    status: str
    message: str
    file_count: int = 0
    total_bytes: int | None = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Acquire Bavaria DGM manifests and optionally download the raw assets.")
    parser.add_argument(
        "--product",
        action="append",
        choices=tuple(PRODUCTS.keys()),
        help="Product to acquire. Repeatable. Defaults to both DGM1 and DGM5.",
    )
    parser.add_argument(
        "--download-root",
        default=str(ROOT / "workspace" / "downloads" / "raw" / "bavaria" / "dgm"),
        help="Directory where manifests and assets will be stored.",
    )
    parser.add_argument(
        "--download-assets",
        action="store_true",
        help="Use aria2c to download the referenced DGM assets after fetching the metalink manifest.",
    )
    parser.add_argument(
        "--aria2c",
        default="aria2c",
        help="Path to the aria2 executable used for metalink downloads.",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Do not update layers_registry metadata after acquisition.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned actions without downloading or updating the database.",
    )
    return parser


def selected_products(args: argparse.Namespace) -> list[str]:
    return list(args.product or PRODUCTS.keys())


def fetch_manifest(url: str, manifest_path: Path) -> bytes:
    try:
        response = requests.get(url, timeout=120)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"failed to fetch metalink manifest from {url}: {exc}") from exc
    manifest_path.write_bytes(response.content)
    return response.content


def parse_metalink(manifest_bytes: bytes) -> tuple[list[dict[str, Any]], int]:
    root = ET.fromstring(manifest_bytes)
    files: list[dict[str, Any]] = []
    total_bytes = 0
    for file_node in root.findall(".//{*}file"):
        name = file_node.attrib.get("name") or ""
        size_text = file_node.findtext(".//{*}size")
        size = int(size_text) if size_text and size_text.isdigit() else None
        if size:
            total_bytes += size
        urls = []
        for url_node in file_node.findall(".//{*}url"):
            text = (url_node.text or "").strip()
            if text:
                urls.append(text)
        hashes = []
        for hash_node in file_node.findall(".//{*}hash"):
            algo = hash_node.attrib.get("type") or ""
            value = (hash_node.text or "").strip()
            if value:
                hashes.append({"type": algo, "value": value})
        files.append({"name": name, "size": size, "urls": urls, "hashes": hashes})
    return files, total_bytes


def run_aria2(aria2c: str, metalink_url: str, asset_dir: Path) -> None:
    asset_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        aria2c,
        "-V",
        "--follow-metalink=mem",
        "--dir",
        str(asset_dir),
        metalink_url,
    ]
    print("[RUN] " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"aria2c exited with code {proc.returncode}")


def update_registry(product: str, info: dict[str, Any], manifest_path: Path | None, asset_dir: Path | None, file_count: int, total_bytes: int | None) -> None:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE layers_registry
                SET metadata = COALESCE(metadata, '{}'::jsonb)
                    || %s::jsonb,
                    updated_at = NOW()
                WHERE layer_key = %s
                """,
                (
                    json.dumps(
                        {
                            "acquisition": {
                                "product": product,
                                "status": info["status"],
                                "message": info["message"],
                                "acquired_at": datetime.now(timezone.utc).isoformat(),
                                "manifest_path": str(manifest_path) if manifest_path else None,
                                "asset_dir": str(asset_dir) if asset_dir else None,
                                "metalink_url": info["metalink_url"],
                                "source_available": info["source_available"],
                                "file_count": file_count,
                                "total_bytes": total_bytes,
                                "notes": info["notes"],
                            }
                        },
                        sort_keys=True,
                    ),
                    info["layer_key"],
                ),
            )
            if cur.rowcount == 0:
                cur.execute(
                    """
                    INSERT INTO layers_registry (
                        layer_key, layer_name, layer_group, source_table, geometry_type,
                        is_user_selectable, is_visible, opacity, sort_order, metadata
                    )
                    VALUES (
                        %s, %s, 'context', %s, 'RASTER',
                        TRUE, FALSE, 1.0, 500, %s::jsonb
                    )
                    ON CONFLICT (layer_key) DO UPDATE
                    SET metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    (
                        info["layer_key"],
                        info["layer_key"],
                        "external_features",
                        json.dumps(
                            {
                                "category": "terrain",
                                "subcategory": "lidar",
                                "description": info["notes"],
                                "source_provider": "Bayerische Vermessungsverwaltung",
                                "source_type": "FILE",
                                "endpoint_url": info["product_page"],
                                "ingestion_method": "external",
                                "priority": "critical" if product == "dgm1" else "high",
                                "region_scope": "regional",
                                "always_show": True,
                                "acquisition": {
                                    "product": product,
                                    "status": info["status"],
                                    "message": info["message"],
                                    "acquired_at": datetime.now(timezone.utc).isoformat(),
                                    "manifest_path": str(manifest_path) if manifest_path else None,
                                    "asset_dir": str(asset_dir) if asset_dir else None,
                                    "metalink_url": info["metalink_url"],
                                    "source_available": info["source_available"],
                                    "file_count": file_count,
                                    "total_bytes": total_bytes,
                                },
                            },
                            sort_keys=True,
                        ),
                    ),
                )
        conn.commit()
    finally:
        conn.close()


def acquire_product(product: str, args: argparse.Namespace) -> AcquisitionResult:
    info = PRODUCTS[product].copy()
    root = Path(args.download_root)
    product_dir = root / product
    manifest_dir = product_dir / "manifest"
    asset_dir = product_dir / "assets"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        return AcquisitionResult(
            product=product,
            layer_key=info["layer_key"],
            manifest_path=str(manifest_dir / "metalink.meta4") if info["metalink_url"] else None,
            asset_dir=str(asset_dir),
            metalink_url=info["metalink_url"],
            source_available=info["source_available"],
            status="dry_run",
            message="no network or database operations performed",
        )

    manifest_path = None
    file_count = 0
    total_bytes: int | None = None
    if info["metalink_url"]:
        manifest_path = manifest_dir / "metalink.meta4"
        manifest_bytes = fetch_manifest(info["metalink_url"], manifest_path)
        files, total_bytes = parse_metalink(manifest_bytes)
        file_count = len(files)

        if args.download_assets:
            aria2c = shutil.which(args.aria2c) or args.aria2c
            run_aria2(aria2c, info["metalink_url"], asset_dir)
            info["source_available"] = True
            info["status"] = "downloaded"
            info["message"] = "manifest_and_assets_downloaded"
        else:
            info["status"] = "manifest_downloaded"
            info["message"] = "metalink_manifest_saved"
    else:
        info["status"] = "registry_only"
        info["message"] = "no_separate_metalink_available; tracked as a derived registry row"

    if not args.skip_db:
        update_registry(product, info, manifest_path, asset_dir if args.download_assets else None, file_count, total_bytes)

    report = AcquisitionResult(
        product=product,
        layer_key=info["layer_key"],
        manifest_path=str(manifest_path) if manifest_path else None,
        asset_dir=str(asset_dir) if args.download_assets else None,
        metalink_url=info["metalink_url"],
        source_available=bool(info["source_available"] or args.download_assets),
        status=info["status"],
        message=info["message"],
        file_count=file_count,
        total_bytes=total_bytes,
    )
    return report


def main() -> int:
    args = build_parser().parse_args()
    results: list[AcquisitionResult] = []
    for product in selected_products(args):
        results.append(acquire_product(product, args))

    print(json.dumps([result.__dict__ for result in results], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
