from __future__ import annotations

from layers.source_layer_browser_service import SourceLayerBrowserService
from map.layer_style_service import LayerStyleService


class SourceLayerRenderService:
    def __init__(self, renderer):
        self.browser = SourceLayerBrowserService()
        self.styles = LayerStyleService()
        self.renderer = renderer

    def render_context_layer(self, layer_key: str):
        summary = self.browser.layer_summary(layer_key)
        style = self.styles.style_for_layer(layer_key)
        payload = {
            "geojson": summary["geojson"],
            "style": style,
            "feature_count": summary["feature_count"],
        }
        self.renderer.render_layer(layer_key, payload["geojson"])
        return payload
