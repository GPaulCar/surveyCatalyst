# Viewport stability fix

## What this fixes
- stops the live map from auto-zooming out on every rerun
- keeps the current viewport in Streamlit session state
- optionally uses the current map view as the active bbox filter

## Key change
The map only refits when you click:
- `Fit map to currently loaded data`

## Run
```powershell
python scripts/run_live_db_map.py
```

## Recommended settings
- Keep `Use bounding box filter` enabled
- Keep `Use current map view as bbox` enabled
- Pan/zoom the map to your area of interest
