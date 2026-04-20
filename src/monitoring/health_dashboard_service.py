from __future__ import annotations

from core.db import build_backend


class HealthDashboardService:
    def __init__(self):
        self.backend = build_backend()

    def overview(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM external_features")
            features = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM ingestion_runs WHERE status='failed'")
            failed = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM ingestion_runs")
            runs = cur.fetchone()[0]

        return {
            "total_features": features,
            "failed_runs": failed,
            "total_runs": runs
        }
