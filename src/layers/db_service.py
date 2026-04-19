from __future__ import annotations

from core.db import build_backend


class DBLayerService:
    def __init__(self):
        self.backend = build_backend()

    def list_layer_records(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                ORDER BY table_schema, table_name
                '''
            )
            rows = cur.fetchall()
        return rows

    def list_external_features(self, table_name: str, limit: int = 100):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                f'''
                SELECT id, properties
                FROM {table_name}
                LIMIT %s
                ''',
                (limit,),
            )
            return cur.fetchall()
