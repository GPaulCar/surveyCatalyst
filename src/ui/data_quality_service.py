from __future__ import annotations

from core.db import build_backend


class DataQualityService:
    def __init__(self):
        self.backend = build_backend()

    def null_geometry_rows(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT layer, COUNT(*)
                FROM external_features
                WHERE geom IS NULL
                GROUP BY layer
                ORDER BY layer
                '''
            )
            return cur.fetchall()

    def invalid_survey_links(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT so.id
                FROM survey_objects so
                LEFT JOIN surveys s ON s.id = so.survey_id
                WHERE s.id IS NULL
                ORDER BY so.id
                '''
            )
            return cur.fetchall()
