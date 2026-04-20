from core.db import build_backend
import json

class ExportService:
    def __init__(self):
        self.backend = build_backend()

    def export_table_geojson(self, table: str, geom_col="geom"):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(f'''
                SELECT jsonb_build_object(
                    'type','FeatureCollection',
                    'features', jsonb_agg(
                        jsonb_build_object(
                            'type','Feature',
                            'geometry', ST_AsGeoJSON({geom_col})::jsonb,
                            'properties', to_jsonb(t) - '{geom_col}'
                        )
                    )
                )
                FROM {table} t
            ''')
            return cur.fetchone()[0]
