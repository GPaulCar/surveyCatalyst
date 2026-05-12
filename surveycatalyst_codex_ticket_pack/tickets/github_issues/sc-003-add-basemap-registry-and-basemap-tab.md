---
id: SC-003
title: Add basemap registry and Basemap tab
priority: High
labels: frontend,basemaps,openlayers
---

# SC-003 - Add basemap registry and Basemap tab

**Priority:** High
**Labels:** frontend,basemaps,openlayers

## Goal
Add selectable basemap options without affecting survey overlays or layer rendering.

## Scope
File:
- `app/static/ui_boot.js`

## Basemap options
- `osm`: `https://{a-c}.tile.openstreetmap.org/{z}/{x}/{y}.png`
- `esri_world_imagery`: `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`
- `esri_world_topo`: `https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}`
- `esri_world_streets`: `https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}`
- `carto_light`: `https://{a-c}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png`
- `carto_dark`: `https://{a-c}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png`

## Tasks
- Add `state.activeBasemap`.
- Create `BASEMAPS`, `createBasemapSource(key)`, and `setBasemap(key)`.
- Initialise one `baseLayer` as first/bottom layer.
- Add right tab `{ id: "basemap", title: "Basemap" }`.
- Add `basemapBody()` and route `rightBody()` for `basemap`.
- Do not duplicate base layers.
- Do not reset map view when switching.
- Ensure overlays remain above basemap.

## Validation
- All basemaps display.
- Switching basemap does not remove survey layers.
- No syntax errors.
