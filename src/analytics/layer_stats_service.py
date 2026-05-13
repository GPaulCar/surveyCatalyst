from __future__ import annotations

from core.db import build_backend
from layers.layer_usage_service import LayerUsageService


class LayerStatsService:
    def __init__(self):
        self.backend = build_backend()

    def feature_counts(self):
        return LayerUsageService().list_layers()

    def survey_object_counts(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT survey_id, COUNT(*)
                FROM survey_objects
                WHERE is_active = TRUE
                GROUP BY survey_id
                ORDER BY survey_id
                '''
            )
            return cur.fetchall()
