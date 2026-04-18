from __future__ import annotations

from pathlib import Path


def ensure_runtime_dirs(root: Path) -> None:
    for rel in ("postgres/bin", "postgres/data", "postgres/share", "logs", "zip", "assets_store"):
        (root / rel).mkdir(parents=True, exist_ok=True)
