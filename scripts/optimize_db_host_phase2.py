from __future__ import annotations

import argparse
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


def q1(cur, sql: str, params: tuple[Any, ...] = ()) -> tuple[Any, ...]:
    cur.execute(sql, params)
    row = cur.fetchone()
    return row if row is not None else tuple()


def run() -> int:
    parser = argparse.ArgumentParser(description="Phase 2 DB optimization: remove redundant layer index and hide/empty BKG proxy layers.")
    parser.add_argument("--apply", action="store_true", help="Apply changes. Default is dry-run.")
    args = parser.parse_args()
    dry_run = not args.apply

    backend = build_backend()
    conn = backend.connect()
    host = socket.gethostname()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    actions: list[dict[str, Any]] = []

    try:
        with conn.cursor() as cur:
            ident = q1(cur, "SELECT current_database()::text, inet_server_addr()::text, inet_server_port(), version()")

            before = {
                "idx_external_features_layer_exists": bool(
                    q1(
                        cur,
                        """
                        SELECT EXISTS (
                          SELECT 1
                          FROM pg_indexes
                          WHERE schemaname = 'public'
                            AND indexname = 'idx_external_features_layer'
                        )
                        """,
                    )[0]
                ),
                "bkg_vg25_rows": int(q1(cur, "SELECT COUNT(*)::bigint FROM data_layers.bkg_vg25_boundaries")[0]),
                "bkg_vg250_rows": int(q1(cur, "SELECT COUNT(*)::bigint FROM data_layers.bkg_vg250_boundaries")[0]),
            }

            if dry_run:
                actions.append({"name": "drop_index:public.idx_external_features_layer", "status": "planned"})
                actions.append({"name": "hide_bkg_registry_layers", "status": "planned"})
                actions.append({"name": "truncate_bkg_tables", "status": "planned"})
                actions.append({"name": "analyze_external_features", "status": "planned"})
            else:
                cur.execute("DROP INDEX IF EXISTS public.idx_external_features_layer")
                actions.append({"name": "drop_index:public.idx_external_features_layer", "status": "applied"})

                cur.execute(
                    """
                    UPDATE layers_registry
                    SET
                      is_visible = FALSE,
                      is_user_selectable = FALSE,
                      metadata = (COALESCE(metadata, '{}'::jsonb) - 'always_show') || '{"hidden_if_empty": true}'::jsonb,
                      updated_at = NOW()
                    WHERE layer_key IN ('bkg_vg250_boundaries', 'bkg_vg25_boundaries')
                    """
                )
                actions.append({"name": "hide_bkg_registry_layers", "status": "applied", "rows_updated": int(cur.rowcount)})

                cur.execute("TRUNCATE TABLE data_layers.bkg_vg250_boundaries")
                cur.execute("TRUNCATE TABLE data_layers.bkg_vg25_boundaries")
                actions.append({"name": "truncate_bkg_tables", "status": "applied"})

                conn.commit()
                conn.autocommit = True
                cur.execute("ANALYZE public.external_features")
                conn.autocommit = False
                actions.append({"name": "analyze_external_features", "status": "applied"})

            after = {
                "idx_external_features_layer_exists": bool(
                    q1(
                        cur,
                        """
                        SELECT EXISTS (
                          SELECT 1
                          FROM pg_indexes
                          WHERE schemaname = 'public'
                            AND indexname = 'idx_external_features_layer'
                        )
                        """,
                    )[0]
                ),
                "bkg_vg25_rows": int(q1(cur, "SELECT COUNT(*)::bigint FROM data_layers.bkg_vg25_boundaries")[0]),
                "bkg_vg250_rows": int(q1(cur, "SELECT COUNT(*)::bigint FROM data_layers.bkg_vg250_boundaries")[0]),
                "bkg_registry": [
                    {
                        "layer_key": r[0],
                        "is_visible": bool(r[1]),
                        "is_user_selectable": bool(r[2]),
                    }
                    for r in cur.execute(
                        """
                        SELECT layer_key, is_visible, is_user_selectable
                        FROM layers_registry
                        WHERE layer_key IN ('bkg_vg250_boundaries', 'bkg_vg25_boundaries')
                        ORDER BY layer_key
                        """
                    ).fetchall()
                ],
            }

            if not dry_run:
                conn.commit()

        report = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "host": host,
            "mode": "apply" if not dry_run else "dry-run",
            "identity": {
                "database": ident[0] if ident else None,
                "server_addr": ident[1] if ident else None,
                "server_port": int(ident[2]) if ident and ident[2] is not None else None,
                "postgres_version": ident[3] if ident else None,
            },
            "before": before,
            "actions": actions,
            "after": after,
        }
    finally:
        conn.close()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"db_optimize_phase2_{host}_{ts}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(out_path), "mode": report["mode"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
