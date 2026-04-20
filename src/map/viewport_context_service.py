from __future__ import annotations

from core.db import build_backend


class ViewportContextService:
    def __init__(self):
        self.backend = build_backend()

    def geojson_for_layer_bbox(self, layer_key: str, minx: float, miny: float, maxx: float, maxy: float):
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
                            'geometry', ST_AsGeoJSON(ef.geom)::jsonb,
                            'properties', COALESCE(ef.properties, '{}'::jsonb) || jsonb_build_object(
                                'id', ef.id,
                                'layer', ef.layer,
                                'source_table', ef.source_table
                            )
                        )
                    ), '[]'::jsonb)
                )
                FROM external_features ef, env
                WHERE ef.layer = %s
                  AND ef.geom IS NOT NULL
                  AND ST_Intersects(ef.geom, env.bbox)
                ''',
                (minx, miny, maxx, maxy, layer_key),
            )
            return cur.fetchone()[0]
