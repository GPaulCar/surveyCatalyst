# Repo Cleanup Archive Workflow

Use this to keep a lean runtime repo while preserving build/ingestion artifacts.

## 1) Create archive bundles (non-destructive)

```powershell
.\.surveyCatalyst_venv\Scripts\python.exe .\scripts\archive_repo_build_inputs.py
```

Outputs are written to:

- `zip/archive/maintenance_scripts_<timestamp>.zip`
- `zip/archive/source_datasets_<timestamp>.zip`
- `zip/archive/archive_manifest_<timestamp>.json`

## 2) Optional prune after archive verification

Only run after verifying archive ZIP contents and checksums.

```powershell
.\.surveyCatalyst_venv\Scripts\python.exe .\scripts\archive_repo_build_inputs.py --prune
```

`--prune` removes archived source files from:

- `scripts/` (maintenance/build scripts, runtime script allowlist is kept)
- `workspace/downloads/raw`
- `workspace/downloads/curated`
- `workspace/osm_ingest_engine/raw`
- `workspace/data_gaps_field_names_geonames/raw`
- `downloads/`
- `exports_full/`

## 3) Runtime-only operation

After `git pull` on the target system, purge to runtime-only:

```powershell
.\.surveyCatalyst_venv\Scripts\python.exe .\scripts\purge_repo_to_runtime.py --yes
```

For runtime operations after cleanup:

```powershell
.\.surveyCatalyst_venv\Scripts\python.exe .\scripts\run_ops_cycle.py --skip-ingest
```

For full rebuild-capable cycle (requires ingest/build assets retained):

```powershell
.\.surveyCatalyst_venv\Scripts\python.exe .\scripts\run_ops_cycle.py
```
