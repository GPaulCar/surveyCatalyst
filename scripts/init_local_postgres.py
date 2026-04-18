from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    postgres_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("postgres")
    port = sys.argv[2] if len(sys.argv) > 2 else "55432"
    user = sys.argv[3] if len(sys.argv) > 3 else "sc_user"

    bin_dir = postgres_root / "bin"
    data_dir = postgres_root / "data"
    initdb = bin_dir / "initdb.exe"
    pg_ctl = bin_dir / "pg_ctl.exe"

    if not initdb.exists():
        raise SystemExit(f"Missing {initdb}")
    if not pg_ctl.exists():
        raise SystemExit(f"Missing {pg_ctl}")

    if not (data_dir / "PG_VERSION").exists():
        cmd = [
            str(initdb),
            "-D", str(data_dir),
            "-U", user,
            "--encoding=UTF8",
            "--locale=C",
            "--auth=trust",
        ]
        subprocess.run(cmd, check=True)

    logfile = postgres_root / "postgres.log"
    start_cmd = [
        str(pg_ctl),
        "-D", str(data_dir),
        "-l", str(logfile),
        "-o", f"-p {port}",
        "start",
    ]
    subprocess.run(start_cmd, check=True)
    print(f"started on port {port}")


if __name__ == "__main__":
    main()
