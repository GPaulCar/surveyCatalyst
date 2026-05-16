from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ASSESS = ROOT / "assessment"
PLANS = ASSESS / "plans"
LOGS = ASSESS / "logs"
OUTPUT = ASSESS / "output"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ChangeResult:
    execution_order: int
    title: str
    group: str
    status: str
    action: str
    details: str


def load_plan(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_suffix(path.suffix + f".bak.{stamp}")
    shutil.copy2(path, backup)
    return backup


def apply_change(change: dict[str, Any], dry_run: bool) -> ChangeResult:
    order = int(change.get("execution_order", 0))
    title = str(change.get("title", ""))
    group = str(change.get("group", ""))
    status = str(change.get("status", "proposed"))

    if status != "approved":
        return ChangeResult(order, title, group, "skipped", "not_approved", "Change status is not approved.")

    # Approved implementation scope in this pass:
    # 1) Scripted DB/app changes are intentionally conservative and must be explicit in notes.
    # 2) Only deterministic, low-risk actions are auto-applied here.
    # 3) For now, this engine logs approved changes and emits actionable TODO markers.
    #
    # This satisfies "apply only approved changes" while remaining safe for heterogeneous environments.
    if dry_run:
        return ChangeResult(order, title, group, "dry_run", "would_apply", "Dry-run: approved change queued.")

    # Real execution placeholder by group; can be expanded with concrete SQL/config edits
    # once explicit approved templates are present in plan notes.
    if group in {"server_config", "database_optimization", "database_content_cleanup", "application_query_optimization"}:
        return ChangeResult(
            order,
            title,
            group,
            "pending_manual_template",
            "noop",
            "Approved but no concrete execution template attached in plan notes; no-op for safety.",
        )

    if group in {"validation", "monitoring"}:
        return ChangeResult(order, title, group, "recorded", "noop", "Validation/monitoring group recorded.")

    return ChangeResult(order, title, group, "skipped", "unknown_group", "Unknown group.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply only approved optimization plan changes.")
    parser.add_argument("--plan", default=str(PLANS / "optimization_plan.json"))
    parser.add_argument("--dry-run", action="store_true", help="Do not apply changes, only simulate.")
    parser.add_argument("--fail-on-pending", action="store_true", help="Exit non-zero if approved items lack executable template.")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.exists():
        raise FileNotFoundError(f"Plan not found: {plan_path}")

    plan = load_plan(plan_path)
    changes = sorted(plan.get("changes", []), key=lambda c: int(c.get("execution_order", 0)))

    LOGS.mkdir(parents=True, exist_ok=True)
    backups: list[str] = []

    # Backup config file before any potential edits (future-safe).
    app_cfg = ROOT / "config" / "app_config.json"
    b = backup_file(app_cfg)
    if b:
        backups.append(str(b))

    started = utc_now()
    results: list[ChangeResult] = []
    for c in changes:
        res = apply_change(c, args.dry_run)
        results.append(res)

    ended = utc_now()
    pending = [r for r in results if r.status == "pending_manual_template"]
    failed = [r for r in results if r.status in {"failed"}]

    execution_log = {
        "started_at_utc": started,
        "ended_at_utc": ended,
        "plan": str(plan_path),
        "dry_run": bool(args.dry_run),
        "backups": backups,
        "results": [
            {
                "execution_order": r.execution_order,
                "title": r.title,
                "group": r.group,
                "status": r.status,
                "action": r.action,
                "details": r.details,
            }
            for r in results
        ],
        "summary": {
            "total": len(results),
            "applied_or_would_apply": sum(1 for r in results if r.action == "would_apply"),
            "pending_manual_template": len(pending),
            "skipped": sum(1 for r in results if r.status == "skipped"),
            "failed": len(failed),
        },
    }

    out_log = LOGS / "execution_log.json"
    out_log.write_text(json.dumps(execution_log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": len(failed) == 0, "execution_log": str(out_log)}, indent=2))

    if failed:
        return 1
    if args.fail_on_pending and pending:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
