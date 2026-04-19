from core.db import build_backend


class HealthCheckService:
    def run(self):
        conn = build_backend().connect()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            return cur.fetchone()
