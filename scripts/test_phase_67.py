import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reporting.run_summary_service import RunSummaryService

svc = RunSummaryService()
print("LATEST:", svc.latest_runs(5))
print("BY_SOURCE:", svc.summary_by_source())
