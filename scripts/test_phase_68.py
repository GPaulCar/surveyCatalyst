import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data.external_feature_projection_service import ExternalFeatureProjectionService

svc = ExternalFeatureProjectionService()
print(svc.project_from_source_table(
    source_table="legal.restricted_areas",
    layer_key="legal_restricted_areas",
    geometry_column="geom",
    property_columns=["name", "category", "source"],
    source_id_column="id",
))
