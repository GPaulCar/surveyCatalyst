import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.selection_contract import SelectionContract
from ui.survey_tab_controller import SurveyTabController


selection = SelectionContract()
controller = SurveyTabController(selection)

print("surveys:", controller.list_surveys())
