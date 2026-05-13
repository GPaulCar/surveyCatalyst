from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import requests


DEFAULT_INSTALL_ROOT = Path(r"C:\surveyCatalyst")
DEFAULT_REPO_NAME = "surveyCatalyst"
DEFAULT_PYTHON_VERSION = "3.11.9"
DEFAULT_POSTGRES_URL = "https://sbp.enterprisedb.com/getfile.jsp?fileid=1260146"
DEFAULT_POSTGIS_URL = "https://download.osgeo.org/postgis/windows/pg18/postgis-bundle-pg18-3.6.2x64.zip"
DEFAULT_GIT_PORTABLE_ASSET = "PortableGit"
DEFAULT_DB_PORT = 55433
DEFAULT_API_PORT = 8000
DEFAULT_DB_NAME = "survey_catalyst"
DEFAULT_DB_USER = "sc_user"


def prompt(text: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{text}{suffix}: ").strip()
    return value or (default or "")


def prompt_bool(text: str, default: bool = True) -> bool:
    suffix = " [Y/n]" if default else " [y/N]"
    value = input(f"{text}{suffix}: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "true", "1"}


def log(message: str) -> None:
    print(message, flush=True)


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    log("[RUN] " + " ".join(cmd))
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.stdout.strip():
        log(proc.stdout.strip())
    if proc.stderr.strip():
        log(proc.stderr.strip())
    if check and proc.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {proc.returncode}: {' '.join(cmd)}")
    return proc


def download(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    log(f"[DL] {url}")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    return destination


def extract_zip(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(destination)


def find_dir_with_name(root: Path, target_name: str) -> Path:
    matches = [p for p in root.rglob(target_name) if p.is_dir()]
    if not matches:
        raise RuntimeError(f"Could not find directory '{target_name}' under {root}")
    return matches[0]


def github_latest_portable_git_asset() -> tuple[str, str]:
    api = "https://api.github.com/repos/git-for-windows/git/releases/latest"
    response = requests.get(api, timeout=60)
    response.raise_for_status()
    payload = response.json()
    for asset in payload.get("assets") or []:
        name = asset.get("name") or ""
        url = asset.get("browser_download_url") or ""
        if DEFAULT_GIT_PORTABLE_ASSET.lower() in name.lower() and name.lower().endswith(".exe"):
            return name, url
    raise RuntimeError("Could not locate a portable Git asset in the latest git-for-windows release")


def install_git(install_root: Path, downloads: Path) -> Path:
    git_root = install_root / "tools" / "git"
    git_exe = git_root / "cmd" / "git.exe"
    if git_exe.exists():
        return git_exe

    asset_name, asset_url = github_latest_portable_git_asset()
    archive = download(asset_url, downloads / asset_name)
    extract_dir = downloads / "git_unpack"
    if extract_dir.exists():
        shutil.rmtree(extract_dir, ignore_errors=True)
    extract_dir.mkdir(parents=True, exist_ok=True)
    installer = archive
    cmd = [
        str(installer),
        "/VERYSILENT",
        "/NORESTART",
        f"/DIR={git_root}",
    ]
    run(cmd, cwd=install_root)
    if not git_exe.exists():
        raise RuntimeError(f"Git portable install did not produce {git_exe}")
    return git_exe


def install_python(install_root: Path, downloads: Path, python_version: str) -> Path:
    python_root = install_root / "tools" / "python"
    python_exe = python_root / "python.exe"
    if python_exe.exists():
        return python_exe
    installer_url = f"https://www.python.org/ftp/python/{python_version}/python-{python_version}-amd64.exe"
    installer = download(installer_url, downloads / Path(installer_url).name)
    cmd = [
        str(installer),
        "/quiet",
        "InstallAllUsers=0",
        "PrependPath=0",
        "Include_test=0",
        "Include_pip=1",
        f"TargetDir={python_root}",
    ]
    run(cmd, cwd=install_root)
    if not python_exe.exists():
        raise RuntimeError(f"Python install did not produce {python_exe}")
    return python_exe


def install_postgres(install_root: Path, downloads: Path, postgres_url: str, postgis_url: str) -> Path:
    postgres_root = install_root / "postgres"
    postgres_exe = postgres_root / "bin" / "postgres.exe"

    if not postgres_exe.exists():
        postgres_zip = download(postgres_url, downloads / Path(postgres_url).name)
        unpack_dir = downloads / "postgres_unpack"
        if unpack_dir.exists():
            shutil.rmtree(unpack_dir, ignore_errors=True)
        extract_zip(postgres_zip, unpack_dir)
        bin_dir = find_dir_with_name(unpack_dir, "bin")
        source_root = bin_dir.parent

        postgres_root.mkdir(parents=True, exist_ok=True)
        for item in source_root.iterdir():
            destination = postgres_root / item.name
            if destination.exists():
                if destination.is_dir():
                    shutil.rmtree(destination, ignore_errors=True)
                else:
                    destination.unlink(missing_ok=True)
            shutil.move(str(item), str(destination))

    postgis_zip = download(postgis_url, downloads / Path(postgis_url).name)
    postgis_unpack = downloads / "postgis_unpack"
    if postgis_unpack.exists():
        shutil.rmtree(postgis_unpack, ignore_errors=True)
    extract_zip(postgis_zip, postgis_unpack)
    bundle_root = next((p for p in postgis_unpack.iterdir() if p.is_dir()), None)
    if bundle_root is None:
        raise RuntimeError(f"Could not find extracted PostGIS bundle folder in {postgis_unpack}")
    for name in ("bin", "lib", "share"):
        source_dir = bundle_root / name
        if not source_dir.exists():
            raise RuntimeError(f"Missing {source_dir}")
        destination_dir = postgres_root / name
        destination_dir.mkdir(parents=True, exist_ok=True)
        for item in source_dir.rglob("*"):
            if not item.is_file():
                continue
            rel = item.relative_to(source_dir)
            dest = destination_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)

    (postgres_root / "data").mkdir(parents=True, exist_ok=True)
    return postgres_root


def git_env(git_exe: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["PATH"] = str(git_exe.parent.parent / "cmd") + os.pathsep + env.get("PATH", "")
    return env


def list_remote_tags(git_exe: Path, repo_url: str) -> list[str]:
    result = run([str(git_exe), "ls-remote", "--tags", repo_url], env=git_env(git_exe), check=True)
    tags: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) != 2:
            continue
        ref = parts[1]
        if ref.endswith("^{}"):
            continue
        if ref.startswith("refs/tags/"):
            tags.append(ref.removeprefix("refs/tags/"))
    return sorted(dict.fromkeys(tags))


def choose_tag(tags: list[str]) -> str:
    if not tags:
        raise RuntimeError("No tags were returned by the repository")
    log("")
    log("Available deployment tags:")
    for index, tag in enumerate(tags, start=1):
        log(f"  {index}. {tag}")
    while True:
        choice = prompt("Select a tag by number or name", tags[-1])
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(tags):
                return tags[index - 1]
        if choice in tags:
            return choice
        log("Invalid selection.")


def clone_or_update_repo(git_exe: Path, repo_url: str, repo_dir: Path, tag: str) -> None:
    if repo_dir.exists() and (repo_dir / ".git").exists():
        run([str(git_exe), "-C", str(repo_dir), "remote", "set-url", "origin", repo_url], env=git_env(git_exe))
        run([str(git_exe), "-C", str(repo_dir), "fetch", "--tags", "origin"], env=git_env(git_exe))
    else:
        if repo_dir.exists():
            shutil.rmtree(repo_dir, ignore_errors=True)
        run([str(git_exe), "clone", repo_url, str(repo_dir)], env=git_env(git_exe))
    run([str(git_exe), "-C", str(repo_dir), "checkout", "--detach", tag], env=git_env(git_exe))
    run([str(git_exe), "-C", str(repo_dir), "reset", "--hard", tag], env=git_env(git_exe))


def create_venv(python_exe: Path, repo_dir: Path) -> Path:
    venv_dir = repo_dir / ".surveyCatalyst_venv"
    venv_python = venv_dir / "Scripts" / "python.exe"
    if not venv_python.exists():
        run([str(python_exe), "-m", "venv", str(venv_dir)], cwd=repo_dir)
    return venv_python


def bootstrap_python_deps(venv_python: Path, repo_dir: Path) -> None:
    run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], cwd=repo_dir)
    run([str(venv_python), str(repo_dir / "scripts" / "bootstrap_python_env.py")], cwd=repo_dir)


def write_app_config(repo_dir: Path, postgres_root: Path) -> None:
    config_path = repo_dir / "config" / "app_config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "app": {"name": "surveyCatalyst", "env": "release"},
        "db": {
            "mode": "local",
            "local": {
                "data_dir": str((postgres_root / "data").resolve()),
                "port": DEFAULT_DB_PORT,
                "database": DEFAULT_DB_NAME,
                "user": DEFAULT_DB_USER,
            },
            "external": {
                "host": "",
                "port": 5432,
                "database": "",
                "user": "",
            },
        },
        "paths": {
            "assets": str((repo_dir / "assets_store").resolve()),
            "logs": str((repo_dir / "runtime" / "logs").resolve()),
            "postgres": str(postgres_root.resolve()),
        },
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def init_postgres(postgres_root: Path, db_user: str) -> None:
    initdb = postgres_root / "bin" / "initdb.exe"
    data_dir = postgres_root / "data"
    if not (data_dir / "PG_VERSION").exists():
        run([
            str(initdb),
            "-D", str(data_dir),
            "-U", db_user,
            "--encoding=UTF8",
            "--locale=C",
            "--auth=trust",
        ], cwd=postgres_root)


def pg_isready(postgres_root: Path, port: int) -> bool:
    exe = postgres_root / "bin" / "pg_isready.exe"
    result = subprocess.run([str(exe), "-h", "127.0.0.1", "-p", str(port)], capture_output=True, text=True, check=False)
    return result.returncode == 0


def start_postgres(postgres_root: Path, port: int, repo_dir: Path) -> None:
    if pg_isready(postgres_root, port):
        return
    pg_ctl = postgres_root / "bin" / "pg_ctl.exe"
    log_file = repo_dir / "runtime" / "logs" / "postgres.bootstrap.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    run([
        str(pg_ctl),
        "-D", str(postgres_root / "data"),
        "-l", str(log_file),
        "-o", f"-p {port}",
        "start",
    ], cwd=repo_dir)
    deadline = time.time() + 60
    while time.time() < deadline:
        if pg_isready(postgres_root, port):
            return
        time.sleep(1)
    raise RuntimeError("Timed out waiting for PostgreSQL to start")


def create_database_if_missing(postgres_root: Path, port: int, db_user: str, db_name: str) -> None:
    psql = postgres_root / "bin" / "psql.exe"
    createdb = postgres_root / "bin" / "createdb.exe"
    exists = run([
        str(psql),
        "-h", "127.0.0.1",
        "-p", str(port),
        "-U", db_user,
        "-d", "postgres",
        "-tAc",
        f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'",
    ], check=False)
    if exists.stdout.strip() != "1":
        run([str(createdb), "-h", "127.0.0.1", "-p", str(port), "-U", db_user, db_name])


def enable_postgis(repo_dir: Path) -> None:
    src_path = repo_dir / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    from core.db import build_backend

    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        conn.commit()
    finally:
        conn.close()


def apply_migrations(repo_dir: Path, venv_python: Path) -> None:
    run([str(venv_python), str(repo_dir / "scripts" / "run_migrations.py")], cwd=repo_dir)


def install_api_service(repo_dir: Path, venv_python: Path) -> None:
    service_name = "surveyCatalystApi"
    query = subprocess.run(["sc.exe", "query", service_name], capture_output=True, text=True, check=False)
    if query.returncode == 0:
        return
    binary_path = f'"{venv_python}" "{repo_dir / "scripts" / "run_api.py"}"'
    ps = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        f"New-Service -Name '{service_name}' -BinaryPathName '{binary_path}' -StartupType Automatic",
    ]
    run(ps, cwd=repo_dir, check=False)


def install_postgres_service(postgres_root: Path) -> None:
    service_name = "surveyCatalystPostgres"
    query = subprocess.run(["sc.exe", "query", service_name], capture_output=True, text=True, check=False)
    if query.returncode == 0:
        return
    pg_ctl = postgres_root / "bin" / "pg_ctl.exe"
    data_dir = postgres_root / "data"
    run([
        str(pg_ctl),
        "register",
        "-N",
        service_name,
        "-D",
        str(data_dir),
        "-S",
        "auto",
        "-o",
        f"-p {DEFAULT_DB_PORT}",
    ], cwd=postgres_root, check=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Interactive bootstrap for a release deployment site.")
    parser.add_argument("--install-root", help="Target installation root. If omitted, you will be prompted.")
    parser.add_argument("--repo-url", help="Git repository URL. If omitted, you will be prompted.")
    parser.add_argument("--repo-name", default=DEFAULT_REPO_NAME, help="Repository folder name under the install root.")
    parser.add_argument("--tag", help="Deployment tag. If omitted, the script will list tags and prompt for a selection.")
    parser.add_argument("--python-version", default=DEFAULT_PYTHON_VERSION, help="Python version to install.")
    parser.add_argument("--postgres-url", default=DEFAULT_POSTGRES_URL, help="PostgreSQL binaries archive URL.")
    parser.add_argument("--postgis-url", default=DEFAULT_POSTGIS_URL, help="PostGIS bundle archive URL.")
    parser.add_argument("--no-services", action="store_true", help="Skip Windows service registration.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    install_root = Path(args.install_root) if args.install_root else Path(prompt("Install root", str(DEFAULT_INSTALL_ROOT)))
    repo_url = args.repo_url or prompt("Git repository URL")
    repo_dir = install_root / args.repo_name
    downloads = install_root / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    install_root.mkdir(parents=True, exist_ok=True)

    log(f"Install root: {install_root}")
    log(f"Repo dir: {repo_dir}")

    git_exe = install_git(install_root, downloads)
    tags = list_remote_tags(git_exe, repo_url)
    tag = args.tag or choose_tag(tags)

    python_exe = install_python(install_root, downloads, args.python_version)
    postgres_root = install_postgres(install_root, downloads, args.postgres_url, args.postgis_url)

    clone_or_update_repo(git_exe, repo_url, repo_dir, tag)
    write_app_config(repo_dir, postgres_root)

    venv_python = create_venv(python_exe, repo_dir)
    bootstrap_python_deps(venv_python, repo_dir)

    init_postgres(postgres_root, DEFAULT_DB_USER)
    start_postgres(postgres_root, DEFAULT_DB_PORT, repo_dir)
    create_database_if_missing(postgres_root, DEFAULT_DB_PORT, DEFAULT_DB_USER, DEFAULT_DB_NAME)
    enable_postgis(repo_dir)
    apply_migrations(repo_dir, venv_python)

    if not args.no_services:
        install_postgres_service(postgres_root)
        install_api_service(repo_dir, venv_python)

    log("")
    log("=== COMPLETE ===")
    log(f"Install root: {install_root}")
    log(f"Repo tag: {tag}")
    log(f"Repository: {repo_dir}")
    log(f"Python: {venv_python}")
    log(f"Postgres: {postgres_root}")
    log(f"Database: {DEFAULT_DB_NAME}")
    log(f"Ports: db={DEFAULT_DB_PORT} api={DEFAULT_API_PORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
