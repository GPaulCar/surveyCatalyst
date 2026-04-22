from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

LAYER_KEY = "roman_roads_curated"

def ensure_registry(cur) -> None:
    cur.execute(
        """
        INSERT INTO layers_registry (
            layer_key, layer_name, layer_group, source_table, geometry_type,
            is_user_selectable, is_visible, opacity, sort_order, metadata
        )
        VALUES (
            %s, %s, 'context', 'external_features', 'LINESTRING',
            TRUE, FALSE, 1.0, 121,
            %s::jsonb
        )
        ON CONFLICT (layer_key) DO UPDATE
        SET layer_name = EXCLUDED.layer_name,
            layer_group = EXCLUDED.layer_group,
            source_table = EXCLUDED.source_table,
            geometry_type = EXCLUDED.geometry_type,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
        """,
        (
            LAYER_KEY,
            "Roman roads (curated)",
            json.dumps({
                "subgroup": "historical",
                "phase": "phase_2",
                "description": "Curated Roman-road scaffold aligned for Itiner-e or other scholarly datasets",
                "target_source": "itiner-e",
            }),
        ),
    )

def iter_features(doc: dict):
    if doc.get("type") == "FeatureCollection":
        for feat in doc.get("features") or []:
            yield feat
    elif doc.get("type") == "Feature":
        yield doc
    else:
        raise ValueError("Input must be GeoJSON Feature or FeatureCollection")

def normalize_feature(feature: dict) -> dict | None:
    geom = feature.get("geometry") or {}
    props = feature.get("properties") or {}
    if geom.get("type") not in {"LineString", "MultiLineString"}:
        return None
    normalized = {
        "name": props.get("name") or props.get("title"),
        "period": props.get("period") or "roman",
        "certainty": props.get("certainty") or props.get("confidence") or props.get("status") or "unspecified",
        "source": props.get("source") or "curated_import",
        "source_ref": props.get("source_ref") or props.get("id") or props.get("identifier"),
        "all_properties": props,
    }
    return {"geometry": geom, "properties": normalized}

def load_geojson(path: Path) -> int:
    doc = json.loads(path.read_text(encoding="utf-8"))
    normalized = [feat for feat in (normalize_feature(f) for f in iter_features(doc)) if feat]
    backend = build_backend()
    conn = backend.connect()
    inserted = 0
    try:
        with conn.cursor() as cur:
            ensure_registry(cur)
            cur.execute("DELETE FROM external_features WHERE layer = %s", (LAYER_KEY,))
            for feat in normalized:
                cur.execute(
                    """
                    INSERT INTO external_features (layer, geom, properties, source_table, source_id)
                    VALUES (
                        %s,
                        ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326),
                        %s::jsonb,
                        %s,
                        %s
                    )
                    """,
                    (
                        LAYER_KEY,
                        json.dumps(feat["geometry"]),
                        json.dumps(feat["properties"]),
                        "curated_roman_roads",
                        str(feat["properties"].get("source_ref") or ""),
                    ),
                )
                inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted

def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: python scripts/load_roman_roads_curated.py <path-to-geojson>")
        return 1
    path = Path(argv[1]).resolve()
    if not path.exists():
        print(f"[ERROR] file not found: {path}")
        return 1
    count = load_geojson(path)
    print(f"[DONE] loaded {count} curated Roman-road features into layer '{LAYER_KEY}'")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
