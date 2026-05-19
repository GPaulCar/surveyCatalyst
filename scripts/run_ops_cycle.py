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
PY = sys.executable
OUT_DIR = ROOT / "assessment" / "output"


def run_step(name: str, cmd: list[str]) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    ended = datetime.now(timezone.utc)
    return {
        "name": name,
        "cmd": cmd,
        "returncode": proc.returncode,
        "ok": proc.returncode == 0,
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-4000:],
    }


def health_check(url: str) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            ok = 200 <= resp.status < 300
            code = resp.status
    except Exception as exc:
        ok = False
        code = None
        body = str(exc)
    ended = datetime.now(timezone.utc)
    return {
        "name": "health_check",
        "url": url,
        "ok": ok,
        "http_status": code,
        "response_excerpt": body[:2000],
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="One-command release operations cycle.")
    parser.add_argument("--skip-ingest", action="store_true", help="Skip ingestion/build pipeline.")
    parser.add_argument("--skip-optimize", action="store_true", help="Skip DB optimization full cycle.")
    parser.add_argument("--skip-restart", action="store_true", help="Skip API/DB restart step.")
    parser.add_argument("--health-url", default="http://127.0.0.1:8000/health", help="Health endpoint URL.")
    args = parser.parse_args()

    host = socket.gethostname()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    steps: list[dict[str, Any]] = []

    if not args.skip_ingest:
        steps.append(
            run_step(
                "ingest_pipeline",
                [PY, str(ROOT / "scripts" / "populate_all_layers.py"), "--force", "--include-osm", "--skip-geojson-loads"],
            )
        )
        if not steps[-1]["ok"]:
            return finalize(host, ts, steps, args.health_url, run_health=False)

    if not args.skip_optimize:
        steps.append(
            run_step(
                "optimize_full_cycle",
                [PY, str(ROOT / "scripts" / "optimize_db_full_cycle.py")],
            )
        )
        if not steps[-1]["ok"]:
            return finalize(host, ts, steps, args.health_url, run_health=False)

    if not args.skip_restart:
        steps.append(
            run_step(
                "restart_services",
                [PY, str(ROOT / "scripts" / "system_control.py"), "restart"],
            )
        )
        if not steps[-1]["ok"]:
            return finalize(host, ts, steps, args.health_url, run_health=False)

    return finalize(host, ts, steps, args.health_url, run_health=True)


def finalize(host: str, ts: str, steps: list[dict[str, Any]], health_url: str, *, run_health: bool) -> int:
    health = health_check(health_url) if run_health else None
    overall_ok = all(step["ok"] for step in steps) and (health["ok"] if health is not None else False)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "python": PY,
        "overall_ok": overall_ok,
        "steps": steps,
        "health": health,
    }
    out = OUT_DIR / f"ops_cycle_{host}_{ts}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "report": str(out)}, indent=2))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
