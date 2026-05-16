from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ASSESS = ROOT / "assessment"
OUT = ASSESS / "output"
REPORTS = ASSESS / "reports"
LOGS = ASSESS / "logs"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def summarize_pgss(rows: list[dict[str, str]]) -> dict[str, float]:
    total_exec = 0.0
    total_calls = 0.0
    total_temp = 0.0
    for r in rows:
        total_exec += float(r.get("total_exec_time") or 0.0)
        total_calls += float(r.get("calls") or 0.0)
        total_temp += float(r.get("temp_blks_read") or 0.0) + float(r.get("temp_blks_written") or 0.0)
    mean_exec = (total_exec / total_calls) if total_calls else 0.0
    return {
        "total_exec_time": total_exec,
        "total_calls": total_calls,
        "mean_exec_per_call": mean_exec,
        "temp_blocks": total_temp,
    }


def count_dead_tuple_tables(rows: list[dict[str, str]], ratio_threshold: float = 0.2) -> int:
    n = 0
    for r in rows:
        live = float(r.get("n_live_tup") or 0.0)
        dead = float(r.get("n_dead_tup") or 0.0)
        if live > 0 and (dead / live) >= ratio_threshold:
            n += 1
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and monitor optimization outcomes from baseline snapshots.")
    parser.add_argument("--pre-dir", default=str(OUT), help="Directory with pre-change baseline outputs.")
    parser.add_argument("--post-dir", default=str(OUT), help="Directory with post-change baseline outputs.")
    parser.add_argument("--plan", default=str(ASSESS / "plans" / "optimization_plan.json"))
    parser.add_argument("--execution-log", default=str(LOGS / "execution_log.json"))
    args = parser.parse_args()

    pre_dir = Path(args.pre_dir)
    post_dir = Path(args.post_dir)

    pre_manifest = read_json(pre_dir / "baseline_manifest.json") if (pre_dir / "baseline_manifest.json").exists() else {}
    post_manifest = read_json(post_dir / "baseline_manifest.json") if (post_dir / "baseline_manifest.json").exists() else {}
    plan = read_json(Path(args.plan)) if Path(args.plan).exists() else {}
    execution_log = read_json(Path(args.execution_log)) if Path(args.execution_log).exists() else {}

    pre_pgss = read_csv(pre_dir / "pg_stat_statements.csv")
    post_pgss = read_csv(post_dir / "pg_stat_statements.csv")
    pre_tables = read_csv(pre_dir / "table_activity.csv")
    post_tables = read_csv(post_dir / "table_activity.csv")
    pre_idx = read_csv(pre_dir / "index_usage.csv")
    post_idx = read_csv(post_dir / "index_usage.csv")
    pre_settings = read_csv(pre_dir / "postgres_settings.csv")
    post_settings = read_csv(post_dir / "postgres_settings.csv")
    pre_ext = read_csv(pre_dir / "extensions.csv")
    post_ext = read_csv(post_dir / "extensions.csv")

    pre_pgss_summary = summarize_pgss(pre_pgss)
    post_pgss_summary = summarize_pgss(post_pgss)

    results = {
        "generated_at_utc": utc_now(),
        "inputs": {
            "pre_dir": str(pre_dir),
            "post_dir": str(post_dir),
            "plan": str(args.plan),
            "execution_log": str(args.execution_log),
        },
        "checks": {
            "postgres_settings_rows_pre": len(pre_settings),
            "postgres_settings_rows_post": len(post_settings),
            "extensions_rows_pre": len(pre_ext),
            "extensions_rows_post": len(post_ext),
            "pgss_summary_pre": pre_pgss_summary,
            "pgss_summary_post": post_pgss_summary,
            "dead_tuple_tables_pre": count_dead_tuple_tables(pre_tables),
            "dead_tuple_tables_post": count_dead_tuple_tables(post_tables),
            "index_usage_rows_pre": len(pre_idx),
            "index_usage_rows_post": len(post_idx),
            "plan_changes": len(plan.get("changes", [])),
            "execution_results": len(execution_log.get("results", [])),
        },
        "recommendation": {
            "keep_or_revert": "keep" if post_pgss_summary["total_exec_time"] <= pre_pgss_summary["total_exec_time"] else "review_revert_candidates",
            "notes": [
                "If total execution time increased materially, inspect top workload findings and rollback high-risk approved changes first.",
                "Track dead tuple table count trend and index usage trend over multiple runs before final keep/revert decision.",
            ],
        },
    }

    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    out_json = OUT / "validation_results.json"
    out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = [
        "# Validation Report",
        "",
        f"Generated: {results['generated_at_utc']}",
        "",
        "## Inputs",
        f"- Pre: {results['inputs']['pre_dir']}",
        f"- Post: {results['inputs']['post_dir']}",
        f"- Plan: {results['inputs']['plan']}",
        f"- Execution log: {results['inputs']['execution_log']}",
        "",
        "## Before/After Summary",
        f"- PG settings rows: pre={results['checks']['postgres_settings_rows_pre']} post={results['checks']['postgres_settings_rows_post']}",
        f"- Extensions rows: pre={results['checks']['extensions_rows_pre']} post={results['checks']['extensions_rows_post']}",
        f"- pg_stat_statements total_exec_time: pre={results['checks']['pgss_summary_pre']['total_exec_time']:.2f} post={results['checks']['pgss_summary_post']['total_exec_time']:.2f}",
        f"- pg_stat_statements mean_exec_per_call: pre={results['checks']['pgss_summary_pre']['mean_exec_per_call']:.6f} post={results['checks']['pgss_summary_post']['mean_exec_per_call']:.6f}",
        f"- pg_stat_statements temp_blocks: pre={results['checks']['pgss_summary_pre']['temp_blocks']:.2f} post={results['checks']['pgss_summary_post']['temp_blocks']:.2f}",
        f"- Dead tuple tables (ratio>=0.2): pre={results['checks']['dead_tuple_tables_pre']} post={results['checks']['dead_tuple_tables_post']}",
        "",
        "## Decision",
        f"- Recommendation: {results['recommendation']['keep_or_revert']}",
        "",
        "## Monitoring Notes",
    ]
    for note in results["recommendation"]["notes"]:
        report.append(f"- {note}")
    report.append("")

    out_md = REPORTS / "validation_report.md"
    out_md.write_text("\n".join(report), encoding="utf-8")

    print(json.dumps({"ok": True, "outputs": [str(out_md), str(out_json)]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
