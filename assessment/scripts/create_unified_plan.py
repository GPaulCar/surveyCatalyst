from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assessment" / "output"
PLANS = ROOT / "assessment" / "plans"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def mk_change(
    order: int,
    group: str,
    title: str,
    source: str,
    risk: str,
    dependencies: list[str],
    rollback: str,
    validation: str,
    restart_requirement: str,
    affects_next_parcel: bool,
    notes: str,
) -> dict[str, Any]:
    return {
        "execution_order": order,
        "group": group,
        "title": title,
        "source": source,
        "risk": risk,
        "dependencies": dependencies,
        "rollback": rollback,
        "validation": validation,
        "restart_or_downtime_requirement": restart_requirement,
        "affects_next_parcel": affects_next_parcel,
        "notes": notes,
        "status": "proposed",
    }


def main() -> int:
    server = load_json(OUT / "server_config_findings.json")
    db_content = load_json(OUT / "database_content_findings.json")
    workload = load_json(OUT / "workload_findings.json")

    changes: list[dict[str, Any]] = []
    order = 1

    # Group 1: server config
    for f in server.get("findings", []):
        changes.append(
            mk_change(
                order=order,
                group="server_config",
                title=f"Adjust setting: {f.get('setting_name')}",
                source="server_config_findings",
                risk=f.get("risk", "medium"),
                dependencies=["baseline_collected"],
                rollback=f.get("rollback", "Restore prior setting value."),
                validation=f.get("validation_method", "Validate with pg_settings and workload checks."),
                restart_requirement=f.get("requires", "reload"),
                affects_next_parcel=True,
                notes=f.get("rationale", ""),
            )
        )
        order += 1

    # Group 2: database optimization (indexes/autovacuum/statistics)
    for f in db_content.get("findings", []):
        f_type = str(f.get("type", ""))
        if f_type in {
            "duplicate_index_definition",
            "overlapping_spatial_indexes",
            "unused_index",
            "dead_tuple_pressure",
            "never_analyzed",
            "missing_spatial_index_candidate",
        }:
            changes.append(
                mk_change(
                    order=order,
                    group="database_optimization",
                    title=f"{f_type} on {f.get('table', 'n/a')}",
                    source="database_content_findings",
                    risk=f.get("severity", "medium"),
                    dependencies=["server_config_reviewed"],
                    rollback="Recreate dropped index / restore previous vacuum settings / revert migration.",
                    validation="Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.",
                    restart_requirement="none_or_reload",
                    affects_next_parcel=True,
                    notes=f.get("recommendation", ""),
                )
            )
            order += 1

    # Group 3: database content cleanup (geometry/SRID)
    for f in db_content.get("findings", []):
        f_type = str(f.get("type", ""))
        if f_type in {"srid_inconsistency", "invalid_geometries", "oversized_geometries"}:
            changes.append(
                mk_change(
                    order=order,
                    group="database_content_cleanup",
                    title=f"{f_type} on {f.get('table', 'n/a')}",
                    source="database_content_findings",
                    risk=f.get("severity", "medium"),
                    dependencies=["database_optimization_started"],
                    rollback="Restore from backup/exported snapshot of affected rows.",
                    validation="Re-run SRID/geometry quality baseline checks.",
                    restart_requirement="none",
                    affects_next_parcel=True,
                    notes=f.get("recommendation", ""),
                )
            )
            order += 1

    # Group 4: application query optimization
    for f in workload.get("findings", []):
        changes.append(
            mk_change(
                order=order,
                group="application_query_optimization",
                title=f"{f.get('type')}",
                source="workload_findings",
                risk=f.get("severity", "medium"),
                dependencies=["database_optimization_started"],
                rollback="Revert application query changes and disable new cache/materialized query path.",
                validation="Compare pg_stat_statements before/after for target query classes.",
                restart_requirement="app_restart_possible",
                affects_next_parcel=True,
                notes=f.get("recommendation", ""),
            )
        )
        order += 1

    # Group 5: validation
    changes.append(
        mk_change(
            order=order,
            group="validation",
            title="Run post-change baseline and compare against pre-change baseline",
            source="plan_generated",
            risk="low",
            dependencies=["all_approved_changes_applied"],
            rollback="Use change-specific rollback procedures if regression thresholds are exceeded.",
            validation="Execute validate_and_monitor.py and review validation_report.md.",
            restart_requirement="none",
            affects_next_parcel=False,
            notes="Validation gate for keep/revert decisions.",
        )
    )
    order += 1

    # Group 6: monitoring
    changes.append(
        mk_change(
            order=order,
            group="monitoring",
            title="Establish recurring health/performance checks",
            source="plan_generated",
            risk="low",
            dependencies=["validation_passed"],
            rollback="Disable monitoring jobs if they create operational noise.",
            validation="Confirm checks run and produce actionable outputs.",
            restart_requirement="none",
            affects_next_parcel=False,
            notes="Track query latency, dead tuples, index usage, lock pressure, and cache effectiveness.",
        )
    )

    # Normalize execution order.
    changes = sorted(changes, key=lambda x: x["execution_order"])
    for i, c in enumerate(changes, start=1):
        c["execution_order"] = i

    plan = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "server_config_findings": str(OUT / "server_config_findings.json"),
            "database_content_findings": str(OUT / "database_content_findings.json"),
            "workload_findings": str(OUT / "workload_findings.json"),
        },
        "groups": [
            "server_config",
            "database_optimization",
            "database_content_cleanup",
            "application_query_optimization",
            "validation",
            "monitoring",
        ],
        "changes": changes,
        "summary": {
            "total_changes": len(changes),
            "by_group": {
                g: sum(1 for c in changes if c["group"] == g)
                for g in [
                    "server_config",
                    "database_optimization",
                    "database_content_cleanup",
                    "application_query_optimization",
                    "validation",
                    "monitoring",
                ]
            },
        },
    }

    PLANS.mkdir(parents=True, exist_ok=True)
    plan_json = PLANS / "optimization_plan.json"
    plan_md = PLANS / "optimization_plan.md"
    plan_json.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    md_lines = [
        "# Unified Optimization Plan",
        "",
        f"Generated: {plan['generated_at_utc']}",
        "",
        "## Group Summary",
    ]
    for group, n in plan["summary"]["by_group"].items():
        md_lines.append(f"- {group}: {n}")
    md_lines.extend(["", "## Ordered Changes", ""])

    for c in changes:
        md_lines.extend(
            [
                f"### {c['execution_order']}. [{c['group']}] {c['title']}",
                f"- Risk: {c['risk']}",
                f"- Dependencies: {', '.join(c['dependencies']) if c['dependencies'] else 'none'}",
                f"- Restart/Downtime: {c['restart_or_downtime_requirement']}",
                f"- Affects next parcel: {c['affects_next_parcel']}",
                f"- Validation: {c['validation']}",
                f"- Rollback: {c['rollback']}",
                f"- Notes: {c['notes']}",
                "",
            ]
        )

    plan_md.write_text("\n".join(md_lines), encoding="utf-8")
    print(json.dumps({"ok": True, "outputs": [str(plan_md), str(plan_json)]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
