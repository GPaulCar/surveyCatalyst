from __future__ import annotations

import argparse
import json
import socket
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend


OUT_DIR = ROOT / "assessment" / "output"


@dataclass
class ActionResult:
    name: str
    status: str
    details: dict[str, Any]


def q1(cur, sql: str, params: tuple[Any, ...] = ()) -> tuple[Any, ...]:
    cur.execute(sql, params)
    row = cur.fetchone()
    return row if row is not None else tuple()


def qa(cur, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    cur.execute(sql, params)
    return cur.fetchall()


def compute_setting_recommendations(settings: dict[str, Any]) -> dict[str, str]:
    # Conservative baseline recommendations; applied manually by operator.
    shared_buffers = "1GB"
    effective_cache_size = "4GB"
    work_mem = "16MB"
    maintenance_work_mem = "512MB"
    max_wal_size = "4GB"
    checkpoint_timeout = "15min"
    autovacuum_max_workers = "5"
    autovacuum_vacuum_scale_factor = "0.05"
    autovacuum_analyze_scale_factor = "0.03"

    return {
        "shared_buffers": shared_buffers,
        "effective_cache_size": effective_cache_size,
        "work_mem": work_mem,
        "maintenance_work_mem": maintenance_work_mem,
        "max_wal_size": max_wal_size,
        "checkpoint_timeout": checkpoint_timeout,
        "autovacuum_max_workers": autovacuum_max_workers,
        "autovacuum_vacuum_scale_factor": autovacuum_vacuum_scale_factor,
        "autovacuum_analyze_scale_factor": autovacuum_analyze_scale_factor,
        "note": (
            "Review against host RAM/IO profile before apply. "
            "Do not blindly copy between servers."
        ),
    }


def collect_current_settings(cur) -> dict[str, str]:
    rows = qa(
        cur,
        """
        SELECT name, setting
        FROM pg_settings
        WHERE name IN (
          'shared_buffers','effective_cache_size','work_mem','maintenance_work_mem',
          'max_wal_size','checkpoint_timeout','autovacuum_max_workers',
          'autovacuum_vacuum_scale_factor','autovacuum_analyze_scale_factor'
        )
        ORDER BY name
        """,
    )
    return {name: setting for name, setting in rows}


def run() -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="Assess and apply safe host-local PostgreSQL optimizations.")
    parser.add_argument("--apply", action="store_true", help="Apply changes. Default is dry-run.")
    args = parser.parse_args()
    dry_run = not args.apply

    backend = build_backend()
    conn = backend.connect()
    conn.autocommit = False

    actions: list[ActionResult] = []
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    host = socket.gethostname()

    vacuum_targets = [
        "public.layers_registry",
        "public.ingestion_runs",
        "data_layers.bkg_vg25_boundaries",
        "data_layers.bkg_vg250_boundaries",
    ]
    reindex_targets = [
        "public.layers_registry",
        "public.ingestion_runs",
        "data_layers.bkg_vg25_boundaries",
        "data_layers.bkg_vg250_boundaries",
    ]

    try:
        with conn.cursor() as cur:
            ident = q1(
                cur,
                """
                SELECT current_database()::text, inet_server_addr()::text, inet_server_port(), version()
                """,
            )
            current_settings = collect_current_settings(cur)
            recommended_settings = compute_setting_recommendations(current_settings)

            # 1) VACUUM ANALYZE targets
            for target in vacuum_targets:
                if dry_run:
                    actions.append(
                        ActionResult(
                            name=f"vacuum_analyze:{target}",
                            status="planned",
                            details={"sql": f"VACUUM (ANALYZE) {target};"},
                        )
                    )
                else:
                    conn.commit()
                    conn.autocommit = True
                    cur.execute(f"VACUUM (ANALYZE) {target};")
                    conn.autocommit = False
                    actions.append(
                        ActionResult(
                            name=f"vacuum_analyze:{target}",
                            status="applied",
                            details={},
                        )
                    )

            # 2) Targeted geometry repair
            invalid_before = q1(
                cur,
                """
                SELECT COUNT(*)::bigint
                FROM external_features
                WHERE layer = 'legal_restricted_areas'
                  AND geom IS NOT NULL
                  AND NOT ST_IsValid(geom)
                """,
            )[0]
            if dry_run:
                actions.append(
                    ActionResult(
                        name="repair_invalid_geometries:legal_restricted_areas",
                        status="planned",
                        details={"invalid_before": int(invalid_before)},
                    )
                )
            else:
                cur.execute(
                    """
                    UPDATE external_features
                    SET geom = ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3))
                    WHERE layer = 'legal_restricted_areas'
                      AND geom IS NOT NULL
                      AND NOT ST_IsValid(geom)
                    """
                )
                repaired = cur.rowcount
                actions.append(
                    ActionResult(
                        name="repair_invalid_geometries:legal_restricted_areas",
                        status="applied",
                        details={"invalid_before": int(invalid_before), "rows_updated": int(repaired)},
                    )
                )

            # 3) REINDEX small/high-churn tables
            for target in reindex_targets:
                if dry_run:
                    actions.append(
                        ActionResult(
                            name=f"reindex_table:{target}",
                            status="planned",
                            details={"sql": f"REINDEX TABLE {target};"},
                        )
                    )
                else:
                    conn.commit()
                    conn.autocommit = True
                    cur.execute(f"REINDEX TABLE {target};")
                    conn.autocommit = False
                    actions.append(
                        ActionResult(
                            name=f"reindex_table:{target}",
                            status="applied",
                            details={},
                        )
                    )

            # 4) Large-index candidates report only (no drops)
            large_indexes = qa(
                cur,
                """
                SELECT schemaname, relname, indexrelname, idx_scan, pg_relation_size(indexrelid) AS bytes
                FROM pg_stat_user_indexes
                WHERE relname = 'external_features'
                ORDER BY pg_relation_size(indexrelid) DESC
                """,
            )
            actions.append(
                ActionResult(
                    name="external_features_index_review",
                    status="reported",
                    details={
                        "drop_automation": "disabled",
                        "candidates": [
                            {
                                "schema": r[0],
                                "table": r[1],
                                "index": r[2],
                                "idx_scan": int(r[3] or 0),
                                "size_bytes": int(r[4] or 0),
                            }
                            for r in large_indexes
                        ],
                        "note": "Re-evaluate after stable workload window; do not drop automatically.",
                    },
                )
            )

            if not dry_run:
                conn.commit()

    finally:
        conn.close()

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "mode": "apply" if not dry_run else "dry-run",
        "identity": {
            "database": ident[0] if ident else None,
            "server_addr": ident[1] if ident else None,
            "server_port": int(ident[2]) if ident and ident[2] is not None else None,
            "postgres_version": ident[3] if ident else None,
        },
        "current_settings": current_settings,
        "recommended_settings": recommended_settings,
        "actions": [a.__dict__ for a in actions],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"db_optimize_{host}_{timestamp}.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, "report": str(out_path), "mode": payload["mode"]}, indent=2))
    return payload


if __name__ == "__main__":
    run()
