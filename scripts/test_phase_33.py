import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data.manual_seed_service import ManualSeedService
from map.geojson_renderer import GeoJSONRenderer
from ui.source_layer_render_service import SourceLayerRenderService

seed = ManualSeedService()

rid = seed.seed_restricted_area(
    "Seed Restricted Area",
    "POLYGON((11.40 48.10, 11.45 48.10, 11.45 48.15, 11.40 48.15, 11.40 48.10))",
)
mid = seed.seed_mining_location(
    "Seed Mine",
    "POINT(11.50 48.20)",
    mineral_type="iron",
    year=1720,
)

print("SEEDED:", rid, mid)

renderer = GeoJSONRenderer()
svc = SourceLayerRenderService(renderer)

print("LEGAL:", svc.render_context_layer("legal_restricted_areas"))
print("ECONOMIC:", svc.render_context_layer("economic_mining_locations"))
print("SNAPSHOT:", renderer.snapshot())
