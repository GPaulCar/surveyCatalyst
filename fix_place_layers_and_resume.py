from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path.cwd()
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

RAW_DIR = ROOT / "workspace" / "downloads" / "raw" / "osm" / "place_layers_fix"
RAW_DIR.mkdir(parents=True, exist_ok=True)

ENDPOINTS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

QUERIES = {
    "field_names": {
        "source_table": "osm_place_layers_fix",
        "query": """
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  node["place"~"locality|hamlet|isolated_dwelling|farm"](area.searchArea);
  node["name"]["place"](area.searchArea);
);
out body;
"""
    },
    "geonames_points": {
        "source_table": "osm_place_layers_fix",
        "query": """
[out:json][timeout:300];
area["ISO3166-2"="DE-BY"][admin_level=4]->.searchArea;
(
  node["place"](area.searchArea);
  node["natural"~"peak|hill"](area.searchArea);
  node["tourism"](area.searchArea);
  node["historic"](area.searchArea);
);
out body;
"""
    },
}

def fetch(layer: str, query: str) -> dict:
    payload = urllib.parse.urlencode({"data": query}).encode("utf-8")
    last_error = None

    for attempt in range(1, 7):
        endpoint = ENDPOINTS[(attempt - 1) % len(ENDPOINTS)]
        wait = 8 * attempt

        req = urllib.request.Request(
            endpoint,
            data=payload,
            headers={"User-Agent": "surveyCatalyst/place-layer-fix"},
            method="POST",
        )

        try:
            print(f"[FETCH] {layer} attempt={attempt} endpoint={endpoint}")
            with urllib.request.urlopen(req, timeout=600) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            out = RAW_DIR / f"{layer}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            out.write_text(json.dumps(data), encoding="utf-8")
            print(f"[OK] raw saved {out}")
            return data

        except Exception as exc:
            last_error = exc
            print(f"[WARN] {layer} failed: {exc}; waiting {wait}s")
            time.sleep(wait)

    raise RuntimeError(f"{layer} failed after retries: {last_error}")

def register_layers() -> None:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            specs = [
                ("field_names", "Field names", "POINT", 340, "place_names"),
                ("geonames_points", "GeoNames / place points", "POINT", 341, "place_names"),
            ]
            for key, name, geom_type, order, subgroup in specs:
                cur.execute(
                    """
                    INSERT INTO layers_registry (
                        layer_key, layer_name, layer_group, source_table, geometry_type,
                        is_user_selectable, is_visible, opacity, sort_order, metadata
                    )
                    VALUES (%s, %s, 'context', 'external_features', %s, TRUE, FALSE, 1.0, %s, %s::jsonb)
                    ON CONFLICT (layer_key) DO UPDATE
                    SET layer_name = EXCLUDED.layer_name,
                        geometry_type = EXCLUDED.geometry_type,
                        sort_order = EXCLUDED.sort_order,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    (
                        key,
                        name,
                        geom_type,
                        order,
                        json.dumps({
                            "subgroup": subgroup,
                            "coverage": "bavaria_admin_area_DE_BY",
                            "repair": "place_layers_out_body_fix",
                        }),
                    ),
                )
        conn.commit()
    finally:
        conn.close()

def load_layer(layer: str, source_table: str, data: dict) -> int:
    backend = build_backend()
    conn = backend.connect()
    loaded = 0

    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM external_features WHERE layer = %s", (layer,))

            seen = set()
            for el in data.get("elements", []):
                if el.get("type") != "node":
                    continue
                if "lat" not in el or "lon" not in el:
                    continue

                key = (el.get("type"), el.get("id"))
                if key in seen:
                    continue
                seen.add(key)

                tags = el.get("tags") or {}
                props = {
                    "name": tags.get("name"),
                    "place": tags.get("place"),
                    "natural": tags.get("natural"),
                    "tourism": tags.get("tourism"),
                    "historic": tags.get("historic"),
                    "source": "osm_place_layers_fix",
                    "osm_type": el.get("type"),
                    "osm_id": el.get("id"),
                    "all_tags": tags,
                }

                cur.execute(
                    """
                    INSERT INTO external_features (layer, geom, properties, source_table, source_id)
                    VALUES (
                        %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        %s::jsonb,
                        %s,
                        %s
                    )
                    """,
                    (
                        layer,
                        el["lon"],
                        el["lat"],
                        json.dumps(props),
                        source_table,
                        str(el.get("id")),
                    ),
                )
                loaded += 1

        conn.commit()
    finally:
        conn.close()

    return loaded

def counts() -> dict[str, int]:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT layer, COUNT(*) FROM external_features GROUP BY layer ORDER BY layer")
            return {str(layer): int(count) for layer, count in cur.fetchall()}
    finally:
        conn.close()

def run(cmd: list[str], required: bool = True) -> None:
    print("[RUN] " + " ".join(str(x) for x in cmd))
    result = subprocess.run(cmd, cwd=ROOT)
    if required and result.returncode != 0:
        raise SystemExit(result.returncode)

def main() -> None:
    print("[1/6] register place layers")
    register_layers()

    print("[2/6] fetch + load place layers")
    for layer, spec in QUERIES.items():
        data = fetch(layer, spec["query"])
        loaded = load_layer(layer, spec["source_table"], data)
        print(f"[DONE] {layer}: loaded={loaded}")
        if loaded <= 0:
            raise SystemExit(f"[FAIL] {layer} loaded zero rows")

    print("[3/6] data quality pass")
    run([sys.executable, "scripts/data_quality_pass.py"])

    print("[4/6] verify counts")
    c = counts()
    for layer in sorted(c):
        print(f"{layer}: {c[layer]}")

    for required in ["field_names", "geonames_points"]:
        if c.get(required, 0) <= 0:
            raise SystemExit(f"[FAIL] {required} missing after repair")

    print("[5/6] restart")
    run([sys.executable, "scripts/system_control.py", "restart"])

    print("[6/6] checkpoint")
    if (ROOT / "apply_checkpoint_bundle.py").exists():
        run([sys.executable, "apply_checkpoint_bundle.py", "place-layers-fix-stage1", "--no-push"], required=False)

    print("[PHASE COMPLETE]")
    print("field_names and geonames_points populated")

if __name__ == "__main__":
    main()