from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    print("[RUN]", " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {proc.returncode}: {' '.join(cmd)}")


def _prompt(question: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{question}{suffix}: ").strip()
    return value or (default or "")


def _check_writable(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    probe = path / ".write_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Install root is not writable: {path} ({exc})") from exc


def _ensure_git() -> str:
    git = shutil.which("git")
    if not git:
        raise RuntimeError(
            "Git is required but not found in PATH. Install Git first, then re-run this bootstrap."
        )
    return git


def _clone_or_update_repo(git: str, repo_url: str, repo_dir: Path, ref: str) -> None:
    if (repo_dir / ".git").exists():
        _run([git, "-C", str(repo_dir), "remote", "set-url", "origin", repo_url])
        _run([git, "-C", str(repo_dir), "fetch", "--tags", "origin"])
    else:
        if repo_dir.exists():
            shutil.rmtree(repo_dir, ignore_errors=True)
        _run([git, "clone", repo_url, str(repo_dir)])
    _run([git, "-C", str(repo_dir), "checkout", "--detach", ref])
    _run([git, "-C", str(repo_dir), "reset", "--hard", ref])


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _bootstrap_python(repo_dir: Path) -> Path:
    venv_dir = repo_dir / ".surveyCatalyst_venv"
    python_exe = Path(sys.executable)
    _run([str(python_exe), "-m", "venv", str(venv_dir)], cwd=repo_dir)
    vpy = _venv_python(venv_dir)
    _run([str(vpy), "-m", "pip", "install", "--upgrade", "pip"], cwd=repo_dir)
    if (repo_dir / "scripts" / "bootstrap_python_env.py").exists():
        _run([str(vpy), str(repo_dir / "scripts" / "bootstrap_python_env.py")], cwd=repo_dir)
    else:
        req = repo_dir / "requirements.txt"
        if req.exists():
            _run([str(vpy), "-m", "pip", "install", "-r", str(req)], cwd=repo_dir)
    return vpy


def _handoff(repo_dir: Path, install_root: Path, repo_url: str, ref: str, vpy: Path, auto_handoff: bool) -> None:
    if os.name == "nt":
        next_cmd = [
            str(vpy),
            str(repo_dir / "scripts" / "bootstrap_deployment_site.py"),
            "--install-root",
            str(install_root),
            "--repo-url",
            repo_url,
            "--tag",
            ref,
        ]
        if auto_handoff:
            _run(next_cmd, cwd=repo_dir)
            return
        print("Next (Windows full runtime+services):", flush=True)
        print(f'  "{" ".join(next_cmd)}"', flush=True)
        return

    print("Next (Linux/macOS):", flush=True)
    print("  1) install PostgreSQL/PostGIS for this host", flush=True)
    print(f'  2) "{vpy}" "{repo_dir / "scripts" / "run_migrations.py"}"', flush=True)
    print(f'  3) "{vpy}" "{repo_dir / "scripts" / "run_api.py"}"', flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Portable bootstrap entrypoint: asks install location, verifies permissions, clones code, then hands off to Python workflows."
    )
    parser.add_argument("--install-root", default="", help="Installation root folder.")
    parser.add_argument("--repo-url", default="", help="Git repository URL.")
    parser.add_argument("--ref", default="main", help="Git tag/branch/commit to deploy.")
    parser.add_argument("--repo-name", default="surveyCatalyst", help="Folder name under install root.")
    parser.add_argument(
        "--auto-handoff",
        action="store_true",
        help="Immediately run the Python deployment handoff after bootstrap.",
    )
    args = parser.parse_args()

    print("=== surveyCatalyst portable bootstrap ===", flush=True)
    print(f"platform: {platform.system()} {platform.release()}", flush=True)
    print(f"python: {sys.version.split()[0]} ({sys.executable})", flush=True)

    default_root = str(Path.home() / "surveyCatalyst")
    install_root = Path(args.install_root or _prompt("Install root", default_root)).expanduser().resolve()
    _check_writable(install_root)

    repo_url = args.repo_url or _prompt("Repository URL", "https://github.com/your-org/surveyCatalyst.git")
    repo_dir = install_root / args.repo_name
    git = _ensure_git()

    _clone_or_update_repo(git, repo_url, repo_dir, args.ref)
    vpy = _bootstrap_python(repo_dir)

    print("", flush=True)
    print("=== handoff ===", flush=True)
    print(f"repo: {repo_dir}", flush=True)
    print(f"venv python: {vpy}", flush=True)
    _handoff(repo_dir, install_root, repo_url, args.ref, vpy, args.auto_handoff)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
