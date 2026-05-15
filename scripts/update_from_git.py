from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VENV_PY = ROOT / ".surveyCatalyst_venv" / "Scripts" / "python.exe"


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("[RUN] " + " ".join(cmd), flush=True)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.stdout.strip():
        print(proc.stdout.strip(), flush=True)
    if proc.stderr.strip():
        print(proc.stderr.strip(), flush=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}")
    return proc


def git_exe() -> str:
    bundled = ROOT / "tools" / "git" / "cmd" / "git.exe"
    if bundled.exists():
        return str(bundled)
    return "git"


def assert_repo() -> None:
    if not (ROOT / ".git").exists():
        raise RuntimeError(f"Not a git repository: {ROOT}")


def ensure_clean(force_hard: bool, git: str) -> None:
    status = run([git, "status", "--porcelain"], cwd=ROOT)
    dirty = bool(status.stdout.strip())
    if not dirty:
        return
    if not force_hard:
        raise RuntimeError(
            "Working tree has local changes. Commit/stash them first, or re-run with --force-hard."
        )
    run([git, "reset", "--hard", "HEAD"], cwd=ROOT)
    run([git, "clean", "-fd"], cwd=ROOT)


def parse_version(tag: str) -> tuple[int, ...]:
    raw = tag.strip()
    raw = raw[1:] if raw.lower().startswith("v") else raw
    nums = re.findall(r"\d+", raw)
    if not nums:
        return tuple()
    return tuple(int(n) for n in nums)


def list_tags(git: str) -> list[str]:
    run([git, "fetch", "--tags", "origin"], cwd=ROOT)
    proc = run([git, "tag"], cwd=ROOT)
    tags = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return tags


def pick_latest_tag(tags: list[str]) -> str:
    if not tags:
        raise RuntimeError("No tags found in repository.")
    with_versions = [(parse_version(tag), tag) for tag in tags]
    versioned = [item for item in with_versions if item[0]]
    if versioned:
        versioned.sort(key=lambda x: x[0])
        return versioned[-1][1]
    tags.sort()
    return tags[-1]


def current_ref(git: str) -> str:
    return run([git, "rev-parse", "--short", "HEAD"], cwd=ROOT).stdout.strip()


def ensure_python() -> Path:
    if VENV_PY.exists():
        return VENV_PY
    fallback = Path(sys.executable)
    if not fallback.exists():
        raise RuntimeError("Python not available for update handoff.")
    return fallback


def run_python_steps(py: Path) -> None:
    run([str(py), str(ROOT / "scripts" / "bootstrap_python_env.py")], cwd=ROOT)
    run([str(py), str(ROOT / "scripts" / "run_migrations.py")], cwd=ROOT)


def restart_services(py: Path) -> None:
    run([str(py), str(ROOT / "scripts" / "system_control.py"), "restart"], cwd=ROOT)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update deployed surveyCatalyst instance from git tags.")
    parser.add_argument("--tag", default="", help="Specific tag to deploy. If omitted, latest tag is used.")
    parser.add_argument("--check-only", action="store_true", help="Check available update and exit.")
    parser.add_argument("--force-hard", action="store_true", help="Discard local changes before update.")
    parser.add_argument("--no-restart", action="store_true", help="Skip service restart after update.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    assert_repo()
    git = git_exe()
    tags = list_tags(git)
    target = args.tag.strip() or pick_latest_tag(tags)
    current = current_ref(git)
    target_commit = run([git, "rev-list", "-n", "1", target], cwd=ROOT).stdout.strip()
    print(f"[INFO] current={current} target_tag={target} target_commit={target_commit}", flush=True)
    if args.check_only:
        up_to_date = current == target_commit[: len(current)] or run(
            [git, "rev-parse", "HEAD"], cwd=ROOT
        ).stdout.strip() == target_commit
        print("[INFO] update_available=" + ("no" if up_to_date else "yes"), flush=True)
        return 0

    ensure_clean(args.force_hard, git)
    run([git, "checkout", "--detach", target], cwd=ROOT)
    run([git, "reset", "--hard", target], cwd=ROOT)

    py = ensure_python()
    run_python_steps(py)
    if not args.no_restart:
        restart_services(py)

    print("[DONE] update complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
