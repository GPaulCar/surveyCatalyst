from layers.registry_service import LayerRegistryService
from map.feature_service import FeatureService


class MapController:
    def __init__(self, renderer, selection_contract):
        self.renderer = renderer
        self.selection = selection_contract
        self.layers = LayerRegistryService()
        self.features = FeatureService()

    def load_visible_layers(self):
        layers = self.layers.list_layers()

        for layer in layers:
            layer_key = layer[0]
            is_visible = layer[6]

            if not is_visible:
                continue

            geojson = self.features.get_layer_geojson(layer_key)
            self.renderer.render_layer(layer_key, geojson)

    def toggle_layer(self, layer_key: str, visible: bool):
        self.layers.set_visibility(layer_key, visible)

        if visible:
            geojson = self.features.get_layer_geojson(layer_key)
            self.renderer.render_layer(layer_key, geojson)
        else:
            self.renderer.clear_layer(layer_key)
