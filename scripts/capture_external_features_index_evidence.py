from __future__ import annotations

import json
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

OUT_DIR = ROOT / "assessment" / "output"


def q_all(cur, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    cur.execute(sql, params)
    return cur.fetchall()


def explain(cur, sql: str, params: tuple[Any, ...] = ()) -> list[str]:
    cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {sql}", params)
    return [row[0] for row in cur.fetchall()]


def main() -> int:
    backend = build_backend()
    conn = backend.connect()
    host = socket.gethostname()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    try:
        with conn.cursor() as cur:
            identity = q_all(
                cur,
                """
                SELECT current_database()::text, inet_server_addr()::text, inet_server_port(), version()
                """,
            )[0]

            index_usage = q_all(
                cur,
                """
                SELECT
                  s.schemaname,
                  s.relname AS table_name,
                  s.indexrelname AS index_name,
                  s.idx_scan,
                  pg_relation_size(s.indexrelid) AS index_size_bytes,
                  pg_size_pretty(pg_relation_size(s.indexrelid)) AS index_size_pretty
                FROM pg_stat_user_indexes s
                WHERE s.relname = 'external_features'
                ORDER BY pg_relation_size(s.indexrelid) DESC
                """,
            )

            layer_count_plan = explain(
                cur,
                "SELECT count(*) FROM external_features WHERE layer = %s",
                ("parcel_boundaries",),
            )
            spatial_filter_plan = explain(
                cur,
                """
                SELECT id
                FROM external_features
                WHERE layer = %s
                  AND geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                LIMIT 500
                """,
                ("parcel_boundaries", 11.0, 48.0, 11.2, 48.2),
            )

            layer_scan_counts = q_all(
                cur,
                """
                SELECT layer, COUNT(*)::bigint
                FROM external_features
                GROUP BY layer
                ORDER BY layer
                """,
            )

        report = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "host": host,
            "identity": {
                "database": identity[0],
                "server_addr": identity[1],
                "server_port": int(identity[2]),
                "postgres_version": identity[3],
            },
            "external_features_index_usage": [
                {
                    "schema": r[0],
                    "table": r[1],
                    "index": r[2],
                    "idx_scan": int(r[3] or 0),
                    "index_size_bytes": int(r[4] or 0),
                    "index_size_pretty": r[5],
                }
                for r in index_usage
            ],
            "query_plans": {
                "count_by_layer_parcel_boundaries": layer_count_plan,
                "spatial_filter_parcel_boundaries_bbox": spatial_filter_plan,
            },
            "layer_counts": [{"layer": r[0], "count": int(r[1])} for r in layer_scan_counts],
        }

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUT_DIR / f"external_features_index_evidence_{host}_{ts}.json"
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "report": str(out_path)}, indent=2))
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
