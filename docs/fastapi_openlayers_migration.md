# FastAPI + OpenLayers migration notes

## Current state

This path now splits the map workload into two delivery modes:

- surveys: bbox-bounded GeoJSON via `/api/surveys/{survey_id}/features`
- heavy context layers: vector tiles via `/api/layers/{layer_key}/tiles/{z}/{x}/{y}.mvt`

This removes the worst raw-GeoJSON bottleneck for large external layers such as BLfD restricted areas.

## Added endpoints

- `/api/context-layers`
- `/api/layers/{layer_key}/tiles/{z}/{x}/{y}.mvt`

## UI behaviour

- surveys remain the main working unit
- context layers are loaded independently as tile-backed overlays
- survey bbox limits and survey feature caps remain in place
- context layers no longer depend on one large JSON response per interaction

## Dependency note

This step depends on the earlier survey-layer refactor being present in `src/map/live_db_map_service.py`, specifically `get_survey_layer_geojson(...)`.

## Next step

The next delta should add:

- per-layer styling rules for vector tiles
- optional tile cache headers
- optional dedicated endpoints for known heavy layers such as legal restricted areas


## Survey export workflow

This step adds three survey export levels:

- layer export as GeoJSON
- data export as JSON with include/exclude controls
- printable HTML document export with optional embedded map image
