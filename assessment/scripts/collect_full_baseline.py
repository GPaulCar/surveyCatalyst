from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import socket
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psycopg


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "assessment" / "output"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def env_or_default(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass
class DBConfig:
    host: str
    port: int
    database: str
    user: str
    password: str

    def dsn(self) -> str:
        parts = [
            f"host={self.host}",
            f"port={self.port}",
            f"dbname={self.database}",
            f"user={self.user}",
        ]
        if self.password:
            parts.append(f"password={self.password}")
        return " ".join(parts)


def build_db_config() -> DBConfig:
    return DBConfig(
        host=env_or_default("SC_DB_HOST", "127.0.0.1"),
        port=int(env_or_default("SC_DB_PORT", "55433")),
        database=env_or_default("SC_DB_NAME", "survey_catalyst"),
        user=env_or_default("SC_DB_USER", "sc_user"),
        password=env_or_default("SC_DB_PASSWORD", ""),
    )


def query_rows(conn: psycopg.Connection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d.name for d in cur.description] if cur.description else []
        out: list[dict[str, Any]] = []
        for row in cur.fetchall():
            out.append({cols[i]: row[i] for i in range(len(cols))})
        return out


def query_scalar(conn: psycopg.Connection, sql: str, params: tuple[Any, ...] = ()) -> Any:
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row else None


def collect_system_baseline() -> dict[str, Any]:
    disk = shutil_disk_usage_safe(ROOT)
    return {
        "collected_at_utc": utc_now(),
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": sys.version,
        "cwd": str(ROOT),
        "disk_usage_root": disk,
    }


def shutil_disk_usage_safe(path: Path) -> dict[str, Any]:
    try:
        import shutil

        du = shutil.disk_usage(path)
        return {"total": du.total, "used": du.used, "free": du.free}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def collect_volume_info() -> list[dict[str, Any]]:
    # Windows-friendly and read-only.
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-PSDrive -PSProvider FileSystem | Select-Object Name,Root,Used,Free | ConvertTo-Json -Depth 3",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0 or not proc.stdout.strip():
            return []
        payload = json.loads(proc.stdout)
        if isinstance(payload, dict):
            payload = [payload]
        out: list[dict[str, Any]] = []
        for item in payload:
            out.append(
                {
                    "name": item.get("Name"),
                    "root": item.get("Root"),
                    "used": item.get("Used"),
                    "free": item.get("Free"),
                }
            )
        return out
    except Exception:  # noqa: BLE001
        return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect full PostgreSQL/PostGIS baseline (read-only).")
    parser.add_argument("--dotenv", default=str(ROOT / ".env"), help="Path to .env file")
    parser.add_argument("--allow-analyze", action="store_true", help="Allow ANALYZE VERBOSE after baseline collection")
    args = parser.parse_args()

    load_dotenv(Path(args.dotenv))
    cfg = build_db_config()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    generated: list[str] = []
    started = utc_now()

    system_baseline = collect_system_baseline()
    system_baseline["volumes"] = collect_volume_info()
    write_json(OUT_DIR / "system_baseline.json", system_baseline)
    generated.append("system_baseline.json")

    with psycopg.connect(cfg.dsn(), connect_timeout=5) as conn:
        postgres_identity = {
            "collected_at_utc": utc_now(),
            "current_database": query_scalar(conn, "SELECT current_database()"),
            "current_user": query_scalar(conn, "SELECT current_user"),
            "server_version": query_scalar(conn, "SHOW server_version"),
            "data_directory": query_scalar(conn, "SHOW data_directory"),
            "config_file": query_scalar(conn, "SHOW config_file"),
            "hba_file": query_scalar(conn, "SHOW hba_file"),
            "ident_file": query_scalar(conn, "SHOW ident_file"),
            "listen_addresses": query_scalar(conn, "SHOW listen_addresses"),
            "port": query_scalar(conn, "SHOW port"),
        }
        write_json(OUT_DIR / "postgres_identity.json", postgres_identity)
        generated.append("postgres_identity.json")

        postgres_settings = query_rows(
            conn,
            """
            SELECT name, setting, unit, category, context, vartype, source, boot_val, reset_val, pending_restart
            FROM pg_settings
            ORDER BY name
            """,
        )
        write_csv(OUT_DIR / "postgres_settings.csv", postgres_settings)
        generated.append("postgres_settings.csv")

        extensions = query_rows(
            conn,
            """
            SELECT e.extname, e.extversion, n.nspname AS schema_name
            FROM pg_extension e
            JOIN pg_namespace n ON n.oid = e.extnamespace
            ORDER BY e.extname
            """,
        )
        write_csv(OUT_DIR / "extensions.csv", extensions)
        generated.append("extensions.csv")

        database_sizes = query_rows(
            conn,
            """
            SELECT datname, pg_database_size(datname) AS bytes
            FROM pg_database
            ORDER BY bytes DESC
            """,
        )
        write_csv(OUT_DIR / "database_sizes.csv", database_sizes)
        generated.append("database_sizes.csv")

        table_sizes = query_rows(
            conn,
            """
            SELECT
              n.nspname AS schema_name,
              c.relname AS table_name,
              pg_total_relation_size(c.oid) AS total_bytes,
              pg_relation_size(c.oid) AS table_bytes,
              pg_indexes_size(c.oid) AS index_bytes,
              COALESCE(s.n_live_tup, 0) AS n_live_tup,
              COALESCE(s.n_dead_tup, 0) AS n_dead_tup
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
            WHERE c.relkind = 'r'
              AND n.nspname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY total_bytes DESC
            """,
        )
        write_csv(OUT_DIR / "table_sizes.csv", table_sizes)
        generated.append("table_sizes.csv")

        index_inventory = query_rows(
            conn,
            """
            SELECT
              schemaname,
              tablename,
              indexname,
              indexdef,
              pg_relation_size((schemaname || '.' || indexname)::regclass) AS index_bytes
            FROM pg_indexes
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            ORDER BY index_bytes DESC NULLS LAST
            """,
        )
        write_csv(OUT_DIR / "index_inventory.csv", index_inventory)
        generated.append("index_inventory.csv")

        index_usage = query_rows(
            conn,
            """
            SELECT
              s.relname AS table_name,
              s.indexrelname AS index_name,
              s.idx_scan,
              s.idx_tup_read,
              s.idx_tup_fetch
            FROM pg_stat_user_indexes s
            ORDER BY s.idx_scan DESC
            """,
        )
        write_csv(OUT_DIR / "index_usage.csv", index_usage)
        generated.append("index_usage.csv")

        table_activity = query_rows(
            conn,
            """
            SELECT
              relname AS table_name,
              seq_scan, seq_tup_read, idx_scan, idx_tup_fetch,
              n_tup_ins, n_tup_upd, n_tup_del, n_tup_hot_upd,
              n_live_tup, n_dead_tup,
              last_vacuum, last_autovacuum, last_analyze, last_autoanalyze
            FROM pg_stat_user_tables
            ORDER BY n_live_tup DESC NULLS LAST
            """,
        )
        write_csv(OUT_DIR / "table_activity.csv", table_activity)
        generated.append("table_activity.csv")

        autovacuum_settings = query_rows(
            conn,
            """
            SELECT
              name, setting, unit, context, source
            FROM pg_settings
            WHERE name LIKE 'autovacuum%%'
               OR name IN ('vacuum_cost_delay', 'vacuum_cost_limit')
            ORDER BY name
            """,
        )
        write_csv(OUT_DIR / "autovacuum_settings.csv", autovacuum_settings)
        generated.append("autovacuum_settings.csv")

        geometry_columns = query_rows(
            conn,
            """
            SELECT f_table_schema, f_table_name, f_geometry_column, coord_dimension, srid, type
            FROM public.geometry_columns
            ORDER BY f_table_schema, f_table_name, f_geometry_column
            """,
        )
        write_csv(OUT_DIR / "geometry_columns.csv", geometry_columns)
        generated.append("geometry_columns.csv")

        srid_distribution = query_rows(
            conn,
            """
            SELECT 'external_features' AS table_name, ST_SRID(geom) AS srid, COUNT(*) AS n
            FROM external_features
            WHERE geom IS NOT NULL
            GROUP BY ST_SRID(geom)
            UNION ALL
            SELECT 'survey_objects' AS table_name, ST_SRID(geom) AS srid, COUNT(*) AS n
            FROM survey_objects
            WHERE geom IS NOT NULL
            GROUP BY ST_SRID(geom)
            UNION ALL
            SELECT 'surveys' AS table_name, ST_SRID(geom) AS srid, COUNT(*) AS n
            FROM surveys
            WHERE geom IS NOT NULL
            GROUP BY ST_SRID(geom)
            ORDER BY table_name, n DESC
            """,
        )
        write_csv(OUT_DIR / "srid_distribution.csv", srid_distribution)
        generated.append("srid_distribution.csv")

        geometry_quality = query_rows(
            conn,
            """
            WITH sample AS (
              SELECT layer, geom
              FROM external_features
              WHERE geom IS NOT NULL
              ORDER BY id DESC
              LIMIT 20000
            )
            SELECT
              layer,
              COUNT(*) AS sampled_features,
              COUNT(*) FILTER (WHERE NOT ST_IsValid(geom)) AS invalid_features,
              AVG(ST_NPoints(geom)) AS avg_points,
              MAX(ST_NPoints(geom)) AS max_points
            FROM sample
            GROUP BY layer
            ORDER BY sampled_features DESC
            """,
        )
        write_csv(OUT_DIR / "geometry_quality.csv", geometry_quality)
        generated.append("geometry_quality.csv")

        has_pgss = query_scalar(conn, "SELECT COUNT(*) FROM pg_extension WHERE extname = 'pg_stat_statements'") == 1
        pg_stat_rows: list[dict[str, Any]] = []
        if has_pgss:
            pg_stat_rows = query_rows(
                conn,
                """
                SELECT queryid, calls, total_exec_time, mean_exec_time, rows,
                       shared_blks_hit, shared_blks_read, temp_blks_read, temp_blks_written,
                       query
                FROM pg_stat_statements
                ORDER BY total_exec_time DESC
                LIMIT 500
                """,
            )
        write_csv(OUT_DIR / "pg_stat_statements.csv", pg_stat_rows)
        generated.append("pg_stat_statements.csv")

        connections = query_rows(
            conn,
            """
            SELECT pid, usename, datname, application_name, client_addr, state,
                   backend_start, xact_start, query_start, wait_event_type, wait_event
            FROM pg_stat_activity
            ORDER BY pid
            """,
        )
        write_csv(OUT_DIR / "connections.csv", connections)
        generated.append("connections.csv")

        locks = query_rows(
            conn,
            """
            SELECT locktype, mode, granted, pid, relation::regclass::text AS relation_name
            FROM pg_locks
            ORDER BY granted, pid
            """,
        )
        write_csv(OUT_DIR / "locks.csv", locks)
        generated.append("locks.csv")

        if args.allow_analyze:
            with conn.cursor() as cur:
                cur.execute("ANALYZE VERBOSE;")

    manifest = {
        "collected_at_utc": utc_now(),
        "started_at_utc": started,
        "output_dir": str(OUT_DIR),
        "db_target": {
            "host": cfg.host,
            "port": cfg.port,
            "database": cfg.database,
            "user": cfg.user,
        },
        "allow_analyze": bool(args.allow_analyze),
        "files": generated,
    }
    write_json(OUT_DIR / "baseline_manifest.json", manifest)
    print(json.dumps({"ok": True, "files": generated + ["baseline_manifest.json"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
