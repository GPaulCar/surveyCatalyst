from __future__ import annotations

from core.db import build_backend


class SurveyLinkService:
    def __init__(self):
        self.backend = build_backend()

    def get_survey_with_objects(self, survey_id: int):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT id, expedition_id, title, status, ST_AsText(geom), layer_key
                FROM surveys
                WHERE id = %s
                ''',
                (survey_id,),
            )
            survey = cur.fetchone()

            cur.execute(
                '''
                SELECT id, survey_id, layer_key, type, properties, ST_AsText(geom), is_active
                FROM survey_objects
                WHERE survey_id = %s
                ORDER BY id
                ''',
                (survey_id,),
            )
            objects = cur.fetchall()
        return {"survey": survey, "objects": objects}

    def find_parent_survey_for_object(self, object_id: int):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT s.id, s.title, s.layer_key
                FROM survey_objects so
                JOIN surveys s ON s.id = so.survey_id
                WHERE so.id = %s
                ''',
                (object_id,),
            )
            return cur.fetchone()
