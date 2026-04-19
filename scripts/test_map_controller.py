import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))


class DummyRenderer:
    def render_layer(self, layer_key, geojson):
        print(f"RENDER {layer_key} -> {len(geojson['features'])} features")

    def clear_layer(self, layer_key):
        print(f"CLEAR {layer_key}")

    def highlight_feature(self, layer_key, feature_id):
        print(f"HIGHLIGHT {layer_key}:{feature_id}")


class DummySelection:
    def select(self, entity_type, entity_id, payload):
        print(f"SELECT {entity_type}:{entity_id}")


from map.controller import MapController

controller = MapController(DummyRenderer(), DummySelection())
controller.load_visible_layers()
