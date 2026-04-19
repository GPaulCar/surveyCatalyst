import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.selection_contract import SelectionContract
from ui.drawing_ingest_controller import DrawingIngestController
from survey.query_service import SurveyQueryService


class ConsoleSelection(SelectionContract):
    def __init__(self):
        super().__init__()
        self.subscribe(self._echo)

    def _echo(self, item):
        print("SELECTED:", item["item_type"], item["item_id"])


selection = ConsoleSelection()
controller = DrawingIngestController(selection)

created = controller.create_survey_from_polygon(
    expedition_id=1,
    title="Test Survey",
    polygon_wkt="POLYGON((11.5 48.1, 11.6 48.1, 11.6 48.2, 11.5 48.2, 11.5 48.1))",
)
print("CREATED SURVEY:", created["survey_id"], created["layer_key"])

object_id = controller.add_object_to_survey(
    survey_id=created["survey_id"],
    expedition_id=1,
    obj_type="marker",
    geom_wkt="POINT(11.55 48.15)",
    properties={"title": "Test Marker", "notes": "Created from test_ingest_flow"},
)
print("CREATED OBJECT:", object_id)

query = SurveyQueryService()
print("SURVEYS:", query.list_surveys())
print("OBJECTS:", query.list_survey_objects(created["survey_id"]))
