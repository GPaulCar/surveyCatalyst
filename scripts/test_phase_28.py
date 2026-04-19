import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.selection_contract import SelectionContract
from ui.survey_workflow_service import SurveyWorkflowService

svc = SurveyWorkflowService(SelectionContract())
print(svc.create_survey(1, "Workflow Survey", "POLYGON((11 48, 11.1 48, 11.1 48.1, 11 48.1, 11 48))"))
