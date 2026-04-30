from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.db import build_backend


APP_VERSION = "0.6.0"
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY_PATH = ROOT / "layer_registry_master.csv"

REQUIRED_COLUMNS = [
    "category",
    "subcategory",
    "layer_name",
    "description",
    "geometry_type",
    "source_provider",
    "source_type",
    "endpoint_url",
    "ingestion_method",
    "priority",
    "region_scope",
    "notes",
]

VALID_GEOMETRY_TYPES = {"point", "line", "polygon", "raster"}
VALID_SOURCE_TYPES = {"WFS", "WMS", "WMTS", "XYZ", "REST", "OSM", "FILE"}
VALID_INGESTION_METHODS = {"postgis", "tile", "external", "postgis_derived"}
VALID_PRIORITIES = {"critical", "high", "medium", "low"}
VALID_REGION_SCOPES = {"local", "regional", "eu", "global"}


@dataclass(frozen=True)
class MasterLayerRecord:
    category: str
    subcategory: str
    layer_name: str
    description: str
    geometry_type: str
    source_provider: str
    source_type: str
    endpoint_url: str
    ingestion_method: str
    priority: str
    region_scope: str
    notes: str

    @property
    def layer_group(self) -> str:
        return "base" if self.category == "base_maps" else "context"

    @property
    def source_table(self) -> str:
        if self.ingestion_method in {"postgis", "postgis_derived"}:
            return "external_features"
        return self.endpoint_url

    @property
    def db_geometry_type(self) -> str:
        if self.geometry_type == "point":
            return "POINT"
        if self.geometry_type == "line":
            return "LINESTRING"
        if self.geometry_type == "polygon":
            return "POLYGON"
        return "RASTER"

    def metadata(self) -> dict[str, Any]:
        data = {
            "registry_version": APP_VERSION,
            "category": self.category,
            "subcategory": self.subcategory,
            "subgroup": self.subcategory,
            "description": self.description,
            "source_provider": self.source_provider,
            "source_type": self.source_type,
            "endpoint_url": self.endpoint_url,
            "ingestion_method": self.ingestion_method,
            "priority": self.priority,
            "region_scope": self.region_scope,
            "notes": self.notes,
            "always_show": True,
        }
        service_layer = infer_service_layer(self)
        if service_layer:
            data["service_layer"] = service_layer
        service_url = infer_service_url(self.endpoint_url)
        if service_url:
            data["service_url"] = service_url
        return data


def infer_service_url(endpoint_url: str) -> str:
    if endpoint_url == "derived":
        return endpoint_url
    return endpoint_url.split("?", 1)[0]


def infer_service_layer(record: MasterLayerRecord) -> str | None:
    notes = record.notes or ""
    match = re.search(r"\b(?:WMS|WMTS)\s+layer\s+([A-Za-z0-9_:\-.]+)", notes)
    if match:
        return match.group(1)

    match = re.search(r"\blayer\s+([0-9]+)\b", notes, flags=re.IGNORECASE)
    if match and record.source_type == "REST":
        return match.group(1)

    match = re.search(r"\bFeature type\s+([A-Za-z0-9_:\-.]+)", notes)
    if match:
        return match.group(1)

    return None


class MasterLayerRegistryService:
    def __init__(self, registry_path: Path | None = None):
        self.registry_path = Path(registry_path or DEFAULT_REGISTRY_PATH)
        self.backend = build_backend()

    def load_records(self) -> list[MasterLayerRecord]:
        with self.registry_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
            if missing:
                raise ValueError(f"Registry is missing required columns: {', '.join(missing)}")
            records = [MasterLayerRecord(**{column: (row.get(column) or "").strip() for column in REQUIRED_COLUMNS}) for row in reader]

        self.validate_records(records)
        return records

    def validate_records(self, records: list[MasterLayerRecord]) -> None:
        if len(records) < 50:
            raise ValueError("Registry must contain at least 50 layers")

        seen: set[str] = set()
        errors: list[str] = []
        for idx, record in enumerate(records, start=2):
            if record.layer_name in seen:
                errors.append(f"line {idx}: duplicate layer_name {record.layer_name}")
            seen.add(record.layer_name)

            if not record.endpoint_url:
                errors.append(f"line {idx}: endpoint_url is required")
            if record.ingestion_method == "postgis_derived" and record.endpoint_url != "derived":
                errors.append(f"line {idx}: derived layers must use endpoint_url=derived")
            if record.geometry_type not in VALID_GEOMETRY_TYPES:
                errors.append(f"line {idx}: invalid geometry_type {record.geometry_type}")
            if record.source_type not in VALID_SOURCE_TYPES:
                errors.append(f"line {idx}: invalid source_type {record.source_type}")
            if record.ingestion_method not in VALID_INGESTION_METHODS:
                errors.append(f"line {idx}: invalid ingestion_method {record.ingestion_method}")
            if record.priority not in VALID_PRIORITIES:
                errors.append(f"line {idx}: invalid priority {record.priority}")
            if record.region_scope not in VALID_REGION_SCOPES:
                errors.append(f"line {idx}: invalid region_scope {record.region_scope}")

        if errors:
            raise ValueError("; ".join(errors))

    def sync_to_database(self) -> dict[str, Any]:
        records = self.load_records()
        conn = self.backend.connect()
        upserted = 0
        try:
            with conn.cursor() as cur:
                for sort_order, record in enumerate(records, start=1000):
                    cur.execute(
                        """
                        INSERT INTO layers_registry (
                            layer_key, layer_name, layer_group, source_table, geometry_type,
                            is_user_selectable, is_visible, opacity, sort_order, metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, TRUE, FALSE, 1.0, %s, %s::jsonb)
                        ON CONFLICT (layer_key) DO UPDATE SET
                            layer_name = EXCLUDED.layer_name,
                            layer_group = EXCLUDED.layer_group,
                            source_table = EXCLUDED.source_table,
                            geometry_type = EXCLUDED.geometry_type,
                            is_user_selectable = EXCLUDED.is_user_selectable,
                            opacity = EXCLUDED.opacity,
                            sort_order = EXCLUDED.sort_order,
                            metadata = EXCLUDED.metadata,
                            updated_at = NOW()
                        """,
                        (
                            record.layer_name,
                            record.layer_name,
                            record.layer_group,
                            record.source_table,
                            record.db_geometry_type,
                            sort_order,
                            json.dumps(record.metadata(), sort_keys=True),
                        ),
                    )
                    upserted += 1
            conn.commit()
        finally:
            conn.close()

        return {
            "registry_path": str(self.registry_path),
            "registry_version": APP_VERSION,
            "layers": len(records),
            "upserted": upserted,
        }
