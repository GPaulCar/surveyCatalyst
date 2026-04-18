from core.db import build_backend

class SurveyObjectService:
    def __init__(self):
        self.backend = build_backend()

    def create_object(self, survey_id: int, expedition_id: int, obj_type: str, geom_wkt: str):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO survey_objects (survey_id, expedition_id, type, geom)
                VALUES (%s, %s, %s, ST_GeomFromText(%s, 4326))
                RETURNING id
                """,
                (survey_id, expedition_id, obj_type, geom_wkt),
            )
            obj_id = cur.fetchone()[0]
        conn.commit()
        return obj_id
