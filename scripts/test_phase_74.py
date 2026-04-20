import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from export.export_pack_service import ExportPackService

print(ExportPackService().export_all_layers(Path("exports")))
