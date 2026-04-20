from core.db import build_backend


class ReportService:
    def __init__(self):
        self.backend = build_backend()

    def tables_summary(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog','information_schema')
                ORDER BY table_schema, table_name
                '''
            )
            return cur.fetchall()
