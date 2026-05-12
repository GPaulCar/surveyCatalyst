from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend


CSV_PATH = ROOT / "docs" / "data" / "layer_registry_master.csv"
REQUIRED_COLUMNS = [
    "category",
    "subcategory",
    "layer_name",
    "description",
    "geometry_type",
    "source_provider",
    "source_type",
    "endpoint_url",
    "ingestion_method",
    "priority",
    "region_scope",
    "notes",
]


def to_snake_case(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def normalize_row(row: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for column in REQUIRED_COLUMNS:
        out[column] = (row.get(column) or "").strip()
    out["layer_name"] = to_snake_case(out["layer_name"])
    return out


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [c for c in REQUIRED_COLUMNS if c not in fieldnames]
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(missing))
        rows = [normalize_row(row) for row in reader]

    return rows


def ensure_table(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS layer_registry (
            id SERIAL PRIMARY KEY,
            category TEXT,
            subcategory TEXT,
            layer_name TEXT UNIQUE,
            description TEXT,
            geometry_type TEXT,
            source_provider TEXT,
            source_type TEXT,
            endpoint_url TEXT,
            ingestion_method TEXT,
            priority TEXT,
            region_scope TEXT,
            notes TEXT,
            is_enabled BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
    )


def main() -> int:
    rows = load_rows(CSV_PATH)
    backend = build_backend()
    conn = backend.connect()
    inserted = 0
    updated = 0
    skipped = 0
    try:
        with conn.cursor() as cur:
            ensure_table(cur)

            for row in rows:
                cur.execute(
                    """
                    SELECT
                        category,
                        subcategory,
                        layer_name,
                        description,
                        geometry_type,
                        source_provider,
                        source_type,
                        endpoint_url,
                        ingestion_method,
                        priority,
                        region_scope,
                        notes
                    FROM layer_registry
                    WHERE layer_name = %s
                    """,
                    (row["layer_name"],),
                )
                existing = cur.fetchone()

                if existing is None:
                    cur.execute(
                        """
                        INSERT INTO layer_registry (
                            category,
                            subcategory,
                            layer_name,
                            description,
                            geometry_type,
                            source_provider,
                            source_type,
                            endpoint_url,
                            ingestion_method,
                            priority,
                            region_scope,
                            notes
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            row["category"],
                            row["subcategory"],
                            row["layer_name"],
                            row["description"],
                            row["geometry_type"],
                            row["source_provider"],
                            row["source_type"],
                            row["endpoint_url"],
                            row["ingestion_method"],
                            row["priority"],
                            row["region_scope"],
                            row["notes"],
                        ),
                    )
                    inserted += 1
                    continue

                existing_map = {
                    "category": existing[0] or "",
                    "subcategory": existing[1] or "",
                    "layer_name": existing[2] or "",
                    "description": existing[3] or "",
                    "geometry_type": existing[4] or "",
                    "source_provider": existing[5] or "",
                    "source_type": existing[6] or "",
                    "endpoint_url": existing[7] or "",
                    "ingestion_method": existing[8] or "",
                    "priority": existing[9] or "",
                    "region_scope": existing[10] or "",
                    "notes": existing[11] or "",
                }
                changed = any(existing_map[k] != row[k] for k in REQUIRED_COLUMNS)
                if not changed:
                    skipped += 1
                    continue

                cur.execute(
                    """
                    UPDATE layer_registry
                    SET
                        category = %s,
                        subcategory = %s,
                        description = %s,
                        geometry_type = %s,
                        source_provider = %s,
                        source_type = %s,
                        endpoint_url = %s,
                        ingestion_method = %s,
                        priority = %s,
                        region_scope = %s,
                        notes = %s
                    WHERE layer_name = %s
                    """,
                    (
                        row["category"],
                        row["subcategory"],
                        row["description"],
                        row["geometry_type"],
                        row["source_provider"],
                        row["source_type"],
                        row["endpoint_url"],
                        row["ingestion_method"],
                        row["priority"],
                        row["region_scope"],
                        row["notes"],
                        row["layer_name"],
                    ),
                )
                updated += 1

        conn.commit()
    finally:
        conn.close()

    print(
        f"[DONE] layer_registry sync rows={len(rows)} inserted={inserted} updated={updated} skipped={skipped}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
