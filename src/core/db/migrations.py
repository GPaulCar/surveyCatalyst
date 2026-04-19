from pathlib import Path
from core.db import build_backend

MIGRATIONS_DIR = Path("db/migrations")

def apply_migrations():
    backend = build_backend()
    conn = backend.connect()
    with conn.cursor() as cur:
        for file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sql = file.read_text(encoding="utf-8")
            cur.execute(sql)
    conn.commit()
    backend.close()
