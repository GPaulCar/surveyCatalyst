import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from map.feature_service import FeatureService

svc = FeatureService()

layer = "survey_objects"  # or a survey_x layer

geojson = svc.get_layer_geojson(layer)

print(geojson)