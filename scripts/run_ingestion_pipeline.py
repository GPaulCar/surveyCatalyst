import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data.ingestion import IngestionService

service = IngestionService()
results = service.run_all(force="--force" in sys.argv)

for key, result in results.items():
    print(key, result)
