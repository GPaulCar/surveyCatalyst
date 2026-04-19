import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.selection_contract import SelectionContract
from ui.console_renderer import ConsoleRenderer
from ui.survey_panel_service import SurveyPanelService
from ui.survey_panel_bridge import SurveyPanelBridge

selection = SelectionContract()
renderer = ConsoleRenderer()
bridge = SurveyPanelBridge(selection, renderer)

panel = SurveyPanelService()

surveys = panel.list_surveys()
print("SURVEYS:", surveys)

if surveys:
    sid = surveys[0]["id"]
    objects = panel.get_survey_objects(sid)
    print("OBJECTS:", objects)

    if objects:
        obj = objects[0]
        selection.select("survey_object", obj["id"], obj)
