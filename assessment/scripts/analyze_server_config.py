from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "assessment" / "output"
REPORTS_DIR = ROOT / "assessment" / "reports"


@dataclass
class SettingRow:
    name: str
    setting: str
    unit: str
    category: str
    context: str
    vartype: str
    source: str
    boot_val: str
    reset_val: str
    pending_restart: str


def load_settings_csv(path: Path) -> dict[str, SettingRow]:
    rows: dict[str, SettingRow] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows[row["name"]] = SettingRow(
                name=row.get("name", ""),
                setting=row.get("setting", ""),
                unit=row.get("unit", ""),
                category=row.get("category", ""),
                context=row.get("context", ""),
                vartype=row.get("vartype", ""),
                source=row.get("source", ""),
                boot_val=row.get("boot_val", ""),
                reset_val=row.get("reset_val", ""),
                pending_restart=row.get("pending_restart", ""),
            )
    return rows


def load_system(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def as_int(value: str, default: int = 0) -> int:
    try:
        return int(float(value))
    except Exception:  # noqa: BLE001
        return default


def mem_mb_from_kb(setting: str) -> int:
    return as_int(setting) // 1024


def recommend_memory(total_bytes: int) -> dict[str, int]:
    total_mb = int(total_bytes / (1024 * 1024)) if total_bytes else 0
    if total_mb <= 0:
        return {"shared_buffers_mb": 1024, "effective_cache_size_mb": 4096, "maintenance_work_mem_mb": 256}
    shared = max(512, int(total_mb * 0.25))
    effective = max(2048, int(total_mb * 0.6))
    maint = max(256, int(total_mb * 0.05))
    return {
        "shared_buffers_mb": shared,
        "effective_cache_size_mb": effective,
        "maintenance_work_mem_mb": maint,
    }


def mk_finding(
    key: str,
    row: SettingRow | None,
    current: str,
    recommended: str,
    rationale: str,
    risk: str,
    requires: str,
    validation: str,
    rollback: str,
    confidence: str = "candidate",
) -> dict[str, Any]:
    return {
        "key": key,
        "setting_name": row.name if row else key,
        "current_value": current,
        "recommended_value": recommended,
        "source": row.source if row else "derived",
        "context": row.context if row else "n/a",
        "pending_restart": row.pending_restart if row else "n/a",
        "confidence": confidence,
        "rationale": rationale,
        "risk": risk,
        "requires": requires,  # restart / reload / none
        "validation_method": validation,
        "rollback": rollback,
    }


def main() -> int:
    settings_csv = OUT_DIR / "postgres_settings.csv"
    system_json = OUT_DIR / "system_baseline.json"
    if not settings_csv.exists():
        raise FileNotFoundError(f"Missing baseline input: {settings_csv}")
    if not system_json.exists():
        raise FileNotFoundError(f"Missing baseline input: {system_json}")

    settings = load_settings_csv(settings_csv)
    system = load_system(system_json)
    total_bytes = int((system.get("disk_usage_root") or {}).get("total") or 0)
    mem_reco = recommend_memory(total_bytes)

    findings: list[dict[str, Any]] = []

    sb = settings.get("shared_buffers")
    if sb:
        cur_mb = mem_mb_from_kb(sb.setting)
        rec_mb = mem_reco["shared_buffers_mb"]
        findings.append(
            mk_finding(
                key="shared_buffers",
                row=sb,
                current=f"{cur_mb} MB",
                recommended=f"{rec_mb} MB",
                rationale="shared_buffers below typical target can increase disk reads.",
                risk="medium",
                requires="restart",
                validation="Compare buffer cache hit ratio and query latency after restart.",
                rollback=f"Restore shared_buffers to {sb.setting}{sb.unit or ''}.",
            )
        )

    ecs = settings.get("effective_cache_size")
    if ecs:
        cur_mb = mem_mb_from_kb(ecs.setting)
        rec_mb = mem_reco["effective_cache_size_mb"]
        findings.append(
            mk_finding(
                key="effective_cache_size",
                row=ecs,
                current=f"{cur_mb} MB",
                recommended=f"{rec_mb} MB",
                rationale="effective_cache_size drives planner assumptions for index scans.",
                risk="low",
                requires="reload",
                validation="Check plan changes for top queries and index usage.",
                rollback=f"Restore effective_cache_size to {ecs.setting}{ecs.unit or ''}.",
            )
        )

    mwm = settings.get("maintenance_work_mem")
    if mwm:
        cur_mb = mem_mb_from_kb(mwm.setting)
        rec_mb = mem_reco["maintenance_work_mem_mb"]
        findings.append(
            mk_finding(
                key="maintenance_work_mem",
                row=mwm,
                current=f"{cur_mb} MB",
                recommended=f"{rec_mb} MB",
                rationale="maintenance operations can be slow with too-small maintenance_work_mem.",
                risk="low",
                requires="reload",
                validation="Observe VACUUM/CREATE INDEX runtime after change.",
                rollback=f"Restore maintenance_work_mem to {mwm.setting}{mwm.unit or ''}.",
            )
        )

    mppw = settings.get("max_parallel_workers_per_gather")
    if mppw:
        cur = as_int(mppw.setting)
        rec = max(2, cur)
        findings.append(
            mk_finding(
                key="max_parallel_workers_per_gather",
                row=mppw,
                current=str(cur),
                recommended=str(rec),
                rationale="parallel execution can improve scans on large analytical reads.",
                risk="low",
                requires="reload",
                validation="Check EXPLAIN plans for Gather nodes and execution time.",
                rollback=f"Restore max_parallel_workers_per_gather to {mppw.setting}.",
            )
        )

    ctc = settings.get("checkpoint_completion_target")
    if ctc:
        cur = float(ctc.setting or 0)
        rec = 0.9 if cur < 0.9 else cur
        findings.append(
            mk_finding(
                key="checkpoint_completion_target",
                row=ctc,
                current=str(cur),
                recommended=str(rec),
                rationale="higher checkpoint_completion_target smooths checkpoint I/O bursts.",
                risk="low",
                requires="reload",
                validation="Track checkpoint write spikes and latency variance.",
                rollback=f"Restore checkpoint_completion_target to {ctc.setting}.",
            )
        )

    wal_buffers = settings.get("wal_buffers")
    if wal_buffers:
        findings.append(
            mk_finding(
                key="wal_buffers",
                row=wal_buffers,
                current=f"{wal_buffers.setting}{wal_buffers.unit or ''}",
                recommended="auto or higher explicit value if WAL contention observed",
                rationale="WAL buffer size can affect write-heavy workloads.",
                risk="low",
                requires="restart",
                validation="Observe WAL write waits and transaction latency during write bursts.",
                rollback=f"Restore wal_buffers to {wal_buffers.setting}{wal_buffers.unit or ''}.",
            )
        )

    finding_payload = {
        "generated_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "input_files": [
            str(settings_csv),
            str(system_json),
        ],
        "findings": findings,
        "summary": {
            "count": len(findings),
            "confirmed": sum(1 for f in findings if f.get("confidence") == "confirmed"),
            "candidate": sum(1 for f in findings if f.get("confidence") != "confirmed"),
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    findings_path = OUT_DIR / "server_config_findings.json"
    findings_path.write_text(json.dumps(finding_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Server Configuration Assessment",
        "",
        f"Generated: {finding_payload['generated_at_utc']}",
        "",
        "## Scope",
        "- Input: assessment/output/postgres_settings.csv",
        "- Input: assessment/output/system_baseline.json",
        "- No changes applied (analysis only).",
        "",
        "## Findings",
        "",
    ]
    for idx, f in enumerate(findings, start=1):
        lines.extend(
            [
                f"### {idx}. {f['setting_name']}",
                f"- Current: {f['current_value']}",
                f"- Recommended: {f['recommended_value']}",
                f"- Confidence: {f['confidence']}",
                f"- Risk: {f['risk']}",
                f"- Requires: {f['requires']}",
                f"- Pending restart flag: {f['pending_restart']}",
                f"- Rationale: {f['rationale']}",
                f"- Validation: {f['validation_method']}",
                f"- Rollback: {f['rollback']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Notes",
            "- Recommendations are candidate values and must be approved before execution.",
            "- Restart/reload requirements are explicit per setting.",
            "- This report intentionally does not edit postgresql.conf or run ALTER SYSTEM.",
            "",
        ]
    )
    report_path = REPORTS_DIR / "server_config_assessment.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"ok": True, "outputs": [str(report_path), str(findings_path)]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
