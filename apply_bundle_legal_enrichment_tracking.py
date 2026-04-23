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
        "layer_key": "protection_buffers",
        "layer_name": "Protection buffers",
        "geometry_type": "POLYGON",
        "sort_order": 212,
        "metadata": {
            "subgroup": "legal_permission",
            "phase": "phase_3",
            "description": "Structured protection and legal buffer polygons",
        },
    },
    {
        "layer_key": "field_names",
        "layer_name": "Field names",
        "geometry_type": "POLYGON",
        "sort_order": 213,
        "metadata": {
            "subgroup": "legal_permission",
            "phase": "phase_3",
            "description": "Structured field-name polygons or references",
        },
    },
    {
        "layer_key": "geonames_points",
        "layer_name": "GeoNames points",
        "geometry_type": "POINT",
        "sort_order": 320,
        "metadata": {
            "subgroup": "enrichment",
            "phase": "phase_5",
            "description": "GeoNames or place-name reference points",
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

    print("[DONE] legal + enrichment layers registered")
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

tracker_init = r'''from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKER_DIR = ROOT / "workspace" / "permissions" / "tracker"
TRACKER_DIR.mkdir(parents=True, exist_ok=True)

TRACKER_FILE = TRACKER_DIR / "request_tracker.jsonl"
INDEX_FILE = TRACKER_DIR / "request_tracker_index.json"

def main() -> int:
    if not TRACKER_FILE.exists():
        TRACKER_FILE.write_text("", encoding="utf-8")
        print(f"[OK] created {TRACKER_FILE}")
    else:
        print(f"[OK] exists {TRACKER_FILE}")

    if not INDEX_FILE.exists():
        INDEX_FILE.write_text(json.dumps({"version": 1, "requests": 0}, indent=2), encoding="utf-8")
        print(f"[OK] created {INDEX_FILE}")
    else:
        print(f"[OK] exists {INDEX_FILE}")

    print("[DONE] permission request tracker initialised")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''

tracker_add = r'''from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACKER_DIR = ROOT / "workspace" / "permissions" / "tracker"
TRACKER_FILE = TRACKER_DIR / "request_tracker.jsonl"
INDEX_FILE = TRACKER_DIR / "request_tracker_index.json"

def main(argv: list[str]) -> int:
    if len(argv) < 5:
        print("Usage: python scripts/add_permission_request.py <layer> <source_id> <status> <description>")
        return 1

    layer = argv[1]
    source_id = argv[2]
    status = argv[3]
    description = " ".join(argv[4:])

    TRACKER_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "saved_at": datetime.now().isoformat(),
        "layer": layer,
        "source_id": source_id,
        "status": status,
        "description": description,
    }

    with TRACKER_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    index = {"version": 1, "requests": 0}
    if INDEX_FILE.exists():
        index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    index["requests"] = int(index.get("requests", 0)) + 1
    INDEX_FILE.write_text(json.dumps(index, indent=2), encoding="utf-8")

    print("[DONE] permission request tracked")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
'''

files = {
    "scripts/build_bundle_legal_enrichment_tracking.py": build_script,
    "scripts/load_protection_buffers_geojson.py": loader_template.replace("__LAYER_KEY__", "protection_buffers").replace("__SOURCE_TABLE__", "protection_buffers_import"),
    "scripts/load_field_names_geojson.py": loader_template.replace("__LAYER_KEY__", "field_names").replace("__SOURCE_TABLE__", "field_names_import"),
    "scripts/load_geonames_geojson.py": loader_template.replace("__LAYER_KEY__", "geonames_points").replace("__SOURCE_TABLE__", "geonames_import"),
    "scripts/init_permission_request_tracker.py": tracker_init,
    "scripts/add_permission_request.py": tracker_add,
}

encoded = {path: base64.b64encode(content.encode("utf-8")).decode("ascii") for path, content in files.items()}

def main() -> None:
    root = Path.cwd()
    for rel_path, payload in encoded.items():
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(payload))
        print(f"[OK] wrote {target}")
    print("[DONE] bundle legal + enrichment + tracking installer applied")
    print("Run:")
    print("  python scripts/build_bundle_legal_enrichment_tracking.py")
    print("  python scripts/init_permission_request_tracker.py")
    print("Optional loaders:")
    print("  python scripts/load_protection_buffers_geojson.py <path-to-geojson>")
    print("  python scripts/load_field_names_geojson.py <path-to-geojson>")
    print("  python scripts/load_geonames_geojson.py <path-to-geojson>")
    print("Track requests:")
    print("  python scripts/add_permission_request.py <layer> <source_id> <status> <description>")

if __name__ == "__main__":
    main()