import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data.ingestion import RealIngestionService

if len(sys.argv) < 3:
    raise SystemExit("Usage: python scripts/run_real_source_ingestion.py <dry-run|run> <source_key>")

mode = sys.argv[1]
source_key = sys.argv[2]

svc = RealIngestionService()

if mode == "dry-run":
    print(svc.dry_run_one(source_key))
elif mode == "run":
    print(svc.run_one(source_key))
else:
    raise SystemExit("Mode must be dry-run or run")
