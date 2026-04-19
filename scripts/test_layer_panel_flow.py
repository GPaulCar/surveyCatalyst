import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.selection_contract import SelectionContract
from ui.console_renderer import ConsoleRenderer
from ui.layer_selection_bridge import LayerSelectionBridge
from map.controller import MapController
from ui.layers_panel_service import LayersPanelService


selection = SelectionContract()
renderer = ConsoleRenderer()
bridge = LayerSelectionBridge(selection, renderer)
controller = MapController(renderer, selection)
panel = LayersPanelService(selection, controller)

print("LAYER PANEL STATE:", panel.load_panel_state())

print("TOGGLE ON survey_objects")
panel.toggle("survey_objects", True)

print("SET OPACITY survey_objects")
panel.set_opacity("survey_objects", 0.55)

print("TOGGLE OFF survey_objects")
panel.toggle("survey_objects", False)
