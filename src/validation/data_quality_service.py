from __future__ import annotations

from core.db import build_backend


class DataQualityService:
    def __init__(self):
        self.backend = build_backend()

    def survey_object_issues(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT id, survey_id, type
                FROM survey_objects
                WHERE geom IS NULL OR type IS NULL OR type = ''
                ORDER BY id
                '''
            )
            return cur.fetchall()

    def external_feature_issues(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT id, layer
                FROM external_features
                WHERE geom IS NULL OR layer IS NULL OR layer = ''
                ORDER BY id
                '''
            )
            return cur.fetchall()
