from __future__ import annotations

import argparse
import json
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


def run_child(name: str, cmd: list[str]) -> dict[str, Any]:
    start = datetime.now(timezone.utc)
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    end = datetime.now(timezone.utc)
    return {
        "name": name,
        "cmd": cmd,
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "started_utc": start.isoformat(),
        "ended_utc": end.isoformat(),
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-4000:],
    }


def q1(cur, sql: str, params: tuple[Any, ...] = ()) -> tuple[Any, ...]:
    cur.execute(sql, params)
    row = cur.fetchone()
    return row if row is not None else tuple()


def qa(cur, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    cur.execute(sql, params)
    return cur.fetchall()


SAFE_DROP_CANDIDATES = [
    # keep small and explicit; more candidates can be added after evidence review
    "public.idx_external_features_layer",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 3: guarded index refinement + post-check batch.")
    parser.add_argument("--apply", action="store_true", help="Apply changes. Default dry-run.")
    args = parser.parse_args()
    dry_run = not args.apply

    host = socket.gethostname()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    backend = build_backend()
    conn = backend.connect()
    actions: list[dict[str, Any]] = []
    child_runs: list[dict[str, Any]] = []

    try:
        with conn.cursor() as cur:
            ident = q1(cur, "SELECT current_database()::text, inet_server_addr()::text, inet_server_port(), version()")
            index_rows = qa(
                cur,
                """
                SELECT
                  format('%I.%I', n.nspname, c.relname) AS fq_index_name,
                  COALESCE(s.idx_scan, 0) AS idx_scan,
                  pg_relation_size(c.oid) AS bytes
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                LEFT JOIN pg_stat_user_indexes s
                  ON s.indexrelname = c.relname
                 AND s.schemaname = n.nspname
                WHERE c.relkind = 'i'
                  AND format('%I.%I', n.nspname, c.relname) = ANY(%s)
                ORDER BY 1
                """,
                (SAFE_DROP_CANDIDATES,),
            )
            existing = {r[0]: {"idx_scan": int(r[1]), "bytes": int(r[2])} for r in index_rows}

            for fq_name in SAFE_DROP_CANDIDATES:
                info = existing.get(fq_name)
                if info is None:
                    actions.append({"name": f"drop_index:{fq_name}", "status": "skipped_not_found"})
                    continue
                if info["idx_scan"] > 0:
                    actions.append(
                        {
                            "name": f"drop_index:{fq_name}",
                            "status": "skipped_guard_idx_scan_gt_0",
                            "idx_scan": info["idx_scan"],
                            "size_bytes": info["bytes"],
                        }
                    )
                    continue
                if dry_run:
                    actions.append(
                        {
                            "name": f"drop_index:{fq_name}",
                            "status": "planned",
                            "idx_scan": info["idx_scan"],
                            "size_bytes": info["bytes"],
                        }
                    )
                else:
                    cur.execute(f"DROP INDEX IF EXISTS {fq_name}")
                    actions.append(
                        {
                            "name": f"drop_index:{fq_name}",
                            "status": "applied",
                            "idx_scan": info["idx_scan"],
                            "size_bytes": info["bytes"],
                        }
                    )

            if not dry_run:
                conn.commit()
                conn.autocommit = True
                cur.execute("ANALYZE public.external_features")
                conn.autocommit = False
                actions.append({"name": "analyze_external_features", "status": "applied"})
            else:
                actions.append({"name": "analyze_external_features", "status": "planned"})

    finally:
        conn.close()

    # always run post-check evidence + health to keep one batch output
    child_runs.append(run_child("capture_evidence", [PY, str(ROOT / "scripts" / "capture_external_features_index_evidence.py")]))
    child_runs.append(run_child("post_assess", [PY, str(ROOT / "scripts" / "assess_db_health.py")]))

    ok = all(r["ok"] for r in child_runs)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "mode": "apply" if not dry_run else "dry-run",
        "overall_ok": ok,
        "identity": {
            "database": ident[0] if ident else None,
            "server_addr": ident[1] if ident else None,
            "server_port": int(ident[2]) if ident and ident[2] is not None else None,
            "postgres_version": ident[3] if ident else None,
        },
        "actions": actions,
        "post_checks": child_runs,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"db_optimize_phase3_{host}_{ts}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": ok, "report": str(out), "mode": report["mode"]}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
