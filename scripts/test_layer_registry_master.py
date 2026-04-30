import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from layers.master_registry_service import MasterLayerRegistryService


records = MasterLayerRegistryService().load_records()
print(
    {
        "layers": len(records),
        "categories": sorted({record.category for record in records}),
        "source_types": sorted({record.source_type for record in records}),
        "derived_layers": sum(1 for record in records if record.ingestion_method == "postgis_derived"),
    }
)
