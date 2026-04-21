# surveyCatalyst FastAPI + OpenLayers migration

This package adds a survey-centric API and browser map path on top of the existing PostGIS-backed services.

## Current state

- FastAPI serves the browser map shell
- OpenLayers manages viewport and interaction state in the browser
- `/api/surveys` returns lightweight survey metadata without geometry
- `/api/surveys/{survey_id}/features` returns bounded GeoJSON for the selected survey using bbox filtering
- generic `/api/layers/{layer_key}/geojson` remains available for context layers and diagnostics

## Why this step exists

The previous Streamlit map shell reran app state too aggressively for a spatial workload. This step moves the operational map path to:

- browser-owned viewport state
- bounded API requests
- survey-driven loading instead of generic layer-driven loading

## Run

```powershell
pip install -r requirements-api.txt
python scripts/run_api.py
```

Open:

```text
http://127.0.0.1:8000/
```

## Important dependency

The survey feature endpoint expects `LiveDBMapService` to already support:

- `get_survey_layer_geojson(layer_key, bounds=None, limit=5000)`

That method comes from the earlier survey-layer refactor. If it is not present in the repo yet, apply that delta first.

## Next architectural step

Once this survey-centric path is validated locally, the next delta should move heavy context layers such as BLfD restricted areas away from raw GeoJSON and toward PostGIS-backed vector tiles.
