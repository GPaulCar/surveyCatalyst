from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = ROOT / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

PG_CTL = ROOT / "postgres" / "bin" / "pg_ctl.exe"
PG_DATA = ROOT / "postgres" / "data"
PYTHON_EXE = ROOT / ".surveyCatalyst_venv" / "Scripts" / "python.exe"
API_SCRIPT = ROOT / "scripts" / "run_api.py"
API_PID_FILE = RUNTIME_DIR / "api.pid"
API_PORT = 8000
DB_PORT = 55433


def _run(cmd: list[str], timeout: float | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)


def _port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def _http_health_ok(url: str, timeout: float = 1.0) -> bool:
    try:
        from urllib.request import urlopen

        with urlopen(url, timeout=timeout) as response:  # nosec B310 - localhost only
            return response.status == 200
    except Exception:
        return False


def _detail_from(result: subprocess.CompletedProcess[str]) -> str:
    detail = (result.stdout or result.stderr or "").strip()
    return detail or f"exit code {result.returncode}"


def db_status() -> dict[str, Any]:
    result = _run([str(PG_CTL), "-D", str(PG_DATA), "status"])
    running = result.returncode == 0
    return {
        "name": "database",
        "running": running,
        "state": "ON" if running else "OFF",
        "detail": _detail_from(result),
        "port": DB_PORT,
    }


def db_start() -> dict[str, Any]:
    result = _run([str(PG_CTL), "-D", str(PG_DATA), "-o", f"-p {DB_PORT}", "start"], timeout=30)
    return {"ok": result.returncode == 0, "detail": _detail_from(result)}


def db_stop() -> dict[str, Any]:
    result = _run([str(PG_CTL), "-D", str(PG_DATA), "stop", "-m", "fast"], timeout=30)
    return {"ok": result.returncode == 0, "detail": _detail_from(result)}


def db_restart() -> dict[str, Any]:
    result = _run([str(PG_CTL), "-D", str(PG_DATA), "-o", f"-p {DB_PORT}", "restart"], timeout=60)
    return {"ok": result.returncode == 0, "detail": _detail_from(result)}


def _read_pid() -> int | None:
    if not API_PID_FILE.exists():
        return None
    try:
        return int(API_PID_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def _write_pid(pid: int) -> None:
    API_PID_FILE.write_text(str(pid), encoding="utf-8")


def _clear_pid() -> None:
    API_PID_FILE.unlink(missing_ok=True)


def _python_exe() -> str:
    return str(PYTHON_EXE if PYTHON_EXE.exists() else Path(sys.executable))


def _start_api_detached() -> int:
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    env["PYTHONPATH"] = src_path + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    proc = subprocess.Popen(
        [_python_exe(), str(API_SCRIPT)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    _write_pid(proc.pid)
    return proc.pid


def api_status() -> dict[str, Any]:
    pid = _read_pid()
    running = _port_open("127.0.0.1", API_PORT) and _http_health_ok(f"http://127.0.0.1:{API_PORT}/health")
    if not running and pid is None:
        state = "OFF"
    else:
        state = "ON" if running else "OFF"
    return {
        "name": "web_server",
        "running": running,
        "state": state,
        "pid": pid,
        "detail": f"127.0.0.1:{API_PORT} healthy" if running else f"127.0.0.1:{API_PORT} not reachable",
        "port": API_PORT,
    }


def api_start() -> dict[str, Any]:
    if api_status()["running"]:
        return {"ok": True, "detail": "API already running"}
    pid = _start_api_detached()
    for _ in range(40):
        time.sleep(0.25)
        if api_status()["running"]:
            return {"ok": True, "detail": f"API started on pid {pid}", "pid": pid}
    return {"ok": False, "detail": f"API start issued for pid {pid}, but health did not become ready in time", "pid": pid}


def _terminate_pid(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True)
    else:
        os.kill(pid, signal.SIGTERM)


def api_stop() -> dict[str, Any]:
    pid = _read_pid()
    if pid is None:
        if not api_status()["running"]:
            return {"ok": True, "detail": "API already stopped"}
        return {"ok": False, "detail": "API running but no pid file is available"}
    try:
        _terminate_pid(pid)
    except Exception as exc:
        return {"ok": False, "detail": str(exc), "pid": pid}
    finally:
        _clear_pid()
    for _ in range(20):
        time.sleep(0.25)
        if not _port_open("127.0.0.1", API_PORT):
            return {"ok": True, "detail": f"Stopped API pid {pid}", "pid": pid}
    return {"ok": True, "detail": f"Stop issued to API pid {pid}", "pid": pid}


def schedule_api_restart(current_pid: int | None = None, delay_seconds: int = 1) -> dict[str, Any]:
    helper = ROOT / "scripts" / "restart_api_helper.py"
    cmd = [_python_exe(), str(helper), str(current_pid or 0), str(delay_seconds)]
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    subprocess.Popen(
        cmd,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    return {"ok": True, "detail": f"Scheduled API restart in {delay_seconds}s"}


def combined_status() -> dict[str, Any]:
    return {"database": db_status(), "web_server": api_status()}
