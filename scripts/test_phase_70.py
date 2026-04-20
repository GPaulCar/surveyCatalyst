import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from map.source_style_registry import SourceStyleRegistry

svc = SourceStyleRegistry()
print(svc.style_for_layer("legal_restricted_areas"))
print(svc.style_for_layer("economic_mining_locations"))
print(svc.style_for_layer("ancient_roman_roads"))
print(svc.style_for_layer("medieval_viabundus_edges"))
