import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data.ingestion.staging_service import StagingService

svc = StagingService(ROOT / "data_workspace")
paths = svc.source_paths("sample_source")
print({k: str(v) for k, v in paths.items()})
print(svc.reset_extracted("sample_source"))
print(svc.promoted_marker("sample_source", "sample_artifact"))
