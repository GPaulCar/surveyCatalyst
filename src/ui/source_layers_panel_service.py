from __future__ import annotations

from layers.source_layer_browser_service import SourceLayerBrowserService


class SourceLayersPanelService:
    def __init__(self, map_controller):
        self.browser = SourceLayerBrowserService()
        self.map_controller = map_controller

    def load(self):
        return self.browser.list_context_layers()

    def preview_layer(self, layer_key: str):
        return self.browser.layer_summary(layer_key)

    def show_layer_on_map(self, layer_key: str):
        self.map_controller.toggle_layer(layer_key, True)
        return self.browser.layer_summary(layer_key)

    def hide_layer_on_map(self, layer_key: str):
        self.map_controller.toggle_layer(layer_key, False)
        return {"layer_key": layer_key, "hidden": True}
