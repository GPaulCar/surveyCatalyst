from __future__ import annotations

from core.db import build_backend


class AlertService:
    def __init__(self):
        self.backend = build_backend()

    def check_failures(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT source_key, COUNT(*)
                FROM ingestion_runs
                WHERE status='failed'
                GROUP BY source_key
                '''
            )
            return cur.fetchall()
