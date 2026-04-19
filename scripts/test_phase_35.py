import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from map.viewport_query_service import ViewportQueryService

svc = ViewportQueryService()
print(svc.features_for_layer_bbox("legal_restricted_areas", 11.0, 48.0, 12.0, 49.0))
