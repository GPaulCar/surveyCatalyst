from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

LAYER_KEY = "roman_roads_curated"
ZENODO_RECORD_ID = "17122148"
BAVARIA_BBOX = (47.20, 8.95, 50.65, 13.95)  # south, west, north, east
OUTPUT_DIR = ROOT / "workspace" / "downloads" / "curated" / "itinere"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
                "description": "Curated Roman roads imported from Itiner-e static version or equivalent scholarly GeoJSON",
                "target_source": "itiner-e",
            }),
        ),
    )

def bbox_intersects(feature_bbox, clip_bbox) -> bool:
    fminx, fminy, fmaxx, fmaxy = feature_bbox
    cminy, cminx, cmaxy, cmaxx = clip_bbox
    return not (fmaxx < cminx or fminx > cmaxx or fmaxy < cminy or fminy > cmaxy)

def coords_bbox(coords):
    xs = []
    ys = []
    def walk(node):
        if isinstance(node, (list, tuple)) and node:
            if isinstance(node[0], (int, float)) and len(node) >= 2:
                xs.append(float(node[0]))
                ys.append(float(node[1]))
            else:
                for child in node:
                    walk(child)
    walk(coords)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))

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
    bbox = coords_bbox(geom.get("coordinates"))
    if not bbox or not bbox_intersects(bbox, BAVARIA_BBOX):
        return None
    normalized = {
        "name": props.get("name") or props.get("title"),
        "period": props.get("period") or "roman",
        "certainty": props.get("certainty") or props.get("confidence") or props.get("status") or props.get("certaintyCategory") or "unspecified",
        "source": props.get("source") or "itiner-e",
        "source_ref": props.get("uri") or props.get("id") or props.get("identifier") or props.get("roadSectionId"),
        "all_properties": props,
    }
    return {"geometry": geom, "properties": normalized}

def discover_zenodo_geojson_url() -> str:
    api_url = f"https://zenodo.org/api/records/{ZENODO_RECORD_ID}"
    with urllib.request.urlopen(api_url, timeout=120) as resp:
        record = json.loads(resp.read().decode("utf-8"))
    files = record.get("files") or []
    for item in files:
        key = item.get("key") or ""
        if key.lower().endswith("itinere_roads.geojson"):
            return item["links"]["self"]
    for item in files:
        key = item.get("key") or ""
        if key.lower().endswith(".geojson"):
            return item["links"]["self"]
    raise RuntimeError("Could not find GeoJSON file in Zenodo record")

def download_geojson(url: str) -> Path:
    from datetime import datetime
    out_path = OUTPUT_DIR / f"itinere_roads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.geojson"
    req = urllib.request.Request(url, headers={"User-Agent": "surveyCatalyst/phase2-curated-itinere"})
    with urllib.request.urlopen(req, timeout=600) as resp, out_path.open("wb") as f:
        f.write(resp.read())
    return out_path

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
                        "itiner_e_curated",
                        str(feat["properties"].get("source_ref") or ""),
                    ),
                )
                inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted

def main(argv: list[str]) -> int:
    if len(argv) == 2:
        path = Path(argv[1]).resolve()
        if not path.exists():
            print(f"[ERROR] file not found: {path}")
            return 1
        count = load_geojson(path)
        print(f"[DONE] loaded {count} curated Roman-road features from local file into layer '{LAYER_KEY}'")
        return 0

    print("[INFO] discovering Itiner-e GeoJSON in Zenodo record 17122148")
    url = discover_zenodo_geojson_url()
    print(f"[INFO] downloading {url}")
    local_file = download_geojson(url)
    print(f"[INFO] downloaded to {local_file}")
    count = load_geojson(local_file)
    print(f"[DONE] loaded {count} curated Roman-road features from Itiner-e into layer '{LAYER_KEY}'")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
