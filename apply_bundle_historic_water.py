from __future__ import annotations

import base64
from pathlib import Path

build_script = r'''from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

LAYER_SPECS = [
    {
        "layer_key": "old_creeks",
        "layer_name": "Old creeks",
        "geometry_type": "LINESTRING",
        "sort_order": 310,
        "metadata": {
            "subgroup": "historic_water",
            "phase": "phase_4",
            "description": "Historic or inferred creeks",
        },
    },
    {
        "layer_key": "old_channels",
        "layer_name": "Old channels",
        "geometry_type": "LINESTRING",
        "sort_order": 311,
        "metadata": {
            "subgroup": "historic_water",
            "phase": "phase_4",
            "description": "Historic or inferred river channels",
        },
    },
    {
        "layer_key": "wetland_history",
        "layer_name": "Wetland history",
        "geometry_type": "POLYGON",
        "sort_order": 312,
        "metadata": {
            "subgroup": "historic_water",
            "phase": "phase_4",
            "description": "Historic wetland, marsh, or damp ground areas",
        },
    },
]

def main() -> int:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            for spec in LAYER_SPECS:
                cur.execute(
                    """
                    INSERT INTO layers_registry (
                        layer_key, layer_name, layer_group, source_table, geometry_type,
                        is_user_selectable, is_visible, opacity, sort_order, metadata
                    )
                    VALUES (
                        %s, %s, 'context', 'external_features', %s,
                        TRUE, FALSE, 1.0, %s, %s::jsonb
                    )
                    ON CONFLICT (layer_key) DO UPDATE
                    SET layer_name = EXCLUDED.layer_name,
                        geometry_type = EXCLUDED.geometry_type,
                        sort_order = EXCLUDED.sort_order,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    (
                        spec["layer_key"],
                        spec["layer_name"],
                        spec["geometry_type"],
                        spec["sort_order"],
                        json.dumps(spec["metadata"]),
                    ),
                )
        conn.commit()
    finally:
        conn.close()

    print("[DONE] historic water layers registered")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''

loader_template = r'''from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

LAYER_KEY = "__LAYER_KEY__"
SOURCE_TABLE = "__SOURCE_TABLE__"

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
'''

files = {
    "scripts/build_bundle_historic_water.py": build_script,
    "scripts/load_old_creeks_geojson.py": loader_template.replace("__LAYER_KEY__", "old_creeks").replace("__SOURCE_TABLE__", "old_creeks_import"),
    "scripts/load_old_channels_geojson.py": loader_template.replace("__LAYER_KEY__", "old_channels").replace("__SOURCE_TABLE__", "old_channels_import"),
    "scripts/load_wetland_history_geojson.py": loader_template.replace("__LAYER_KEY__", "wetland_history").replace("__SOURCE_TABLE__", "wetland_history_import"),
}

encoded = {path: base64.b64encode(content.encode("utf-8")).decode("ascii") for path, content in files.items()}

def main() -> None:
    root = Path.cwd()
    for rel_path, payload in encoded.items():
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(payload))
        print(f"[OK] wrote {target}")
    print("[DONE] bundle historic water installer applied")
    print("Run:")
    print("  python scripts/build_bundle_historic_water.py")
    print("Optional loaders:")
    print("  python scripts/load_old_creeks_geojson.py <path-to-geojson>")
    print("  python scripts/load_old_channels_geojson.py <path-to-geojson>")
    print("  python scripts/load_wetland_history_geojson.py <path-to-geojson>")

if __name__ == "__main__":
    main()