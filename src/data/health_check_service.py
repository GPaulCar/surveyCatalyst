from core.db import build_backend

class HealthCheckService:
    def __init__(self):
        self.backend = build_backend()

    def run(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            return cur.fetchone()[0] == 1
