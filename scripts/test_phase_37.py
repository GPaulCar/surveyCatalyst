import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from survey.survey_link_service import SurveyLinkService

svc = SurveyLinkService()
print("SURVEY 1:", svc.get_survey_with_objects(1))
print("PARENT OF OBJECT 1:", svc.find_parent_survey_for_object(1))
