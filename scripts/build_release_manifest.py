from __future__ import annotations

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
manifest = {
    "app": "surveyCatalyst",
    "runtime": "portable-postgresql-postgis",
    "status": "release-candidate-1",
}
out = ROOT / "release_manifest.json"
out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(out)
