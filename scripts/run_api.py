from __future__ import annotations

import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main():
    uvicorn.run("api.app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
