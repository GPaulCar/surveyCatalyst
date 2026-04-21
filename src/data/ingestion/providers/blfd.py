from __future__ import annotations

import json
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

    DEFAULT_TYPENAME = "ProtectedSites"

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

    def fetch_wfs_geojson(self, typename: str, max_features: int = 5000) -> dict:
        params = {
            "service": "WFS",
            "request": "GetFeature",
            "version": "2.0.0",
            "typeNames": typename,
            "outputFormat": "application/json",
            "srsName": "EPSG:4326",
            "count": max_features,
        }
        url = self.WFS_URL + "?" + urlencode(params)
        response = requests.get(url, timeout=180)
        response.raise_for_status()
        data = response.json()
        if "features" not in data:
            raise RuntimeError("BLfD WFS response did not contain GeoJSON features")
        return data

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
                            'source', source
                        ) || properties
                    )
                FROM {self.schema_name}.restricted_areas
                WHERE geom IS NOT NULL
                ''',
                ("legal_restricted_areas", f"{self.schema_name}.restricted_areas"),
            )
            inserted = cur.rowcount
        conn.commit()
        return inserted

    def run(self, force: bool = False, typename: str | None = None, max_features: int = 5000) -> ProviderResult:
        self.ensure_target_table()
        effective_typename = typename or self.DEFAULT_TYPENAME

        geojson = self.fetch_wfs_geojson(effective_typename, max_features=max_features)
        loaded = self.load_geojson_into_table(geojson, effective_typename)
        projected = self.project_to_external_features()

        self.register_layer(
            "legal_restricted_areas",
            "Restricted Areas",
            "legal.restricted_areas",
            "GEOMETRY",
            {
                "source_key": self.source_key,
                "wms_url": self.WMS_URL,
                "wfs_url": self.WFS_URL,
                "typename": effective_typename,
                "loaded": loaded,
                "projected": projected,
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
