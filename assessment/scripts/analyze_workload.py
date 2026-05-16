from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assessment" / "output"
REPORTS = ROOT / "assessment" / "reports"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def to_float(v: str | None, default: float = 0.0) -> float:
    try:
        return float(v or "0")
    except Exception:  # noqa: BLE001
        return default


def to_int(v: str | None, default: int = 0) -> int:
    try:
        return int(float(v or "0"))
    except Exception:  # noqa: BLE001
        return default


def normalize_query(q: str) -> str:
    return " ".join((q or "").split())


def contains_external_features_layer_count(q: str) -> bool:
    text = normalize_query(q).lower()
    return (
        "select" in text
        and "count(" in text
        and "from external_features" in text
        and "group by layer" in text
    )


def main() -> int:
    pgss_path = OUT / "pg_stat_statements.csv"
    if not pgss_path.exists():
        raise FileNotFoundError(f"Missing baseline input: {pgss_path}")

    rows = read_csv(pgss_path)
    findings: list[dict[str, Any]] = []
    top_total: list[dict[str, Any]] = []
    top_mean: list[dict[str, Any]] = []
    high_reads: list[dict[str, Any]] = []
    temp_spills: list[dict[str, Any]] = []
    repeated_meta: list[dict[str, Any]] = []
    spatial_hotspots: list[dict[str, Any]] = []

    for row in rows:
        q = row.get("query", "") or ""
        calls = to_int(row.get("calls"))
        total = to_float(row.get("total_exec_time"))
        mean = to_float(row.get("mean_exec_time"))
        blks_read = to_int(row.get("shared_blks_read"))
        temp_read = to_int(row.get("temp_blks_read"))
        temp_written = to_int(row.get("temp_blks_written"))
        norm = normalize_query(q)
        low = norm.lower()

        item = {
            "queryid": row.get("queryid"),
            "calls": calls,
            "total_exec_time": total,
            "mean_exec_time": mean,
            "shared_blks_read": blks_read,
            "temp_blks_read": temp_read,
            "temp_blks_written": temp_written,
            "query": norm,
        }

        if total > 0:
            top_total.append(item)
        if mean > 0:
            top_mean.append(item)
        if blks_read > 0:
            high_reads.append(item)
        if temp_read > 0 or temp_written > 0:
            temp_spills.append(item)
        if any(k in low for k in ("from pg_", "from information_schema", "show ", "select current_")) and calls >= 50:
            repeated_meta.append(item)
        if any(k in low for k in ("st_intersects", "st_within", "st_dwithin", "st_transform", "st_asgeojson", "st_asmvt")):
            spatial_hotspots.append(item)
        if contains_external_features_layer_count(norm):
            findings.append(
                {
                    "type": "expensive_external_features_layer_count_query",
                    "severity": "high",
                    "status": "confirmed",
                    "evidence": item,
                    "recommendation": "Replace repeated live COUNT(*) GROUP BY layer with cached/materialized counts refreshed on ingest/update events.",
                    "candidate_scope": "application + database",
                }
            )

    top_total = sorted(top_total, key=lambda x: x["total_exec_time"], reverse=True)[:20]
    top_mean = sorted(top_mean, key=lambda x: x["mean_exec_time"], reverse=True)[:20]
    high_reads = sorted(high_reads, key=lambda x: x["shared_blks_read"], reverse=True)[:20]
    temp_spills = sorted(temp_spills, key=lambda x: (x["temp_blks_written"] + x["temp_blks_read"]), reverse=True)[:20]
    repeated_meta = sorted(repeated_meta, key=lambda x: x["calls"], reverse=True)[:20]
    spatial_hotspots = sorted(spatial_hotspots, key=lambda x: x["total_exec_time"], reverse=True)[:20]

    if top_total:
        findings.append(
            {
                "type": "high_total_time_queries",
                "severity": "high",
                "status": "confirmed",
                "evidence": {"top_n": 20, "queries": top_total},
                "recommendation": "Target top total time queries first for latency/cost reduction.",
                "candidate_scope": "application + database",
            }
        )
    if top_mean:
        findings.append(
            {
                "type": "high_mean_time_queries",
                "severity": "medium",
                "status": "confirmed",
                "evidence": {"top_n": 20, "queries": top_mean},
                "recommendation": "Investigate plans for high mean execution time outliers.",
                "candidate_scope": "database",
            }
        )
    if high_reads:
        findings.append(
            {
                "type": "high_block_read_queries",
                "severity": "medium",
                "status": "confirmed",
                "evidence": {"top_n": 20, "queries": high_reads},
                "recommendation": "Review indexing/plans and cache effectiveness for read-heavy SQL.",
                "candidate_scope": "database",
            }
        )
    if temp_spills:
        findings.append(
            {
                "type": "temp_spill_queries",
                "severity": "high",
                "status": "confirmed",
                "evidence": {"top_n": 20, "queries": temp_spills},
                "recommendation": "Tune work_mem candidates and/or rewrite spill-heavy queries.",
                "candidate_scope": "database + application",
            }
        )
    if repeated_meta:
        findings.append(
            {
                "type": "repeated_metadata_queries",
                "severity": "low",
                "status": "candidate",
                "evidence": {"top_n": 20, "queries": repeated_meta},
                "recommendation": "Cache repeated metadata lookups in application process where safe.",
                "candidate_scope": "application",
            }
        )
    if spatial_hotspots:
        findings.append(
            {
                "type": "spatial_predicate_hotspots",
                "severity": "high",
                "status": "confirmed",
                "evidence": {"top_n": 20, "queries": spatial_hotspots},
                "recommendation": "Focus on spatial index selectivity and geometry simplification paths for hotspot queries.",
                "candidate_scope": "database + application",
            }
        )

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_files": {"pg_stat_statements": str(pgss_path)},
        "summary": {
            "total_findings": len(findings),
            "confirmed": sum(1 for f in findings if f.get("status") == "confirmed"),
            "candidate": sum(1 for f in findings if f.get("status") != "confirmed"),
        },
        "findings": findings,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    out_json = OUT / "workload_findings.json"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Workload Assessment",
        "",
        f"Generated: {payload['generated_at_utc']}",
        "",
        "## Scope",
        "- Input: assessment/output/pg_stat_statements.csv",
        "- Optional plans directory not required for this pass",
        "- No database/app modifications applied",
        "",
        "## Summary",
        f"- Total findings: {payload['summary']['total_findings']}",
        f"- Confirmed: {payload['summary']['confirmed']}",
        f"- Candidate: {payload['summary']['candidate']}",
        "",
        "## Findings",
        "",
    ]
    for i, f in enumerate(findings, start=1):
        lines.extend(
            [
                f"### {i}. {f.get('type')} ({f.get('severity')})",
                f"- Status: {f.get('status')}",
                f"- Scope: {f.get('candidate_scope')}",
                f"- Recommendation: {f.get('recommendation')}",
                "",
            ]
        )
    out_md = REPORTS / "workload_assessment.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"ok": True, "outputs": [str(out_md), str(out_json)]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
