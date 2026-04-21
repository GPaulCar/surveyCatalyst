# Restricted Areas refresh-loop fix

## Problem
Turning on the very large Restricted Areas layer caused repeated reruns and viewport resets.

## Cause
The app was writing the current map bounds back into Streamlit widget values on every rerun.

## Fix
- map state is stored separately from widget defaults
- current view is only captured when explicitly requested
- bbox inputs are no longer continuously rewritten from the map component

## Run
```powershell
python scripts/run_live_db_map.py
```

## Recommended settings
- Keep `Use bounding box filter` enabled
- Leave `Use current map view as bbox` off unless you need it
- Use `Capture current view` only when you want to update the bbox from the map
