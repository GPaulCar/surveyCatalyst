from __future__ import annotations

import json
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

PY = sys.executable
OUT_DIR = ROOT / "assessment" / "output"
LEGACY_PATTERN = re.compile(r"^external_features_legacy_[0-9a-z]+$")


def run_step(name: str, cmd: list[str]) -> dict[str, Any]:
    start = datetime.now(timezone.utc)
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    end = datetime.now(timezone.utc)
    return {
        "name": name,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "started_utc": start.isoformat(),
        "ended_utc": end.isoformat(),
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-4000:],
    }


def main() -> int:
    host = socket.gethostname()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    backend = build_backend()
    conn = backend.connect()
    dropped: list[str] = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname='public'
                  AND tablename LIKE 'external_features_legacy_%'
                ORDER BY tablename
                """
            )
            tables = [r[0] for r in cur.fetchall() if LEGACY_PATTERN.match(r[0] or "")]
            for t in tables:
                cur.execute(f'DROP TABLE IF EXISTS public."{t}" CASCADE')
                dropped.append(t)
            cur.execute("ANALYZE public.external_features")
        conn.commit()
    finally:
        conn.close()

    assess = run_step("assess_db_health", [PY, str(ROOT / "scripts" / "assess_db_health.py")])
    evidence = run_step("capture_external_features_index_evidence", [PY, str(ROOT / "scripts" / "capture_external_features_index_evidence.py")])

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "dropped_legacy_tables": dropped,
        "steps": [assess, evidence],
        "overall_ok": assess["ok"] and evidence["ok"],
    }
    out = OUT_DIR / f"cleanup_legacy_external_features_{host}_{ts}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": report["overall_ok"], "report": str(out), "dropped_legacy_tables": dropped}, indent=2))
    return 0 if report["overall_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

