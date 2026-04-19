from __future__ import annotations


class LayerSelectionBridge:
    def __init__(self, selection_contract, renderer):
        self.selection = selection_contract
        self.renderer = renderer
        self.selection.subscribe(self._on_selection)

    def _on_selection(self, item):
        item_type = item.get("item_type")
        payload = item.get("payload") or {}

        if item_type == "layer_visibility":
            layer_key = payload.get("layer_key")
            visible = payload.get("visible")
            if visible is False:
                self.renderer.clear_layer(layer_key)

        elif item_type == "layer_opacity":
            layer_key = payload.get("layer_key")
            opacity = payload.get("opacity")
            self.renderer.set_layer_opacity(layer_key, opacity)
