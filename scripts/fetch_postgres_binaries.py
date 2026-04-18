from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests


EDB_BINARIES_PAGE = "https://www.enterprisedb.com/download-postgresql-binaries"


def find_windows_x64_link(version: str) -> str:
    html = requests.get(EDB_BINARIES_PAGE, timeout=60).text
    m = re.search(rf"Binaries from installer Version\s+{re.escape(version)}(.*?)(Binaries from installer Version|Additional Resources)", html, re.S)
    if not m:
        raise RuntimeError(f"Version {version} not found on EDB binaries page")
    block = m.group(1)

    hrefs = re.findall(r'href="([^"]+)"', block)
    candidates = []
    for href in hrefs:
        full = urljoin(EDB_BINARIES_PAGE, href)
        lowered = full.lower()
        if any(token in lowered for token in ["windows", "win", "x64", "x86-64", ".zip", ".exe"]):
            candidates.append(full)

    if not candidates:
        # fall back to any href in block
        if hrefs:
            return urljoin(EDB_BINARIES_PAGE, hrefs[0])
        raise RuntimeError(f"No download link found for {version}")

    return candidates[0]


def main() -> None:
    version = sys.argv[1] if len(sys.argv) > 1 else "17.9"
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("downloads")
    out_dir.mkdir(parents=True, exist_ok=True)

    url = find_windows_x64_link(version)
    target = out_dir / url.split("/")[-1]

    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with target.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    print(target)


if __name__ == "__main__":
    main()
