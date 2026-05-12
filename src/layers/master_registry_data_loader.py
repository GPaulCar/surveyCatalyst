from __future__ import annotations

import json
import math
import time
import urllib.parse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests
from requests import Response

from core.db import build_backend
from layers.master_registry_service import MasterLayerRecord, MasterLayerRegistryService


ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = ROOT / "workspace" / "master_registry_load_report.json"
RAW_DIR = ROOT / "workspace" / "downloads" / "raw" / "master_registry"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_URLS = [
    "https://overpass.kumi.systems/api/interpreter",
    OVERPASS_URL,
]
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
REQUEST_TIMEOUT_SECONDS = 240
OVERPASS_MIN_INTERVAL_SECONDS = 2.0


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
        self._last_overpass_request_at = 0.0

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
        selected_records = [
            record for record in records
            if not layer_names or record.layer_name in layer_names
            if not source_types or record.source_type in source_types
        ]
        results: list[LayerLoadResult] = []

        for index, record in enumerate(selected_records, start=1):
            progress_label = f"[{index}/{len(selected_records)}] {record.layer_name}"

            reason = self._skip_reason(record, include_osm=include_osm, bbox=bbox)
            if reason:
                print(f"[SKIP] {progress_label}: {reason}", flush=True)
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
                    print(f"[SKIP] {progress_label}: already_loaded ({existing})", flush=True)
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
                print(
                    f"[LOAD] {progress_label}: {record.source_type} {record.ingestion_method}",
                    flush=True,
                )
                result = self._load_record(record, bbox=bbox, max_records=max_records_per_layer, force=force)
                print(
                    f"[DONE] {progress_label}: seen={result.records_seen} loaded={result.records_loaded}",
                    flush=True,
                )
            except Exception as exc:
                print(f"[FAIL] {progress_label}: {exc.__class__.__name__}: {exc}", flush=True)
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
        if record.ingestion_method in {"postgis_derived", "raster_derived"}:
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
            geojson = self._fetch_wfs(record, max_records=max_records, bbox=bbox)
        elif record.source_type == "REST":
            geojson = self._fetch_rest(record, max_records=max_records, bbox=bbox)
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

    def _limit_reached(self, features: list[Any], max_records: int) -> bool:
        return max_records > 0 and len(features) >= max_records

    def _remaining_count(self, max_records: int, current_count: int, default_page_size: int) -> int:
        if max_records <= 0:
            return default_page_size
        return min(default_page_size, max_records - current_count)

    def _limit_features(self, features: list[dict[str, Any]], max_records: int) -> list[dict[str, Any]]:
        if max_records <= 0:
            return features
        return features[:max_records]

    def _bbox_param(self, bbox: tuple[float, float, float, float], *, include_crs: bool = False) -> str:
        minx, miny, maxx, maxy = bbox
        value = f"{minx},{miny},{maxx},{maxy}"
        if include_crs:
            return f"{value},EPSG:4326"
        return value

    def _feature_page_fingerprint(self, features: list[dict[str, Any]]) -> tuple[str, ...] | None:
        if not features:
            return None
        keys = []
        for feature in features[:5]:
            props = feature.get("properties") or {}
            feature_id = feature.get("id") or props.get("id") or props.get("OBJECTID") or props.get("objectid")
            keys.append(str(feature_id) if feature_id is not None else json.dumps(feature.get("geometry"), sort_keys=True)[:120])
        return tuple(keys)

    def _fetch_wfs(
        self,
        record: MasterLayerRecord,
        *,
        max_records: int,
        bbox: tuple[float, float, float, float] | None,
    ) -> dict[str, Any]:
        url, params = self._split_url(record.endpoint_url)
        params.setdefault("service", "WFS")
        params.setdefault("request", "GetFeature")
        params.setdefault("outputFormat", "application/json")
        params.setdefault("srsName", "EPSG:4326")
        return self._fetch_wfs_pages(
            url,
            params,
            max_records=max_records,
            bbox=bbox,
            context=f"WFS {record.layer_name}",
        )

    def _fetch_wfs_pages(
        self,
        url: str,
        base_params: dict[str, str],
        *,
        max_records: int,
        bbox: tuple[float, float, float, float] | None,
        context: str,
    ) -> dict[str, Any]:
        features: list[dict[str, Any]] = []
        offset = 0
        page_size = 1000
        previous_fingerprint: tuple[str, ...] | None = None

        while not self._limit_reached(features, max_records):
            request_count = self._remaining_count(max_records, len(features), page_size)
            params = dict(base_params)
            params["count"] = str(request_count)
            params["maxFeatures"] = str(request_count)
            if offset:
                params["startIndex"] = str(offset)
            if bbox is not None:
                params.setdefault("bbox", self._bbox_param(bbox, include_crs=True))

            data = self._request_json("GET", url, params=params, context=context)
            if data.get("type") == "FeatureCollection":
                page = data.get("features") or []
            elif "features" in data:
                page = data["features"] or []
            else:
                raise RuntimeError("WFS response did not contain GeoJSON features")

            fingerprint = self._feature_page_fingerprint(page)
            if offset and fingerprint and fingerprint == previous_fingerprint:
                break
            previous_fingerprint = fingerprint

            features.extend(page)
            print(f"[PAGE] {context}: offset={offset} got={len(page)} total={len(features)}", flush=True)
            if not page or len(page) < request_count:
                break
            offset += len(page)
            time.sleep(0.2)

        return {"type": "FeatureCollection", "features": self._limit_features(features, max_records)}

    def _fetch_rest(
        self,
        record: MasterLayerRecord,
        *,
        max_records: int,
        bbox: tuple[float, float, float, float] | None,
    ) -> dict[str, Any]:
        endpoint = record.endpoint_url
        if "/items" in endpoint:
            return self._fetch_ogc_items(endpoint, max_records=max_records, bbox=bbox)
        if "/MapServer" in endpoint or "/FeatureServer" in endpoint:
            return self._fetch_arcgis(record, max_records=max_records, bbox=bbox)
        raise RuntimeError("REST endpoint is not an OGC API items URL or ArcGIS layer URL")

    def _fetch_ogc_items(
        self,
        endpoint: str,
        *,
        max_records: int,
        bbox: tuple[float, float, float, float] | None,
    ) -> dict[str, Any]:
        url, params = self._split_url(endpoint)
        params.setdefault("f", "json")
        if bbox is not None:
            params.setdefault("bbox", self._bbox_param(bbox))

        features: list[dict[str, Any]] = []
        offset = 0
        page_size = 1000
        while not self._limit_reached(features, max_records):
            request_count = self._remaining_count(max_records, len(features), page_size)
            page_params = dict(params)
            page_params["limit"] = str(request_count)
            if offset:
                page_params.setdefault("offset", str(offset))
            try:
                data = self._request_json("GET", url, params=page_params, context=f"OGC API {url}")
            except RuntimeError:
                fallback = self._fetch_hessen_denkx_wfs(endpoint, max_records=max_records, bbox=bbox)
                if fallback is None:
                    raise
                return fallback

            if data.get("type") == "FeatureCollection":
                page = data.get("features") or []
            elif "features" in data:
                page = data["features"] or []
            else:
                fallback = self._fetch_hessen_denkx_wfs(endpoint, max_records=max_records, bbox=bbox)
                if fallback is not None:
                    return fallback
                raise RuntimeError("OGC API response did not contain features")

            features.extend(page)
            print(f"[PAGE] OGC API {url}: offset={offset} got={len(page)} total={len(features)}", flush=True)
            if not page:
                break

            next_href = self._ogc_next_href(data)
            if next_href:
                url, params = self._split_url(urllib.parse.urljoin(url, next_href))
                params.setdefault("f", "json")
                if bbox is not None:
                    params.setdefault("bbox", self._bbox_param(bbox))
                offset = 0
                continue

            if len(page) < request_count:
                break
            offset += len(page)
            time.sleep(0.2)

        return {"type": "FeatureCollection", "features": self._limit_features(features, max_records)}

    def _fetch_hessen_denkx_wfs(
        self,
        endpoint: str,
        *,
        max_records: int,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> dict[str, Any] | None:
        typename = self._hessen_denkx_typename(endpoint)
        if not typename:
            return None
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": typename,
            "outputFormat": "application/json",
            "srsName": "EPSG:4326",
        }
        return self._fetch_wfs_pages(
            "https://geodienste.denkx.de/geoserver/denkx/wfs",
            params,
            max_records=max_records,
            bbox=bbox,
            context=f"Hessen DenkX WFS {typename}",
        )

    def _ogc_next_href(self, data: dict[str, Any]) -> str | None:
        for link in data.get("links") or []:
            if not isinstance(link, dict):
                continue
            rel = str(link.get("rel") or "").lower()
            if rel == "next" and link.get("href"):
                return str(link["href"])
        return None

    def _hessen_denkx_typename(self, endpoint: str) -> str | None:
        parsed = urllib.parse.urlparse(endpoint)
        if parsed.netloc.lower() != "www.geoportal.hessen.de":
            return None
        parts = parsed.path.strip("/").split("/")
        try:
            collection_index = parts.index("collections")
        except ValueError:
            return None
        if collection_index + 1 >= len(parts):
            return None
        typename = urllib.parse.unquote(parts[collection_index + 1])
        return typename if typename.startswith("denkx:") else None

    def _fetch_arcgis(
        self,
        record: MasterLayerRecord,
        *,
        max_records: int,
        bbox: tuple[float, float, float, float] | None,
    ) -> dict[str, Any]:
        endpoint = record.endpoint_url.rstrip("/")
        if self._arcgis_endpoint_has_layer_id(endpoint):
            return self._fetch_arcgis_layer(endpoint, max_records=max_records, bbox=bbox)
        return self._fetch_arcgis_service(record, max_records=max_records, bbox=bbox)

    def _fetch_arcgis_service(
        self,
        record: MasterLayerRecord,
        *,
        max_records: int,
        bbox: tuple[float, float, float, float] | None,
    ) -> dict[str, Any]:
        endpoint = record.endpoint_url.rstrip("/")
        service_meta = self._request_json(
            "GET",
            endpoint,
            params={"f": "json"},
            context=f"ArcGIS service {record.layer_name}",
        )
        layers = service_meta.get("layers") or []
        layer_candidates = self._select_arcgis_service_layers(record, layers)
        if not layer_candidates:
            raise RuntimeError("ArcGIS service did not expose a matching vector layer")

        features: list[dict[str, Any]] = []
        for layer_meta in layer_candidates:
            if self._limit_reached(features, max_records):
                break
            layer_id = layer_meta.get("id")
            if layer_id is None:
                continue
            layer_url = f"{endpoint}/{layer_id}"
            remaining = 0 if max_records <= 0 else max_records - len(features)
            page = self._fetch_arcgis_layer(layer_url, max_records=remaining, bbox=bbox)
            for feature in page.get("features") or []:
                props = feature.get("properties")
                if not isinstance(props, dict):
                    props = {}
                    feature["properties"] = props
                props.setdefault("arcgis_service_layer_id", layer_id)
                if layer_meta.get("name"):
                    props.setdefault("arcgis_service_layer_name", layer_meta.get("name"))
                features.append(feature)

        return {"type": "FeatureCollection", "features": self._limit_features(features, max_records)}

    def _fetch_arcgis_layer(
        self,
        endpoint: str,
        *,
        max_records: int,
        bbox: tuple[float, float, float, float] | None,
    ) -> dict[str, Any]:
        query_url = endpoint.rstrip("/") + "/query"
        last_error: Exception | None = None
        for output_format in ("geojson", "json"):
            for page_size in self._arcgis_page_sizes(max_records):
                try:
                    return self._fetch_arcgis_layer_pages(
                        query_url,
                        max_records=max_records,
                        bbox=bbox,
                        output_format=output_format,
                        page_size=page_size,
                    )
                except requests.HTTPError as exc:
                    last_error = exc
                    status_code = exc.response.status_code if exc.response is not None else None
                    if output_format == "geojson" and status_code in {400, 404}:
                        continue
                    if status_code not in RETRY_STATUS_CODES:
                        raise
                except requests.Timeout as exc:
                    last_error = exc
                except RuntimeError as exc:
                    last_error = exc
                    if output_format == "json":
                        raise
        if last_error is not None:
            raise last_error
        raise RuntimeError("ArcGIS query failed without a captured error")

    def _fetch_arcgis_layer_pages(
        self,
        query_url: str,
        *,
        max_records: int,
        bbox: tuple[float, float, float, float] | None,
        output_format: str,
        page_size: int,
    ) -> dict[str, Any]:
        features: list[dict[str, Any]] = []
        offset = 0
        while not self._limit_reached(features, max_records):
            request_count = self._remaining_count(max_records, len(features), page_size)
            params = {
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": "true",
                "outSR": "4326",
                "f": output_format,
                "resultOffset": str(offset),
                "resultRecordCount": str(request_count),
            }
            if bbox is not None:
                minx, miny, maxx, maxy = bbox
                params.update(
                    {
                        "geometry": f"{minx},{miny},{maxx},{maxy}",
                        "geometryType": "esriGeometryEnvelope",
                        "inSR": "4326",
                        "spatialRel": "esriSpatialRelIntersects",
                    }
                )
            data = self._request_json("GET", query_url, params=params, context=f"ArcGIS query {query_url}")
            if "error" in data:
                error = data["error"]
                message = error.get("message") if isinstance(error, dict) else str(error)
                raise RuntimeError(f"ArcGIS query error: {message}")
            if output_format == "json":
                page = self._arcgis_json_features_to_geojson(data.get("features") or [])
            else:
                raw_page = data.get("features") or []
                if raw_page and "attributes" in raw_page[0]:
                    page = self._arcgis_json_features_to_geojson(raw_page)
                else:
                    page = raw_page
            features.extend(page)
            print(
                f"[PAGE] ArcGIS {query_url}: offset={offset} got={len(page)} total={len(features)}",
                flush=True,
            )
            exceeded = bool(data.get("exceededTransferLimit") or data.get("properties", {}).get("exceededTransferLimit"))
            if not page or (not exceeded and len(page) < request_count):
                break
            offset += len(page)
            time.sleep(0.2)
        return {"type": "FeatureCollection", "features": self._limit_features(features, max_records)}

    def _fetch_geojson_file(self, record: MasterLayerRecord, *, max_records: int) -> dict[str, Any]:
        data = self._request_json("GET", record.endpoint_url, context=f"GeoJSON file {record.layer_name}")
        features = data.get("features") or []
        return {"type": "FeatureCollection", "features": self._limit_features(features, max_records)}

    def _fetch_osm(
        self,
        record: MasterLayerRecord,
        *,
        bbox: tuple[float, float, float, float],
        max_records: int,
    ) -> dict[str, Any]:
        features: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        tiles = self._osm_tiles(bbox) if max_records <= 0 else [bbox]
        for index, tile in enumerate(tiles, start=1):
            if self._limit_reached(features, max_records):
                break
            remaining = 0 if max_records <= 0 else max_records - len(features)
            query = self._overpass_query(record, bbox=tile, max_records=remaining)
            data = self._request_overpass_json(query, context=f"Overpass {record.layer_name} tile {index}/{len(tiles)}")
            page = self._osm_elements_to_features(data.get("elements") or [], record)
            added = 0
            for feature in page:
                feature_id = str(feature.get("id") or "")
                if feature_id and feature_id in seen_ids:
                    continue
                if feature_id:
                    seen_ids.add(feature_id)
                features.append(feature)
                added += 1
                if self._limit_reached(features, max_records):
                    break
            print(
                f"[PAGE] Overpass {record.layer_name}: tile={index}/{len(tiles)} got={len(page)} added={added} total={len(features)}",
                flush=True,
            )
        return {"type": "FeatureCollection", "features": self._limit_features(features, max_records)}

    def _osm_tiles(self, bbox: tuple[float, float, float, float]) -> list[tuple[float, float, float, float]]:
        minx, miny, maxx, maxy = bbox
        lon_parts = max(1, math.ceil((maxx - minx) / 1.75))
        lat_parts = max(1, math.ceil((maxy - miny) / 1.25))
        lon_step = (maxx - minx) / lon_parts
        lat_step = (maxy - miny) / lat_parts
        tiles = []
        for y_index in range(lat_parts):
            tile_miny = miny + y_index * lat_step
            tile_maxy = maxy if y_index == lat_parts - 1 else miny + (y_index + 1) * lat_step
            for x_index in range(lon_parts):
                tile_minx = minx + x_index * lon_step
                tile_maxx = maxx if x_index == lon_parts - 1 else minx + (x_index + 1) * lon_step
                tiles.append((tile_minx, tile_miny, tile_maxx, tile_maxy))
        return tiles

    def _request_overpass_json(self, query: str, *, context: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for endpoint in OVERPASS_URLS:
            try:
                self._throttle_overpass()
                return self._request_json(
                    "POST",
                    endpoint,
                    data={"data": query},
                    timeout=600,
                    retries=4,
                    context=context,
                )
            except requests.HTTPError as exc:
                last_error = exc
                status_code = exc.response.status_code if exc.response is not None else None
                if status_code not in RETRY_STATUS_CODES:
                    raise
            except (requests.Timeout, requests.ConnectionError, RuntimeError) as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
        raise RuntimeError("Overpass request failed without a captured error")

    def _throttle_overpass(self) -> None:
        elapsed = time.monotonic() - self._last_overpass_request_at
        if elapsed < OVERPASS_MIN_INTERVAL_SECONDS:
            time.sleep(OVERPASS_MIN_INTERVAL_SECONDS - elapsed)
        self._last_overpass_request_at = time.monotonic()

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
        out_limit = f" {max_records}" if max_records > 0 else ""
        return f"""
[out:json][timeout:300];
(
  {body}
);
out tags geom{out_limit};
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

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        timeout: int = REQUEST_TIMEOUT_SECONDS,
        retries: int = 3,
        context: str,
    ) -> dict[str, Any]:
        response = self._request(
            method,
            url,
            params=params,
            data=data,
            timeout=timeout,
            retries=retries,
        )
        try:
            return response.json()
        except ValueError as exc:
            content_type = response.headers.get("content-type", "unknown")
            snippet = " ".join((response.text or "").split())[:300]
            if not snippet:
                snippet = "<empty response body>"
            raise RuntimeError(
                f"{context} returned non-JSON response "
                f"({response.status_code}, content-type={content_type}): {snippet}"
            ) from exc

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        timeout: int,
        retries: int,
    ) -> Response:
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                response = requests.request(
                    method,
                    url,
                    params=params,
                    data=data,
                    timeout=timeout,
                    headers=self._headers(),
                )
                if response.status_code in RETRY_STATUS_CODES and attempt < retries - 1:
                    time.sleep(self._retry_delay(response, attempt))
                    continue
                response.raise_for_status()
                return response
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
                if attempt >= retries - 1:
                    raise
                time.sleep(self._retry_delay(None, attempt))
            except requests.HTTPError as exc:
                last_error = exc
                response = exc.response
                status_code = response.status_code if response is not None else None
                if status_code not in RETRY_STATUS_CODES or attempt >= retries - 1:
                    raise
                time.sleep(self._retry_delay(response, attempt))
        if last_error is not None:
            raise last_error
        raise RuntimeError(f"{method} {url} failed without a captured error")

    def _retry_delay(self, response: Response | None, attempt: int) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return min(float(retry_after), 60.0)
                except ValueError:
                    pass
        return min(2.0 ** attempt, 30.0)

    def _arcgis_endpoint_has_layer_id(self, endpoint: str) -> bool:
        last_part = urllib.parse.urlparse(endpoint).path.rstrip("/").split("/")[-1]
        return last_part.isdigit()

    def _select_arcgis_service_layers(
        self,
        record: MasterLayerRecord,
        layers: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        expected_geometry = {
            "point": "esriGeometryPoint",
            "line": "esriGeometryPolyline",
            "polygon": "esriGeometryPolygon",
        }.get(record.geometry_type)
        vector_layers = [
            layer for layer in layers
            if not layer.get("subLayerIds")
            and (layer.get("type", "Feature Layer") == "Feature Layer" or layer.get("geometryType"))
        ]
        if expected_geometry:
            matching_geometry = [layer for layer in vector_layers if layer.get("geometryType") == expected_geometry]
            if matching_geometry:
                vector_layers = matching_geometry
        tokens = self._record_search_tokens(record)
        scored = [(self._layer_match_score(layer, tokens), layer) for layer in vector_layers]
        if not scored:
            return []
        best_score = max(score for score, _layer in scored)
        if best_score > 0:
            return [layer for score, layer in scored if score == best_score][:3]
        return [scored[0][1]]

    def _record_search_tokens(self, record: MasterLayerRecord) -> set[str]:
        text = f"{record.layer_name} {record.notes}"
        normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
        stop_words = {
            "arcgis",
            "bgr",
            "eea",
            "esri",
            "feature",
            "features",
            "from",
            "layer",
            "line",
            "mapserver",
            "polygon",
            "rest",
            "service",
            "the",
            "use",
            "with",
        }
        return {token for token in normalized.split() if len(token) > 2 and token not in stop_words}

    def _layer_match_score(self, layer: dict[str, Any], tokens: set[str]) -> int:
        searchable = " ".join(str(layer.get(key) or "") for key in ("name", "description", "type")).lower()
        return sum(1 for token in tokens if token in searchable)

    def _arcgis_page_sizes(self, max_records: int) -> list[int]:
        if max_records <= 0:
            return [1000, 500, 100]
        candidates = [1000, 500, 100]
        sizes = [min(max_records, size) for size in candidates]
        return [size for index, size in enumerate(sizes) if size > 0 and size not in sizes[:index]]

    def _arcgis_json_features_to_geojson(self, features: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        for feature in features:
            geometry = self._arcgis_geometry_to_geojson(feature.get("geometry") or {})
            if geometry is None:
                continue
            props = dict(feature.get("attributes") or feature.get("properties") or {})
            feature_id = feature.get("id") or props.get("OBJECTID") or props.get("objectid")
            converted.append(
                {
                    "type": "Feature",
                    "id": feature_id,
                    "geometry": geometry,
                    "properties": props,
                }
            )
        return converted

    def _arcgis_geometry_to_geojson(self, geometry: dict[str, Any]) -> dict[str, Any] | None:
        if "x" in geometry and "y" in geometry:
            return {"type": "Point", "coordinates": [geometry["x"], geometry["y"]]}
        if "points" in geometry:
            return {"type": "MultiPoint", "coordinates": geometry.get("points") or []}
        if "paths" in geometry:
            paths = geometry.get("paths") or []
            if len(paths) == 1:
                return {"type": "LineString", "coordinates": paths[0]}
            return {"type": "MultiLineString", "coordinates": paths}
        if "rings" in geometry:
            rings = [self._closed_ring(ring) for ring in geometry.get("rings") or [] if len(ring) >= 3]
            if not rings:
                return None
            return {"type": "Polygon", "coordinates": rings}
        return None

    def _closed_ring(self, ring: list[list[float]]) -> list[list[float]]:
        if ring and ring[0] != ring[-1]:
            return [*ring, ring[0]]
        return ring

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
        return {
            "User-Agent": "surveyCatalyst/0.6 master-registry-loader",
            "Accept": "application/geo+json, application/json;q=0.9, */*;q=0.1",
        }

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
