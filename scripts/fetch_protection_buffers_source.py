from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "workspace" / "downloads" / "curated" / "protection_buffers"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WFS_BASE = "https://www.lfu.bayern.de/gdi/wfs/natur/schutzgebiete?"
CAPS_URL = WFS_BASE + "service=WFS&request=GetCapabilities"

INCLUDE_TERMS = (
    "landschaftsschutz",
    "naturschutz",
    "naturpark",
    "nationalpark",
    "nationales naturmonument",
    "biosph",
    "ramsar",
    "ffh",
    "vogelschutz",
    "landschaftsbestandteil",
    "naturdenkmal",
)
EXCLUDE_TERMS = (
    "punkte",
    "point",
)

OUTPUT_FORMATS = [
    "application/json",
    "json",
    "geojson",
]

def fetch_bytes(url: str, data: bytes | None = None) -> bytes:
    req = urllib.request.Request(
        url,
        data=data,
        headers={"User-Agent": "surveyCatalyst/protection-pipeline"},
        method="POST" if data is not None else "GET",
    )
    last_error = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return resp.read()
        except Exception as exc:
            last_error = exc
            print(f"[WARN] request failed attempt {attempt}: {exc}")
            if attempt < 3:
                time.sleep(3 * attempt)
    raise last_error  # type: ignore[misc]

def fetch_text(url: str, data: bytes | None = None) -> str:
    return fetch_bytes(url, data=data).decode("utf-8", errors="replace")

def feature_types_from_capabilities(xml_text: str) -> list[dict[str, str]]:
    root = ET.fromstring(xml_text)
    items: list[dict[str, str]] = []

    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag != "FeatureType":
            continue

        name = ""
        title = ""
        for child in elem:
            child_tag = child.tag.split("}")[-1]
            if child_tag == "Name" and child.text:
                name = child.text.strip()
            elif child_tag == "Title" and child.text:
                title = child.text.strip()

        if name:
            items.append({"name": name, "title": title})

    return items

def wanted_feature_type(item: dict[str, str]) -> bool:
    hay = f"{item['name']} {item['title']}".lower()
    if any(term in hay for term in EXCLUDE_TERMS):
        return False
    return any(term in hay for term in INCLUDE_TERMS)

def save_debug_response(type_name: str, fmt: str, content: bytes, suffix: str) -> Path:
    safe_name = type_name.replace(":", "_")
    safe_fmt = fmt.replace("/", "_")
    path = OUT_DIR / f"{safe_name}_{safe_fmt}.{suffix}"
    path.write_bytes(content)
    return path

def try_parse_geojson(content: bytes) -> dict | None:
    text = content.decode("utf-8", errors="replace").strip()
    if not text:
        return None
    if not text.startswith("{"):
        return None
    try:
        data = json.loads(text)
    except Exception:
        return None
    if data.get("type") == "FeatureCollection":
        return data
    return None

def get_feature_geojson(type_name: str) -> dict:
    last_text = ""
    for fmt in OUTPUT_FORMATS:
        params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": type_name,
            "srsName": "EPSG:4326",
            "outputFormat": fmt,
        }
        url = WFS_BASE + urllib.parse.urlencode(params)
        content = fetch_bytes(url)

        parsed = try_parse_geojson(content)
        if parsed is not None:
            save_debug_response(type_name, fmt, content, "geojson")
            return parsed

        text = content.decode("utf-8", errors="replace")
        last_text = text
        save_debug_response(type_name, fmt, content, "txt")
        print(f"[WARN] non-JSON response for {type_name} using outputFormat={fmt}")

    preview = last_text[:800].strip()
    raise RuntimeError(f"Could not get GeoJSON for {type_name}. Last response preview:\n{preview}")

def normalise_feature(feature: dict, source_type: str) -> dict | None:
    geom = feature.get("geometry")
    if not geom:
        return None

    props = feature.get("properties") or {}
    merged_props = dict(props)
    merged_props["source"] = "lfu_bayern_wfs_schutzgebiete"
    merged_props["source_type_name"] = source_type

    src_id = (
        feature.get("id")
        or props.get("id")
        or props.get("kennung")
        or props.get("kennziffer")
        or props.get("name")
    )
    merged_props["source_id"] = str(src_id) if src_id is not None else None

    return {
        "type": "Feature",
        "geometry": geom,
        "properties": merged_props,
    }

def main() -> int:
    print("[INFO] fetching WFS capabilities")
    caps = fetch_text(CAPS_URL)
    capabilities_file = OUT_DIR / "schutzgebiete_capabilities.xml"
    capabilities_file.write_text(caps, encoding="utf-8")

    all_types = feature_types_from_capabilities(caps)
    selected_types = [item for item in all_types if wanted_feature_type(item)]

    if not selected_types:
        print("[ERROR] no matching protection feature types found in capabilities")
        return 1

    print("[INFO] selected feature types:")
    for item in selected_types:
        print(f"  - {item['name']} | {item['title']}")

    merged_features: list[dict] = []
    seen_ids: set[tuple[str, str]] = set()

    for item in selected_types:
        print(f"[INFO] downloading {item['name']}")
        fc = get_feature_geojson(item["name"])
        raw_file = OUT_DIR / f"{item['name'].replace(':', '_')}.geojson"
        raw_file.write_text(json.dumps(fc), encoding="utf-8")

        count_before = len(merged_features)
        for feat in fc.get("features") or []:
            norm = normalise_feature(feat, item["name"])
            if not norm:
                continue
            src_id = str((norm["properties"] or {}).get("source_id") or "")
            dedupe_key = (item["name"], src_id)
            if dedupe_key in seen_ids:
                continue
            seen_ids.add(dedupe_key)
            merged_features.append(norm)

        print(f"[DONE] {item['name']}: +{len(merged_features) - count_before} features")

    merged = {
        "type": "FeatureCollection",
        "features": merged_features,
    }

    merged_file = OUT_DIR / "protection_buffers_merged.geojson"
    merged_file.write_text(json.dumps(merged), encoding="utf-8")

    manifest = {
        "capabilities_file": str(capabilities_file),
        "merged_file": str(merged_file),
        "feature_type_count": len(selected_types),
        "feature_count": len(merged_features),
        "feature_types": selected_types,
    }
    manifest_file = OUT_DIR / "protection_buffers_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[DONE] merged GeoJSON written: {merged_file}")
    print(f"[DONE] feature count: {len(merged_features)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())