from __future__ import annotations

from core.db import build_backend


class SurveyPanelService:
    def __init__(self):
        self.backend = build_backend()

    def list_surveys(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT id, title FROM surveys ORDER BY id")
            return [{"id": r[0], "title": r[1]} for r in cur.fetchall()]

    def get_survey_objects(self, survey_id: int):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, ST_AsText(geom) FROM survey_objects WHERE survey_id = %s ORDER BY id",
                (survey_id,),
            )
            return [{"id": r[0], "geom": r[1]} for r in cur.fetchall()]
