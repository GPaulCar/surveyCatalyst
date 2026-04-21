# surveyCatalyst live DB map

## What it does
- reads layers directly from Postgres/PostGIS
- uses `layers_registry`, `external_features`, `surveys`, and `survey_objects`
- shows layer toggles and feature counts
- renders context layers and surveys without exporting GeoJSON first

## Install
```powershell
pip install -r requirements-live-db-map.txt
```

## Run
```powershell
python scripts/run_live_db_map.py
```

## Requirements
- working `.surveyCatalyst_venv`
- imports resolved for `src`
- PostgreSQL/PostGIS running
- project DB populated enough to render data
