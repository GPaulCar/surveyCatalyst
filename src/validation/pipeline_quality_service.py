from __future__ import annotations

from core.db import build_backend


class PipelineQualityService:
    def __init__(self):
        self.backend = build_backend()

    def source_quality(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT source_key,
                       COUNT(*) FILTER (WHERE status = 'failed') AS failed_runs,
                       COUNT(*) FILTER (WHERE status = 'success') AS successful_runs,
                       MAX(completed_at) AS last_completed_at
                FROM ingestion_runs
                GROUP BY source_key
                ORDER BY source_key
                '''
            )
            return cur.fetchall()

    def external_feature_quality(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT layer,
                       COUNT(*) AS total_rows,
                       COUNT(*) FILTER (WHERE geom IS NULL) AS null_geom_rows,
                       COUNT(*) FILTER (WHERE layer IS NULL OR layer = '') AS missing_layer_rows
                FROM external_features
                GROUP BY layer
                ORDER BY layer
                '''
            )
            return cur.fetchall()
