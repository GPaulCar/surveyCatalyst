import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ui.viewport_service import ViewportService

svc = ViewportService()
svc.set_bounds([10,10,20,20])
print(svc.get_bounds())
