import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.selection_contract import SelectionContract
from map.geojson_renderer import GeoJSONRenderer
from map.controller import MapController
from ui.widgets.layers_tab_widget import LayersTabWidget
from ui.widgets.survey_tab_widget import SurveyTabWidget
from ui.widgets.details_tab_widget import DetailsTabWidget
from ui.widgets.data_tab_widget import DataTabWidget

selection = SelectionContract()
renderer = GeoJSONRenderer()
controller = MapController(renderer, selection)

print(LayersTabWidget(selection, controller).load())
print(SurveyTabWidget(selection).load())
print(DetailsTabWidget(selection).load())
print(DataTabWidget().load())
