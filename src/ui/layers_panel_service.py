from __future__ import annotations

from layers.layer_management_service import LayerManagementService


class LayersPanelService:
    def __init__(self, selection_contract, map_controller):
        self.layers = LayerManagementService(selection_contract)
        self.map_controller = map_controller

    def load_panel_state(self):
        return self.layers.list_grouped_layers()

    def toggle(self, layer_key: str, visible: bool):
        result = self.layers.toggle_layer(layer_key, visible)
        self.map_controller.toggle_layer(layer_key, visible)
        return result

    def set_opacity(self, layer_key: str, opacity: float):
        return self.layers.set_layer_opacity(layer_key, opacity)
