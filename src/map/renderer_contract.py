class RendererContract:
    def render_layer(self, layer_key: str, geojson: dict):
        raise NotImplementedError

    def clear_layer(self, layer_key: str):
        raise NotImplementedError

    def highlight_feature(self, layer_key: str, feature_id: int):
        raise NotImplementedError
