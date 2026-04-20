import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from validation.pipeline_quality_service import PipelineQualityService

svc = PipelineQualityService()
print("SOURCE_QUALITY:", svc.source_quality())
print("FEATURE_QUALITY:", svc.external_feature_quality())
