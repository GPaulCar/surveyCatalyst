from __future__ import annotations

from core.db import build_backend


class ExportPipelineService:
    def __init__(self):
        self.backend = build_backend()

    def export_layer_geojson(self, layer_key: str):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT jsonb_build_object(
                    'type','FeatureCollection',
                    'features', COALESCE(jsonb_agg(
                        jsonb_build_object(
                            'type','Feature',
                            'geometry', ST_AsGeoJSON(geom)::jsonb,
                            'properties', properties
                        )
                    ), '[]'::jsonb)
                )
                FROM external_features
                WHERE layer = %s
                ''',
                (layer_key,)
            )
            return cur.fetchone()[0]
