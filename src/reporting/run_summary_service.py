from __future__ import annotations

from core.db import build_backend


class RunSummaryService:
    def __init__(self):
        self.backend = build_backend()

    def latest_runs(self, limit: int = 20):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT source_key, status, message, records_loaded, layer_keys, started_at, completed_at
                FROM ingestion_runs
                ORDER BY started_at DESC, id DESC
                LIMIT %s
                ''',
                (limit,),
            )
            return cur.fetchall()

    def summary_by_source(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT source_key,
                       COUNT(*) AS runs,
                       MAX(started_at) AS last_started_at,
                       MAX(completed_at) AS last_completed_at
                FROM ingestion_runs
                GROUP BY source_key
                ORDER BY source_key
                '''
            )
            return cur.fetchall()
