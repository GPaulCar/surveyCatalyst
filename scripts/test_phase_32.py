import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.ingestion_map_runtime_service import IngestionMapRuntimeService

runtime = IngestionMapRuntimeService()
state = runtime.boot()
print("BOOT:", state)

layers = runtime.source_layers.load()
print("CONTEXT LAYERS:", layers)

if layers:
    layer_key = layers[0][0]
    print("PREVIEW:", runtime.source_layers.preview_layer(layer_key))
    print("SHOW:", runtime.source_layers.show_layer_on_map(layer_key))
    print("HIDE:", runtime.source_layers.hide_layer_on_map(layer_key))
