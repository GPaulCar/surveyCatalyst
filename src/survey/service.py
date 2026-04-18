from core.db import build_backend

class SurveyService:
    def __init__(self):
        self.backend = build_backend()

    def create_survey(self, expedition_id: int, title: str):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO surveys (expedition_id, title) VALUES (%s, %s) RETURNING id",
                (expedition_id, title),
            )
            survey_id = cur.fetchone()[0]
        conn.commit()
        return survey_id

    def list_surveys(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, status FROM surveys")
            return cur.fetchall()
