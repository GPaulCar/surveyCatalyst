from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

EXPORT_ROOT = ROOT / "workspace" / "permissions" / "requests"
EXPORT_ROOT.mkdir(parents=True, exist_ok=True)

def slugify(value: str | None, default: str = "permission-request") -> str:
    raw = (value or "").strip().lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return raw or default

def main(argv: list[str]) -> int:
    if len(argv) < 4:
        print("Usage: python scripts/export_permission_candidate.py <layer_key> <source_id> <description>")
        return 1

    layer_key = argv[1]
    source_id = argv[2]
    description = " ".join(argv[3:])

    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    layer,
                    source_id,
                    source_table,
                    properties,
                    ST_AsGeoJSON(geom)
                FROM external_features
                WHERE layer = %s AND source_id = %s
                LIMIT 1
                """,
                (layer_key, source_id),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        print("[ERROR] no matching feature found")
        return 1

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = EXPORT_ROOT / f"{stamp}_{slugify(description)}"
    folder.mkdir(parents=True, exist_ok=True)

    payload = {
        "layer": row[0],
        "source_id": row[1],
        "source_table": row[2],
        "properties": row[3],
        "geometry": json.loads(row[4]) if row[4] else None,
        "description": description,
        "saved_at": datetime.now().isoformat(),
    }

    out = folder / "permission_candidate.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[DONE] wrote {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
