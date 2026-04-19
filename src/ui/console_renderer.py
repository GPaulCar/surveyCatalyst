from __future__ import annotations


class ConsoleRenderer:
    def __init__(self):
        self.selected = None
        self.layer_opacity = {}

    def render_layer(self, layer_key: str, geojson: dict):
        print(f"RENDER {layer_key} -> {len(geojson.get('features', []))} features")

    def clear_layer(self, layer_key: str):
        print(f"CLEAR {layer_key}")

    def highlight_feature(self, layer_key: str, feature_id: int):
        print(f"HIGHLIGHT {layer_key}:{feature_id}")

    def focus_geometry(self, geom_wkt: str | None):
        print(f"FOCUS {geom_wkt}")

    def set_selected(self, item_type: str, item_id: int):
        self.selected = (item_type, item_id)
        print(f"SELECTED {item_type}:{item_id}")

    def set_layer_opacity(self, layer_key: str, opacity: float):
        self.layer_opacity[layer_key] = opacity
        print(f"OPACITY {layer_key}:{opacity}")
