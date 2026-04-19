from __future__ import annotations

from core.db import build_backend


class FeatureService:
    def __init__(self):
        self.backend = build_backend()

    def get_layer_geojson(self, layer_key: str):
        conn = self.backend.connect()

        with conn.cursor() as cur:
            # survey-backed layer
            cur.execute(
                """
                SELECT jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(jsonb_agg(
                        jsonb_build_object(
                            'type', 'Feature',
                            'geometry', ST_AsGeoJSON(geom)::jsonb,
                            'properties', properties || jsonb_build_object(
                                'id', id,
                                'type', type,
                                'layer_key', layer_key
                            )
                        )
                    ), '[]'::jsonb)
                )
                FROM survey_objects
                WHERE layer_key = %s AND is_active = TRUE
                """,
                (layer_key,),
            )
            result = cur.fetchone()[0]

            if result["features"]:
                return result

            # fallback → external_features
            cur.execute(
                """
                SELECT jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(jsonb_agg(
                        jsonb_build_object(
                            'type', 'Feature',
                            'geometry', ST_AsGeoJSON(geom)::jsonb,
                            'properties', properties || jsonb_build_object(
                                'id', id,
                                'layer', layer
                            )
                        )
                    ), '[]'::jsonb)
                )
                FROM external_features
                WHERE layer = %s
                """,
                (layer_key,),
            )
            return cur.fetchone()[0]