from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKER_DIR = ROOT / "workspace" / "permissions" / "tracker"
TRACKER_DIR.mkdir(parents=True, exist_ok=True)

TRACKER_FILE = TRACKER_DIR / "request_tracker.jsonl"
INDEX_FILE = TRACKER_DIR / "request_tracker_index.json"

def main() -> int:
    if not TRACKER_FILE.exists():
        TRACKER_FILE.write_text("", encoding="utf-8")
        print(f"[OK] created {TRACKER_FILE}")
    else:
        print(f"[OK] exists {TRACKER_FILE}")

    if not INDEX_FILE.exists():
        INDEX_FILE.write_text(json.dumps({"version": 1, "requests": 0}, indent=2), encoding="utf-8")
        print(f"[OK] created {INDEX_FILE}")
    else:
        print(f"[OK] exists {INDEX_FILE}")

    print("[DONE] permission request tracker initialised")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
