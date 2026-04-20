from __future__ import annotations

import shutil
from pathlib import Path


class StagingService:
    def __init__(self, workspace_root: Path | None = None):
        self.workspace_root = Path(workspace_root or "data_workspace")
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def source_paths(self, source_key: str) -> dict[str, Path]:
        root = self.workspace_root / source_key
        paths = {
            "root": root,
            "raw": root / "raw",
            "extracted": root / "extracted",
            "processed": root / "processed",
            "reports": root / "reports",
        }
        for p in paths.values():
            p.mkdir(parents=True, exist_ok=True)
        return paths

    def reset_extracted(self, source_key: str) -> Path:
        extracted = self.source_paths(source_key)["extracted"]
        if extracted.exists():
            shutil.rmtree(extracted, ignore_errors=True)
        extracted.mkdir(parents=True, exist_ok=True)
        return extracted

    def promoted_marker(self, source_key: str, artifact_name: str) -> Path:
        processed = self.source_paths(source_key)["processed"]
        marker = processed / f"{artifact_name}.promoted"
        marker.write_text("promoted\n", encoding="utf-8")
        return marker
