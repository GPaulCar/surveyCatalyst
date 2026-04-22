from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT / "workspace"
DOWNLOADS_ROOT = WORKSPACE_ROOT / "downloads"
DOWNLOADS_RAW_ROOT = DOWNLOADS_ROOT / "raw"
DOWNLOADS_CURATED_ROOT = DOWNLOADS_ROOT / "curated"
EXPORTS_ROOT = WORKSPACE_ROOT / "exports"

for path in [
    WORKSPACE_ROOT,
    DOWNLOADS_ROOT,
    DOWNLOADS_RAW_ROOT,
    DOWNLOADS_CURATED_ROOT,
    EXPORTS_ROOT,
]:
    path.mkdir(parents=True, exist_ok=True)

def slugify(value: str | None, default: str = "export") -> str:
    raw = (value or "").strip().lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return raw or default

def timestamp_slug(description: str | None, default: str = "export") -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{slugify(description, default=default)}"

def export_folder(description: str | None, default: str = "export") -> Path:
    folder = EXPORTS_ROOT / timestamp_slug(description, default=default)
    folder.mkdir(parents=True, exist_ok=True)
    return folder
