from __future__ import annotations

import csv
import json
from pathlib import Path


class SchemaInspectionService:
    GEOM_PREFIXES = ("POINT", "LINESTRING", "POLYGON", "MULTIPOLYGON", "MULTILINESTRING", "MULTIPOINT")

    def inspect_csv(self, csv_path: str | Path, sample_size: int = 20) -> dict:
        csv_path = Path(csv_path)
        with csv_path.open("r", encoding="utf-8", errors="ignore", newline="") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames or []
            samples = []
            wkt_columns = set()
            row_count = 0

            for row in reader:
                row_count += 1
                if len(samples) < sample_size:
                    samples.append(row)
                for key, value in row.items():
                    if isinstance(value, str) and value.upper().startswith(self.GEOM_PREFIXES):
                        wkt_columns.add(key)

        return {
            "path": str(csv_path),
            "fieldnames": fieldnames,
            "detected_wkt_columns": sorted(wkt_columns),
            "row_count": row_count,
            "sample_rows": samples,
        }

    def write_report(self, report: dict, destination: str | Path) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return destination
