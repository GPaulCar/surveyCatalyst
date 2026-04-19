from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import shutil
import subprocess
from typing import Any

import requests

from core.db import build_backend


@dataclass
class ProviderResult:
    source_key: str
    status: str
    message: str
    records_loaded: int = 0
    layer_keys: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    version_label: str | None = None


class BaseProvider:
    source_key: str = ""
    source_name: str = ""
    schema_name: str = ""
    workspace_name: str = ""

    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = workspace_root or Path("data_workspace")
        self.workspace = self.workspace_root / self.workspace_name
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.backend = build_backend()

    def run(self, force: bool = False) -> ProviderResult:
        raise NotImplementedError

    def create_schema(self) -> None:
        conn = self.backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}")
            conn.commit()
        finally:
            self.backend.close()

    def write_artifact_record(self, artifact_type: str, local_path: Path, remote_url: str | None = None, version_label: str | None = None) -> None:
        backend = build_backend()
        conn = backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO ingestion_artifacts (source_key, artifact_type, local_path, remote_url, version_label)
                    VALUES (%s, %s, %s, %s, %s)
                    ''',
                    (self.source_key, artifact_type, str(local_path), remote_url, version_label),
                )
            conn.commit()
        finally:
            backend.close()

    def register_layer(self, layer_key: str, layer_name: str, source_table: str, geometry_type: str, metadata: dict[str, Any] | None = None, sort_order: int = 500) -> None:
        backend = build_backend()
        conn = backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO layers_registry (
                        layer_key, layer_name, layer_group, source_table, geometry_type,
                        is_user_selectable, is_visible, opacity, sort_order, metadata
                    )
                    VALUES (%s, %s, 'context', %s, %s, TRUE, TRUE, 1.0, %s, %s::jsonb)
                    ON CONFLICT (layer_key) DO UPDATE SET
                        layer_name = EXCLUDED.layer_name,
                        source_table = EXCLUDED.source_table,
                        geometry_type = EXCLUDED.geometry_type,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    ''',
                    (layer_key, layer_name, source_table, geometry_type, sort_order, json.dumps(metadata or {})),
                )
            conn.commit()
        finally:
            backend.close()

    def download_file(self, url: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(url, stream=True, timeout=120)
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
        return destination

    def extract_zip(self, zip_path: Path, destination: Path) -> Path:
        import zipfile

        if destination.exists():
            shutil.rmtree(destination)
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(destination)
        return destination

    def run_sql(self, sql: str, params: tuple | None = None) -> list[tuple]:
        backend = build_backend()
        conn = backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, params or ())
                rows = cur.fetchall() if cur.description else []
            conn.commit()
            return rows
        finally:
            backend.close()

    def import_with_ogr2ogr(self, source_path: Path, table_name: str, geometry_name: str = "geom", overwrite: bool = True) -> None:
        settings_rows = self.run_sql("SELECT current_database()")
        _ = settings_rows
        conninfo = self.backend.dsn() if hasattr(self.backend, "dsn") else ""
        cmd = [
            "ogr2ogr",
            "-f", "PostgreSQL",
            f"PG:{conninfo}",
            str(source_path),
            "-nln", f"{self.schema_name}.{table_name}",
            "-lco", f"GEOMETRY_NAME={geometry_name}",
            "-lco", f"SCHEMA={self.schema_name}",
        ]
        if overwrite:
            cmd.append("-overwrite")

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "ogr2ogr failed")
