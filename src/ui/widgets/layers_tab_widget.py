from __future__ import annotations

from ui.layers_panel_service import LayersPanelService


class LayersTabWidget:
    def __init__(self, selection_contract, map_controller):
        self.service = LayersPanelService(selection_contract, map_controller)

    def load(self):
        return self.service.load_panel_state()

    def toggle(self, layer_key: str, visible: bool):
        return self.service.toggle(layer_key, visible)

    def set_opacity(self, layer_key: str, opacity: float):
        return self.service.set_opacity(layer_key, opacity)
