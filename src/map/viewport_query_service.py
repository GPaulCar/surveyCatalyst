from __future__ import annotations

from core.db import build_backend


class ViewportQueryService:
    def __init__(self):
        self.backend = build_backend()

    def features_for_layer_bbox(self, layer_key: str, minx: float, miny: float, maxx: float, maxy: float):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                WITH env AS (
                    SELECT ST_MakeEnvelope(%s, %s, %s, %s, 4326) AS bbox
                )
                SELECT jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(jsonb_agg(
                        jsonb_build_object(
                            'type', 'Feature',
                            'geometry', ST_AsGeoJSON(geom)::jsonb,
                            'properties', properties || jsonb_build_object('id', id, 'layer', layer)
                        )
                    ), '[]'::jsonb)
                )
                FROM external_features, env
                WHERE layer = %s
                  AND geom IS NOT NULL
                  AND ST_Intersects(geom, env.bbox)
                ''',
                (minx, miny, maxx, maxy, layer_key),
            )
            result = cur.fetchone()[0]
        return result
