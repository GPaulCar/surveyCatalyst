from __future__ import annotations

import json
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium


ROOT = Path(__file__).resolve().parent.parent
EXPORT_DIR = ROOT / "exports_full"


def load_geojson_files(export_dir: Path):
    export_dir.mkdir(parents=True, exist_ok=True)
    data = {}
    for path in sorted(export_dir.glob("*.geojson")):
        try:
            data[path.stem] = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            data[path.stem] = {
                "type": "FeatureCollection",
                "features": [],
                "_error": str(exc),
            }
    return data


def style_for_layer(layer_key: str):
    if layer_key.startswith("legal_"):
        return {"color": "#b00020", "weight": 2, "fillColor": "#ffdde3", "fillOpacity": 0.45}
    if layer_key.startswith("economic_"):
        return {"color": "#1f77b4", "weight": 2, "fillColor": "#1f77b4", "fillOpacity": 0.7}
    if layer_key.startswith("ancient_"):
        return {"color": "#7b4f2a", "weight": 2}
    if layer_key.startswith("medieval_"):
        return {"color": "#355caa", "weight": 2}
    if layer_key.startswith("survey_") or layer_key == "surveys":
        return {"color": "#0a8f55", "weight": 2, "fillColor": "#b8f5d1", "fillOpacity": 0.35}
    return {"color": "#666666", "weight": 1}


def flatten_coords(coords):
    out = []
    if isinstance(coords, (list, tuple)):
        if len(coords) == 2 and all(isinstance(x, (int, float)) for x in coords):
            out.append(coords)
        else:
            for item in coords:
                out.extend(flatten_coords(item))
    return out


def feature_bounds(all_data: dict):
    coords = []
    for geojson in all_data.values():
        for feature in geojson.get("features", []):
            geom = feature.get("geometry") or {}
            coords.extend(flatten_coords(geom.get("coordinates")))
    if not coords:
        return None
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]


def feature_summary(feature: dict):
    props = feature.get("properties") or {}
    geom = feature.get("geometry") or {}
    return {
        "geometry_type": geom.get("type"),
        "properties": props,
    }


def add_point_feature(map_obj, feature, layer_key):
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates") or []
    if len(coords) != 2:
        return
    lon, lat = coords
    props = feature.get("properties") or {}
    popup_html = f"<b>{layer_key}</b><br/>{json.dumps(props, ensure_ascii=False)}"
    folium.CircleMarker(
        location=[lat, lon],
        radius=6,
        color=style_for_layer(layer_key).get("color", "#666666"),
        fill=True,
        fill_opacity=0.8,
        popup=folium.Popup(popup_html, max_width=400),
    ).add_to(map_obj)


def make_map(selected_layers: dict[str, bool], data: dict):
    map_obj = folium.Map(location=[48.15, 11.55], zoom_start=8, tiles="OpenStreetMap")

    visible_data = {k: v for k, v in data.items() if selected_layers.get(k)}
    bounds = feature_bounds(visible_data)
    if bounds:
        map_obj.fit_bounds(bounds)

    for layer_key, enabled in selected_layers.items():
        if not enabled:
            continue

        geojson = data.get(layer_key, {"type": "FeatureCollection", "features": []})
        style = style_for_layer(layer_key)

        non_points = {"type": "FeatureCollection", "features": []}
        for feature in geojson.get("features", []):
            geom_type = (feature.get("geometry") or {}).get("type")
            if geom_type == "Point":
                add_point_feature(map_obj, feature, layer_key)
            else:
                non_points["features"].append(feature)

        if non_points["features"]:
            folium.GeoJson(
                non_points,
                name=layer_key,
                style_function=lambda _feature, s=style: s,
                highlight_function=lambda _feature: {"weight": 4},
            ).add_to(map_obj)

    folium.LayerControl().add_to(map_obj)
    return map_obj


st.set_page_config(page_title="surveyCatalyst Map", layout="wide")
st.title("surveyCatalyst Map")

data = load_geojson_files(EXPORT_DIR)

with st.sidebar:
    st.header("Layers")
    if not data:
        st.info("No GeoJSON exports found in exports_full.")
    selected_layers = {}
    for layer_key in data:
        selected_layers[layer_key] = st.checkbox(layer_key, value=True)

    st.divider()
    st.caption("Expected export folder")
    st.code(str(EXPORT_DIR))

left, right = st.columns([2, 1])

with left:
    if data:
        fmap = make_map(selected_layers, data)
        map_state = st_folium(fmap, width=None, height=700)
    else:
        map_state = None
        st.warning("No exported layers found. Run the export script first.")

with right:
    st.subheader("Layer summary")
    for layer_key, geojson in data.items():
        st.write(f"**{layer_key}** — {len(geojson.get('features', []))} features")
        if "_error" in geojson:
            st.error(geojson["_error"])

    st.divider()
    st.subheader("Map click")
    if map_state and map_state.get("last_clicked"):
        st.json(map_state["last_clicked"])
    else:
        st.write("Click the map to inspect coordinates.")

    st.divider()
    st.subheader("Visible layers")
    st.write([k for k, v in selected_layers.items() if v])

    st.divider()
    st.subheader("How to refresh data")
    st.write("Re-export layers into the exports_full folder, then refresh this page.")
