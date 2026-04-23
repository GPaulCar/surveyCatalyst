from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PG_CTL = ROOT / "postgres" / "bin" / "pg_ctl.exe"
PG_DATA = ROOT / "postgres" / "data"
API_SCRIPT = ROOT / "scripts" / "run_api.py"
PID_FILE = ROOT / "runtime" / "api.pid"
PORT = 8000


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def kill_processes():
    print("[INFO] killing python processes")
    run(["taskkill", "/IM", "python.exe", "/F"])

    print("[INFO] killing postgres processes")
    run(["taskkill", "/IM", "postgres.exe", "/F"])


def remove_lock():
    pid_file = PG_DATA / "postmaster.pid"
    if pid_file.exists():
        pid_file.unlink()
        print("[OK] removed postmaster.pid")


def port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_db():
    print("[INFO] starting database")
    run([str(PG_CTL), "-D", str(PG_DATA), "-o", "-p 55433", "start"])


def stop_db():
    print("[INFO] stopping database")
    run([str(PG_CTL), "-D", str(PG_DATA), "stop", "-m", "immediate"])


def start_api():
    print("[INFO] starting api")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")

    proc = subprocess.Popen(
        [sys.executable, str(API_SCRIPT)],
        cwd=ROOT,
        env=env,
    )

    PID_FILE.parent.mkdir(exist_ok=True)
    PID_FILE.write_text(str(proc.pid))


def stop_api():
    if not PID_FILE.exists():
        return
    try:
        pid = int(PID_FILE.read_text())
        os.kill(pid, signal.SIGTERM)
    except Exception:
        pass
    PID_FILE.unlink(missing_ok=True)


def wait_for_api():
    for _ in range(20):
        if port_open(PORT):
            print("[OK] API running")
            return True
        time.sleep(0.5)
    print("[WARN] API not responding")
    return False


def status():
    db = run([str(PG_CTL), "-D", str(PG_DATA), "status"])
    print("[DB]", "ON" if db.returncode == 0 else "OFF")

    print("[API]", "ON" if port_open(PORT) else "OFF")


def start():
    remove_lock()
    start_db()
    time.sleep(2)
    start_api()
    wait_for_api()


def stop():
    stop_api()
    stop_db()
    kill_processes()
    remove_lock()


def restart():
    stop()
    time.sleep(2)
    start()


def cleanup():
    print("[INFO] removing old scripts")
    for f in [
        ROOT / "start_surveyCatalyst.bat",
        ROOT / "start_surveyCatalyst.ps1",
        ROOT / "stop_surveyCatalyst.bat",
        ROOT / "stop_surveyCatalyst.ps1",
    ]:
        if f.exists():
            f.unlink()
            print(f"[OK] removed {f}")


def main():
    if len(sys.argv) < 2:
        print("usage: start | stop | restart | status | cleanup")
        return

    cmd = sys.argv[1]

    if cmd == "start":
        start()
    elif cmd == "stop":
        stop()
    elif cmd == "restart":
        restart()
    elif cmd == "status":
        status()
    elif cmd == "cleanup":
        cleanup()
    else:
        print("unknown command")


if __name__ == "__main__":
    main()