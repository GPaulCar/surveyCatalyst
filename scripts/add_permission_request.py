from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKER_DIR = ROOT / "workspace" / "permissions" / "tracker"
TRACKER_FILE = TRACKER_DIR / "request_tracker.jsonl"
INDEX_FILE = TRACKER_DIR / "request_tracker_index.json"

def main(argv: list[str]) -> int:
    if len(argv) < 5:
        print("Usage: python scripts/add_permission_request.py <layer> <source_id> <status> <description>")
        return 1

    layer = argv[1]
    source_id = argv[2]
    status = argv[3]
    description = " ".join(argv[4:])

    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "saved_at": datetime.now().isoformat(),
        "layer": layer,
        "source_id": source_id,
        "status": status,
        "description": description,
    }

    with TRACKER_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    index = {"version": 1, "requests": 0}
    if INDEX_FILE.exists():
        index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    index["requests"] = int(index.get("requests", 0)) + 1
    INDEX_FILE.write_text(json.dumps(index, indent=2), encoding="utf-8")

    print("[DONE] permission request tracked")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
