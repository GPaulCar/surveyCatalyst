from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path.cwd()

def run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError((result.stdout or "") + (result.stderr or ""))

def main() -> None:
    target = ROOT / "app" / "openlayers_map.html"
    if not target.exists():
        raise FileNotFoundError(target)

    run(["git", "checkout", "--", "app/openlayers_map.html"])
    print("[OK] restored app/openlayers_map.html from git HEAD")
    print("[DONE] restart the API and hard refresh the browser")

if __name__ == "__main__":
    main()