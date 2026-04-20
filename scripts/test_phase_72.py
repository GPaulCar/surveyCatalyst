import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from analytics.survey_context_analysis_service import SurveyContextAnalysisService

svc = SurveyContextAnalysisService()
print(svc.linked_summary(1))
