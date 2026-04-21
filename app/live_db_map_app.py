from __future__ import annotations

import json
import sys
from pathlib import Path

import folium
import streamlit as st
from streamlit_folium import st_folium

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from map.live_db_map_service import LiveDBMapService


DEFAULT_BOUNDS = (10.5, 47.0, 13.8, 50.8)
DEFAULT_CENTER = [48.15, 11.55]
DEFAULT_ZOOM = 7
AGGREGATE_SURVEY_LAYER_KEYS = {"surveys", "survey_objects"}


def style_for_layer(layer_key: str, feature: dict | None = None):
    props = (feature or {}).get("properties") or {}
    feature_role = props.get("feature_role")

    if layer_key.startswith("legal_"):
        return {"color": "#b00020", "weight": 1, "fillColor": "#ffdde3", "fillOpacity": 0.25}
    if layer_key.startswith("economic_"):
        return {"color": "#1f77b4", "weight": 2, "fillColor": "#1f77b4", "fillOpacity": 0.70}
    if layer_key.startswith("ancient_"):
        return {"color": "#7b4f2a", "weight": 2}
    if layer_key.startswith("medieval_"):
        return {"color": "#355caa", "weight": 2}
    if layer_key.startswith("survey_") or layer_key == "surveys" or layer_key == "survey_objects":
        if feature_role == "survey_boundary":
            return {"color": "#0a8f55", "weight": 3, "fillColor": "#b8f5d1", "fillOpacity": 0.18}
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


def feature_bounds(data_by_layer: dict):
    coords = []
    for geojson in data_by_layer.values():
        for feature in geojson.get("features", []):
            geom = feature.get("geometry") or {}
            coords.extend(flatten_coords(geom.get("coordinates")))
    if not coords:
        return None
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]


def popup_title(layer_key: str, props: dict):
    feature_role = props.get("feature_role")
    if feature_role == "survey_boundary":
        title = props.get("title") or props.get("layer_key") or layer_key
        status = props.get("status")
        if status:
            return f"{title} ({status})"
        return title
    if feature_role == "survey_object":
        obj_type = props.get("type") or "survey_object"
        obj_id = props.get("id")
        if obj_id is not None:
            return f"{obj_type} #{obj_id}"
        return obj_type
    return layer_key


def add_point_feature(map_obj, feature, layer_key):
    geom = feature.get("geometry") or {}
    coords = geom.get("coordinates") or []
    if len(coords) != 2:
        return
    lon, lat = coords
    props = feature.get("properties") or {}
    popup_html = "<b>{}</b><br/><pre style='white-space: pre-wrap'>{}</pre>".format(
        popup_title(layer_key, props),
        json.dumps(props, ensure_ascii=False, indent=2),
    )
    style = style_for_layer(layer_key, feature)
    radius = 5 if props.get("feature_role") == "survey_object" else 4
    folium.CircleMarker(
        location=[lat, lon],
        radius=radius,
        color=style.get("color", "#666666"),
        fill=True,
        fill_opacity=0.8,
        popup=folium.Popup(popup_html, max_width=500),
    ).add_to(map_obj)


def render_map(data_by_layer: dict, selected_layers: dict[str, bool], center: list[float], zoom: int, refit: bool):
    map_obj = folium.Map(location=center, zoom_start=zoom, tiles="OpenStreetMap")

    if refit:
        bounds = feature_bounds(data_by_layer)
        if bounds:
            map_obj.fit_bounds(bounds)

    for layer_key, enabled in selected_layers.items():
        if not enabled:
            continue

        geojson = data_by_layer.get(layer_key, {"type": "FeatureCollection", "features": []})
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
                style_function=lambda f, lk=layer_key: style_for_layer(lk, f),
                highlight_function=lambda _feature: {"weight": 4},
                popup=folium.GeoJsonPopup(fields=[]),
            ).add_to(map_obj)

    folium.LayerControl().add_to(map_obj)
    return map_obj


def bounds_from_map_state(map_state):
    if not map_state:
        return None
    bounds = map_state.get("bounds")
    if not bounds:
        return None
    south = bounds.get("_southWest", {})
    north = bounds.get("_northEast", {})
    if not south or not north:
        return None
    return (
        float(south.get("lng")),
        float(south.get("lat")),
        float(north.get("lng")),
        float(north.get("lat")),
    )


def center_zoom_from_map_state(map_state):
    if not map_state:
        return None, None
    center = map_state.get("center") or {}
    zoom = map_state.get("zoom")
    if not center:
        return None, zoom
    lat = center.get("lat")
    lng = center.get("lng")
    if lat is None or lng is None:
        return None, zoom
    return [float(lat), float(lng)], zoom


def label_for_survey_row(row):
    layer_key, survey_id, title, status, expedition_id, is_visible, object_count, extent_geojson = row
    label_title = title or f"Survey {survey_id}"
    status_text = status or "unknown"
    return f"{label_title} [{layer_key}] ({status_text}, objects: {object_count})"


st.set_page_config(page_title="surveyCatalyst Live DB Map", layout="wide")
st.title("surveyCatalyst Live DB Map")

if "bbox_bounds" not in st.session_state:
    st.session_state.bbox_bounds = DEFAULT_BOUNDS
if "map_center" not in st.session_state:
    st.session_state.map_center = DEFAULT_CENTER
if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = DEFAULT_ZOOM
if "map_refit_once" not in st.session_state:
    st.session_state.map_refit_once = False
if "last_map_state" not in st.session_state:
    st.session_state.last_map_state = None
if "selected_survey_layer_keys" not in st.session_state:
    st.session_state.selected_survey_layer_keys = []
if "survey_focus_layer_key" not in st.session_state:
    st.session_state.survey_focus_layer_key = None

svc = LiveDBMapService()
layers = svc.list_layers()
survey_rows = svc.list_survey_layers()
survey_layer_keys = [row[0] for row in survey_rows]

if survey_rows and not st.session_state.selected_survey_layer_keys:
    default_selected = [row[0] for row in survey_rows if bool(row[5])][:3]
    st.session_state.selected_survey_layer_keys = default_selected
if survey_rows and st.session_state.survey_focus_layer_key not in survey_layer_keys:
    st.session_state.survey_focus_layer_key = survey_rows[0][0]

context_layers = [row for row in layers if row[2] != "survey"]
diagnostic_survey_layers = [row for row in layers if row[0] in AGGREGATE_SURVEY_LAYER_KEYS]

with st.sidebar:
    st.header("Layers")

    max_features = st.number_input("Max features per layer", min_value=100, max_value=20000, value=5000, step=100)

    st.divider()
    st.subheader("Bounding box filter")
    use_bbox = st.checkbox("Use bounding box filter", value=True)
    auto_use_current_view = st.checkbox("Use current map view as bbox", value=False)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Capture current view"):
            captured = bounds_from_map_state(st.session_state.last_map_state)
            if captured:
                st.session_state.bbox_bounds = captured
    with col2:
        if st.button("Fit to loaded data"):
            st.session_state.map_refit_once = True

    minx_default, miny_default, maxx_default, maxy_default = st.session_state.bbox_bounds
    minx = st.number_input("Min longitude", value=minx_default, format="%.6f", disabled=auto_use_current_view)
    miny = st.number_input("Min latitude", value=miny_default, format="%.6f", disabled=auto_use_current_view)
    maxx = st.number_input("Max longitude", value=maxx_default, format="%.6f", disabled=auto_use_current_view)
    maxy = st.number_input("Max latitude", value=maxy_default, format="%.6f", disabled=auto_use_current_view)

    st.divider()
    st.subheader("Surveys")

    survey_options = {label_for_survey_row(row): row[0] for row in survey_rows}
    selected_survey_labels = [label for label, key in survey_options.items() if key in st.session_state.selected_survey_layer_keys]
    chosen_labels = st.multiselect(
        "Visible surveys",
        options=list(survey_options.keys()),
        default=selected_survey_labels,
        key="visible_surveys_multiselect",
    )
    st.session_state.selected_survey_layer_keys = [survey_options[label] for label in chosen_labels]

    survey_button_col1, survey_button_col2 = st.columns(2)
    with survey_button_col1:
        if st.button("Select all surveys"):
            st.session_state.selected_survey_layer_keys = survey_layer_keys
            st.rerun()
    with survey_button_col2:
        if st.button("Clear surveys"):
            st.session_state.selected_survey_layer_keys = []
            st.rerun()

    focus_labels = {label_for_survey_row(row): row[0] for row in survey_rows}
    if focus_labels:
        focus_label_list = list(focus_labels.keys())
        current_focus_label = next(
            (label for label, key in focus_labels.items() if key == st.session_state.survey_focus_layer_key),
            focus_label_list[0],
        )
        selected_focus_label = st.selectbox(
            "Survey focus",
            options=focus_label_list,
            index=focus_label_list.index(current_focus_label),
        )
        st.session_state.survey_focus_layer_key = focus_labels[selected_focus_label]

        focus_col1, focus_col2 = st.columns(2)
        with focus_col1:
            if st.button("Show only focused survey"):
                st.session_state.selected_survey_layer_keys = [st.session_state.survey_focus_layer_key]
                st.rerun()
        with focus_col2:
            if st.button("Use focus extent as bbox"):
                focus_row = next((row for row in survey_rows if row[0] == st.session_state.survey_focus_layer_key), None)
                if focus_row and focus_row[7] and focus_row[7].get("coordinates"):
                    coords = flatten_coords(focus_row[7]["coordinates"])
                    if coords:
                        lons = [c[0] for c in coords]
                        lats = [c[1] for c in coords]
                        st.session_state.bbox_bounds = (min(lons), min(lats), max(lons), max(lats))
                        st.session_state.map_refit_once = True
                        st.rerun()

    st.divider()
    st.subheader("Context layers")
    context_groups = sorted({row[2] for row in context_layers})
    selected_groups = st.multiselect("Context groups", options=context_groups, default=context_groups)
    filtered_context_layers = [row for row in context_layers if row[2] in selected_groups]

    selected_layers = {layer_key: False for layer_key in survey_layer_keys}
    for row in filtered_context_layers:
        layer_key, layer_name, layer_group, source_table, geometry_type, is_visible, opacity, sort_order, metadata = row
        selected_layers[layer_key] = st.checkbox(
            f"{layer_name} [{layer_key}]",
            value=bool(is_visible),
            key=f"layer_{layer_key}",
        )

    for layer_key in st.session_state.selected_survey_layer_keys:
        selected_layers[layer_key] = True

    with st.expander("Diagnostics"):
        st.caption("Aggregate survey layers are hidden from the main working view.")
        for row in diagnostic_survey_layers:
            layer_key, layer_name, layer_group, source_table, geometry_type, is_visible, opacity, sort_order, metadata = row
            selected_layers[layer_key] = st.checkbox(
                f"{layer_name} [{layer_key}]",
                value=False,
                key=f"layer_{layer_key}",
            )

    st.divider()
    st.caption("Data source")
    st.code("Live Postgres/PostGIS via build_backend()")

if auto_use_current_view and st.session_state.last_map_state:
    captured = bounds_from_map_state(st.session_state.last_map_state)
    if captured:
        bounds = captured
    else:
        bounds = st.session_state.bbox_bounds if use_bbox else None
else:
    if use_bbox:
        st.session_state.bbox_bounds = (minx, miny, maxx, maxy)
        bounds = st.session_state.bbox_bounds
    else:
        bounds = None

data_by_layer = {}
for layer_key, enabled in selected_layers.items():
    if enabled:
        try:
            data_by_layer[layer_key] = svc.get_layer_geojson(layer_key, bounds=bounds, limit=int(max_features))
        except Exception as exc:
            data_by_layer[layer_key] = {"type": "FeatureCollection", "features": [], "_error": str(exc)}

left, right = st.columns([2, 1])

with left:
    if any(selected_layers.values()):
        map_obj = render_map(
            data_by_layer,
            selected_layers,
            center=st.session_state.map_center,
            zoom=st.session_state.map_zoom,
            refit=st.session_state.map_refit_once,
        )
        map_state = st_folium(map_obj, width=None, height=720, key="live_db_map")
        st.session_state.map_refit_once = False

        if map_state:
            st.session_state.last_map_state = map_state
            center, zoom = center_zoom_from_map_state(map_state)
            if center:
                st.session_state.map_center = center
            if zoom is not None:
                st.session_state.map_zoom = int(zoom)
    else:
        map_state = None
        st.info("Select at least one survey or context layer.")

with right:
    st.subheader("Layer summary")
    for layer_key, enabled in selected_layers.items():
        if enabled:
            feature_count = len((data_by_layer.get(layer_key) or {}).get("features", []))
            st.write(f"**{layer_key}** — {feature_count} loaded")
            if "_error" in data_by_layer.get(layer_key, {}):
                st.error(data_by_layer[layer_key]["_error"])

    st.divider()
    st.subheader("Active bounds")
    st.json({
        "use_bbox": use_bbox,
        "auto_use_current_view": auto_use_current_view,
        "bounds": bounds,
        "max_features_per_layer": int(max_features),
        "visible_surveys": st.session_state.selected_survey_layer_keys,
    })

    st.divider()
    st.subheader("Map click")
    if map_state and map_state.get("last_clicked"):
        st.json(map_state["last_clicked"])
    else:
        st.write("Click the map to inspect coordinates.")

    st.divider()
    st.subheader("Notes")
    st.write("Survey visibility is now managed per survey layer. Aggregate survey layers are hidden under Diagnostics.")
    st.write("Current view is not written back into bbox widgets on every rerun. Use Capture current view when needed.")
