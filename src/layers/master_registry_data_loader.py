from __future__ import annotations

import json
import time
import urllib.parse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests

from core.db import build_backend
from layers.master_registry_service import MasterLayerRecord, MasterLayerRegistryService


ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "workspace" / "master_registry_load_report.json"
RAW_DIR = ROOT / "workspace" / "downloads" / "raw" / "master_registry"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


@dataclass
class LayerLoadResult:
    layer_name: str
    status: str
    source_type: str
    ingestion_method: str
    records_loaded: int = 0
    records_seen: int = 0
    message: str = ""
    artifact: str | None = None


class MasterRegistryDataLoader:
    def __init__(self, registry_path: Path | None = None, workspace_root: Path | None = None):
        self.registry = MasterLayerRegistryService(registry_path=registry_path)
        self.backend = build_backend()
        self.workspace_root = Path(workspace_root or ROOT / "workspace")
        self.raw_dir = self.workspace_root / "downloads" / "raw" / "master_registry"
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def plan(
        self,
        include_osm: bool = False,
        bbox: tuple[float, float, float, float] | None = None,
        layer_names: set[str] | None = None,
        source_types: set[str] | None = None,
    ) -> dict[str, Any]:
        records = self.registry.load_records()
        loadable = []
        skipped = []
        for record in records:
            if layer_names and record.layer_name not in layer_names:
                continue
            if source_types and record.source_type not in source_types:
                continue
            reason = self._skip_reason(record, include_osm=include_osm, bbox=bbox)
            if reason:
                skipped.append({"layer_name": record.layer_name, "reason": reason})
            else:
                loadable.append(record.layer_name)
        return {
            "total": len(records),
            "loadable": len(loadable),
            "skipped": len(skipped),
            "loadable_layers": loadable,
            "skipped_layers": skipped,
        }

    def load_all(
        self,
        *,
        force: bool = False,
        include_osm: bool = False,
        bbox: tuple[float, float, float, float] | None = None,
        max_records_per_layer: int = 5000,
        layer_names: set[str] | None = None,
        source_types: set[str] | None = None,
    ) -> dict[str, Any]:
        records = self.registry.load_records()
        results: list[LayerLoadResult] = []

        for record in records:
            if layer_names and record.layer_name not in layer_names:
                continue
            if source_types and record.source_type not in source_types:
                continue

            reason = self._skip_reason(record, include_osm=include_osm, bbox=bbox)
            if reason:
                results.append(
                    LayerLoadResult(
                        layer_name=record.layer_name,
                        status="skipped",
                        source_type=record.source_type,
                        ingestion_method=record.ingestion_method,
                        message=reason,
                    )
                )
                continue

            if not force:
                existing = self._layer_count(record.layer_name)
                if existing > 0:
                    results.append(
                        LayerLoadResult(
                            layer_name=record.layer_name,
                            status="skipped",
                            source_type=record.source_type,
                            ingestion_method=record.ingestion_method,
                            records_loaded=existing,
                            message="already_loaded",
                        )
                    )
                    continue

            try:
                result = self._load_record(record, bbox=bbox, max_records=max_records_per_layer, force=force)
            except Exception as exc:
                result = LayerLoadResult(
                    layer_name=record.layer_name,
                    status="failed",
                    source_type=record.source_type,
                    ingestion_method=record.ingestion_method,
                    message=f"{exc.__class__.__name__}: {exc}",
                )
            results.append(result)

        report = self._report(results)
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    def _skip_reason(
        self,
        record: MasterLayerRecord,
        *,
        include_osm: bool,
        bbox: tuple[float, float, float, float] | None,
    ) -> str | None:
        if record.ingestion_method == "tile":
            return "tile_service_registered_only"
        if record.ingestion_method == "external":
            return "external_service_registered_only"
        if record.ingestion_method == "postgis_derived":
            return "derived_layer_requires_base_layers"
        if record.geometry_type == "raster":
            return "raster_layer_not_loaded_to_external_features"
        if record.source_type == "OSM" and not include_osm:
            return "osm_requires_include_osm"
        if record.source_type == "OSM" and bbox is None:
            return "osm_requires_bbox"
        if record.source_type == "FILE" and not record.endpoint_url.lower().endswith((".json", ".geojson")):
            return "file_format_requires_manual_or_optional_parser"
        if record.source_type not in {"WFS", "REST", "OSM", "FILE"}:
            return f"unsupported_source_type_{record.source_type}"
        return None

    def _load_record(
        self,
        record: MasterLayerRecord,
        *,
        bbox: tuple[float, float, float, float] | None,
        max_records: int,
        force: bool,
    ) -> LayerLoadResult:
        if record.source_type == "WFS":
            geojson = self._fetch_wfs(record, max_records=max_records)
        elif record.source_type == "REST":
            geojson = self._fetch_rest(record, max_records=max_records)
        elif record.source_type == "OSM":
            if bbox is None:
                raise ValueError("bbox is required for OSM")
            geojson = self._fetch_osm(record, bbox=bbox, max_records=max_records)
        elif record.source_type == "FILE":
            geojson = self._fetch_geojson_file(record, max_records=max_records)
        else:
            raise ValueError(f"Unsupported source type: {record.source_type}")

        artifact = self._write_raw_artifact(record.layer_name, geojson)
        loaded = self._store_features(record, geojson.get("features") or [], force=force)
        return LayerLoadResult(
            layer_name=record.layer_name,
            status="loaded",
            source_type=record.source_type,
            ingestion_method=record.ingestion_method,
            records_seen=len(geojson.get("features") or []),
            records_loaded=loaded,
            artifact=str(artifact),
        )

    def _fetch_wfs(self, record: MasterLayerRecord, *, max_records: int) -> dict[str, Any]:
        url, params = self._split_url(record.endpoint_url)
        params.setdefault("service", "WFS")
        params.setdefault("request", "GetFeature")
        params.setdefault("outputFormat", "application/json")
        params.setdefault("srsName", "EPSG:4326")
        params.setdefault("count", str(max_records))
        params.setdefault("maxFeatures", str(max_records))
        response = requests.get(url, params=params, timeout=240, headers=self._headers())
        response.raise_for_status()
        data = response.json()
        if data.get("type") == "FeatureCollection":
            return data
        if "features" in data:
            return {"type": "FeatureCollection", "features": data["features"]}
        raise RuntimeError("WFS response did not contain GeoJSON features")

    def _fetch_rest(self, record: MasterLayerRecord, *, max_records: int) -> dict[str, Any]:
        endpoint = record.endpoint_url
        if "/items" in endpoint:
            return self._fetch_ogc_items(endpoint, max_records=max_records)
        if "/MapServer/" in endpoint or "/FeatureServer/" in endpoint:
            return self._fetch_arcgis_layer(endpoint, max_records=max_records)
        raise RuntimeError("REST endpoint is not an OGC API items URL or ArcGIS layer URL")

    def _fetch_ogc_items(self, endpoint: str, *, max_records: int) -> dict[str, Any]:
        url, params = self._split_url(endpoint)
        params.setdefault("f", "json")
        params.setdefault("limit", str(max_records))
        response = requests.get(url, params=params, timeout=240, headers=self._headers())
        response.raise_for_status()
        data = response.json()
        if data.get("type") == "FeatureCollection":
            return data
        if "features" in data:
            return {"type": "FeatureCollection", "features": data["features"]}
        raise RuntimeError("OGC API response did not contain features")

    def _fetch_arcgis_layer(self, endpoint: str, *, max_records: int) -> dict[str, Any]:
        query_url = endpoint.rstrip("/") + "/query"
        features: list[dict[str, Any]] = []
        page_size = min(max_records, 2000)
        offset = 0
        while len(features) < max_records:
            params = {
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": "geojson",
                "resultOffset": str(offset),
                "resultRecordCount": str(min(page_size, max_records - len(features))),
            }
            response = requests.get(query_url, params=params, timeout=240, headers=self._headers())
            response.raise_for_status()
            data = response.json()
            page = data.get("features") or []
            features.extend(page)
            if not page or not data.get("exceededTransferLimit"):
                break
            offset += len(page)
            time.sleep(0.2)
        return {"type": "FeatureCollection", "features": features[:max_records]}

    def _fetch_geojson_file(self, record: MasterLayerRecord, *, max_records: int) -> dict[str, Any]:
        response = requests.get(record.endpoint_url, timeout=240, headers=self._headers())
        response.raise_for_status()
        data = response.json()
        features = data.get("features") or []
        return {"type": "FeatureCollection", "features": features[:max_records]}

    def _fetch_osm(
        self,
        record: MasterLayerRecord,
        *,
        bbox: tuple[float, float, float, float],
        max_records: int,
    ) -> dict[str, Any]:
        query = self._overpass_query(record, bbox=bbox, max_records=max_records)
        response = requests.post(
            OVERPASS_URL,
            data={"data": query},
            timeout=600,
            headers=self._headers(),
        )
        response.raise_for_status()
        data = response.json()
        features = self._osm_elements_to_features(data.get("elements") or [], record)
        return {"type": "FeatureCollection", "features": features[:max_records]}

    def _overpass_query(
        self,
        record: MasterLayerRecord,
        *,
        bbox: tuple[float, float, float, float],
        max_records: int,
    ) -> str:
        minx, miny, maxx, maxy = bbox
        box = f"{miny},{minx},{maxy},{maxx}"
        selectors = {
            "osm_archaeological_sites": [
                'nwr["historic"="archaeological_site"]',
                'nwr["archaeology"]',
                'nwr["site_type"]',
            ],
            "osm_roman_roads": [
                'way["historic"="roman_road"]',
                'way["historic"="road"]["roman"="yes"]',
                'way["roman"="yes"]',
            ],
            "osm_burial_tumulus_sites": [
                'nwr["historic"="tomb"]',
                'nwr["site_type"~"tumulus|burial|grave"]',
                'nwr["megalith_type"="dolmen"]',
            ],
            "osm_historic_cemeteries": [
                'nwr["landuse"="cemetery"]',
                'nwr["amenity"="grave_yard"]',
            ],
            "osm_rivers": [
                'way["waterway"="river"]',
                'way["waterway"="riverbank"]',
            ],
            "osm_streams": [
                'way["waterway"~"stream|ditch|drain"]',
            ],
            "osm_wetlands": [
                'nwr["natural"="wetland"]',
                'nwr["wetland"]',
            ],
            "osm_roads": [
                'way["highway"]["highway"!~"proposed|construction"]',
            ],
            "osm_tracks_paths": [
                'way["highway"~"track|path|service"]',
            ],
            "osm_railways": [
                'way["railway"~"rail|tram|disused|abandoned"]',
            ],
            "osm_modern_settlements": [
                'node["place"]',
                'way["landuse"="residential"]',
                'relation["landuse"="residential"]',
            ],
        }.get(record.layer_name)
        if not selectors:
            raise ValueError(f"No Overpass selector configured for {record.layer_name}")
        body = "\n  ".join(f"{selector}({box});" for selector in selectors)
        return f"""
[out:json][timeout:300];
(
  {body}
);
out tags geom {max_records};
"""

    def _osm_elements_to_features(self, elements: list[dict[str, Any]], record: MasterLayerRecord) -> list[dict[str, Any]]:
        features: list[dict[str, Any]] = []
        for element in elements:
            feature = self._osm_element_to_feature(element, record)
            if feature:
                features.append(feature)
        return features

    def _osm_element_to_feature(self, element: dict[str, Any], record: MasterLayerRecord) -> dict[str, Any] | None:
        tags = element.get("tags") or {}
        osm_type = element.get("type")
        osm_id = element.get("id")
        if osm_type == "node" and "lon" in element and "lat" in element:
            geometry = {"type": "Point", "coordinates": [element["lon"], element["lat"]]}
        else:
            coords = [[point["lon"], point["lat"]] for point in element.get("geometry") or [] if "lon" in point and "lat" in point]
            if len(coords) < 2:
                return None
            if record.geometry_type == "polygon" or (len(coords) > 3 and coords[0] == coords[-1]):
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                geometry = {"type": "Polygon", "coordinates": [coords]}
            else:
                geometry = {"type": "LineString", "coordinates": coords}
        props = dict(tags)
        props.update(
            {
                "source": "osm_overpass_master_registry",
                "osm_type": osm_type,
                "osm_id": osm_id,
                "registry_layer": record.layer_name,
            }
        )
        return {"type": "Feature", "geometry": geometry, "id": f"{osm_type}/{osm_id}", "properties": props}

    def _store_features(self, record: MasterLayerRecord, features: list[dict[str, Any]], *, force: bool) -> int:
        conn = self.backend.connect()
        inserted = 0
        seen: set[tuple[str, str | None]] = set()
        try:
            with conn.cursor() as cur:
                if force:
                    cur.execute("DELETE FROM external_features WHERE layer = %s", (record.layer_name,))
                for feature in features:
                    geometry = feature.get("geometry")
                    if not geometry:
                        continue
                    props = dict(feature.get("properties") or {})
                    props.setdefault("registry_layer", record.layer_name)
                    props.setdefault("source_provider", record.source_provider)
                    props.setdefault("source_type", record.source_type)
                    source_id = self._source_id(feature, props)
                    dedupe_key = (record.layer_name, source_id)
                    if source_id is not None and dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    cur.execute(
                        """
                        INSERT INTO external_features (layer, geom, properties, source_table, source_id)
                        VALUES (
                            %s,
                            ST_SetSRID(ST_Force2D(ST_MakeValid(ST_GeomFromGeoJSON(%s))), 4326),
                            %s::jsonb,
                            %s,
                            %s
                        )
                        """,
                        (
                            record.layer_name,
                            json.dumps(geometry),
                            json.dumps(props),
                            record.source_table,
                            source_id,
                        ),
                    )
                    inserted += 1
            conn.commit()
        finally:
            conn.close()
        return inserted

    def _source_id(self, feature: dict[str, Any], props: dict[str, Any]) -> str | None:
        value = feature.get("id")
        if value is None:
            for key in ("id", "gml_id", "identifier", "OBJECTID", "objectid", "fid", "osm_id"):
                if props.get(key) is not None:
                    value = props[key]
                    break
        return str(value) if value is not None else None

    def _layer_count(self, layer_name: str) -> int:
        conn = self.backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM external_features WHERE layer = %s", (layer_name,))
                return int((cur.fetchone() or [0])[0] or 0)
        finally:
            conn.close()

    def _write_raw_artifact(self, layer_name: str, data: dict[str, Any]) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in layer_name)
        path = self.raw_dir / f"{safe}.geojson"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def _split_url(self, endpoint_url: str) -> tuple[str, dict[str, str]]:
        parsed = urllib.parse.urlparse(endpoint_url)
        params = {key: values[-1] for key, values in urllib.parse.parse_qs(parsed.query).items() if values}
        url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
        return url, params

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": "surveyCatalyst/0.6 master-registry-loader"}

    def _report(self, results: list[LayerLoadResult]) -> dict[str, Any]:
        counts: dict[str, int] = {}
        for result in results:
            counts[result.status] = counts.get(result.status, 0) + 1
        return {
            "results": [asdict(result) for result in results],
            "summary": {
                "layers_processed": len(results),
                "records_loaded": sum(result.records_loaded for result in results if result.status == "loaded"),
                "by_status": counts,
            },
        }
