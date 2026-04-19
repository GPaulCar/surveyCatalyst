import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from layers.layer_filter_service import LayerFilterService

svc = LayerFilterService()
print("ALL:", svc.list_layers())
print("VISIBLE CONTEXT:", svc.visible_context_layers())
