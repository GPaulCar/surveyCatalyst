from __future__ import annotations

from layers.registry_service import LayerRegistryService
from map.feature_service import FeatureService


class SourceLayerBrowserService:
    def __init__(self):
        self.registry = LayerRegistryService()
        self.features = FeatureService()

    def list_context_layers(self):
        return self.registry.list_group("context")

    def layer_summary(self, layer_key: str):
        geojson = self.features.get_layer_geojson(layer_key)
        return {
            "layer_key": layer_key,
            "feature_count": len(geojson.get("features", [])),
            "geojson": geojson,
        }

    def load_visible_context_layers(self):
        layers = self.registry.list_group("context")
        result = []
        for row in layers:
            layer_key = row[0]
            is_visible = row[4]
            opacity = row[5]
            if is_visible:
                result.append(
                    {
                        "layer_key": layer_key,
                        "opacity": opacity,
                        "summary": self.layer_summary(layer_key),
                    }
                )
        return result
