import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from validation.data_quality_service import DataQualityService

svc = DataQualityService()
print("SURVEY_OBJECT_ISSUES:", svc.survey_object_issues())
print("EXTERNAL_FEATURE_ISSUES:", svc.external_feature_issues())
