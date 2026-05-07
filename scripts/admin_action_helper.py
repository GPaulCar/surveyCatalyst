from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import system_control


def kill_pid_without_tree(pid: int) -> None:
    if pid <= 0 or pid == os.getpid():
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        os.kill(pid, 15)


def stop_api_without_killing_helper() -> None:
    print("[INFO] stopping api")
    pid = system_control.read_pid(system_control.API_PID_FILE)
    if pid:
        kill_pid_without_tree(pid)

    listener_pid = system_control.find_listener_pid(system_control.API_PORT)
    if listener_pid:
        kill_pid_without_tree(listener_pid)

    deadline = time.time() + 10
    while time.time() < deadline:
        if not system_control.api_status():
            break
        time.sleep(0.5)

    system_control.delete_pid(system_control.API_PID_FILE)
    print("[API] stopped")


def run_action(target: str, action: str) -> None:
    if target == "api":
        if action == "stop":
            stop_api_without_killing_helper()
        elif action == "restart":
            stop_api_without_killing_helper()
            time.sleep(1.0)
            system_control.start_api()
        elif action == "start":
            system_control.start_api()
    elif target == "database":
        if action == "stop":
            system_control.stop_db()
        elif action == "restart":
            system_control.stop_db()
            time.sleep(1.0)
            system_control.start_db()
        elif action == "start":
            system_control.start_db()
    elif target == "all":
        if action == "stop":
            stop_api_without_killing_helper()
            system_control.stop_db()
        elif action == "restart":
            stop_api_without_killing_helper()
            system_control.stop_db()
            time.sleep(1.0)
            system_control.start_db()
            system_control.start_api()
        elif action == "start":
            system_control.start_all()
    else:
        raise ValueError("unsupported target")


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: admin_action_helper.py api|database|all start|stop|restart [delay_seconds]")
        return 1

    target = argv[1].strip().lower()
    action = argv[2].strip().lower()
    delay = float(argv[3]) if len(argv) > 3 else 0.8

    print("")
    print(f"[{datetime.now().isoformat(timespec='seconds')}] scheduled {target} {action}")
    time.sleep(max(0.0, delay))
    run_action(target, action)
    print(f"[{datetime.now().isoformat(timespec='seconds')}] complete {target} {action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
