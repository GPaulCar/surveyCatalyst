from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "app_config.json"

PG_CTL = ROOT / "postgres" / "bin" / "pg_ctl.exe"
PG_SERVER = ROOT / "postgres" / "bin" / "postgres.exe"
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
DB_READY_TIMEOUT = 90.0
DB_READY_POLL = 1.0


def creation_flags() -> int:
    flags = 0
    flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    return flags


def detached_creation_flags() -> int:
    flags = creation_flags()
    flags |= getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0)
    return flags


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def wait_for_port(port: int, timeout_seconds: float = 60.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if port_open(port):
            return True
        time.sleep(0.5)
    return port_open(port)


def wait_for_port_or_exit(proc: subprocess.Popen | None, port: int, timeout_seconds: float = 60.0) -> tuple[bool, str | None]:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            return False, "[ERROR] database process exited early with code " + str(proc.returncode)
        if port_open(port):
            return True, None
        time.sleep(0.5)
    if port_open(port):
        return True, None
    if proc is not None and proc.poll() is not None:
        return False, "[ERROR] database process exited early with code " + str(proc.returncode)
    return False, None


def db_dsn() -> str:
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    local = data["db"]["local"]
    parts = [
        f"host=127.0.0.1",
        f"port={local['port']}",
        f"dbname={local['database']}",
        f"user={local['user']}",
    ]
    return " ".join(parts)


def probe_db_ready(connect_timeout: int = 2) -> bool:
    try:
        probe_code = (
            "import sys\n"
            "import psycopg\n"
            f"conn = psycopg.connect({db_dsn()!r}, connect_timeout={connect_timeout})\n"
            "with conn.cursor() as cur:\n"
            "    cur.execute('SELECT 1')\n"
            "    row = cur.fetchone()\n"
            "conn.close()\n"
            "sys.exit(0 if row and row[0] == 1 else 1)\n"
        )
        result = subprocess.run(
            [str(venv_python()), "-c", probe_code],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags(),
        )
        return result.returncode == 0
    except Exception:
        return False


def wait_for_db_ready(timeout_seconds: float = DB_READY_TIMEOUT, poll_seconds: float = DB_READY_POLL) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if probe_db_ready():
            return True
        time.sleep(poll_seconds)
    return probe_db_ready()


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


def tail_file(path: Path, lines: int = 80) -> str:
    if not path.exists():
        return "[missing] " + str(path)
    try:
        data = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(data[-lines:]) if data else "[empty]"
    except Exception as exc:
        return "[unreadable] " + str(path) + ": " + str(exc)


def print_api_logs() -> None:
    print("")
    print("[API STDERR - tail]")
    print(tail_file(API_STDERR_LOG))
    print("")
    print("[API STDOUT - tail]")
    print(tail_file(API_STDOUT_LOG))
    print("")


def print_db_logs() -> None:
    print("")
    print("[POSTGRES STDERR - tail]")
    print(tail_file(DB_STDERR_LOG))
    print("")
    print("[POSTGRES STDOUT - tail]")
    print(tail_file(DB_STDOUT_LOG))
    print("")


def remove_postgres_lock() -> None:
    for name in ("postmaster.pid", "postmaster.opts"):
        path = PG_DATA / name
        if path.exists():
            try:
                path.unlink()
                print("[OK] removed " + path.name)
            except Exception as exc:
                print("[WARN] could not remove " + path.name + ": " + str(exc))


def find_listener_pid(port: int) -> int | None:
    result = subprocess.run(
        ["netstat", "-ano"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    for line in (result.stdout or "").splitlines():
        line = line.strip()
        if ":" + str(port) in line and "LISTENING" in line:
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
    return probe_db_ready()


def api_status() -> bool:
    return port_open(API_PORT)


def venv_python() -> Path:
    candidate = ROOT / ".surveyCatalyst_venv" / "Scripts" / "python.exe"
    if candidate.exists():
        return candidate
    return Path(sys.executable)


def api_health_ready() -> bool:
    try:
        url = "http://127.0.0.1:" + str(API_PORT) + "/health"
        request = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
        with urllib.request.urlopen(request, timeout=2) as response:
            return 200 <= int(getattr(response, "status", 0)) < 500
    except Exception:
        return False


def wait_for_api(proc: subprocess.Popen | None, timeout_seconds: float = 75.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            print("[ERROR] api process exited early with code " + str(proc.returncode))
            return False
        if api_health_ready():
            return True

        time.sleep(0.5)

    return api_health_ready()


def start_db() -> None:
    if db_status():
        print("[DB] already running")
        return

    if not PG_SERVER.exists():
        raise RuntimeError("postgres not found: " + str(PG_SERVER))
    if not PG_DATA.exists():
        raise RuntimeError("Postgres data directory not found: " + str(PG_DATA))

    remove_postgres_lock()
    print("[INFO] starting database")

    proc = subprocess.Popen(
        [
            str(PG_SERVER),
            "-D",
            str(PG_DATA),
            "-p",
            str(DB_PORT),
        ],
        cwd=ROOT,
        stdout=DB_STDOUT_LOG.open("a", encoding="utf-8"),
        stderr=DB_STDERR_LOG.open("a", encoding="utf-8"),
        stdin=subprocess.DEVNULL,
        creationflags=detached_creation_flags(),
    )

    write_pid(DB_PID_FILE, proc.pid)

    if not wait_for_db_ready(90):
        print_db_logs()
        raise RuntimeError("database did not become ready")

    print("[DB] started")


def stop_db() -> None:
    print("[INFO] stopping database")

    pid = read_pid(DB_PID_FILE)
    if pid:
        kill_pid(pid)

    listener_pid = find_listener_pid(DB_PORT)
    if listener_pid:
        kill_pid(listener_pid)

    deadline = time.time() + 15
    while time.time() < deadline:
        if not db_status():
            break
        time.sleep(0.5)

    delete_pid(DB_PID_FILE)
    remove_postgres_lock()


def start_api() -> None:
    if api_status():
        print("[API] already running")
        return

    if not API_SCRIPT.exists():
        raise RuntimeError("API script not found: " + str(API_SCRIPT))

    stale_listener = find_listener_pid(API_PORT)
    if stale_listener:
        print("[WARN] removing stale API listener on port " + str(API_PORT) + ": pid " + str(stale_listener))
        kill_pid(stale_listener)
        time.sleep(1.0)

    print("[INFO] starting api")

    env = os.environ.copy()
    src_path = str(ROOT / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src_path if not existing else src_path + os.pathsep + existing
    env["SURVEYCATALYST_ROOT"] = str(ROOT)
    env["PYTHONUNBUFFERED"] = "1"

    with API_STDOUT_LOG.open("a", encoding="utf-8") as out, API_STDERR_LOG.open("a", encoding="utf-8") as err:
        proc = subprocess.Popen(
            [str(venv_python()), str(API_SCRIPT)],
            cwd=ROOT,
            env=env,
            stdout=out,
            stderr=err,
            stdin=subprocess.DEVNULL,
            creationflags=detached_creation_flags(),
        )

    write_pid(API_PID_FILE, proc.pid)

    if not wait_for_api(proc, 75):
        print_api_logs()
        raise RuntimeError("api did not become ready; see runtime/logs/api.err.log")

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
    print("[DB] " + ("ON" if db_status() else "OFF"))
    print("[API] " + ("ON" if api_status() else "OFF"))


def health() -> None:
    try:
        url = "http://127.0.0.1:" + str(API_PORT) + "/health"
        with urllib.request.urlopen(url, timeout=3) as response:
            print(response.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        print("[HEALTH] failed: " + str(exc))
        print_api_logs()
        raise SystemExit(1)


def logs() -> None:
    print_db_logs()
    print_api_logs()


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
            print("[OK] removed " + str(path))
    print("[DONE] cleanup complete")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python scripts/system_control.py start|stop|restart|status|health|logs|cleanup")
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
    elif command == "logs":
        logs()
    elif command == "cleanup":
        cleanup()
    else:
        print("Usage: python scripts/system_control.py start|stop|restart|status|health|logs|cleanup")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
