from __future__ import annotations

import argparse
import json
import re
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


def qa(cur, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    cur.execute(sql, params)
    return cur.fetchall()


def sql_lit(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def safe_ident(value: str) -> str:
    x = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip().lower())
    x = re.sub(r"_+", "_", x).strip("_")
    if not x:
        x = "layer"
    return x


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate external_features to partitioned-by-layer table with guarded swap.")
    parser.add_argument("--apply", action="store_true", help="Apply migration. Default is dry-run.")
    parser.add_argument("--partition-count", type=int, default=24, help="Max explicit layer partitions; remainder goes to default.")
    args = parser.parse_args()
    dry_run = not args.apply

    host = socket.gethostname()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    legacy_table = f"external_features_legacy_{stamp.lower()}"
    staging_table = "external_features_part_new"

    backend = build_backend()
    conn = backend.connect()
    conn.autocommit = False
    actions: list[dict[str, Any]] = []

    try:
        with conn.cursor() as cur:
            ident = q1(cur, "SELECT current_database()::text, inet_server_addr()::text, inet_server_port(), version()")
            already_partitioned = bool(
                q1(
                    cur,
                    """
                    SELECT EXISTS (
                      SELECT 1
                      FROM pg_partitioned_table p
                      JOIN pg_class c ON c.oid = p.partrelid
                      WHERE c.relname = 'external_features'
                    )
                    """,
                )[0]
            )
            if already_partitioned:
                actions.append({"name": "precheck", "status": "already_partitioned"})
                report = {
                    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                    "host": host,
                    "mode": "apply" if not dry_run else "dry-run",
                    "overall_ok": True,
                    "identity": {
                        "database": ident[0] if ident else None,
                        "server_addr": ident[1] if ident else None,
                        "server_port": int(ident[2]) if ident and ident[2] is not None else None,
                        "postgres_version": ident[3] if ident else None,
                    },
                    "actions": actions,
                }
                OUT_DIR.mkdir(parents=True, exist_ok=True)
                out = OUT_DIR / f"partition_external_features_{host}_{stamp}.json"
                out.write_text(json.dumps(report, indent=2), encoding="utf-8")
                print(json.dumps({"ok": True, "report": str(out)}, indent=2))
                return 0

            layer_rows = qa(
                cur,
                """
                SELECT layer, COUNT(*)::bigint AS cnt
                FROM external_features
                GROUP BY layer
                ORDER BY cnt DESC
                """,
            )
            layers = [str(r[0]) for r in layer_rows if r[0] is not None][: max(1, args.partition_count)]
            actions.append({"name": "plan_layers", "status": "ok", "count": len(layers)})

            if dry_run:
                actions.append({"name": "create_staging_partitioned_table", "status": "planned"})
                actions.append({"name": "copy_data", "status": "planned"})
                actions.append({"name": "swap_tables_and_indexes", "status": "planned", "legacy_table": legacy_table})
                actions.append({"name": "rebuild_permission_fk", "status": "planned"})
            else:
                # Clean leftover staging if present.
                cur.execute(f"DROP TABLE IF EXISTS {staging_table} CASCADE")

                # Create partitioned staging table.
                cur.execute(
                    f"""
                    CREATE TABLE {staging_table} (
                      id integer NOT NULL DEFAULT nextval('external_features_id_seq'::regclass),
                      layer text NOT NULL,
                      geom geometry(GEOMETRY, 4326),
                      properties jsonb NOT NULL DEFAULT '{{}}'::jsonb,
                      created_at timestamp without time zone DEFAULT now(),
                      source_table text,
                      source_id text
                    ) PARTITION BY LIST (layer)
                    """
                )
                actions.append({"name": "create_staging_partitioned_table", "status": "applied"})

                # Explicit partitions for top layers.
                used_names: set[str] = set()
                for idx, layer_name in enumerate(layers, start=1):
                    base = f"extf_p_{safe_ident(layer_name)}"
                    name = base[:50]
                    while name in used_names:
                        name = f"{base[:44]}_{idx}"
                    used_names.add(name)
                    cur.execute(
                        f"CREATE TABLE {name} PARTITION OF {staging_table} FOR VALUES IN ({sql_lit(layer_name)})"
                    )
                cur.execute(f"CREATE TABLE extf_p_default PARTITION OF {staging_table} DEFAULT")
                actions.append({"name": "create_partitions", "status": "applied", "explicit_partitions": len(layers)})

                # Copy data preserving IDs.
                cur.execute(
                    f"""
                    INSERT INTO {staging_table} (id, layer, geom, properties, created_at, source_table, source_id)
                    SELECT id, COALESCE(layer, '__null__'), geom, properties, created_at, source_table, source_id
                    FROM external_features
                    """
                )
                copied = int(cur.rowcount)
                actions.append({"name": "copy_data", "status": "applied", "rows": copied})

                # Constraints + indexes on staging.
                cur.execute(f"ALTER TABLE {staging_table} ADD CONSTRAINT extf_part_pk PRIMARY KEY (id, layer)")
                cur.execute(f"CREATE INDEX extf_part_geom_gist ON {staging_table} USING GIST (geom)")
                cur.execute(f"CREATE INDEX extf_part_layer_btree ON {staging_table} (layer)")
                cur.execute(f"CREATE INDEX extf_part_layer_source_id ON {staging_table} (layer, source_id)")
                actions.append({"name": "create_constraints_indexes", "status": "applied"})

                # Atomic swap window.
                cur.execute("LOCK TABLE external_features IN ACCESS EXCLUSIVE MODE")
                has_perm = bool(
                    q1(
                        cur,
                        """
                        SELECT EXISTS (
                          SELECT 1
                          FROM information_schema.tables
                          WHERE table_schema='public' AND table_name='permission_requests'
                        )
                        """,
                    )[0]
                )
                if has_perm:
                    cur.execute("LOCK TABLE permission_requests IN ACCESS EXCLUSIVE MODE")

                # Drop existing FK(s) from permission_requests to external_features
                if has_perm:
                    fks = qa(
                        cur,
                        """
                        SELECT conname
                        FROM pg_constraint
                        WHERE contype='f'
                          AND conrelid='permission_requests'::regclass
                          AND confrelid='external_features'::regclass
                        """
                    )
                    for (conname,) in fks:
                        cur.execute(f'ALTER TABLE permission_requests DROP CONSTRAINT "{conname}"')
                    actions.append({"name": "drop_permission_fks", "status": "applied", "count": len(fks)})

                # Rename current table to legacy.
                cur.execute(f"ALTER TABLE external_features RENAME TO {legacy_table}")

                # Rename legacy indexes to avoid name collisions.
                legacy_indexes = qa(
                    cur,
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname='public' AND tablename=%s
                    """,
                    (legacy_table,),
                )
                for (idx_name,) in legacy_indexes:
                    new_idx_name = f"{idx_name}_legacy_{stamp.lower()}"[:63]
                    cur.execute(f'ALTER INDEX "{idx_name}" RENAME TO "{new_idx_name}"')

                # Bring partitioned table into canonical name.
                cur.execute(f"ALTER TABLE {staging_table} RENAME TO external_features")

                # Rename staged indexes to canonical names expected by runtime.
                cur.execute('ALTER INDEX extf_part_geom_gist RENAME TO idx_external_features_geom')
                cur.execute('ALTER INDEX extf_part_layer_btree RENAME TO idx_external_features_layer_btree')
                cur.execute('ALTER INDEX extf_part_layer_source_id RENAME TO idx_external_features_layer_source_id')

                # Rebuild optional composite FK on permission_requests(feature_id, layer).
                if has_perm:
                    cur.execute(
                        """
                        ALTER TABLE permission_requests
                        ADD CONSTRAINT permission_requests_feature_layer_fk
                        FOREIGN KEY (feature_id, layer)
                        REFERENCES external_features(id, layer)
                        ON DELETE SET NULL
                        NOT VALID
                        """
                    )
                    cur.execute("ALTER TABLE permission_requests VALIDATE CONSTRAINT permission_requests_feature_layer_fk")
                    actions.append({"name": "rebuild_permission_fk", "status": "applied"})

                cur.execute("ANALYZE external_features")
                actions.append(
                    {
                        "name": "swap_complete",
                        "status": "applied",
                        "legacy_table": legacy_table,
                        "rollback_hint": f"rename external_features -> failed_{stamp.lower()}, {legacy_table} -> external_features",
                    }
                )

            if not dry_run:
                conn.commit()
            else:
                conn.rollback()

    finally:
        conn.close()

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "mode": "apply" if not dry_run else "dry-run",
        "overall_ok": True,
        "actions": actions,
        "legacy_table": legacy_table if not dry_run else None,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"partition_external_features_{host}_{stamp}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(out), "mode": report["mode"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
