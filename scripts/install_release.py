from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools"
PYTHON_DIR = TOOLS_DIR / "python"
POSTGRES_DIR = ROOT / "postgres"
DOWNLOADS_DIR = ROOT / "downloads"
CONFIG_PATH = ROOT / "config" / "app_config.json"
VENV_DIR = ROOT / ".surveyCatalyst_venv"

DB_PORT = 55433
DB_NAME = "survey_catalyst"
DB_USER = "sc_user"
RUNTIME_PYTHON_EXE = PYTHON_DIR / "python.exe"
VENV_PYTHON_EXE = VENV_DIR / "Scripts" / "python.exe"
POSTGRES_ARCHIVE_GLOB = "postgresql-*-windows-x64-binaries.zip"
POSTGIS_ARCHIVE_GLOB = "postgis-bundle-pg18-*.zip"
PYTHON_INSTALLER_GLOB = "python-*-amd64.exe"


def log(message: str) -> None:
    print(message, flush=True)


def run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    log("RUN: " + " ".join(cmd))
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout.strip():
        log(result.stdout.strip())
    if result.stderr.strip():
        log(result.stderr.strip())
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(cmd)}")
    return result


def select_single(glob_pattern: str) -> Path:
    matches = sorted(DOWNLOADS_DIR.glob(glob_pattern))
    if not matches:
        raise RuntimeError(f"Missing required download matching {glob_pattern} in {DOWNLOADS_DIR}")
    return matches[-1]


def write_config() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "app": {"name": "surveyCatalyst", "env": "release"},
        "db": {
            "mode": "local",
            "local": {
                "data_dir": str((POSTGRES_DIR / "data").resolve()),
                "port": DB_PORT,
                "database": DB_NAME,
                "user": DB_USER,
            },
            "external": {
                "host": "",
                "port": 5432,
                "database": "",
                "user": "",
            },
        },
        "paths": {
            "assets": str((ROOT / "assets_store").resolve()),
            "logs": str((ROOT / "runtime" / "logs").resolve()),
            "tools": str(TOOLS_DIR.resolve()),
            "postgres": str(POSTGRES_DIR.resolve()),
        },
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    log(f"Wrote {CONFIG_PATH}")


def ensure_python_runtime() -> Path:
    if RUNTIME_PYTHON_EXE.exists():
        return RUNTIME_PYTHON_EXE

    installer = select_single(PYTHON_INSTALLER_GLOB)
    PYTHON_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(installer),
        "/quiet",
        "InstallAllUsers=0",
        "PrependPath=0",
        "Include_test=0",
        "Include_pip=1",
        f"TargetDir={PYTHON_DIR}",
    ]
    run(cmd, cwd=ROOT)
    if RUNTIME_PYTHON_EXE.exists():
        return RUNTIME_PYTHON_EXE
    alt_local = sorted(PYTHON_DIR.rglob("python.exe"))
    if alt_local:
        return alt_local[0]
    local_appdata = Path.home() / "AppData" / "Local" / "Programs" / "Python"
    if local_appdata.exists():
        alt_existing = sorted(local_appdata.rglob("python.exe"))
        if alt_existing:
            log(f"[WARN] using existing Python runtime: {alt_existing[0]}")
            return alt_existing[0]
    raise RuntimeError(f"Python runtime was not created at {RUNTIME_PYTHON_EXE}")


def ensure_venv(runtime_python: Path) -> None:
    if not runtime_python.exists():
        raise RuntimeError("Python runtime is missing; cannot create venv")
    if not VENV_DIR.exists():
        run([str(runtime_python), "-m", "venv", str(VENV_DIR)], cwd=ROOT)
    if not VENV_PYTHON_EXE.exists():
        run([str(runtime_python), "-m", "venv", str(VENV_DIR)], cwd=ROOT)


def bootstrap_python_deps() -> None:
    python_exe = VENV_PYTHON_EXE
    if not python_exe.exists():
        raise RuntimeError(f"Missing virtualenv python at {python_exe}")
    run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], cwd=ROOT)
    run([str(python_exe), str(ROOT / "scripts" / "bootstrap_python_env.py")], cwd=ROOT)


def extract_zip(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(destination)


def find_dir_with_name(root: Path, target_name: str) -> Path:
    matches = [p for p in root.rglob(target_name) if p.is_dir()]
    if not matches:
        raise RuntimeError(f"Could not find directory '{target_name}' under {root}")
    return matches[0]


def install_postgres_runtime(postgres_zip: Path) -> None:
    unpack_dir = DOWNLOADS_DIR / "postgres_unpack"
    if unpack_dir.exists():
        shutil.rmtree(unpack_dir, ignore_errors=True)
    extract_zip(postgres_zip, unpack_dir)
    bin_dir = find_dir_with_name(unpack_dir, "bin")
    source_root = bin_dir.parent
    POSTGRES_DIR.mkdir(parents=True, exist_ok=True)
    for item in source_root.iterdir():
        destination = POSTGRES_DIR / item.name
        if destination.exists():
            if destination.is_dir():
                shutil.rmtree(destination, ignore_errors=True)
            else:
                destination.unlink(missing_ok=True)
        shutil.move(str(item), str(destination))
    (POSTGRES_DIR / "data").mkdir(parents=True, exist_ok=True)


def merge_tree(source_dir: Path, destination_dir: Path) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True)
    for item in source_dir.iterdir():
        destination = destination_dir / item.name
        if item.is_dir():
            merge_tree(item, destination)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)


def install_postgis_bundle(postgis_zip: Path) -> None:
    unpack_dir = DOWNLOADS_DIR / "postgis_unpack"
    if unpack_dir.exists():
        shutil.rmtree(unpack_dir, ignore_errors=True)
    extract_zip(postgis_zip, unpack_dir)
    bundle_root = next((p for p in unpack_dir.iterdir() if p.is_dir()), None)
    if bundle_root is None:
        raise RuntimeError(f"Could not find extracted PostGIS bundle folder in {unpack_dir}")
    for name in ("bin", "lib", "share"):
        source_dir = bundle_root / name
        if not source_dir.exists():
            raise RuntimeError(f"Missing {source_dir}")
        merge_tree(source_dir, POSTGRES_DIR / name)


def init_cluster() -> None:
    initdb = POSTGRES_DIR / "bin" / "initdb.exe"
    data_dir = POSTGRES_DIR / "data"
    if (data_dir / "PG_VERSION").exists():
        return
    run([
        str(initdb),
        "-D", str(data_dir),
        "-U", DB_USER,
        "--encoding=UTF8",
        "--locale=C",
        "--auth=trust",
    ], cwd=ROOT)


def pg_isready() -> bool:
    exe = POSTGRES_DIR / "bin" / "pg_isready.exe"
    if not exe.exists():
        return False
    result = subprocess.run([str(exe), "-h", "127.0.0.1", "-p", str(DB_PORT)], capture_output=True, text=True, check=False)
    return result.returncode == 0


def start_postgres() -> None:
    if pg_isready():
        return
    pg_ctl = POSTGRES_DIR / "bin" / "pg_ctl.exe"
    data_dir = POSTGRES_DIR / "data"
    log_file = ROOT / "runtime" / "logs" / "postgres.release.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    run([
        str(pg_ctl),
        "-D", str(data_dir),
        "-l", str(log_file),
        "-o", f"-p {DB_PORT}",
        "start",
    ], cwd=ROOT)
    deadline = time.time() + 60
    while time.time() < deadline:
        if pg_isready():
            return
        time.sleep(1)
    raise RuntimeError("Timed out waiting for PostgreSQL to start")


def create_database_if_missing() -> None:
    psql = POSTGRES_DIR / "bin" / "psql.exe"
    createdb = POSTGRES_DIR / "bin" / "createdb.exe"
    exists = run([
        str(psql),
        "-h", "127.0.0.1",
        "-p", str(DB_PORT),
        "-U", DB_USER,
        "-d", "postgres",
        "-tAc",
        f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'",
    ], cwd=ROOT, check=False)
    if exists.stdout.strip() != "1":
        run([str(createdb), "-h", "127.0.0.1", "-p", str(DB_PORT), "-U", DB_USER, DB_NAME], cwd=ROOT)


def enable_postgis() -> None:
    from core.db import build_backend

    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        conn.commit()
    finally:
        conn.close()


def apply_migrations() -> None:
    run([str(VENV_DIR / "Scripts" / "python.exe"), str(ROOT / "scripts" / "run_migrations.py")], cwd=ROOT)


def main() -> int:
    log("=== INSTALL RELEASE BUNDLE ===")
    if not DOWNLOADS_DIR.exists():
        raise RuntimeError(f"Downloads directory missing: {DOWNLOADS_DIR}")
    write_config()
    runtime_python = ensure_python_runtime()
    ensure_venv(runtime_python)
    bootstrap_python_deps()
    install_postgres_runtime(select_single(POSTGRES_ARCHIVE_GLOB))
    install_postgis_bundle(select_single(POSTGIS_ARCHIVE_GLOB))
    init_cluster()
    start_postgres()
    create_database_if_missing()
    enable_postgis()
    apply_migrations()
    log("=== COMPLETE ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
