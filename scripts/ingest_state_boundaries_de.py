from __future__ import annotations

import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend

LAYER_KEY = "state_boundaries_de"
SOURCE_URL = "https://raw.githubusercontent.com/isellsoap/deutschlandGeoJSON/master/2_bundeslaender/4_niedrig.geo.json"
RAW_DIR = ROOT / "workspace" / "downloads" / "raw" / "osm"
RAW_DIR.mkdir(parents=True, exist_ok=True)

STATE_NAME_MAP = {
    "bayern": "de_by",
    "baden-württemberg": "de_bw",
    "hessen": "de_he",
    "thüringen": "de_th",
    "thueringen": "de_th",
    "sachsen": "de_sn",
}

TARGET_STATES = {"de_by", "de_bw", "de_he", "de_th", "de_sn"}


def fetch_overpass(retries: int = 7, base_delay: float = 3.0) -> dict:
    from datetime import datetime

    req = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "surveyCatalyst/state-boundaries"},
        method="GET",
    )
    payload = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            status = getattr(exc, "code", None)
            retryable = status in (429, 500, 502, 503, 504)
            if attempt >= retries or not retryable:
                raise
            delay = base_delay * (2 ** (attempt - 1))
            print(f"[RETRY] state boundaries status={status} attempt={attempt}/{retries} delay={delay:.1f}s", flush=True)
            time.sleep(delay)
    if payload is None:
        raise RuntimeError("failed to fetch state boundaries from overpass")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RAW_DIR / f"state_boundaries_de_{stamp}.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    print(f"[INFO] raw download saved to {out}", flush=True)
    return payload


def normalize_state(name: str) -> str:
    text = (name or "").strip().lower()
    if "bayern" in text or "bavaria" in text:
        return "de_by"
    if "baden" in text:
        return "de_bw"
    if "hessen" in text or "hesse" in text:
        return "de_he"
    if "thüringen" in text or "thueringen" in text or "thuringia" in text:
        return "de_th"
    if "sachsen" in text or "saxony" in text:
        return "de_sn"
    return STATE_NAME_MAP.get(text, "")


def source_feature_to_feature(element: dict) -> dict | None:
    if element.get("type") != "Feature":
        return None
    props = element.get("properties") or {}
    state_id = normalize_state(props.get("name", ""))
    if not state_id:
        state_id = normalize_state(props.get("NAME_1", ""))
    if not state_id:
        return None
    if state_id not in TARGET_STATES:
        return None
    geometry = element.get("geometry")
    if not geometry:
        return None
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "state_id": state_id,
            "name": props.get("name") or props.get("NAME_1"),
            "admin_level": "4",
            "source": "deutschland_geojson_states",
            "source_id": str(props.get("id") or props.get("AGS_1") or ""),
            "all_tags": props,
        },
    }


def ensure_registry(cur) -> None:
    cur.execute(
        """
        INSERT INTO layers_registry (
            layer_key, layer_name, layer_group, source_table, geometry_type,
            is_user_selectable, is_visible, opacity, sort_order, metadata
        )
        VALUES (
            %s, %s, 'context', 'external_features', 'MULTIPOLYGON',
            TRUE, TRUE, 1.0, 30, %s::jsonb
        )
        ON CONFLICT (layer_key) DO UPDATE
        SET layer_name = EXCLUDED.layer_name,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
        """,
        (
            LAYER_KEY,
            "State boundaries (Bavaria region)",
            json.dumps({"subgroup": "reference", "description": "Administrative state boundaries around Bavaria"}),
        ),
    )


def load_features(features: list[dict]) -> int:
    backend = build_backend()
    conn = backend.connect()
    inserted = 0
    try:
        with conn.cursor() as cur:
            ensure_registry(cur)
            cur.execute("DELETE FROM external_features WHERE layer = %s", (LAYER_KEY,))
            for feat in features:
                props = feat["properties"]
                cur.execute(
                    """
                    INSERT INTO external_features (layer, geom, properties, source_table, source_id)
                    VALUES (
                        %s,
                        ST_Multi(ST_Force2D(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))),
                        %s::jsonb,
                        %s,
                        %s
                    )
                    """,
                    (
                        LAYER_KEY,
                        json.dumps(feat["geometry"]),
                        json.dumps(props),
                        "de_state_boundaries",
                        str(props.get("source_id") or ""),
                    ),
                )
                inserted += 1
        conn.commit()
    finally:
        conn.close()
    return inserted


def main() -> int:
    print("[INFO] downloading state boundaries for Bavaria + neighboring states")
    raw = fetch_overpass()
    elements = raw.get("features") or []
    features = []
    for element in elements:
        feature = source_feature_to_feature(element)
        if feature:
            features.append(feature)
    print(f"[INFO] parsed state boundaries: {len(features)}", flush=True)
    inserted = load_features(features)
    print(f"[DONE] loaded {inserted} state boundaries into layer '{LAYER_KEY}'", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
