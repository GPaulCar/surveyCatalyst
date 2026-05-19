from __future__ import annotations

import json
import socket
import subprocess
import sys
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
        "started_utc": started.isoformat(),
        "ended_utc": ended.isoformat(),
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-4000:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    host = socket.gethostname()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    steps = [
        ("pre_assess", [PY, str(ROOT / "scripts" / "assess_db_health.py")]),
        ("phase1_apply", [PY, str(ROOT / "scripts" / "optimize_db_host.py"), "--apply"]),
        ("phase2_apply", [PY, str(ROOT / "scripts" / "optimize_db_host_phase2.py"), "--apply"]),
        ("capture_evidence", [PY, str(ROOT / "scripts" / "capture_external_features_index_evidence.py")]),
        ("post_assess", [PY, str(ROOT / "scripts" / "assess_db_health.py")]),
    ]

    results: list[dict[str, Any]] = []
    for name, cmd in steps:
        r = run_step(name, cmd)
        results.append(r)
        if not r["ok"]:
            break

    overall_ok = all(r["ok"] for r in results)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "python": PY,
        "overall_ok": overall_ok,
        "steps": results,
    }
    out = OUT_DIR / f"db_optimize_full_cycle_{host}_{ts}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "report": str(out)}, indent=2))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
