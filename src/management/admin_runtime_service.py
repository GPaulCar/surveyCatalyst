from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import system_control  # noqa: E402


class AdminRuntimeService:
    LOG_DIR = ROOT / "runtime" / "logs"

    def __init__(self) -> None:
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)

    def system_status(self) -> dict[str, Any]:
        db_running = self._safe_bool(system_control.db_status)
        api_running = self._safe_bool(system_control.api_status)
        return {
            "ok": True,
            "services": {
                "api": {
                    "name": "API",
                    "running": api_running,
                    "state": "ON" if api_running else "OFF",
                    "port": system_control.API_PORT,
                    "pid": system_control.read_pid(system_control.API_PID_FILE),
                },
                "database": {
                    "name": "Database",
                    "running": db_running,
                    "state": "ON" if db_running else "OFF",
                    "port": system_control.DB_PORT,
                    "pid": system_control.read_pid(system_control.DB_PID_FILE),
                },
            },
        }

    def run_action(self, target: str, action: str) -> dict[str, Any]:
        normalized_target = self._normalize_target(target)
        normalized_action = action.strip().lower()
        if normalized_action not in {"start", "stop", "restart"}:
            raise ValueError("Unsupported admin action")

        if self._requires_detached_helper(normalized_target, normalized_action):
            self._schedule_action(normalized_target, normalized_action)
            return {
                "ok": True,
                "scheduled": True,
                "target": normalized_target,
                "action": normalized_action,
                "detail": f"Scheduled {normalized_target} {normalized_action}",
                "status": self.system_status()["services"],
            }

        detail = self._run_sync(normalized_target, normalized_action)
        return {
            "ok": True,
            "scheduled": False,
            "target": normalized_target,
            "action": normalized_action,
            "detail": detail or f"{normalized_target} {normalized_action} complete",
            "status": self.system_status()["services"],
        }

    def list_logs(self) -> dict[str, Any]:
        logs = []
        for path in sorted(self.LOG_DIR.glob("*.log"), key=lambda p: p.name.lower()):
            stat = path.stat()
            logs.append(
                {
                    "name": path.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
                }
            )
        return {"ok": True, "logs": logs}

    def read_log(
        self,
        name: str,
        mode: str = "tail",
        lines: int = 200,
        query: str = "",
        case_sensitive: bool = False,
    ) -> dict[str, Any]:
        path = self._resolve_log(name)
        mode = mode.strip().lower()
        if mode not in {"tail", "search"}:
            raise ValueError("Unsupported log mode")

        line_limit = max(1, min(int(lines or 200), 1000))
        query = query or ""
        numbered = list(enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1))

        if mode == "tail":
            selected = numbered[-line_limit:]
            if query:
                selected = self._filter_lines(selected, query, case_sensitive)
        else:
            selected = self._filter_lines(numbered, query, case_sensitive) if query else numbered
            selected = selected[-line_limit:]

        entries = [{"line": number, "text": text} for number, text in selected]
        return {
            "ok": True,
            "name": path.name,
            "mode": mode,
            "query": query,
            "line_limit": line_limit,
            "total_lines": len(numbered),
            "returned": len(entries),
            "entries": entries,
            "lines": [f"{entry['line']}: {entry['text']}" for entry in entries],
        }

    def _normalize_target(self, target: str) -> str:
        value = target.strip().lower()
        aliases = {"db": "database", "postgres": "database", "web": "api", "web_server": "api"}
        value = aliases.get(value, value)
        if value not in {"api", "database", "all"}:
            raise ValueError("Unsupported admin target")
        return value

    def _requires_detached_helper(self, target: str, action: str) -> bool:
        return action in {"stop", "restart"} and target in {"api", "all"}

    def _run_sync(self, target: str, action: str) -> str:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            if target == "database":
                self._database_action(action)
            elif target == "api":
                self._api_action(action)
            elif target == "all":
                self._all_action(action)
        return buffer.getvalue().strip()

    def _database_action(self, action: str) -> None:
        if action == "start":
            system_control.start_db()
        elif action == "stop":
            system_control.stop_db()
        elif action == "restart":
            system_control.stop_db()
            system_control.start_db()

    def _api_action(self, action: str) -> None:
        if action == "start":
            system_control.start_api()
        elif action == "stop":
            system_control.stop_api()
        elif action == "restart":
            system_control.stop_api()
            system_control.start_api()

    def _all_action(self, action: str) -> None:
        if action == "start":
            system_control.start_all()
        elif action == "stop":
            system_control.stop_all()
        elif action == "restart":
            system_control.restart_all()

    def _schedule_action(self, target: str, action: str) -> None:
        helper = ROOT / "scripts" / "admin_action_helper.py"
        if not helper.exists():
            raise RuntimeError("Admin action helper is missing")

        env = os.environ.copy()
        src_path = str(ROOT / "src")
        env["PYTHONPATH"] = src_path + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        env["SURVEYCATALYST_ROOT"] = str(ROOT)
        env["PYTHONUNBUFFERED"] = "1"

        log_path = self.LOG_DIR / "admin_control.log"
        with log_path.open("a", encoding="utf-8") as log:
            subprocess.Popen(
                [str(system_control.venv_python()), str(helper), target, action, "0.8"],
                cwd=ROOT,
                env=env,
                stdout=log,
                stderr=log,
                stdin=subprocess.DEVNULL,
                creationflags=system_control.detached_creation_flags(),
            )

    def _resolve_log(self, name: str) -> Path:
        if not name:
            raise ValueError("Log name is required")
        root = self.LOG_DIR.resolve()
        path = (root / name).resolve()
        if path.parent != root or path.suffix.lower() != ".log":
            raise ValueError("Unsupported log name")
        if not path.exists():
            raise FileNotFoundError(name)
        return path

    @staticmethod
    def _filter_lines(lines: list[tuple[int, str]], query: str, case_sensitive: bool) -> list[tuple[int, str]]:
        if case_sensitive:
            return [(number, text) for number, text in lines if query in text]
        needle = query.lower()
        return [(number, text) for number, text in lines if needle in text.lower()]

    @staticmethod
    def _safe_bool(func) -> bool:
        try:
            return bool(func())
        except Exception:
            return False
