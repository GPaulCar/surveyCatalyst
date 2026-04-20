import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data.raw_loader_service import RawLoaderService

sample = ROOT / "sample_phase_64.csv"
sample.write_text("a\nb\n", encoding="utf-8")

svc = RawLoaderService()
print(svc.load_csv_lines("raw_test", sample))
