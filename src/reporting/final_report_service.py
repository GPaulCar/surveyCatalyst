from core.db import build_backend

class FinalReportService:
    def __init__(self):
        self.backend = build_backend()

    def generate(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            tables = [r[0] for r in cur.fetchall()]
        return {"tables": tables}
