import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.selection_contract import SelectionContract
from ui.survey_browser_service import SurveyBrowserService
from ui.details_state_service import DetailsStateService
from ui.map_panel_bridge import MapPanelBridge
from ui.console_renderer import ConsoleRenderer


selection = SelectionContract()
renderer = ConsoleRenderer()
details = DetailsStateService(selection)
bridge = MapPanelBridge(selection, renderer)
browser = SurveyBrowserService(selection)

surveys = browser.list_surveys_with_objects()
print("SURVEYS:", surveys)

if surveys:
    survey_id = surveys[0]["survey"][0]
    payload = browser.select_survey(survey_id)
    print("SELECTED SURVEY PAYLOAD:", payload)
    if payload["objects"]:
        object_id = payload["objects"][0][0]
        obj = browser.select_object(survey_id, object_id)
        print("SELECTED OBJECT:", obj)

print("DETAILS STATE:", details.get_current_details())
