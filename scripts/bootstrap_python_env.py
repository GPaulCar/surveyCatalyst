from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]):
    print("RUN:", " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")


def main():
    repo_root = Path(__file__).resolve().parent.parent
    src_path = repo_root / "src"

    # Detect active Python (must be inside venv)
    python_exe = Path(sys.executable)
    venv_root = python_exe.parent.parent
    site_packages = venv_root / "Lib" / "site-packages"

    if not site_packages.exists():
        raise RuntimeError(f"site-packages not found at {site_packages}")

    # Write .pth file
    pth_file = site_packages / "surveyCatalyst_src.pth"
    pth_file.write_text(str(src_path), encoding="ascii")

    print(f"Wrote .pth file: {pth_file}")
    print(f"Registered src path: {src_path}")

    # Upgrade pip
    run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"])

    # Install requirements
    requirements = repo_root / "requirements.txt"
    if not requirements.exists():
        raise RuntimeError("requirements.txt not found in repo root")

    run([str(python_exe), "-m", "pip", "install", "-r", str(requirements)])

    print("\n=== COMPLETE ===")
    print("Python executable:", python_exe)
    print("Venv root:", venv_root)

    print("\nVerify with:")
    print(
        'python -c "from orchestration.pipeline_orchestrator import PipelineOrchestrator as P; print(P)"'
    )


if __name__ == "__main__":
    main()