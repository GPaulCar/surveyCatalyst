# surveyCatalyst FastAPI + OpenLayers migration starter

This package adds a runnable API and a browser-native map prototype on top of the current PostGIS-backed codebase.

## Why this is the next step

The current bottleneck is the UI execution model, not the spatial database design.

The repo already has usable service boundaries for:

- Postgres/PostGIS connection management
- layer registry access
- survey querying
- live DB layer GeoJSON retrieval
- ingestion/orchestration

This starter reuses those existing services and inserts an API layer in front of them.

## Added files

- `src/api/app.py`
- `src/api/schemas.py`
- `src/api/__init__.py`
- `app/openlayers_map.html`
- `scripts/run_api.py`
- `requirements-api.txt`

## What is runnable now

### API

Routes:

- `/health`
- `/api`
- `/api/layers`
- `/api/surveys`
- `/api/surveys/{survey_id}`
- `/api/layers/{layer_key}/geojson?bbox=minx,miny,maxx,maxy&limit=5000`

### Map prototype

The root route `/` serves a simple OpenLayers client that:

- lists available layers from the live registry
- requests selected layers from the API
- applies bbox and limit controls
- renders vector data directly in the browser
- shows clicked feature properties

This is intentionally additive. It does not remove the Streamlit app yet.

## Install

Activate your existing environment, then install the API dependencies:

```powershell
pip install -r requirements-api.txt
```

## Run

```powershell
python scripts/run_api.py
```

Open:

```text
http://127.0.0.1:8000/
```

## Immediate advantages over the current map shell

- browser owns viewport state
- API requests are bounded by bbox and limit
- no full-script rerun on every interaction
- map and data concerns are separated
- existing PostGIS service code remains in use

## Next migration step

The next technical step should be to add a dedicated survey-layer endpoint that returns:

- survey boundary
- survey objects

in one payload for `survey_*` layers, aligned with the survey-layer refactor already discussed.

After that, the next high-value improvement is tile or vector-tile serving for heavy legal layers such as BLfD restricted areas.
