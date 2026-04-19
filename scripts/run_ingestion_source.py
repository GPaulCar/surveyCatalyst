import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data.ingestion import IngestionService

if len(sys.argv) < 2:
    raise SystemExit("Usage: python scripts/run_ingestion_source.py <source_key> [--force]")

source_key = sys.argv[1]
force = "--force" in sys.argv[2:]

service = IngestionService()
result = service.run_one(source_key, force=force)
print(result)
