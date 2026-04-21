# surveyCatalyst minimal map app

## What it does
- reads exported GeoJSON layers from `exports_full`
- shows them on a map
- provides layer toggles
- shows click coordinates and per-layer feature counts

## Install
```powershell
pip install -r requirements-map-ui.txt
```

## Export data first
```powershell
python scripts/export_all_layers.py
```

## Run app
```powershell
python -m streamlit run app/map_app.py
```

or:

```powershell
.\scripts\run_map_app.ps1
```

## Notes
This app is intentionally minimal. It visualises the pipeline output you already generated rather than replacing the database-backed application logic.
