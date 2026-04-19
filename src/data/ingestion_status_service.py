from core.db import build_backend

class IngestionStatusService:
    def __init__(self):
        self.backend = build_backend()

    def status(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT layer, COUNT(*) FROM external_features GROUP BY layer")
            return dict(cur.fetchall())
