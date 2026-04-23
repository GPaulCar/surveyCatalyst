from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PG_CTL = ROOT / "postgres" / "bin" / "pg_ctl.exe"
PG_DATA = ROOT / "postgres" / "data"
API_SCRIPT = ROOT / "scripts" / "run_api.py"

RUNTIME_DIR = ROOT / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

LOG_DIR = RUNTIME_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

DB_PID_FILE = RUNTIME_DIR / "db.pid"
API_PID_FILE = RUNTIME_DIR / "api.pid"

DB_STDOUT_LOG = LOG_DIR / "postgres.out.log"
DB_STDERR_LOG = LOG_DIR / "postgres.err.log"
API_STDOUT_LOG = LOG_DIR / "api.out.log"
API_STDERR_LOG = LOG_DIR / "api.err.log"

DB_PORT = 55433
API_PORT = 8000


def creation_flags() -> int:
    flags = 0
    flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return flags


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def wait_for_port(port: int, timeout_seconds: float = 30.0) -> bool:
    started = time.time()
    while time.time() - started < timeout_seconds:
        if port_open(port):
            return True
        time.sleep(0.5)
    return False


def read_pid(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def write_pid(path: Path, pid: int) -> None:
    path.write_text(str(pid), encoding="utf-8")


def delete_pid(path: Path) -> None:
    path.unlink(missing_ok=True)


def remove_postgres_lock() -> None:
    for name in ("postmaster.pid", "postmaster.opts"):
        path = PG_DATA / name
        if path.exists():
            try:
                path.unlink()
                print(f"[OK] removed {path.name}")
            except Exception as exc:
                print(f"[WARN] could not remove {path.name}: {exc}")


def find_listener_pid(port: int) -> int | None:
    result = subprocess.run(
        ["netstat", "-ano"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if f":{port}" in line and "LISTENING" in line:
            parts = line.split()
            try:
                return int(parts[-1])
            except Exception:
                return None
    return None


def kill_pid(pid: int) -> None:
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def db_status() -> bool:
    return port_open(DB_PORT)


def api_status() -> bool:
    return port_open(API_PORT)


def start_db() -> None:
    if db_status():
        print("[DB] already running")
        return

    remove_postgres_lock()
    print("[INFO] starting database")

    with DB_STDOUT_LOG.open("a", encoding="utf-8") as out, DB_STDERR_LOG.open("a", encoding="utf-8") as err:
        proc = subprocess.Popen(
            [str(PG_CTL), "-D", str(PG_DATA), "-o", f"-p {DB_PORT}", "start"],
            cwd=ROOT,
            stdout=out,
            stderr=err,
            creationflags=creation_flags(),
        )
    write_pid(DB_PID_FILE, proc.pid)

    if not wait_for_port(DB_PORT, 30):
        raise RuntimeError("database did not become ready")

    print("[DB] started")


def stop_db() -> None:
    print("[INFO] stopping database")

    subprocess.Popen(
        [str(PG_CTL), "-D", str(PG_DATA), "stop", "-m", "immediate"],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags(),
    )

    deadline = time.time() + 15
    while time.time() < deadline:
        if not db_status():
            break
        time.sleep(0.5)

    if db_status():
        listener_pid = find_listener_pid(DB_PORT)
        if listener_pid:
            kill_pid(listener_pid)

    delete_pid(DB_PID_FILE)
    remove_postgres_lock()


def start_api() -> None:
    if api_status():
        print("[API] already running")
        return

    print("[INFO] starting api")

    env = os.environ.copy()
    src_path = str(ROOT / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src_path if not existing else src_path + os.pathsep + existing

    pythonw = Path(sys.executable).with_name("pythonw.exe")
    python_exe = str(pythonw if pythonw.exists() else Path(sys.executable))

    with API_STDOUT_LOG.open("a", encoding="utf-8") as out, API_STDERR_LOG.open("a", encoding="utf-8") as err:
        proc = subprocess.Popen(
            [python_exe, str(API_SCRIPT)],
            cwd=ROOT,
            env=env,
            stdout=out,
            stderr=err,
            creationflags=creation_flags(),
        )
    write_pid(API_PID_FILE, proc.pid)

    if not wait_for_port(API_PORT, 30):
        raise RuntimeError("api did not become ready")

    print("[API] started")


def stop_api() -> None:
    print("[INFO] stopping api")

    pid = read_pid(API_PID_FILE)
    if pid:
        kill_pid(pid)

    listener_pid = find_listener_pid(API_PORT)
    if listener_pid:
        kill_pid(listener_pid)

    deadline = time.time() + 10
    while time.time() < deadline:
        if not api_status():
            break
        time.sleep(0.5)

    delete_pid(API_PID_FILE)


def status() -> None:
    print(f"[DB] {'ON' if db_status() else 'OFF'}")
    print(f"[API] {'ON' if api_status() else 'OFF'}")


def health() -> None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{API_PORT}/health", timeout=3) as resp:
            print(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        print(f"[HEALTH] failed: {exc}")
        raise SystemExit(1)


def start_all() -> None:
    start_db()
    start_api()
    status()


def stop_all() -> None:
    stop_api()
    stop_db()
    status()


def restart_all() -> None:
    stop_all()
    time.sleep(2.0)
    start_all()


def cleanup() -> None:
    for path in [
        ROOT / "start_surveyCatalyst.bat",
        ROOT / "stop_surveyCatalyst.bat",
        ROOT / "start_surveyCatalyst.ps1",
    ]:
        if path.exists():
            path.unlink()
            print(f"[OK] removed {path}")
    print("[DONE] cleanup complete")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python scripts/system_control.py start|stop|restart|status|health|cleanup")
        return 1

    command = argv[1].strip().lower()

    if command == "start":
        start_all()
    elif command == "stop":
        stop_all()
    elif command == "restart":
        restart_all()
    elif command == "status":
        status()
    elif command == "health":
        health()
    elif command == "cleanup":
        cleanup()
    else:
        print("Usage: python scripts/system_control.py start|stop|restart|status|health|cleanup")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))