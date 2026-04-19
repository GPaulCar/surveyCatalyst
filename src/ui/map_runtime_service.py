from __future__ import annotations

from map.controller import MapController
from map.geojson_renderer import GeoJSONRenderer
from ui.selection_contract import SelectionContract
from ui.map_panel_bridge import MapPanelBridge
from ui.layer_selection_bridge import LayerSelectionBridge
from ui.survey_panel_bridge import SurveyPanelBridge


class MapRuntimeService:
    def __init__(self):
        self.selection = SelectionContract()
        self.renderer = GeoJSONRenderer()
        self.controller = MapController(self.renderer, self.selection)

        self.map_bridge = MapPanelBridge(self.selection, self.renderer)
        self.layer_bridge = LayerSelectionBridge(self.selection, self.renderer)
        self.survey_bridge = SurveyPanelBridge(self.selection, self.renderer)

    def boot(self):
        self.controller.load_visible_layers()
        return self.renderer.snapshot()

    def toggle_layer(self, layer_key: str, visible: bool):
        self.controller.toggle_layer(layer_key, visible)
        return self.renderer.snapshot()
