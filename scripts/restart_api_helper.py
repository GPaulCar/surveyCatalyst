from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: restart_api_helper.py <pid>")

    pid = int(sys.argv[1])
    root = Path(__file__).resolve().parents[1]
    python_exe = root / ".surveyCatalyst_venv" / "Scripts" / "python.exe"
    if not python_exe.exists():
        python_exe = Path(sys.executable)

    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

    time.sleep(1.5)
    subprocess.run(["taskkill", "/PID", str(pid), "/F"], cwd=str(root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)

    creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen(
        [str(python_exe), str(root / "scripts" / "run_api.py")],
        cwd=str(root),
        env=env,
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


if __name__ == "__main__":
    main()
