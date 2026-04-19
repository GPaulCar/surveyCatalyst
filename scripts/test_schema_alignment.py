import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db.migrations import apply_migrations
from layers.registry_service import LayerRegistryService

apply_migrations()
service = LayerRegistryService()
print(service.list_layers())
