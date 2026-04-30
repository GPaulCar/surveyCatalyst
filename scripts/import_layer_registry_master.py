import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from layers.master_registry_service import MasterLayerRegistryService


if __name__ == "__main__":
    result = MasterLayerRegistryService().sync_to_database()
    print(result)
