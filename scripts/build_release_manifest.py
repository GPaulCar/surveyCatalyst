from __future__ import annotations

from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
manifest = {
    "app": "surveyCatalyst",
    "version": "0.6.0",
    "runtime": "portable-postgresql-postgis",
    "status": "minor-release",
}
out = ROOT / "release_manifest.json"
out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(out)
