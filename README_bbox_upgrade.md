# BBox loading upgrade

## What this fixes
Prevents the live DB map from trying to load entire very large layers, which caused JSON size limit errors.

## What changed
- `src/map/live_db_map_service.py`
  - adds `bounds` and `limit` support
  - bbox filters `external_features`, `surveys`, and `survey_objects`
- `app/live_db_map_app.py`
  - adds bounding box controls in the sidebar
  - adds per-layer feature cap
  - loads only visible subsets

## Run
```powershell
python scripts/run_live_db_map.py
```

## Suggested initial settings
- Keep `Use bounding box filter` enabled
- Start with `Max features per layer = 5000`
- Tighten the bbox to your immediate working area
