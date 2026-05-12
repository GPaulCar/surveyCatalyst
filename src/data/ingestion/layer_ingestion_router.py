from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from core.db import build_backend
from layers.master_registry_data_loader import MasterRegistryDataLoader
from layers.master_registry_service import MasterLayerRecord, MasterLayerRegistryService


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY_PATH = ROOT / "docs" / "data" / "layer_registry_master.csv"
REPORT_PATH = ROOT / "workspace" / "layer_ingestion_router_report.json"

VECTOR_SOURCE_TYPES = {"WFS", "REST", "OSM", "FILE"}
TILE_SOURCE_TYPES = {"WMS", "WMTS", "XYZ"}


@dataclass(frozen=True)
class LayerRoutingResult:
    layer_name: str
    route: str
    status: str
    source_type: str
    ingestion_method: str
    records_loaded: int = 0
    records_seen: int = 0
    message: str = ""
    artifact: str | None = None


def safe_identifier(value: str) -> str:
    text = re.sub(r"[^a-z0-9_]+", "_", (value or "").strip().lower())
    text = re.sub(r"_+", "_", text).strip("_")
    if not text:
        raise ValueError("identifier cannot be empty")
    if text[0].isdigit():
        text = f"layer_{text}"
    return text


class LayerIngestionRouter:
    def __init__(self, registry_path: Path | None = None, workspace_root: Path | None = None):
        self.registry = MasterLayerRegistryService(registry_path=registry_path or DEFAULT_REGISTRY_PATH)
        self.loader = MasterRegistryDataLoader(registry_path=registry_path or DEFAULT_REGISTRY_PATH, workspace_root=workspace_root)
        self.backend = build_backend()
        self.report_path = REPORT_PATH
        self.report_path.parent.mkdir(parents=True, exist_ok=True)

    def build_all(
        self,
        *,
        force: bool = False,
        include_osm: bool = False,
        ingest_vectors: bool = False,
        bbox: tuple[float, float, float, float] | None = None,
        max_records_per_layer: int = 5000,
        layer_names: set[str] | None = None,
        source_types: set[str] | None = None,
    ) -> dict[str, Any]:
        records = self.registry.load_records()
        selected = [
            record for record in records
            if not layer_names or record.layer_name in layer_names
            if not source_types or record.source_type in source_types
        ]

        results: list[LayerRoutingResult] = []
        for index, record in enumerate(selected, start=1):
            label = f"[{index}/{len(selected)}] {record.layer_name}"
            try:
                result = self.route_record(
                    record,
                    force=force,
                    include_osm=include_osm,
                    ingest_vectors=ingest_vectors,
                    bbox=bbox,
                    max_records=max_records_per_layer,
                )
                print(f"[DONE] {label}: {result.route} {result.status}", flush=True)
            except Exception as exc:
                print(f"[FAIL] {label}: {exc.__class__.__name__}: {exc}", flush=True)
                result = LayerRoutingResult(
                    layer_name=record.layer_name,
                    route="failed",
                    status="failed",
                    source_type=record.source_type,
                    ingestion_method=record.ingestion_method,
                    message=f"{exc.__class__.__name__}: {exc}",
                )
            results.append(result)

        report = self._report(results)
        self.report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    def route_record(
        self,
        record: MasterLayerRecord,
        *,
        force: bool,
        include_osm: bool,
        ingest_vectors: bool,
        bbox: tuple[float, float, float, float] | None,
        max_records: int,
    ) -> LayerRoutingResult:
        if record.ingestion_method == "postgis_derived":
            return LayerRoutingResult(
                layer_name=record.layer_name,
                route="derived",
                status="skipped",
                source_type=record.source_type,
                ingestion_method=record.ingestion_method,
                message="derived_layer_requires_builder",
            )

        if record.ingestion_method == "raster_derived":
            self._register_placeholder_raster_layer(record)
            return LayerRoutingResult(
                layer_name=record.layer_name,
                route="derived",
                status="registered",
                source_type=record.source_type,
                ingestion_method=record.ingestion_method,
                message="registered_as_raster_derived_placeholder",
            )

        if record.source_type in TILE_SOURCE_TYPES or record.ingestion_method == "tile" or record.geometry_type == "raster":
            self._register_tile_layer(record)
            return LayerRoutingResult(
                layer_name=record.layer_name,
                route="tile",
                status="registered",
                source_type=record.source_type,
                ingestion_method=record.ingestion_method,
                message="registered_as_external_tile_layer",
            )

        if record.source_type == "OSM":
            if not include_osm:
                return LayerRoutingResult(
                    layer_name=record.layer_name,
                    route="vector",
                    status="skipped",
                    source_type=record.source_type,
                    ingestion_method=record.ingestion_method,
                    message="osm_requires_include_osm",
                )
            if bbox is None:
                return LayerRoutingResult(
                    layer_name=record.layer_name,
                    route="vector",
                    status="skipped",
                    source_type=record.source_type,
                    ingestion_method=record.ingestion_method,
                    message="osm_requires_bbox",
                )

        if record.source_type not in VECTOR_SOURCE_TYPES:
            return LayerRoutingResult(
                layer_name=record.layer_name,
                route="unknown",
                status="skipped",
                source_type=record.source_type,
                ingestion_method=record.ingestion_method,
                message=f"unsupported_source_type_{record.source_type}",
            )

        if not ingest_vectors:
            return LayerRoutingResult(
                layer_name=record.layer_name,
                route="vector",
                status="skipped",
                source_type=record.source_type,
                ingestion_method=record.ingestion_method,
                message="vector_ingestion_disabled_by_default",
            )

        geojson, fetch_message = self._fetch_geojson(record, include_osm=include_osm, bbox=bbox, max_records=max_records)
        if geojson is None:
            return LayerRoutingResult(
                layer_name=record.layer_name,
                route="vector",
                status="skipped",
                source_type=record.source_type,
                ingestion_method=record.ingestion_method,
                message=fetch_message or "no_geojson_available",
            )

        loaded, artifact = self._store_vector_layer(record, geojson, force=force)
        self._register_vector_layer(record, loaded)
        return LayerRoutingResult(
            layer_name=record.layer_name,
            route="vector",
            status="loaded",
            source_type=record.source_type,
            ingestion_method=record.ingestion_method,
            records_seen=len(geojson.get("features") or []),
            records_loaded=loaded,
            artifact=str(artifact) if artifact else None,
        )

    def _fetch_geojson(
        self,
        record: MasterLayerRecord,
        *,
        include_osm: bool,
        bbox: tuple[float, float, float, float] | None,
        max_records: int,
    ) -> tuple[dict[str, Any] | None, str]:
        try:
            if record.source_type == "WFS":
                return self.loader._fetch_wfs(record, max_records=max_records, bbox=bbox), "ok"
            if record.source_type == "REST":
                return self.loader._fetch_rest(record, max_records=max_records, bbox=bbox), "ok"
            if record.source_type == "OSM":
                return self.loader._fetch_osm(record, bbox=bbox, max_records=max_records), "ok"
            if record.source_type == "FILE":
                if not record.endpoint_url.lower().endswith((".json", ".geojson")):
                    return None, "file_requires_geojson_endpoint"
                return self.loader._fetch_geojson_file(record, max_records=max_records), "ok"
        except Exception as exc:
            return None, f"{exc.__class__.__name__}: {exc}"
        return None, "no_fetcher_available"

    def _register_tile_layer(self, record: MasterLayerRecord) -> None:
        conn = self.backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO layers_registry (
                        layer_key, layer_name, layer_group, source_table, geometry_type,
                        is_user_selectable, is_visible, opacity, sort_order, metadata
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        TRUE, TRUE, 1.0, 500,
                        %s::jsonb
                    )
                    ON CONFLICT (layer_key) DO UPDATE
                    SET layer_name = EXCLUDED.layer_name,
                        layer_group = EXCLUDED.layer_group,
                        source_table = EXCLUDED.source_table,
                        geometry_type = EXCLUDED.geometry_type,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    (
                        record.layer_name,
                        record.layer_name,
                        record.layer_group,
                        record.endpoint_url,
                        record.db_geometry_type,
                        json.dumps({
                            "category": record.category,
                            "subcategory": record.subcategory,
                            "source_provider": record.source_provider,
                            "source_type": record.source_type,
                            "endpoint_url": record.endpoint_url,
                            "ingestion_method": record.ingestion_method,
                            "region_scope": record.region_scope,
                            "routing": "tile",
                        }),
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def _register_vector_layer(self, record: MasterLayerRecord, loaded: int) -> None:
        conn = self.backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO layers_registry (
                        layer_key, layer_name, layer_group, source_table, geometry_type,
                        is_user_selectable, is_visible, opacity, sort_order, metadata
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        TRUE, TRUE, 1.0, 500,
                        %s::jsonb
                    )
                    ON CONFLICT (layer_key) DO UPDATE
                    SET layer_name = EXCLUDED.layer_name,
                        layer_group = EXCLUDED.layer_group,
                        source_table = EXCLUDED.source_table,
                        geometry_type = EXCLUDED.geometry_type,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    (
                        record.layer_name,
                        record.layer_name,
                        record.layer_group,
                        f"data_layers.{safe_identifier(record.layer_name)}",
                        record.db_geometry_type,
                        json.dumps({
                            "category": record.category,
                            "subcategory": record.subcategory,
                            "source_provider": record.source_provider,
                            "source_type": record.source_type,
                            "endpoint_url": record.endpoint_url,
                            "ingestion_method": record.ingestion_method,
                            "region_scope": record.region_scope,
                            "routing": "vector",
                            "loaded_records": loaded,
                        }),
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def _register_placeholder_raster_layer(self, record: MasterLayerRecord) -> None:
        conn = self.backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO layers_registry (
                        layer_key, layer_name, layer_group, source_table, geometry_type,
                        is_user_selectable, is_visible, opacity, sort_order, metadata
                    )
                    VALUES (
                        %s, %s, %s, 'external_features', 'RASTER',
                        TRUE, TRUE, 1.0, 500,
                        %s::jsonb
                    )
                    ON CONFLICT (layer_key) DO UPDATE
                    SET layer_name = EXCLUDED.layer_name,
                        layer_group = EXCLUDED.layer_group,
                        source_table = EXCLUDED.source_table,
                        geometry_type = EXCLUDED.geometry_type,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    (
                        record.layer_name,
                        record.layer_name,
                        record.layer_group,
                        json.dumps({
                            "category": record.category,
                            "subcategory": record.subcategory,
                            "source_provider": record.source_provider,
                            "source_type": record.source_type,
                            "endpoint_url": record.endpoint_url,
                            "ingestion_method": record.ingestion_method,
                            "region_scope": record.region_scope,
                            "routing": "raster_derived",
                            "source_available": False,
                        }),
                    ),
                )
            conn.commit()
        finally:
            conn.close()

    def _ensure_vector_table(self, cur, table_name: str) -> None:
        cur.execute("CREATE SCHEMA IF NOT EXISTS data_layers")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS data_layers.{table_name} (
                id SERIAL PRIMARY KEY,
                geom GEOMETRY,
                properties JSONB NOT NULL DEFAULT '{{}}'::jsonb
            )
            """
        )
        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_geom_gist
            ON data_layers.{table_name}
            USING GIST (geom)
            """
        )

    def _store_vector_layer(
        self,
        record: MasterLayerRecord,
        geojson: dict[str, Any],
        *,
        force: bool,
    ) -> tuple[int, Path | None]:
        table_name = safe_identifier(record.layer_name)
        features = geojson.get("features") or []
        conn = self.backend.connect()
        inserted = 0
        artifact = self.loader._write_raw_artifact(record.layer_name, geojson)
        try:
            with conn.cursor() as cur:
                self._ensure_vector_table(cur, table_name)
                if force:
                    cur.execute(f"DELETE FROM data_layers.{table_name}")
                else:
                    cur.execute(f"SELECT COUNT(*) FROM data_layers.{table_name}")
                    existing = int((cur.fetchone() or [0])[0] or 0)
                    if existing > 0:
                        return existing, artifact

                seen: set[str] = set()
                for feature in features:
                    geometry = feature.get("geometry")
                    if not geometry:
                        continue
                    props = dict(feature.get("properties") or {})
                    props.setdefault("registry_layer", record.layer_name)
                    props.setdefault("source_provider", record.source_provider)
                    props.setdefault("source_type", record.source_type)
                    source_id = self.loader._source_id(feature, props)
                    if source_id is not None and source_id in seen:
                        continue
                    if source_id is not None:
                        seen.add(source_id)
                    cur.execute(
                        f"""
                        INSERT INTO data_layers.{table_name} (geom, properties)
                        VALUES (
                            ST_SetSRID(ST_Force2D(ST_MakeValid(ST_GeomFromGeoJSON(%s))), 4326),
                            %s::jsonb
                        )
                        """,
                        (json.dumps(geometry), json.dumps(props)),
                    )
                    inserted += 1
            conn.commit()
        finally:
            conn.close()
        return inserted, artifact

    def _report(self, results: list[LayerRoutingResult]) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for result in results:
            counts[result.status] = counts.get(result.status, 0) + 1
        return {
            "results": [asdict(result) for result in results],
            "summary": {
                "layers_processed": len(results),
                "records_loaded": sum(result.records_loaded for result in results),
                "by_status": counts,
            },
        }
