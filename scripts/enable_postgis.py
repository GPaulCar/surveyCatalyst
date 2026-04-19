from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend


def main() -> None:
    backend = build_backend()
    conn = backend.connect()
    try:
        conn.autocommit = True
    except Exception:
        pass
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        try:
            cur.execute("SELECT PostGIS_Version();")
            version = cur.fetchone()[0]
        except Exception:
            version = "unknown"
    try:
        conn.commit()
    except Exception:
        pass
    backend.close()
    print(f"PostGIS enabled: {version}")


if __name__ == "__main__":
    main()
