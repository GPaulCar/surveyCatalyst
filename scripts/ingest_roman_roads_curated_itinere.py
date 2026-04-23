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

# Bavaria bbox (EPSG:4326)
BAVARIA_WEST = 8.95
BAVARIA_SOUTH = 47.20
BAVARIA_EAST = 13.95
BAVARIA_NORTH = 50.65

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
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
        """,
        (
            LAYER_KEY,
            "Roman roads (curated)",
            json.dumps({
                "subgroup": "historical",
                "phase": "phase_2",
                "source": "itiner-e"
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
        raise ValueError("Invalid GeoJSON")


def discover_url() -> str:
    api_url = f"https://zenodo.org/api/records/{ZENODO_RECORD_ID}"
    with urllib.request.urlopen(api_url, timeout=120) as resp:
        record = json.loads(resp.read().decode("utf-8"))

    for f in record.get("files", []):
        if f["key"].lower().endswith(".geojson"):
            return f["links"]["self"]

    raise RuntimeError("No GeoJSON found in Zenodo record")


def download_geojson(url: str) -> Path:
    from datetime import datetime

    out = OUTPUT_DIR / f"itinere_{datetime.now().strftime('%Y%m%d_%H%M%S')}.geojson"

    req = urllib.request.Request(url, headers={"User-Agent": "surveyCatalyst"})
    with urllib.request.urlopen(req, timeout=600) as resp, out.open("wb") as f:
        f.write(resp.read())

    return out


def normalize_props(p: dict) -> dict:
    p = p or {}
    return {
        "name": p.get("name") or p.get("title"),
        "certainty": p.get("certainty") or p.get("confidence") or "unknown",
        "source": "itiner-e",
        "source_ref": p.get("id") or p.get("uri"),
        "raw": p
    }


def load_geojson(path: Path) -> int:
    doc = json.loads(path.read_text(encoding="utf-8"))

    backend = build_backend()
    conn = backend.connect()

    total = 0
    inserted = 0

    try:
        with conn.cursor() as cur:
            ensure_registry(cur)

            cur.execute("DELETE FROM external_features WHERE layer = %s", (LAYER_KEY,))

            for f in iter_features(doc):
                total += 1

                geom = f.get("geometry")
                if not geom:
                    continue

                gtype = geom.get("type")
                if gtype not in ("LineString", "MultiLineString"):
                    continue

                props = normalize_props(f.get("properties"))

                # ---- FIX: FORCE 2D ----
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
                        "itiner_e",
                        str(props.get("source_ref") or total),
                    ),
                )

                inserted += 1

            print(f"[INFO] total features: {total}")
            print(f"[INFO] inserted before clip: {inserted}")

            # Bavaria clip (done in DB, safe)
            cur.execute(
                """
                DELETE FROM external_features
                WHERE layer = %s
                AND NOT ST_Intersects(
                    geom,
                    ST_MakeEnvelope(%s, %s, %s, %s, 4326)
                )
                """,
                (LAYER_KEY, BAVARIA_WEST, BAVARIA_SOUTH, BAVARIA_EAST, BAVARIA_NORTH),
            )

            cur.execute(
                "SELECT COUNT(*) FROM external_features WHERE layer = %s",
                (LAYER_KEY,),
            )
            kept = cur.fetchone()[0]

        conn.commit()

    finally:
        conn.close()

    print(f"[INFO] kept after Bavaria clip: {kept}")
    return kept


def main(argv):
    if len(argv) == 2:
        path = Path(argv[1])
        return load_geojson(path)

    print("[INFO] downloading Itiner-e dataset")
    url = discover_url()
    file = download_geojson(url)

    print(f"[INFO] saved to {file}")
    return load_geojson(file)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))