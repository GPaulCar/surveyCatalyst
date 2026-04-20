import sys
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data.ingestion.schema_inspection_service import SchemaInspectionService

workspace = ROOT / "data_workspace"
workspace.mkdir(exist_ok=True)
csv_path = workspace / "sample_schema.csv"

with csv_path.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "name", "wkt_geom"])
    writer.writeheader()
    writer.writerow({"id": "1", "name": "A", "wkt_geom": "POINT(11.5 48.1)"})
    writer.writerow({"id": "2", "name": "B", "wkt_geom": "POINT(11.6 48.2)"})

svc = SchemaInspectionService()
report = svc.inspect_csv(csv_path)
report_path = svc.write_report(report, workspace / "sample_schema_report.json")
print(report_path)
print(report)
