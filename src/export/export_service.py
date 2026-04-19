from core.db import build_backend


class ExportService:
    def __init__(self):
        self.backend = build_backend()

    def export_layer_geojson(self, layer_key: str):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT jsonb_build_object(
                    'type', 'FeatureCollection',
                    'features', COALESCE(jsonb_agg(
                        jsonb_build_object(
                            'type', 'Feature',
                            'geometry', ST_AsGeoJSON(geom)::jsonb,
                            'properties', COALESCE(properties, '{}'::jsonb)
                        )
                    ), '[]'::jsonb)
                )
                FROM external_features
                WHERE layer = %s
                ''',
                (layer_key,),
            )
            return cur.fetchone()[0]
