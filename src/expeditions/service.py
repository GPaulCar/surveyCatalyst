from core.db import build_backend

class ExpeditionService:
    def __init__(self):
        self.backend = build_backend()

    def create_expedition(self, title: str):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO expeditions (title) VALUES (%s) RETURNING id",
                (title,),
            )
            expedition_id = cur.fetchone()[0]
        conn.commit()
        return expedition_id

    def list_expeditions(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT id, title, status FROM expeditions")
            return cur.fetchall()
