from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse


class DownloadManifestService:
    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = Path(workspace_root or "data_workspace")
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def checksum_sha256(self, path: str | Path) -> str:
        path = Path(path)
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def build_manifest_entry(
        self,
        source_key: str,
        remote_url: str,
        local_path: str | Path,
        version_label: str | None = None,
    ) -> dict:
        local_path = Path(local_path)
        parsed = urlparse(remote_url)
        return {
            "source_key": source_key,
            "remote_url": remote_url,
            "filename": local_path.name,
            "suffix": local_path.suffix.lower(),
            "local_path": str(local_path),
            "version_label": version_label,
            "sha256": self.checksum_sha256(local_path) if local_path.exists() else None,
            "size_bytes": local_path.stat().st_size if local_path.exists() else None,
            "remote_host": parsed.netloc,
        }

    def write_manifest(self, source_key: str, entry: dict) -> Path:
        source_dir = self.workspace_root / source_key
        source_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = source_dir / "download_manifest.json"
        manifest_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
        return manifest_path
