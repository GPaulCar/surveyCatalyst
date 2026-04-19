import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.selection_contract import SelectionContract
from map.geojson_renderer import GeoJSONRenderer
from ui.selection_sync_service import SelectionSyncService

selection = SelectionContract()
renderer = GeoJSONRenderer()
sync = SelectionSyncService(selection, renderer)

selection.select("survey_object", 1, {"geom": "POINT(11.5 48.1)", "layer_key": "survey_1"})
print(renderer.snapshot())
