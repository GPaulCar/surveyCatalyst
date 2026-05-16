from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ASSESS_SCRIPTS = ROOT / "assessment" / "scripts"
OUT = ROOT / "assessment" / "output"
LOGS = ROOT / "assessment" / "logs"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_step(script_name: str, args: list[str]) -> dict:
    cmd = [sys.executable, str(ASSESS_SCRIPTS / script_name), *args]
    started = utc_now()
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    ended = utc_now()
    return {
        "script": script_name,
        "command": cmd,
        "started_at_utc": started,
        "ended_at_utc": ended,
        "returncode": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-4000:],
        "stderr_tail": (proc.stderr or "")[-4000:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run assessment/planning block in dependency order.")
    parser.add_argument("--dotenv", default=str(ROOT / "assessment" / ".env.example"))
    parser.add_argument("--allow-analyze", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    LOGS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    steps = [
        ("collect_full_baseline.py", ["--dotenv", args.dotenv] + (["--allow-analyze"] if args.allow_analyze else [])),
        ("analyze_server_config.py", []),
        ("analyze_database_content.py", []),
        ("analyze_workload.py", []),
        ("create_unified_plan.py", []),
    ]

    results: list[dict] = []
    for script, sargs in steps:
        print(f"[RUN] {script}", flush=True)
        result = run_step(script, sargs)
        results.append(result)
        if result["ok"]:
            print(f"[OK] {script}", flush=True)
        else:
            print(f"[FAIL] {script} (exit {result['returncode']})", flush=True)
            if not args.continue_on_error:
                break

    payload = {
        "started_at_utc": results[0]["started_at_utc"] if results else utc_now(),
        "ended_at_utc": utc_now(),
        "steps": results,
        "summary": {
            "total": len(results),
            "ok": sum(1 for r in results if r["ok"]),
            "failed": sum(1 for r in results if not r["ok"]),
        },
    }
    out_file = LOGS / "assessment_block_run.json"
    out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[REPORT] {out_file}", flush=True)

    return 0 if payload["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
