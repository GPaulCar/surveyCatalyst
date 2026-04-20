from pathlib import Path

from core.db import build_backend


class RawLoaderService:
    def __init__(self):
        self.backend = build_backend()

    def load_csv_lines(self, table_name: str, path: str | Path):
        path = Path(path)
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id SERIAL PRIMARY KEY,
                    data TEXT NOT NULL
                )
                '''
            )
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    cur.execute(
                        f"INSERT INTO {table_name} (data) VALUES (%s)",
                        (line.strip(),),
                    )
        conn.commit()
        return {"table": table_name, "rows_loaded": len([x for x in path.read_text(encoding='utf-8').splitlines() if x.strip()])}
