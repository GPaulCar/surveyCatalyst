from __future__ import annotations

from layers.registry_service import LayerRegistryService
from ui.selection_contract import SelectionContract


class LayerManagementService:
    def __init__(self, selection_contract: SelectionContract):
        self.selection = selection_contract
        self.registry = LayerRegistryService()

    def list_grouped_layers(self):
        return {
            "base": self.registry.list_group("base"),
            "context": self.registry.list_group("context"),
            "survey": self.registry.list_group("survey"),
        }

    def toggle_layer(self, layer_key: str, visible: bool):
        self.registry.set_visibility(layer_key, visible)
        payload = {"layer_key": layer_key, "visible": visible}
        self.selection.select("layer_visibility", 0, payload)
        return payload

    def set_layer_opacity(self, layer_key: str, opacity: float):
        self.registry.set_opacity(layer_key, opacity)
        payload = {"layer_key": layer_key, "opacity": opacity}
        self.selection.select("layer_opacity", 0, payload)
        return payload
