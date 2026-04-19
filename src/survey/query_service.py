from __future__ import annotations

from core.db import build_backend


class SurveyQueryService:
    def __init__(self):
        self.backend = build_backend()

    def list_surveys(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT id, expedition_id, title, status
                FROM surveys
                ORDER BY id
                '''
            )
            return cur.fetchall()

    def get_survey(self, survey_id: int):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT id, expedition_id, title, status, ST_AsText(geom)
                FROM surveys
                WHERE id = %s
                ''',
                (survey_id,),
            )
            return cur.fetchone()

    def list_survey_objects(self, survey_id: int):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT id, survey_id, expedition_id, type, properties, ST_AsText(geom)
                FROM survey_objects
                WHERE survey_id = %s
                ORDER BY id
                ''',
                (survey_id,),
            )
            return cur.fetchall()

    def linked_and_contained_features(self, survey_id: int):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT ef.id, ef.layer, ef.properties
                FROM external_features ef
                JOIN surveys s ON s.id = %s
                WHERE s.geom IS NOT NULL
                  AND ef.geom IS NOT NULL
                  AND ST_Intersects(ef.geom, s.geom)
                ORDER BY ef.id
                ''',
                (survey_id,),
            )
            return cur.fetchall()
