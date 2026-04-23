from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

LAYER_KEY = "rivers_streams"
SOURCE_TABLE = "rivers_streams_import"

def iter_features(doc: dict):
    if doc.get("type") == "FeatureCollection":
        for feat in doc.get("features") or []:
            yield feat
    elif doc.get("type") == "Feature":
        yield doc
    else:
        raise ValueError("Input must be GeoJSON Feature or FeatureCollection")

def pick_source_id(props: dict, fallback: int) -> str:
    props = props or {}
    for key in ("id", "identifier", "source_id", "name", "ref"):
        value = props.get(key)
        if value not in (None, ""):
            return str(value)
    return str(fallback)

def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: python scripts/{Path(__file__).name} <path-to-geojson>")
        return 1

    path = Path(argv[1]).resolve()
    if not path.exists():
        print(f"[ERROR] file not found: {path}")
        return 1

    doc = json.loads(path.read_text(encoding="utf-8"))
    backend = build_backend()
    conn = backend.connect()
    inserted = 0
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM external_features WHERE layer = %s", (LAYER_KEY,))
            for idx, feat in enumerate(iter_features(doc), start=1):
                geom = feat.get("geometry")
                props = feat.get("properties") or {}
                if not geom:
                    continue
                cur.execute(
                    """
                    INSERT INTO external_features (layer, geom, properties, source_table, source_id)
                    VALUES (
                        %s,
                        ST_Force2D(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)),
                        %s::jsonb,
                        %s,
                        %s
                    )
                    """,
                    (
                        LAYER_KEY,
                        json.dumps(geom),
                        json.dumps(props),
                        SOURCE_TABLE,
                        pick_source_id(props, idx),
                    ),
                )
                inserted += 1
        conn.commit()
    finally:
        conn.close()

    print(f"[DONE] loaded {inserted} features into layer '{LAYER_KEY}'")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
