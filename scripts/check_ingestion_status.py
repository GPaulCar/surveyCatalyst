import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

backend = build_backend()
conn = backend.connect()
with conn.cursor() as cur:
    cur.execute("SELECT source_key, status, message, started_at, completed_at FROM ingestion_runs ORDER BY id DESC LIMIT 20")
    rows = cur.fetchall()

for row in rows:
    print(row)
