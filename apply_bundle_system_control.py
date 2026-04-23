from __future__ import annotations

import base64
from pathlib import Path

system_control = r'''from __future__ import annotations

import os
import signal
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
API_PID_FILE = RUNTIME_DIR / "api.pid"
API_PORT = 8000
DB_PORT = 55433

def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)

def print_result(label: str, result: subprocess.CompletedProcess) -> None:
    text = ((result.stdout or "") + (result.stderr or "")).strip()
    if text:
        print(f"[{label}] {text}")

def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0

def wait_for_port(port: int, timeout_seconds: float = 20.0) -> bool:
    start = time.time()
    while time.time() - start < timeout_seconds:
        if port_open(port):
            return True
        time.sleep(0.5)
    return False

def remove_postgres_lock() -> None:
    for name in ("postmaster.pid", "postmaster.opts"):
        path = PG_DATA / name
        if path.exists():
            try:
                path.unlink()
                print(f"[OK] removed {path}")
            except Exception as exc:
                print(f"[WARN] could not remove {path}: {exc}")

def db_status() -> bool:
    result = run([str(PG_CTL), "-D", str(PG_DATA), "status"])
    return result.returncode == 0

def api_status() -> bool:
    return port_open(API_PORT)

def start_db() -> None:
    if db_status():
        print("[DB] already running")
        return
    result = run([str(PG_CTL), "-D", str(PG_DATA), "-o", f"-p {DB_PORT}", "start"])
    print_result("DB", result)
    if not wait_for_port(DB_PORT, 20):
        raise RuntimeError("database did not become ready")

def stop_db() -> None:
    if not db_status():
        print("[DB] already stopped")
        return
    result = run([str(PG_CTL), "-D", str(PG_DATA), "stop", "-m", "immediate"])
    print_result("DB", result)
    time.sleep(1.0)

def start_api() -> None:
    if api_status():
        print("[API] already running")
        return
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src_path if not existing else src_path + os.pathsep + existing
    proc = subprocess.Popen(
        [sys.executable, str(API_SCRIPT)],
        cwd=ROOT,
        env=env,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    API_PID_FILE.write_text(str(proc.pid), encoding="utf-8")
    if not wait_for_port(API_PORT, 20):
        raise RuntimeError("api did not become ready")
    print(f"[API] started pid={proc.pid}")

def stop_api() -> None:
    if API_PID_FILE.exists():
        try:
            pid = int(API_PID_FILE.read_text(encoding="utf-8").strip())
            os.kill(pid, signal.SIGTERM)
            print(f"[API] stop issued pid={pid}")
        except Exception as exc:
            print(f"[WARN] api stop via pid file failed: {exc}")
        finally:
            API_PID_FILE.unlink(missing_ok=True)
    if port_open(API_PORT):
        subprocess.run(
            ["taskkill", "/F", "/PID", str(find_listener_pid(API_PORT))],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
    time.sleep(1.0)

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
            if parts:
                try:
                    return int(parts[-1])
                except ValueError:
                    return None
    return None

def status() -> None:
    print(f"[DB] {'ON' if db_status() else 'OFF'}")
    print(f"[API] {'ON' if api_status() else 'OFF'}")

def health() -> None:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{API_PORT}/health", timeout=3) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            print(body)
    except Exception as exc:
        print(f"[HEALTH] failed: {exc}")
        raise SystemExit(1)

def start_all() -> None:
    remove_postgres_lock()
    start_db()
    start_api()
    status()

def stop_all() -> None:
    stop_api()
    stop_db()
    remove_postgres_lock()
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
'''

payload = base64.b64encode(system_control.encode("utf-8")).decode("ascii")

def main() -> None:
    root = Path.cwd()
    target = root / "scripts" / "system_control.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(base64.b64decode(payload))
    print(f"[OK] wrote {target}")
    print("[DONE] bundle system control installer applied")
    print("Run:")
    print("  python scripts/system_control.py start")
    print("  python scripts/system_control.py status")
    print("  python scripts/system_control.py health")
    print("  python scripts/system_control.py restart")
    print("  python scripts/system_control.py stop")
    print("  python scripts/system_control.py cleanup")

if __name__ == "__main__":
    main()