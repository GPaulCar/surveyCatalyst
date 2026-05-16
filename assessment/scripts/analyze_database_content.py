from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assessment" / "output"
REPORTS = ROOT / "assessment" / "reports"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def to_int(v: str | None, default: int = 0) -> int:
    try:
        return int(float(v or "0"))
    except Exception:  # noqa: BLE001
        return default


def idx_signature(indexdef: str) -> str:
    txt = " ".join((indexdef or "").lower().split())
    txt = txt.replace("create index", "").replace("if not exists", "")
    return txt


def main() -> int:
    required = {
        "table_sizes": OUT / "table_sizes.csv",
        "index_inventory": OUT / "index_inventory.csv",
        "index_usage": OUT / "index_usage.csv",
        "table_activity": OUT / "table_activity.csv",
        "geometry_columns": OUT / "geometry_columns.csv",
        "srid_distribution": OUT / "srid_distribution.csv",
        "geometry_quality": OUT / "geometry_quality.csv",
    }
    for name, path in required.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing baseline input {name}: {path}")

    table_sizes = read_csv(required["table_sizes"])
    index_inventory = read_csv(required["index_inventory"])
    index_usage = read_csv(required["index_usage"])
    table_activity = read_csv(required["table_activity"])
    geometry_columns = read_csv(required["geometry_columns"])
    srid_distribution = read_csv(required["srid_distribution"])
    geometry_quality = read_csv(required["geometry_quality"])

    findings: list[dict[str, Any]] = []

    # Duplicate/overlapping indexes.
    by_table: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in index_inventory:
        by_table[(row.get("schemaname", ""), row.get("tablename", ""))].append(row)

    for (schema, table), items in by_table.items():
        sig_map: dict[str, list[dict[str, str]]] = defaultdict(list)
        for item in items:
            sig_map[idx_signature(item.get("indexdef", ""))].append(item)
        for _, dupes in sig_map.items():
            if len(dupes) > 1:
                findings.append(
                    {
                        "type": "duplicate_index_definition",
                        "severity": "high",
                        "table": f"{schema}.{table}",
                        "indexes": [d.get("indexname") for d in dupes],
                        "evidence": [d.get("indexdef") for d in dupes],
                        "recommendation": "Review duplicates and retain only required index set after workload validation.",
                        "action": "candidate",
                    }
                )

    # Confirm overlapping GiST concern on external_features if present.
    ext_indexes = [r for r in index_inventory if r.get("tablename") == "external_features"]
    ext_gist = [r for r in ext_indexes if "using gist" in (r.get("indexdef", "").lower())]
    if len(ext_gist) >= 2:
        findings.append(
            {
                "type": "overlapping_spatial_indexes",
                "severity": "high",
                "table": "external_features",
                "indexes": [r.get("indexname") for r in ext_gist],
                "evidence": [r.get("indexdef") for r in ext_gist],
                "recommendation": "Validate per-index usage and consolidate redundant GiST indexes.",
                "action": "confirmed",
            }
        )

    # Low-use indexes.
    for row in index_usage:
        idx_scan = to_int(row.get("idx_scan"))
        name = row.get("index_name", "")
        table = row.get("table_name", "")
        if idx_scan == 0:
            findings.append(
                {
                    "type": "unused_index",
                    "severity": "medium",
                    "table": table,
                    "index": name,
                    "evidence": {"idx_scan": idx_scan},
                    "recommendation": "Review whether index is still needed; avoid blind drops without query-history window.",
                    "action": "candidate",
                }
            )

    # Dead tuple / autovacuum signal.
    for row in table_activity:
        table = row.get("table_name", "")
        live = to_int(row.get("n_live_tup"))
        dead = to_int(row.get("n_dead_tup"))
        if live <= 0:
            continue
        ratio = dead / max(live, 1)
        if table == "external_features" and ratio >= 0.1:
            findings.append(
                {
                    "type": "dead_tuple_pressure",
                    "severity": "high",
                    "table": table,
                    "evidence": {"n_live_tup": live, "n_dead_tup": dead, "dead_ratio": ratio},
                    "recommendation": "Tune autovacuum thresholds/scale factors and monitor bloat growth.",
                    "action": "confirmed",
                }
            )
        elif ratio >= 0.2:
            findings.append(
                {
                    "type": "dead_tuple_pressure",
                    "severity": "medium",
                    "table": table,
                    "evidence": {"n_live_tup": live, "n_dead_tup": dead, "dead_ratio": ratio},
                    "recommendation": "Investigate vacuum/analyze cadence for this table.",
                    "action": "candidate",
                }
            )

    # Un-analyzed signal.
    for row in table_activity:
        if not (row.get("last_analyze") or row.get("last_autoanalyze")):
            findings.append(
                {
                    "type": "never_analyzed",
                    "severity": "medium",
                    "table": row.get("table_name"),
                    "evidence": {
                        "last_analyze": row.get("last_analyze"),
                        "last_autoanalyze": row.get("last_autoanalyze"),
                    },
                    "recommendation": "Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.",
                    "action": "candidate",
                }
            )

    # SRID inconsistencies.
    srid_by_table: dict[str, set[str]] = defaultdict(set)
    for row in srid_distribution:
        srid_by_table[row.get("table_name", "")].add(str(row.get("srid", "")))
    for table, srids in srid_by_table.items():
        if len(srids) > 1:
            findings.append(
                {
                    "type": "srid_inconsistency",
                    "severity": "high",
                    "table": table,
                    "evidence": {"srids": sorted(srids)},
                    "recommendation": "Normalize geometry SRIDs per table to avoid costly runtime transforms.",
                    "action": "candidate",
                }
            )

    # Geometry validity/complexity.
    for row in geometry_quality:
        layer = row.get("layer", "")
        invalid = to_int(row.get("invalid_features"))
        max_points = to_int(row.get("max_points"))
        if invalid > 0:
            findings.append(
                {
                    "type": "invalid_geometries",
                    "severity": "high",
                    "table": "external_features",
                    "layer": layer,
                    "evidence": {"invalid_features": invalid},
                    "recommendation": "Repair invalid geometries in ingestion/build pipeline before serving.",
                    "action": "candidate",
                }
            )
        if max_points > 50000:
            findings.append(
                {
                    "type": "oversized_geometries",
                    "severity": "medium",
                    "table": "external_features",
                    "layer": layer,
                    "evidence": {"max_points": max_points},
                    "recommendation": "Consider generalized geometries for low zoom and heavy render paths.",
                    "action": "candidate",
                }
            )

    # Missing obvious spatial index signal by geometry_columns + inventory text match.
    inv_text = "\n".join((r.get("indexdef", "") or "") for r in index_inventory).lower()
    for gc in geometry_columns:
        table = gc.get("f_table_name", "")
        col = gc.get("f_geometry_column", "")
        if table and col:
            key = f" on {table} using gist ({col.lower()}"
            if key not in inv_text:
                findings.append(
                    {
                        "type": "missing_spatial_index_candidate",
                        "severity": "high",
                        "table": table,
                        "column": col,
                        "evidence": {"index_match_probe": key},
                        "recommendation": "Confirm whether a GiST/SP-GiST index exists or should be created.",
                        "action": "candidate",
                    }
                )

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_files": {k: str(v) for k, v in required.items()},
        "summary": {
            "total_findings": len(findings),
            "confirmed": sum(1 for f in findings if f.get("action") == "confirmed"),
            "candidate": sum(1 for f in findings if f.get("action") != "confirmed"),
        },
        "findings": findings,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    out_json = OUT / "database_content_findings.json"
    out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines: list[str] = [
        "# Database Content Assessment",
        "",
        f"Generated: {payload['generated_at_utc']}",
        "",
        "## Scope",
        "- Baseline CSV outputs only",
        "- No schema/data changes applied",
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
                f"- Table: {f.get('table', 'n/a')}",
                f"- Action status: {f.get('action')}",
                f"- Evidence: `{json.dumps(f.get('evidence', {}), ensure_ascii=False)}`",
                f"- Recommendation: {f.get('recommendation')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Notes",
            "- Duplicate/overlap findings are review candidates until usage and plan review complete.",
            "- No indexes were created/dropped by this assessment.",
            "",
        ]
    )
    out_md = REPORTS / "database_content_assessment.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"ok": True, "outputs": [str(out_md), str(out_json)]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
