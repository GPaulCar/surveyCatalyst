from __future__ import annotations

import importlib
from pathlib import Path

modules = [
    "core.db",
    "data.ingestion.service",
    "orchestration.pipeline_orchestrator",
    "export.export_pack_service",
    "reporting.run_summary_service",
]

print("Repo root:", Path.cwd())
for name in modules:
    mod = importlib.import_module(name)
    print(f"OK: {name} -> {mod.__file__}")
