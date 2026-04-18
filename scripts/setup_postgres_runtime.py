from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path


def main() -> None:
    archive = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    postgres_root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("postgres")

    if archive is None or not archive.exists():
        raise SystemExit("Usage: python scripts/setup_postgres_runtime.py <archive_path> [postgres_root]")

    postgres_root.mkdir(parents=True, exist_ok=True)
    (postgres_root / "bin").mkdir(parents=True, exist_ok=True)
    (postgres_root / "data").mkdir(parents=True, exist_ok=True)
    (postgres_root / "share").mkdir(parents=True, exist_ok=True)

    suffix = archive.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(archive, "r") as z:
            z.extractall(postgres_root / "_staging")
    else:
        raise SystemExit("Only zip archives are supported by this setup script")

    staging = postgres_root / "_staging"
    candidates = [p for p in staging.rglob("*") if p.is_dir() and p.name.lower() == "bin"]
    if not candidates:
        raise SystemExit("Could not locate extracted PostgreSQL bin directory")

    source_root = candidates[0].parent
    for item in source_root.iterdir():
        dest = postgres_root / item.name
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()
        shutil.move(str(item), str(dest))

    shutil.rmtree(staging, ignore_errors=True)
    print(postgres_root.resolve())


if __name__ == "__main__":
    main()
