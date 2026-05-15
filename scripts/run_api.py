from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main():
    reload_enabled = os.environ.get("SURVEYCATALYST_API_RELOAD", "1").lower() not in {"0", "false", "no"}
    reload_dirs = [
        str(ROOT / "src"),
        str(ROOT / "app" / "static"),
        str(ROOT / "app"),
    ] if reload_enabled else None
    reload_excludes = [
        "runtime/*",
        ".cache/*",
        "workspace/*",
    ] if reload_enabled else None
    uvicorn.run(
        "api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=reload_enabled,
        reload_dirs=reload_dirs,
        reload_excludes=reload_excludes,
    )


if __name__ == "__main__":
    main()
