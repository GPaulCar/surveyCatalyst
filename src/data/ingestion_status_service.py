from core.db import build_backend


class IngestionStatusService:
    def __init__(self):
        self.backend = build_backend()

    def summary(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT source_key, status, started_at, completed_at
                FROM ingestion_runs
                ORDER BY started_at DESC, id DESC
                '''
            )
            return cur.fetchall()
