from __future__ import annotations

import json
import socket
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assessment" / "output"
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend


@dataclass
class HealthThresholds:
    dead_tuple_warn_ratio: float = 0.20
    dead_tuple_critical_ratio: float = 0.40
    index_unused_warn_size_mb: int = 128
    stale_stats_warn_minutes: int = 60 * 24


def query_all(cur, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    cur.execute(sql, params)
    return cur.fetchall()


def query_one(cur, sql: str, params: tuple[Any, ...] = ()) -> tuple[Any, ...]:
    cur.execute(sql, params)
    row = cur.fetchone()
    return row if row is not None else tuple()


def assess() -> dict[str, Any]:
    thresholds = HealthThresholds()
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            identity = query_one(
                cur,
                """
                SELECT
                  current_database()::text,
                  inet_server_addr()::text,
                  inet_server_port(),
                  version()
                """,
            )

            db_size = query_one(
                cur,
                """
                SELECT
                  pg_database_size(current_database()),
                  pg_size_pretty(pg_database_size(current_database()))
                """,
            )

            ext = query_all(
                cur,
                "SELECT extname, extversion FROM pg_extension ORDER BY extname",
            )

            table_activity = query_all(
                cur,
                """
                SELECT
                  schemaname,
                  relname,
                  n_live_tup,
                  n_dead_tup,
                  CASE WHEN n_live_tup > 0 THEN (n_dead_tup::numeric / n_live_tup) ELSE 0 END AS dead_ratio,
                  last_autovacuum,
                  last_autoanalyze
                FROM pg_stat_user_tables
                ORDER BY n_dead_tup DESC
                """,
            )

            index_usage = query_all(
                cur,
                """
                SELECT
                  s.schemaname,
                  s.relname,
                  s.indexrelname,
                  s.idx_scan,
                  pg_relation_size(s.indexrelid) AS size_bytes,
                  pg_size_pretty(pg_relation_size(s.indexrelid)) AS size_pretty,
                  EXISTS (
                    SELECT 1
                    FROM pg_inherits i
                    JOIN pg_class child ON child.oid = i.inhrelid
                    JOIN pg_class parent ON parent.oid = i.inhparent
                    WHERE child.relname = s.relname
                      AND parent.relname = 'external_features'
                  ) AS is_external_features_partition_child
                FROM pg_stat_user_indexes s
                ORDER BY pg_relation_size(s.indexrelid) DESC
                """,
            )

            partition_index_family = query_all(
                cur,
                """
                WITH part_idx AS (
                  SELECT
                    s.indexrelname,
                    COALESCE(s.idx_scan, 0) AS idx_scan,
                    pg_relation_size(s.indexrelid) AS size_bytes,
                    CASE
                      WHEN s.indexrelname LIKE '%%_geom_idx' THEN 'geom_idx'
                      WHEN s.indexrelname LIKE '%%_layer_source_id_idx' THEN 'layer_source_id_idx'
                      WHEN s.indexrelname LIKE '%%_layer_idx' THEN 'layer_idx'
                      WHEN s.indexrelname LIKE '%%_pkey' THEN 'pkey'
                      ELSE 'other'
                    END AS family
                  FROM pg_stat_user_indexes s
                  JOIN pg_inherits i
                    ON i.inhrelid = (SELECT oid FROM pg_class WHERE relname = s.relname LIMIT 1)
                  JOIN pg_class p ON p.oid = i.inhparent
                  WHERE p.relname = 'external_features'
                )
                SELECT family, SUM(idx_scan)::bigint, SUM(size_bytes)::bigint
                FROM part_idx
                GROUP BY family
                ORDER BY SUM(size_bytes) DESC
                """,
            )

            duplicate_indexes = query_all(
                cur,
                """
                WITH idx AS (
                  SELECT
                    n.nspname AS schemaname,
                    t.relname AS tablename,
                    i.relname AS indexname,
                    pg_get_indexdef(i.oid) AS idxdef
                  FROM pg_index x
                  JOIN pg_class i ON i.oid = x.indexrelid
                  JOIN pg_class t ON t.oid = x.indrelid
                  JOIN pg_namespace n ON n.oid = t.relnamespace
                  WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                )
                SELECT a.schemaname, a.tablename, a.indexname, b.indexname, a.idxdef
                FROM idx a
                JOIN idx b
                  ON a.schemaname = b.schemaname
                 AND a.tablename = b.tablename
                 AND a.idxdef = b.idxdef
                 AND a.indexname < b.indexname
                ORDER BY a.schemaname, a.tablename
                """,
            )

            external_layer_counts = query_all(
                cur,
                """
                SELECT layer, COUNT(*)::bigint
                FROM external_features
                GROUP BY layer
                ORDER BY layer
                """,
            )

            invalid_geom_top = query_all(
                cur,
                """
                SELECT layer, COUNT(*)::bigint AS invalid_count
                FROM external_features
                WHERE geom IS NOT NULL AND NOT ST_IsValid(geom)
                GROUP BY layer
                ORDER BY invalid_count DESC
                LIMIT 50
                """,
            )

            settings = query_all(
                cur,
                """
                SELECT name, setting, unit, context
                FROM pg_settings
                WHERE name IN (
                  'shared_buffers','effective_cache_size','work_mem','maintenance_work_mem',
                  'max_wal_size','checkpoint_timeout','autovacuum','autovacuum_max_workers',
                  'autovacuum_vacuum_scale_factor','autovacuum_analyze_scale_factor'
                )
                ORDER BY name
                """,
            )

        now_utc = datetime.now(timezone.utc)
        dead_table_alerts: list[dict[str, Any]] = []
        stale_stats_alerts: list[dict[str, Any]] = []
        unused_big_indexes: list[dict[str, Any]] = []

        for row in table_activity:
            schema, table, live, dead, dead_ratio, last_vac, last_analyze = row
            if dead_ratio is not None and float(dead_ratio) >= thresholds.dead_tuple_warn_ratio:
                severity = "critical" if float(dead_ratio) >= thresholds.dead_tuple_critical_ratio else "warn"
                dead_table_alerts.append(
                    {
                        "severity": severity,
                        "table": f"{schema}.{table}",
                        "live_tuples": int(live or 0),
                        "dead_tuples": int(dead or 0),
                        "dead_ratio": float(dead_ratio or 0),
                    }
                )

            ref = last_analyze or last_vac
            if ref is not None:
                age_minutes = (now_utc - ref.astimezone(timezone.utc)).total_seconds() / 60.0
                if age_minutes >= thresholds.stale_stats_warn_minutes:
                    stale_stats_alerts.append(
                        {
                            "severity": "warn",
                            "table": f"{schema}.{table}",
                            "minutes_since_stats": round(age_minutes, 1),
                        }
                    )

        for row in index_usage:
            schema, table, index_name, idx_scan, size_bytes, _, is_extf_partition_child = row
            size_mb = int(size_bytes or 0) / (1024 * 1024)
            # Legacy rollback table indexes should not influence runtime health scoring.
            if str(table).startswith("external_features_legacy_"):
                continue
            # Per-partition indexes can legitimately have zero scans; we evaluate these in aggregate below.
            if bool(is_extf_partition_child):
                continue
            if int(idx_scan or 0) == 0 and size_mb >= thresholds.index_unused_warn_size_mb:
                unused_big_indexes.append(
                    {
                        "severity": "warn",
                        "index": f"{schema}.{index_name}",
                        "table": f"{schema}.{table}",
                        "size_mb": round(size_mb, 1),
                    }
                )

        partition_index_family_summary = []
        for family, scan_sum, size_sum in partition_index_family:
            partition_index_family_summary.append(
                {
                    "family": family,
                    "idx_scan_sum": int(scan_sum or 0),
                    "size_mb_total": round(int(size_sum or 0) / (1024 * 1024), 1),
                }
            )

        findings = {
            "dead_tuple_alerts": dead_table_alerts,
            "stale_stats_alerts": stale_stats_alerts,
            "unused_big_indexes": unused_big_indexes,
            "partition_index_family_summary": partition_index_family_summary,
            "duplicate_index_candidates": [
                {
                    "schema": r[0],
                    "table": r[1],
                    "index_a": r[2],
                    "index_b": r[3],
                }
                for r in duplicate_indexes
            ],
            "invalid_geometry_layers": [{"layer": r[0], "invalid_count": int(r[1])} for r in invalid_geom_top],
        }

        severity_score = (
            len([x for x in dead_table_alerts if x["severity"] == "critical"]) * 3
            + len([x for x in dead_table_alerts if x["severity"] == "warn"]) * 2
            + len(unused_big_indexes)
            + len(duplicate_indexes)
        )
        overall = "critical" if severity_score >= 10 else "warn" if severity_score >= 3 else "ok"

        return {
            "generated_at_utc": now_utc.isoformat(),
            "host": socket.gethostname(),
            "identity": {
                "database": identity[0] if identity else None,
                "server_addr": identity[1] if identity else None,
                "server_port": int(identity[2]) if identity and identity[2] is not None else None,
                "postgres_version": identity[3] if identity else None,
            },
            "database_size": {
                "bytes": int(db_size[0]) if db_size else 0,
                "pretty": db_size[1] if db_size else "0 bytes",
            },
            "extensions": [{"name": r[0], "version": r[1]} for r in ext],
            "key_settings": [{"name": r[0], "setting": r[1], "unit": r[2], "context": r[3]} for r in settings],
            "layer_counts": [{"layer": r[0], "count": int(r[1])} for r in external_layer_counts],
            "findings": findings,
            "summary": {
                "overall": overall,
                "severity_score": severity_score,
                "dead_tuple_alert_count": len(dead_table_alerts),
                "unused_big_index_count": len(unused_big_indexes),
                "duplicate_index_candidate_count": len(duplicate_indexes),
                "invalid_geometry_layer_count": len(invalid_geom_top),
            },
        }
    finally:
        conn.close()


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = assess()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    host = report.get("host", "unknown-host")
    out_path = OUT_DIR / f"db_health_{host}_{stamp}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(out_path), "summary": report["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
