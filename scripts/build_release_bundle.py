from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT / "dist"
DEFAULT_TAG = "HEAD"
DEFAULT_POSTGRES_URL = "https://sbp.enterprisedb.com/getfile.jsp?fileid=1260146"
DEFAULT_POSTGIS_URL = "https://download.osgeo.org/postgis/windows/pg18/postgis-bundle-pg18-3.6.2x64.zip"

RUNTIME_PATHS = [
    "app",
    "config",
    "db/migrations",
    "docs/data/layer_registry_master.csv",
    "requirements.txt",
    "README.md",
    "INSTALLATION.md",
    "VERSION",
    "scripts/bootstrap_python_env.py",
    "scripts/bootstrap_python_env.ps1",
    "scripts/build_release_manifest.py",
    "scripts/enable_postgis.py",
    "scripts/install_release.py",
    "scripts/run_api.py",
    "scripts/run_migrations.py",
    "scripts/reset_install_runtime_end_to_end_fix2.py",
    "scripts/setup_postgres_runtime.py",
    "scripts/start_api_managed.py",
    "scripts/system_control.py",
    "scripts/verify_python_env.py",
    "src",
]

PYTHON_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a release zip with bundled Python and PostgreSQL runtimes.")
    parser.add_argument("--tag", default=DEFAULT_TAG, help="Git ref or tag to package.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for the generated zip and staging files.")
    parser.add_argument("--name", default="", help="Optional output filename without extension.")
    parser.add_argument("--python-version", default=PYTHON_VERSION, help="Python version to download, e.g. 3.11.9.")
    parser.add_argument("--postgres-url", default=DEFAULT_POSTGRES_URL, help="PostgreSQL binaries archive URL.")
    parser.add_argument("--postgis-url", default=DEFAULT_POSTGIS_URL, help="PostGIS bundle URL.")
    return parser


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("[RUN] " + " ".join(cmd), flush=True)
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {proc.returncode}: {' '.join(cmd)}")


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[DL] {url}", flush=True)
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with dest.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)
    return dest


def git_worktree_checkout(ref: str, worktree_dir: Path) -> None:
    if worktree_dir.exists():
        shutil.rmtree(worktree_dir, ignore_errors=True)
    run(["git", "worktree", "add", "--detach", str(worktree_dir), ref], cwd=ROOT)


def remove_worktree(worktree_dir: Path) -> None:
    if worktree_dir.exists():
        run(["git", "worktree", "remove", "--force", str(worktree_dir)], cwd=ROOT)


def copy_selected_items(source_root: Path, staging_root: Path) -> None:
    staging_root.mkdir(parents=True, exist_ok=True)
    for rel in RUNTIME_PATHS:
        source = source_root / rel
        if not source.exists():
            continue
        destination = staging_root / rel
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def download_python_installer(version: str, dest_dir: Path) -> Path:
    url = f"https://www.python.org/ftp/python/{version}/python-{version}-amd64.exe"
    return download(url, dest_dir / Path(url).name)


def write_manifest(staging_root: Path, args: argparse.Namespace, tag_commit: str) -> Path:
    manifest = {
        "app": "surveyCatalyst",
        "tag": args.tag,
        "commit": tag_commit,
        "built_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python_version": args.python_version,
        "postgres_url": args.postgres_url,
        "postgis_url": args.postgis_url,
        "runtime": "portable-postgresql-postgis",
        "contents": RUNTIME_PATHS + [
            "downloads",
            ".surveyCatalyst_venv",
            "tools/python",
            "postgres",
        ],
    }
    out = staging_root / "release_manifest.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return out


def make_zip(staging_root: Path, out_zip: Path) -> None:
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    if out_zip.exists():
        out_zip.unlink()
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in staging_root.rglob("*"):
            if not path.is_file():
                continue
            zf.write(path, path.relative_to(staging_root))


def main() -> int:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle_name = args.name or f"surveyCatalyst-{args.tag}".replace("/", "_")
    staging_root = output_dir / f"{bundle_name}_staging"
    worktree_dir = output_dir / f"{bundle_name}_worktree"
    if staging_root.exists():
        shutil.rmtree(staging_root, ignore_errors=True)
    if worktree_dir.exists():
        shutil.rmtree(worktree_dir, ignore_errors=True)

    git_worktree_checkout(args.tag, worktree_dir)
    try:
        copy_selected_items(worktree_dir, staging_root)

        downloads_dir = staging_root / "downloads"
        download_python_installer(args.python_version, downloads_dir)
        download(args.postgres_url, downloads_dir / Path(args.postgres_url).name)
        download(args.postgis_url, downloads_dir / Path(args.postgis_url).name)

        commit = subprocess.run(
            ["git", "rev-parse", args.tag],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip() or args.tag
        write_manifest(staging_root, args, commit)

        out_zip = output_dir / f"{bundle_name}.zip"
        make_zip(staging_root, out_zip)
        print(out_zip)
    finally:
        remove_worktree(worktree_dir)
        shutil.rmtree(staging_root, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
