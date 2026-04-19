from __future__ import annotations


class GeoJSONRenderer:
    def __init__(self):
        self.layers = {}
        self.selected = None

    def render_layer(self, layer_key: str, geojson: dict):
        self.layers[layer_key] = geojson
        print(f"RENDER {layer_key} -> {len(geojson.get('features', []))} features")

    def clear_layer(self, layer_key: str):
        self.layers.pop(layer_key, None)
        print(f"CLEAR {layer_key}")

    def highlight_feature(self, layer_key: str, feature_id: int):
        self.selected = (layer_key, feature_id)
        print(f"HIGHLIGHT {layer_key}:{feature_id}")

    def focus_geometry(self, geom_wkt: str | None):
        print(f"FOCUS {geom_wkt}")

    def set_selected(self, item_type: str, item_id: int):
        print(f"SELECTED {item_type}:{item_id}")

    def snapshot(self):
        return {
            "layers": list(self.layers.keys()),
            "selected": self.selected,
        }
