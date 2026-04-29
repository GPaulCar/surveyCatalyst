# surveyCatalyst

surveyCatalyst is a Windows-first survey workflow app with a FastAPI backend, PostGIS storage, and an OpenLayers frontend.

## What matters

- Survey creation, selection, loading, zoom, editing, and export are wired through the API and the OpenLayers UI.
- Basemaps, layers, details, and survey object editing are all part of the same runtime.
- Local development depends on the bundled PostgreSQL runtime and `scripts/system_control.py`.

## Main runtime entry points

- `scripts/system_control.py` starts, stops, and checks the local Postgres + API stack.
- `scripts/run_api.py` launches the FastAPI app.
- `app/openlayers_map_shell.html` and `app/static/ui_boot.js` provide the frontend shell.
- `src/api/app.py` exposes the API.
- `src/survey/edit_service.py` handles survey and survey-object persistence.
- `src/map/live_db_map_service.py` serves live layer data.

## Running locally

```powershell
python scripts/system_control.py restart
```

Then open the local app URL served by the API.

## Desktop launcher

The desktop launcher was documented separately before the cleanup. The launcher workflow is still part of the project, but the notes now live here and in the design docs.

## Language support

The UI supports English and German, with the translation table in `app/static/ui_boot.js`.

## Documentation

Core workflow and stability notes:

- [Installation guide](INSTALLATION.md)
- [Survey workflow stability](docs/survey_workflow_stability.md)
- [FastAPI / OpenLayers migration notes](docs/fastapi_openlayers_migration.md)
- [Python environment setup](docs/python_environment_setup.md)

Selected historical notes and phase reports remain under `docs/` and `reports/`.

## Helper scripts archive

Root-level helper `.py` files that are not part of the live runtime have been moved into `zip/` to keep the repository root clean.
