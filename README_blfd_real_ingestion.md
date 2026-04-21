# BLfD real ingestion upgrade

## What this package does
- upgrades the BLfD provider from endpoint-only registration to actual WFS ingestion
- loads features into `legal.restricted_areas`
- projects them into `external_features`
- keeps `legal_restricted_areas` renderable in the live map

## Install
```powershell
pip install -r requirements-blfd.txt
```

## First try
```powershell
python scripts/run_blfd_ingestion.py
```

## If the default typename fails
Fetch capabilities and inspect the available feature type names:

```powershell
python scripts/check_blfd_typename.py
```

Then rerun with an explicit typename:

```powershell
python scripts/run_blfd_ingestion.py <typename>
```

## Verify
```powershell
python scripts/test_blfd_ingestion.py
python scripts/run_live_db_map.py
```
