from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path.cwd()
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

POSTGRES_DIR = ROOT / "postgres"
DOWNLOADS_DIR = ROOT / "downloads"
CONFIG_PATH = ROOT / "config" / "app_config.json"

POSTGRES_URL = "https://sbp.enterprisedb.com/getfile.jsp?fileid=1260146"
POSTGIS_URL = "https://download.osgeo.org/postgis/windows/pg18/postgis-bundle-pg18-3.6.2x64.zip"

POSTGRES_FILENAME = "postgresql-18.3-3-windows-x64-binaries.zip"
POSTGIS_FILENAME = "postgis-bundle-pg18-3.6.2x64.zip"

PORT = 55433
DB_NAME = "survey_catalyst"
DB_USER = "sc_user"


def log(message: str) -> None:
    print(message, flush=True)


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
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


def pg_isready() -> bool:
    exe = POSTGRES_DIR / "bin" / "pg_isready.exe"
    if not exe.exists():
        return False
    result = subprocess.run(
        [str(exe), "-h", "127.0.0.1", "-p", str(PORT)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def stop_postgres_if_running() -> None:
    pg_ctl = POSTGRES_DIR / "bin" / "pg_ctl.exe"
    data_dir = POSTGRES_DIR / "data"
    if not pg_ctl.exists() or not data_dir.exists():
        return
    run([str(pg_ctl), "-D", str(data_dir), "stop"], check=False)


def remove_runtime() -> None:
    stop_postgres_if_running()
    targets = [
        ROOT / "postgres",
        ROOT / "downloads" / "postgres_unpack",
        ROOT / "downloads" / "postgis_unpack",
        ROOT / "downloads" / POSTGRES_FILENAME,
        ROOT / "downloads" / POSTGIS_FILENAME,
    ]
    for target in targets:
        if target.exists():
            log(f"Removing {target} ...")
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            else:
                target.unlink(missing_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)


def ensure_config() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "app": {"name": "surveyCatalyst", "env": "local"},
        "db": {
            "mode": "local",
            "local": {
                "data_dir": "./postgres/data",
                "port": PORT,
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
        "paths": {"assets": "./assets_store", "logs": "./logs"},
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    log(f"Wrote {CONFIG_PATH}")


def download_file(url: str, destination: Path) -> None:
    log(f"Downloading {url}")

    def reporthook(block_num: int, block_size: int, total_size: int) -> None:
        if total_size <= 0:
            return
        downloaded = block_num * block_size
        percent = int(min(100, downloaded * 100 / total_size))
        if percent % 10 == 0:
            log(f"{destination.name}: {percent}%")

    destination.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, destination, reporthook=reporthook)
    log(f"Saved to {destination}")


def extract_zip(zip_path: Path, destination: Path) -> None:
    log(f"Extracting {zip_path} -> {destination}")
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
    log(f"PostgreSQL runtime installed to {POSTGRES_DIR}")


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
    extract_zip(postgis_zip, unpack_dir)
    bundle_root = next((p for p in unpack_dir.iterdir() if p.is_dir()), None)
    if bundle_root is None:
        raise RuntimeError(f"Could not find extracted PostGIS bundle folder in {unpack_dir}")

    for name in ("bin", "lib", "share"):
        source_dir = bundle_root / name
        if not source_dir.exists():
            raise RuntimeError(f"Missing {source_dir}")
        merge_tree(source_dir, POSTGRES_DIR / name)

    required = [
        POSTGRES_DIR / "share" / "extension" / "postgis.control",
        POSTGRES_DIR / "share" / "extension" / "plpgsql.control",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError("PostGIS merge incomplete:\n" + "\n".join(missing))
    log("PostGIS bundle merged into portable runtime.")


def init_cluster() -> None:
    initdb = POSTGRES_DIR / "bin" / "initdb.exe"
    data_dir = POSTGRES_DIR / "data"
    if not initdb.exists():
        raise RuntimeError(f"Missing {initdb}")
    if (data_dir / "PG_VERSION").exists():
        log("Cluster already initialised.")
        return
    run([
        str(initdb),
        "-D", str(data_dir),
        "-U", DB_USER,
        "--encoding=UTF8",
        "--locale=C",
        "--auth=trust",
    ])


def start_postgres() -> None:
    if pg_isready():
        log("PostgreSQL is already running.")
        return

    pg_ctl = POSTGRES_DIR / "bin" / "pg_ctl.exe"
    data_dir = POSTGRES_DIR / "data"
    log_file = POSTGRES_DIR / "postgres.log"

    cmd = [
        str(pg_ctl),
        "-D", str(data_dir),
        "-l", str(log_file),
        "-o", f"-p {PORT}",
        "start",
    ]
    log("RUN: " + " ".join(cmd))
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    deadline = time.time() + 30
    while time.time() < deadline:
        if pg_isready():
            log("PostgreSQL is ready.")
            break
        if proc.poll() is not None:
            break
        time.sleep(1)
    else:
        raise RuntimeError("Timed out waiting for PostgreSQL to become ready")

    try:
        out, err = proc.communicate(timeout=3)
        if out.strip():
            log(out.strip())
        if err.strip():
            log(err.strip())
    except subprocess.TimeoutExpired:
        proc.kill()

    if not pg_isready():
        raise RuntimeError("PostgreSQL failed to start")


def create_database_if_missing() -> None:
    psql = POSTGRES_DIR / "bin" / "psql.exe"
    createdb = POSTGRES_DIR / "bin" / "createdb.exe"
    exists = run([
        str(psql),
        "-h", "127.0.0.1",
        "-p", str(PORT),
        "-U", DB_USER,
        "-d", "postgres",
        "-tAc",
        f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'",
    ], check=False)

    if exists.stdout.strip() == "1":
        log(f"Database {DB_NAME} already exists.")
        return

    run([
        str(createdb),
        "-h", "127.0.0.1",
        "-p", str(PORT),
        "-U", DB_USER,
        DB_NAME,
    ])


def enable_postgis() -> None:
    from core.db import build_backend
    backend = build_backend()
    conn = backend.connect()
    try:
        conn.autocommit = True
    except Exception:
        pass
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        cur.execute("SELECT PostGIS_Version();")
        version = cur.fetchone()[0]
    try:
        conn.commit()
    except Exception:
        pass
    backend.close()
    log(f"PostGIS enabled: {version}")


def apply_migrations() -> None:
    from core.db.migrations import apply_migrations as _apply_migrations
    _apply_migrations()
    log("Migrations applied.")


def main() -> int:
    log("=== RESET + INSTALL PORTABLE POSTGRESQL/POSTGIS ===")
    remove_runtime()
    ensure_config()

    postgres_zip = DOWNLOADS_DIR / POSTGRES_FILENAME
    postgis_zip = DOWNLOADS_DIR / POSTGIS_FILENAME

    download_file(POSTGRES_URL, postgres_zip)
    download_file(POSTGIS_URL, postgis_zip)

    install_postgres_runtime(postgres_zip)
    init_cluster()
    install_postgis_bundle(postgis_zip)
    start_postgres()
    create_database_if_missing()
    enable_postgis()
    apply_migrations()

    log("")
    log("=== COMPLETE ===")
    log(f"Runtime root: {POSTGRES_DIR}")
    log(f"Database: {DB_NAME}")
    log(f"Port: {PORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
