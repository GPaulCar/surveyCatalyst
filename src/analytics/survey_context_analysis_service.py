from __future__ import annotations

from core.db import build_backend


class SurveyContextAnalysisService:
    def __init__(self):
        self.backend = build_backend()

    def intersecting_context_counts(self, survey_id: int):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT ef.layer, COUNT(*)
                FROM surveys s
                JOIN external_features ef
                  ON s.geom IS NOT NULL
                 AND ef.geom IS NOT NULL
                 AND ST_Intersects(s.geom, ef.geom)
                WHERE s.id = %s
                GROUP BY ef.layer
                ORDER BY ef.layer
                ''',
                (survey_id,),
            )
            return cur.fetchall()

    def linked_summary(self, survey_id: int):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT id, title, layer_key, ST_AsText(geom)
                FROM surveys
                WHERE id = %s
                ''',
                (survey_id,),
            )
            survey = cur.fetchone()
        return {
            "survey": survey,
            "context_counts": self.intersecting_context_counts(survey_id),
        }
