from __future__ import annotations

import json
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

import requests

from data.ingestion.base import BaseProvider, ProviderResult


class BLfDProvider(BaseProvider):
    source_key = "blfd"
    source_name = "BLfD Restricted Areas"
    schema_name = "legal"
    workspace_name = "blfd"

    SERVICE_PAGE = "https://geoportal.bayern.de/geoportalbayern/anwendungen/details?resId=752ebf39-f3eb-44be-893e-3b0624273061"
    WMS_URL = "https://gdiserv.bayern.de/srv24352/services/inspire_ps_denkmal_simpl-wms"
    WFS_URL = "https://gdiserv.bayern.de/srv24352/services/inspire_ps_denkmal_simpl-wfs"

    DEFAULT_TYPENAME = "spsde:SimplifiedBavarianMonument"
    DEFAULT_MAX_FEATURES = 0
    PAGE_SIZE = 1000
    RETRY_STATUS_CODES = {429, 500, 502, 503, 504}

    def dry_run(self) -> ProviderResult:
        return ProviderResult(
            source_key=self.source_key,
            status="success",
            message="BLfD service endpoints recorded",
            artifacts=[self.SERVICE_PAGE, self.WMS_URL, self.WFS_URL],
            metadata={
                "service_page": self.SERVICE_PAGE,
                "wms_url": self.WMS_URL,
                "wfs_url": self.WFS_URL,
                "default_typename": self.DEFAULT_TYPENAME,
                "default_max_features": self.DEFAULT_MAX_FEATURES,
            },
        )

    def ensure_target_table(self) -> None:
        self.create_schema()
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {self.schema_name}.restricted_areas (
                    id SERIAL PRIMARY KEY,
                    source_id TEXT,
                    name TEXT,
                    category TEXT,
                    source TEXT NOT NULL DEFAULT 'blfd_wfs',
                    geom geometry(GEOMETRY, 4326),
                    properties JSONB NOT NULL DEFAULT '{{}}'::jsonb
                )
                '''
            )
            cur.execute(
                f'''
                CREATE INDEX IF NOT EXISTS idx_restricted_areas_geom
                ON {self.schema_name}.restricted_areas
                USING GIST (geom)
                '''
            )
        conn.commit()

    def fetch_wfs_geojson(self, typename: str, max_features: int = DEFAULT_MAX_FEATURES) -> dict:
        features = []
        offset = 0
        previous_fingerprint = None
        while max_features <= 0 or len(features) < max_features:
            request_count = self.PAGE_SIZE if max_features <= 0 else min(self.PAGE_SIZE, max_features - len(features))
            params = {
                "service": "WFS",
                "request": "GetFeature",
                "version": "2.0.0",
                "typeNames": typename,
                "outputFormat": "text/xml; subtype=gml/3.2.1",
                "srsName": "urn:ogc:def:crs:EPSG::4326",
                "count": request_count,
            }
            if offset:
                params["startIndex"] = offset
            url = self.WFS_URL + "?" + urlencode(params)
            response = self._get_wfs_page(url)
            page = self._gml_feature_collection_to_geojson(response.text, typename).get("features") or []
            fingerprint = self._feature_page_fingerprint(page)
            if offset and fingerprint and fingerprint == previous_fingerprint:
                break
            previous_fingerprint = fingerprint
            features.extend(page)
            print(f"[PAGE] BLfD WFS: offset={offset} got={len(page)} total={len(features)}", flush=True)
            if not page or len(page) < request_count:
                break
            offset += len(page)
            time.sleep(0.2)
        return {"type": "FeatureCollection", "features": features if max_features <= 0 else features[:max_features]}

    def _get_wfs_page(self, url: str) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(1, 5):
            try:
                response = requests.get(url, timeout=180)
                if response.status_code in self.RETRY_STATUS_CODES and attempt < 4:
                    wait_seconds = min(2 ** attempt, 30)
                    print(f"[WARN] BLfD WFS HTTP {response.status_code}; retrying in {wait_seconds}s", flush=True)
                    time.sleep(wait_seconds)
                    continue
                response.raise_for_status()
                return response
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
                last_error = exc
                status_code = exc.response.status_code if isinstance(exc, requests.HTTPError) and exc.response is not None else None
                if status_code is not None and status_code not in self.RETRY_STATUS_CODES:
                    raise
                if attempt >= 4:
                    raise
                wait_seconds = min(2 ** attempt, 30)
                print(f"[WARN] BLfD WFS request failed; retrying in {wait_seconds}s: {exc}", flush=True)
                time.sleep(wait_seconds)
        if last_error is not None:
            raise last_error
        raise RuntimeError("BLfD WFS request failed without a captured error")

    def staged_feature_count(self) -> int:
        conn = self.backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {self.schema_name}.restricted_areas WHERE source = 'blfd_wfs'")
                return int((cur.fetchone() or [0])[0] or 0)
        finally:
            conn.close()

    def _feature_page_fingerprint(self, features: list[dict]) -> tuple[str, ...] | None:
        if not features:
            return None
        keys = []
        for feature in features[:5]:
            feature_id = feature.get("id") or (feature.get("properties") or {}).get("gml_id")
            keys.append(str(feature_id) if feature_id is not None else json.dumps(feature.get("geometry"), sort_keys=True)[:120])
        return tuple(keys)

    def _gml_feature_collection_to_geojson(self, xml_text: str, typename: str) -> dict:
        ns = {
            "gml": "http://www.opengis.net/gml/3.2",
            "wfs": "http://www.opengis.net/wfs/2.0",
        }
        root = ET.fromstring(xml_text)
        features = []
        for member in root.findall(".//wfs:member", ns):
            if not list(member):
                continue
            source = list(member)[0]
            geometry = self._feature_geometry(source, ns)
            if geometry is None:
                continue
            props = self._feature_properties(source, ns)
            feature_id = source.attrib.get(f"{{{ns['gml']}}}id") or props.get("id") or props.get("identifier")
            features.append(
                {
                    "type": "Feature",
                    "id": feature_id,
                    "geometry": geometry,
                    "properties": {
                        **props,
                        "gml_id": feature_id,
                        "typename": typename,
                    },
                }
            )
        return {"type": "FeatureCollection", "features": features}

    def _feature_properties(self, feature: ET.Element, ns: dict[str, str]) -> dict:
        props = {}
        for child in list(feature):
            if self._contains_geometry(child, ns):
                continue
            key = self._local_name(child.tag)
            text = " ".join("".join(child.itertext()).split())
            if text:
                props[key] = text
        return props

    def _feature_geometry(self, feature: ET.Element, ns: dict[str, str]) -> dict | None:
        polygon = feature.find(".//gml:Polygon", ns)
        if polygon is not None:
            return self._gml_polygon_to_geojson(polygon, ns)
        multi_surface = feature.find(".//gml:MultiSurface", ns)
        if multi_surface is not None:
            polygons = []
            for surface_member in multi_surface.findall(".//gml:surfaceMember", ns):
                member_polygon = surface_member.find(".//gml:Polygon", ns)
                if member_polygon is None:
                    continue
                polygon_geometry = self._gml_polygon_to_geojson(member_polygon, ns)
                if polygon_geometry:
                    polygons.append(polygon_geometry["coordinates"])
            if polygons:
                return {"type": "MultiPolygon", "coordinates": polygons}
        return None

    def _gml_polygon_to_geojson(self, polygon: ET.Element, ns: dict[str, str]) -> dict | None:
        rings = []
        exterior = polygon.find(".//gml:exterior/gml:LinearRing/gml:posList", ns)
        if exterior is not None and exterior.text:
            rings.append(self._pos_list_to_ring(exterior.text))
        for interior in polygon.findall(".//gml:interior/gml:LinearRing/gml:posList", ns):
            if interior.text:
                rings.append(self._pos_list_to_ring(interior.text))
        rings = [ring for ring in rings if len(ring) >= 4]
        if not rings:
            return None
        return {"type": "Polygon", "coordinates": rings}

    def _pos_list_to_ring(self, text: str) -> list[list[float]]:
        values = [float(value) for value in text.split()]
        coords = []
        for index in range(0, len(values) - 1, 2):
            lat = values[index]
            lon = values[index + 1]
            coords.append([lon, lat])
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        return coords

    def _contains_geometry(self, element: ET.Element, ns: dict[str, str]) -> bool:
        return element.find(".//gml:Polygon", ns) is not None or element.find(".//gml:MultiSurface", ns) is not None

    def _local_name(self, tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    def load_geojson_into_table(self, geojson: dict, typename: str) -> int:
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {self.schema_name}.restricted_areas WHERE source = 'blfd_wfs'")
            inserted = 0
            for feature in geojson.get("features", []):
                props = feature.get("properties") or {}
                geom = feature.get("geometry")
                if not geom:
                    continue
                source_id = props.get("id") or props.get("gml_id") or props.get("identifier")
                name = props.get("name") or props.get("bezeichnung") or props.get("title")
                category = props.get("category") or props.get("denkmalart") or typename

                cur.execute(
                    f'''
                    INSERT INTO {self.schema_name}.restricted_areas
                        (source_id, name, category, source, geom, properties)
                    VALUES
                        (%s, %s, %s, 'blfd_wfs',
                         ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326),
                         %s::jsonb)
                    ''',
                    (
                        str(source_id) if source_id is not None else None,
                        name,
                        category,
                        json.dumps(geom),
                        json.dumps(props),
                    ),
                )
                inserted += 1
        conn.commit()
        return inserted

    def project_to_external_features(self) -> int:
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM external_features WHERE layer = %s", ("legal_restricted_areas",))
            cur.execute(
                f'''
                INSERT INTO external_features (layer, source_table, source_id, geom, properties)
                SELECT
                    %s,
                    %s,
                    source_id,
                    geom,
                    jsonb_strip_nulls(
                        jsonb_build_object(
                            'name', name,
                            'category', category,
                            'source', source,
                            'legal_severity',
                                CASE
                                    WHEN lower(COALESCE(category, '') || ' ' || COALESCE(name, '') || ' ' || properties::text)
                                         ~ '(bodendenkmal|archaeolog|archaeological|ground monument)'
                                        THEN 'high'
                                    WHEN lower(COALESCE(category, '') || ' ' || COALESCE(name, '') || ' ' || properties::text)
                                         ~ '(denkmal|monument|protected|cultural|restricted)'
                                        THEN 'medium'
                                    ELSE 'medium'
                                END,
                            'restriction_label',
                                CASE
                                    WHEN lower(COALESCE(category, '') || ' ' || COALESCE(name, '') || ' ' || properties::text)
                                         ~ '(bodendenkmal|archaeolog|archaeological|ground monument)'
                                        THEN 'High legal restriction'
                                    WHEN lower(COALESCE(category, '') || ' ' || COALESCE(name, '') || ' ' || properties::text)
                                         ~ '(denkmal|monument|protected|cultural|restricted)'
                                        THEN 'Protected/restricted area'
                                    ELSE 'Restriction requires verification'
                                END,
                            'metal_detecting_status', 'Restricted - verify legal permission before detecting'
                        ) || properties
                    )
                FROM {self.schema_name}.restricted_areas
                WHERE geom IS NOT NULL
                  AND source = 'blfd_wfs'
                ''',
                ("legal_restricted_areas", f"{self.schema_name}.restricted_areas"),
            )
            inserted = cur.rowcount
        conn.commit()
        return inserted

    def run(self, force: bool = False, typename: str | None = None, max_features: int = DEFAULT_MAX_FEATURES) -> ProviderResult:
        self.ensure_target_table()
        effective_typename = typename or self.DEFAULT_TYPENAME

        staged = self.staged_feature_count()
        if staged > 0 and not force and typename is None:
            projected = self.project_to_external_features()
            self.register_layer(
                "legal_restricted_areas",
                "No Metal Detecting / Legal Restrictions",
                "legal.restricted_areas",
                "GEOMETRY",
                {
                    "source_key": self.source_key,
                    "subgroup": "legal_permission",
                    "wms_url": self.WMS_URL,
                    "wfs_url": self.WFS_URL,
                    "typename": effective_typename,
                    "loaded": staged,
                    "projected": projected,
                    "cached": True,
                    "always_show": True,
                    "severity_field": "legal_severity",
                    "description": "Protected and restricted areas where metal detecting may be prohibited or require explicit permission. Verify current legal status before fieldwork.",
                },
                sort_order=230,
            )
            return ProviderResult(
                source_key=self.source_key,
                status="success",
                message=f"BLfD existing staged data reused ({staged} staged, {projected} projected); use --force to refresh WFS",
                records_loaded=projected,
                layer_keys=["legal_restricted_areas"],
                artifacts=[self.WFS_URL],
                metadata={
                    "typename": effective_typename,
                    "loaded": staged,
                    "projected": projected,
                    "cached": True,
                },
            )

        geojson = self.fetch_wfs_geojson(effective_typename, max_features=max_features)
        loaded = self.load_geojson_into_table(geojson, effective_typename)
        projected = self.project_to_external_features()

        self.register_layer(
            "legal_restricted_areas",
            "No Metal Detecting / Legal Restrictions",
            "legal.restricted_areas",
            "GEOMETRY",
            {
                "source_key": self.source_key,
                "subgroup": "legal_permission",
                "wms_url": self.WMS_URL,
                "wfs_url": self.WFS_URL,
                "typename": effective_typename,
                "loaded": loaded,
                "projected": projected,
                "always_show": True,
                "severity_field": "legal_severity",
                "description": "Protected and restricted areas where metal detecting may be prohibited or require explicit permission. Verify current legal status before fieldwork.",
            },
            sort_order=230,
        )

        return ProviderResult(
            source_key=self.source_key,
            status="success",
            message=f"BLfD WFS ingestion complete ({loaded} loaded, {projected} projected)",
            records_loaded=projected,
            layer_keys=["legal_restricted_areas"],
            artifacts=[self.WFS_URL],
            metadata={
                "typename": effective_typename,
                "loaded": loaded,
                "projected": projected,
            },
        )
