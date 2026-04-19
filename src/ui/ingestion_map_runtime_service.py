from __future__ import annotations

from map.geojson_renderer import GeoJSONRenderer
from map.controller import MapController
from ui.selection_contract import SelectionContract
from ui.source_layers_panel_service import SourceLayersPanelService
from ui.layer_selection_bridge import LayerSelectionBridge


class IngestionMapRuntimeService:
    def __init__(self):
        self.selection = SelectionContract()
        self.renderer = GeoJSONRenderer()
        self.map_controller = MapController(self.renderer, self.selection)
        self.layer_bridge = LayerSelectionBridge(self.selection, self.renderer)
        self.source_layers = SourceLayersPanelService(self.map_controller)

    def boot(self):
        self.map_controller.load_visible_layers()
        return {
            "renderer": self.renderer.snapshot(),
            "context_layers": self.source_layers.load(),
        }
