from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import urllib.request
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


def run_step(name: str, cmd: list[str]) -> dict[str, Any]:
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


def health(url: str) -> dict[str, Any]:
    start = datetime.now(timezone.utc)
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            ok = 200 <= resp.status < 300
            code = resp.status
    except Exception as exc:
        ok = False
        code = None
        body = str(exc)
    end = datetime.now(timezone.utc)
    return {
        "ok": ok,
        "status": code,
        "excerpt": body[:1000],
        "started_utc": start.isoformat(),
        "ended_utc": end.isoformat(),
    }


def run_sql_batch() -> dict[str, Any]:
    backend = build_backend()
    conn = backend.connect()
    actions: list[dict[str, Any]] = []
    try:
        with conn.cursor() as cur:
            # 1) materialized stats table
            cur.execute(
                """
                CREATE SCHEMA IF NOT EXISTS runtime;
                CREATE TABLE IF NOT EXISTS runtime.layer_counts_cache (
                  layer text PRIMARY KEY,
                  feature_count bigint NOT NULL,
                  refreshed_at timestamptz NOT NULL
                );
                """
            )
            actions.append({"name": "ensure_layer_counts_cache_table", "ok": True})
            cur.execute(
                """
                INSERT INTO runtime.layer_counts_cache (layer, feature_count, refreshed_at)
                SELECT layer, COUNT(*)::bigint, NOW()
                FROM external_features
                GROUP BY layer
                ON CONFLICT (layer) DO UPDATE
                SET feature_count = EXCLUDED.feature_count,
                    refreshed_at = EXCLUDED.refreshed_at
                """
            )
            actions.append({"name": "refresh_layer_counts_cache", "ok": True, "rows": int(cur.rowcount)})

            # 2) partition prep analysis (no destructive migration)
            cur.execute(
                """
                SELECT layer, COUNT(*)::bigint AS cnt
                FROM external_features
                GROUP BY layer
                ORDER BY cnt DESC
                LIMIT 20
                """
            )
            top = [{"layer": r[0], "count": int(r[1])} for r in cur.fetchall()]
            actions.append({"name": "partition_prep_top_layers", "ok": True, "top_layers": top})

            # 3) cache-enablement flags for app metadata
            cur.execute(
                """
                UPDATE layers_registry
                SET metadata = COALESCE(metadata, '{}'::jsonb) || '{"runtime_cache_hint":"layer_counts_cache"}'::jsonb,
                    updated_at = NOW()
                WHERE layer_group IN ('context','survey')
                """
            )
            actions.append({"name": "set_runtime_cache_hints", "ok": True, "rows": int(cur.rowcount)})
        conn.commit()
    finally:
        conn.close()
    return {"actions": actions}


def main() -> int:
    parser = argparse.ArgumentParser(description="Full stack optimization batch: DB tuning+cache+partition prep+stats.")
    parser.add_argument("--health-url", default="http://127.0.0.1:8000/health")
    args = parser.parse_args()

    host = socket.gethostname()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    steps: list[dict[str, Any]] = []
    steps.append(run_step("optimize_db_phase1", [PY, str(ROOT / "scripts" / "optimize_db_host.py"), "--apply"]))
    steps.append(run_step("optimize_db_phase2", [PY, str(ROOT / "scripts" / "optimize_db_host_phase2.py"), "--apply"]))
    steps.append(run_step("optimize_db_phase3", [PY, str(ROOT / "scripts" / "optimize_db_host_phase3.py"), "--apply"]))

    sql_batch = run_sql_batch()

    steps.append(run_step("restart_services", [PY, str(ROOT / "scripts" / "system_control.py"), "restart"]))
    health_result = health(args.health_url)
    steps.append(run_step("post_assess", [PY, str(ROOT / "scripts" / "assess_db_health.py")]))
    steps.append(run_step("capture_evidence", [PY, str(ROOT / "scripts" / "capture_external_features_index_evidence.py")]))

    overall_ok = all(s["ok"] for s in steps) and health_result["ok"]
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "overall_ok": overall_ok,
        "steps": steps,
        "sql_batch": sql_batch,
        "health": health_result,
    }
    out = OUT_DIR / f"optimize_stack_full_{host}_{ts}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "report": str(out)}, indent=2))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

