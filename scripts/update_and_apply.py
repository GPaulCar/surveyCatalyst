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


def read_version() -> str | None:
    version_file = ROOT / "VERSION"
    if not version_file.exists():
        return None
    return version_file.read_text(encoding="utf-8").strip() or None


def main() -> int:
    parser = argparse.ArgumentParser(description="Update code via git and apply DB/service updates.")
    parser.add_argument("--tag", default=None, help="Optional git tag to checkout before applying updates.")
    parser.add_argument("--health-url", default="http://127.0.0.1:8000/health")
    parser.add_argument("--skip-pull", action="store_true", help="Skip git pull/fetch steps.")
    args = parser.parse_args()

    host = socket.gethostname()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    before_version = read_version()
    steps: list[dict[str, Any]] = []

    if not args.skip_pull:
        steps.append(run_step("git_fetch_tags", ["git", "fetch", "--tags", "origin"]))
        if not steps[-1]["ok"]:
            return write_report(host, ts, before_version, read_version(), steps, args.health_url, None)

        if args.tag:
            steps.append(run_step("git_checkout_tag", ["git", "checkout", "--detach", f"tags/{args.tag}"]))
            if not steps[-1]["ok"]:
                return write_report(host, ts, before_version, read_version(), steps, args.health_url, None)
        else:
            steps.append(run_step("git_pull_main", ["git", "pull", "--ff-only", "origin", "main"]))
            if not steps[-1]["ok"]:
                return write_report(host, ts, before_version, read_version(), steps, args.health_url, None)

    # DB migrations (mandatory)
    steps.append(run_step("run_migrations", [PY, str(ROOT / "scripts" / "run_migrations.py")]))
    if not steps[-1]["ok"]:
        return write_report(host, ts, before_version, read_version(), steps, args.health_url, None)

    # Optional post-update task hook
    post_update = ROOT / "scripts" / "post_update_tasks.py"
    if post_update.exists():
        steps.append(run_step("post_update_tasks", [PY, str(post_update)]))
        if not steps[-1]["ok"]:
            return write_report(host, ts, before_version, read_version(), steps, args.health_url, None)

    # Restart and verify
    steps.append(run_step("restart_services", [PY, str(ROOT / "scripts" / "system_control.py"), "restart"]))
    health_result = health(args.health_url)

    after_version = read_version()
    return write_report(host, ts, before_version, after_version, steps, args.health_url, health_result)


def write_report(
    host: str,
    ts: str,
    before_version: str | None,
    after_version: str | None,
    steps: list[dict[str, Any]],
    health_url: str,
    health_result: dict[str, Any] | None,
) -> int:
    overall_ok = all(s["ok"] for s in steps) and (health_result["ok"] if health_result is not None else False)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "python": PY,
        "before_version": before_version,
        "after_version": after_version,
        "overall_ok": overall_ok,
        "health_url": health_url,
        "steps": steps,
        "health": health_result,
        "rollback_hint": "If update failed after pull, checkout previous tag/commit and rerun update_and_apply.",
    }
    out = OUT_DIR / f"update_run_{host}_{ts}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "report": str(out)}, indent=2))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

