from core.db import build_backend


class AggregationService:
    def __init__(self):
        self.backend = build_backend()

    def count_by_table(self, table: str):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            return cur.fetchone()[0]
