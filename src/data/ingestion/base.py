from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
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
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseProvider:
    source_key: str = ""
    source_name: str = ""
    schema_name: str = ""
    workspace_name: str = ""

    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = Path(workspace_root or "data_workspace")
        self.workspace = self.workspace_root / self.workspace_name
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.backend = build_backend()

    def dry_run(self) -> ProviderResult:
        raise NotImplementedError

    def run(self, force: bool = False) -> ProviderResult:
        raise NotImplementedError

    def create_schema(self) -> None:
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}")
        conn.commit()

    def download_file(self, url: str, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=300) as response:
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        return destination

    def extract_zip(self, zip_path: Path, destination: Path) -> Path:
        import zipfile
        if destination.exists():
            shutil.rmtree(destination, ignore_errors=True)
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(destination)
        return destination

    def write_artifact_record(self, artifact_type: str, local_path: Path, remote_url: str | None = None, version_label: str | None = None) -> None:
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO ingestion_artifacts (source_key, artifact_type, local_path, remote_url, version_label)
                VALUES (%s, %s, %s, %s, %s)
                ''',
                (self.source_key, artifact_type, str(local_path), remote_url, version_label),
            )
        conn.commit()

    def register_layer(self, layer_key: str, layer_name: str, source_table: str, geometry_type: str, metadata: dict[str, Any] | None = None, sort_order: int = 500) -> None:
        conn = self.backend.connect()
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
