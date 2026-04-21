from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend
from data.ingestion.providers.blfd import BLfDProvider


provider = BLfDProvider()
print(provider.dry_run())

backend = build_backend()
conn = backend.connect()
with conn.cursor() as cur:
    cur.execute("SELECT COUNT(*) FROM external_features WHERE layer = 'legal_restricted_areas'")
    print("projected_rows", cur.fetchone()[0])
