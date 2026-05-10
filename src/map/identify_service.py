from __future__ import annotations

import json
import math
import urllib.parse
from dataclasses import dataclass
from typing import Any

import requests

from core.db import build_backend


DEFAULT_INFO_FORMATS = (
    "application/json",
    "application/geo+json",
    "text/plain",
    "text/html",
)


@dataclass
class IdentifyLayer:
    layer_key: str
    layer_name: str
    source_type: str | None
    service_url: str | None
    service_layer: str | None
    metadata: dict[str, Any]


class LayerIdentifyService:
    def __init__(self):
        self.backend = build_backend()

    def identify(
        self,
        *,
        layer_keys: list[str],
        bbox: tuple[float, float, float, float],
        size: tuple[int, int],
        pixel: tuple[int, int],
        limit: int = 5,
    ) -> dict[str, Any]:
        layers = self._load_layers(layer_keys)
        hits: list[dict[str, Any]] = []

        for layer in layers:
            if layer.source_type == "WMS" and layer.service_url:
                hit = self._identify_wms_layer(layer, bbox=bbox, size=size, pixel=pixel, limit=limit)
                if hit:
                    hits.extend(hit)
                continue

            if layer.source_type == "WMTS" and layer.service_url:
                hit = self._identify_wmts_layer(layer, bbox=bbox, size=size, pixel=pixel, limit=limit)
                hits.append(hit)
                continue

            if layer.source_type == "XYZ" and layer.service_url:
                hits.append(self._tile_context_hit(layer, bbox=bbox, size=size, pixel=pixel, identify_kind="xyz_tile"))
                continue

        return {
            "bbox": list(bbox),
            "size": list(size),
            "pixel": list(pixel),
            "checked_layers": [layer.layer_key for layer in layers],
            "hits": hits,
            "count": len(hits),
        }

    def _load_layers(self, layer_keys: list[str]) -> list[IdentifyLayer]:
        if not layer_keys:
            return []

        conn = self.backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT layer_key, layer_name, metadata
                    FROM layers_registry
                    WHERE layer_key = ANY(%s)
                    ORDER BY sort_order, layer_name
                    """,
                    (layer_keys,),
                )
                rows = cur.fetchall()
        finally:
            conn.close()

        layers: list[IdentifyLayer] = []
        for row in rows:
            metadata = row[2] or {}
            layers.append(
                IdentifyLayer(
                    layer_key=row[0],
                    layer_name=row[1],
                    source_type=str(metadata.get("source_type") or "").upper() or None,
                    service_url=self._service_url(metadata),
                    service_layer=self._service_layer(row[0], metadata),
                    metadata=metadata,
                )
            )
        return layers

    def _service_url(self, metadata: dict[str, Any]) -> str | None:
        service_url = str(metadata.get("service_url") or metadata.get("endpoint_url") or "").strip()
        if not service_url:
            return None
        parsed = urllib.parse.urlparse(service_url)
        return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

    def _service_layer(self, layer_key: str, metadata: dict[str, Any]) -> str | None:
        service_layer = str(metadata.get("service_layer") or "").strip()
        if service_layer:
            return service_layer
        if metadata.get("source_type") == "WMS":
            return layer_key
        return None

    def _identify_wms_layer(
        self,
        layer: IdentifyLayer,
        *,
        bbox: tuple[float, float, float, float],
        size: tuple[int, int],
        pixel: tuple[int, int],
        limit: int,
    ) -> list[dict[str, Any]] | None:
        base_url = layer.service_url
        service_layer = layer.service_layer
        if not base_url or not service_layer:
            return None

        widths = max(int(size[0]), 1)
        heights = max(int(size[1]), 1)
        x = min(max(int(pixel[0]), 0), widths - 1)
        y = min(max(int(pixel[1]), 0), heights - 1)
        bbox_text = ",".join(str(v) for v in bbox)

        for info_format in DEFAULT_INFO_FORMATS:
            params = {
                "service": "WMS",
                "version": "1.1.1",
                "request": "GetFeatureInfo",
                "layers": service_layer,
                "query_layers": service_layer,
                "bbox": bbox_text,
                "width": str(widths),
                "height": str(heights),
                "srs": "EPSG:4326",
                "x": str(x),
                "y": str(y),
                "feature_count": str(limit),
                "info_format": info_format,
                "format": "image/png",
                "styles": "",
            }
            try:
                response = requests.get(
                    base_url,
                    params=params,
                    timeout=40,
                    headers={"User-Agent": "surveyCatalyst/identify-service"},
                )
                if not response.ok:
                    continue
            except Exception:
                continue

            parsed = self._parse_response(layer, response, info_format)
            if parsed:
                return parsed.get("hits") or []

        return None

    def _identify_wmts_layer(
        self,
        layer: IdentifyLayer,
        *,
        bbox: tuple[float, float, float, float],
        size: tuple[int, int],
        pixel: tuple[int, int],
        limit: int,
    ) -> dict[str, Any]:
        # WMTS usually does not expose feature info in a uniform way across providers.
        # Return a tile-context record so the UI still has meaningful inspect data.
        context = self._tile_context(layer, bbox=bbox, size=size, pixel=pixel)
        context["identify_kind"] = "wmts_tile_context"
        context["properties"]["identify_kind"] = "wmts_tile_context"

        # Best-effort feature info request for providers that support it.
        attempt = self._identify_wmts_feature_info(layer, bbox=bbox, size=size, pixel=pixel, limit=limit)
        if attempt:
            return attempt
        return context

    def _identify_wmts_feature_info(
        self,
        layer: IdentifyLayer,
        *,
        bbox: tuple[float, float, float, float],
        size: tuple[int, int],
        pixel: tuple[int, int],
        limit: int,
    ) -> dict[str, Any] | None:
        # This is intentionally best-effort. Many WMTS services do not support it, or
        # require capability-derived matrix settings we do not have locally.
        base_url = layer.service_url
        if not base_url:
            return None

        widths = max(int(size[0]), 1)
        heights = max(int(size[1]), 1)
        x = min(max(int(pixel[0]), 0), widths - 1)
        y = min(max(int(pixel[1]), 0), heights - 1)
        lon, lat = self._pixel_to_lonlat(bbox=bbox, size=size, pixel=pixel)
        z, tile_x, tile_y = self._lonlat_to_xyz(lon, lat)

        matrix_set = layer.metadata.get("tile_matrix_set") or layer.metadata.get("matrix_set") or "EPSG:3857"
        params = {
            "service": "WMTS",
            "request": "GetFeatureInfo",
            "version": "1.0.0",
            "layer": layer.service_layer or layer.layer_key,
            "tilematrixset": matrix_set,
            "tilematrix": str(z),
            "tilerow": str(tile_y),
            "tilecol": str(tile_x),
            "i": str(x),
            "j": str(y),
            "feature_count": str(limit),
            "info_format": "application/json",
        }
        try:
            response = requests.get(
                base_url,
                params=params,
                timeout=40,
                headers={"User-Agent": "surveyCatalyst/identify-service"},
            )
        except Exception:
            return None

        if not response.ok:
            return None

        parsed = self._parse_response(layer, response, "application/json")
        if parsed:
            return parsed
        return None

    def _parse_response(self, layer: IdentifyLayer, response: requests.Response, info_format: str) -> dict[str, Any] | None:
        content_type = response.headers.get("content-type", "")
        text = response.text.strip()
        payload: Any = None

        if "json" in content_type or info_format.endswith("json") or text.startswith("{") or text.startswith("["):
            try:
                payload = response.json()
            except Exception:
                payload = None

        if isinstance(payload, dict):
            features = payload.get("features")
            results = payload.get("results")

            if isinstance(features, list) and features:
                items = [self._normalise_json_hit(layer, feature, response, info_format) for feature in features]
                return self._build_result(layer, response, info_format, items)

            if isinstance(results, list) and results:
                items = [self._normalise_json_hit(layer, result, response, info_format) for result in results]
                return self._build_result(layer, response, info_format, items)

            if payload:
                items = [self._normalise_json_hit(layer, payload, response, info_format)]
                return self._build_result(layer, response, info_format, items)

        if text:
            return self._build_result(
                layer,
                response,
                info_format,
                [
                    {
                        "layer_key": layer.layer_key,
                        "layer_name": layer.layer_name,
                        "content_type": content_type,
                        "info_format": info_format,
                        "raw": text,
                        "properties": {},
                    }
                ],
            )

        return None

    def _tile_context_hit(
        self,
        layer: IdentifyLayer,
        *,
        bbox: tuple[float, float, float, float],
        size: tuple[int, int],
        pixel: tuple[int, int],
        identify_kind: str,
    ) -> dict[str, Any]:
        context = self._tile_context(layer, bbox=bbox, size=size, pixel=pixel)
        context["identify_kind"] = identify_kind
        context["properties"]["identify_kind"] = identify_kind
        return context

    def _tile_context(
        self,
        layer: IdentifyLayer,
        *,
        bbox: tuple[float, float, float, float],
        size: tuple[int, int],
        pixel: tuple[int, int],
    ) -> dict[str, Any]:
        lon, lat = self._pixel_to_lonlat(bbox=bbox, size=size, pixel=pixel)
        z = self._estimate_zoom(bbox=bbox, size=size)
        tile_x, tile_y = self._lonlat_to_xyz(lon, lat, z)
        tile_url = self._sample_tile_url(layer.service_url or "", z=z, x=tile_x, y=tile_y)
        return {
            "layer_key": layer.layer_key,
            "layer_name": layer.layer_name,
            "service_url": layer.service_url,
            "service_layer": layer.service_layer,
            "source_type": layer.source_type,
            "status": "ok",
            "content_type": "application/json",
            "info_format": "tile-context",
            "identify_kind": "tile_context",
            "hits": [
                {
                    "layer_key": layer.layer_key,
                    "layer_name": layer.layer_name,
                    "title": layer.layer_name,
                    "content_type": "application/json",
                    "info_format": "tile-context",
                    "identify_kind": "tile_context",
                    "properties": {
                        "layer_key": layer.layer_key,
                        "layer_name": layer.layer_name,
                        "source_type": layer.source_type,
                        "service_url": layer.service_url,
                        "service_layer": layer.service_layer,
                        "tile_z": z,
                        "tile_x": tile_x,
                        "tile_y": tile_y,
                        "click_lon": lon,
                        "click_lat": lat,
                        "sample_tile_url": tile_url,
                        "note": "Tile layers do not expose feature attributes through a standard identify protocol.",
                    },
                    "raw": {
                        "layer_key": layer.layer_key,
                        "service_url": layer.service_url,
                        "sample_tile_url": tile_url,
                        "tile_z": z,
                        "tile_x": tile_x,
                        "tile_y": tile_y,
                        "click_lon": lon,
                        "click_lat": lat,
                    },
                }
            ],
            "count": 1,
        }

    def _pixel_to_lonlat(
        self,
        *,
        bbox: tuple[float, float, float, float],
        size: tuple[int, int],
        pixel: tuple[int, int],
    ) -> tuple[float, float]:
        min_lon, min_lat, max_lon, max_lat = bbox
        width = max(int(size[0]), 1)
        height = max(int(size[1]), 1)
        x = min(max(int(pixel[0]), 0), width - 1)
        y = min(max(int(pixel[1]), 0), height - 1)
        lon = min_lon + (max_lon - min_lon) * (x / width)
        lat = max_lat - (max_lat - min_lat) * (y / height)
        return lon, lat

    def _estimate_zoom(self, *, bbox: tuple[float, float, float, float], size: tuple[int, int]) -> int:
        min_lon, _, max_lon, _ = bbox
        lon_span = max(max_lon - min_lon, 1e-9)
        width = max(int(size[0]), 1)
        resolution_deg = lon_span / width
        zoom = round(math.log2(360.0 / max(resolution_deg * 256.0, 1e-9)))
        return max(0, min(22, zoom))

    def _lonlat_to_xyz(self, lon: float, lat: float, zoom: int) -> tuple[int, int]:
        lat = max(min(lat, 85.05112878), -85.05112878)
        lat_rad = math.radians(lat)
        tile_x = int((lon + 180.0) / 360.0 * (1 << zoom))
        tile_y = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * (1 << zoom))
        return tile_x, tile_y

    def _sample_tile_url(self, template: str, *, z: int, x: int, y: int) -> str:
        if not template:
            return ""
        url = template.replace("{z}", str(z)).replace("{x}", str(x)).replace("{y}", str(y))
        if "{a-c}" in url:
            url = url.replace("{a-c}", "a")
        return url

    def _normalise_json_hit(self, layer: IdentifyLayer, payload: dict[str, Any], response: requests.Response, info_format: str) -> dict[str, Any]:
        properties = self._extract_properties(payload)
        title = self._extract_title(properties, payload)
        return {
            "layer_key": layer.layer_key,
            "layer_name": layer.layer_name,
            "content_type": response.headers.get("content-type", ""),
            "info_format": info_format,
            "title": title,
            "properties": properties,
            "raw": payload,
        }

    def _extract_properties(self, payload: dict[str, Any]) -> dict[str, Any]:
        if isinstance(payload.get("properties"), dict):
            return dict(payload["properties"])
        if isinstance(payload.get("attributes"), dict):
            return dict(payload["attributes"])
        if isinstance(payload.get("properties"), list):
            return {"properties": payload["properties"]}
        if isinstance(payload.get("feature"), dict):
            return self._extract_properties(payload["feature"])
        if isinstance(payload.get("feature"), list):
            return {"feature": payload["feature"]}
        return dict(payload)

    def _extract_title(self, properties: dict[str, Any], payload: dict[str, Any]) -> str:
        for key in ("title", "name", "label", "layer_name", "layer", "class", "type"):
            value = properties.get(key) or payload.get(key)
            if value not in (None, ""):
                return str(value)
        return "Feature"

    def _build_result(
        self,
        layer: IdentifyLayer,
        response: requests.Response,
        info_format: str,
        hits: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "layer_key": layer.layer_key,
            "layer_name": layer.layer_name,
            "service_url": layer.service_url,
            "service_layer": layer.service_layer,
            "source_type": layer.source_type,
            "status": "ok",
            "content_type": response.headers.get("content-type", ""),
            "info_format": info_format,
            "hits": hits,
            "count": len(hits),
        }
