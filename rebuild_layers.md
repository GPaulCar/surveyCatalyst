# Rebuild Layers (Single Root: surveyCatalyst)

Use only this root path:

```powershell
$ROOT="C:\Users\klenk\desktop\surveyCatalyst"
$PY="$ROOT\.surveyCatalyst_venv\Scripts\python.exe"
$GIT="$ROOT\tools\git\cmd\git.exe"
```

## 1) Git + release tag (same folder)

```powershell
$env:Path="$ROOT\tools\git\cmd;$env:Path"
& $GIT --version
& $GIT -C $ROOT status
& $GIT -C $ROOT remote -v
& $GIT -C $ROOT fetch --tags origin
& $GIT -C $ROOT checkout --detach deploy-2026-05-15
```

## 2) Core DB + registry

```powershell
& $PY $ROOT\scripts\run_migrations.py
& $PY $ROOT\scripts\import_layer_registry_master.py
```

## 3) Master registry load (Bavaria full extent, all records)

```powershell
& $PY $ROOT\scripts\load_master_registry_data.py run --bbox 8.95,47.20,13.95,50.65 --all-records --force --include-osm
```

## 4) Provider ingestions (all configured)

```powershell
& $PY $ROOT\scripts\run_ingestion_source.py blfd --force
& $PY $ROOT\scripts\run_ingestion_source.py itiner_e --force
& $PY $ROOT\scripts\run_ingestion_source.py viabundus --force
& $PY $ROOT\scripts\run_ingestion_source.py gesis --force
```

## 5) Special ingestions

```powershell
& $PY $ROOT\scripts\ingest_state_boundaries_de.py
& $PY $ROOT\scripts\ingest_hydrology_osm.py
& $PY $ROOT\scripts\ingest_historical_enrichment_osm.py
& $PY $ROOT\scripts\ingest_parcel_boundaries_osm.py
& $PY $ROOT\scripts\ingest_roman_roads_osm.py
& $PY $ROOT\scripts\restore_legal_restricted_layer.py
```

## 6) Bavaria DGM acquisition

```powershell
& $PY $ROOT\scripts\acquire_bavaria_dgm.py --product dgm1 --product dgm5
```

## 7) Derived/build layers

```powershell
& $PY $ROOT\scripts\build_bundle_hydrology_core.py
& $PY $ROOT\scripts\build_historical_enrichment_layers.py
& $PY $ROOT\scripts\build_hydrology_protection_layers.py
& $PY $ROOT\scripts\build_phase_3_parcel_permission.py
& $PY $ROOT\scripts\build_roman_roads_confidence.py
```

## 8) Optional manual GeoJSON layers (run only if you have files)

```powershell
& $PY $ROOT\scripts\load_field_names_geojson.py <path-to-field_names.geojson>
& $PY $ROOT\scripts\load_geonames_geojson.py <path-to-geonames.geojson>
& $PY $ROOT\scripts\load_old_creeks_geojson.py <path-to-old_creeks.geojson>
& $PY $ROOT\scripts\load_old_channels_geojson.py <path-to-old_channels.geojson>
& $PY $ROOT\scripts\load_wetland_history_geojson.py <path-to-wetland_history.geojson>
& $PY $ROOT\scripts\load_rivers_streams_geojson.py <path-to-rivers_streams.geojson>
& $PY $ROOT\scripts\load_waterbodies_geojson.py <path-to-waterbodies.geojson>
& $PY $ROOT\scripts\load_floodplains_geojson.py <path-to-floodplains.geojson>
& $PY $ROOT\scripts\load_parcel_boundaries_geojson.py <path-to-parcel_boundaries.geojson>
& $PY $ROOT\scripts\load_protection_buffers_geojson.py <path-to-protection_buffers.geojson>
& $PY $ROOT\scripts\load_roman_roads_curated.py <path-to-roman_roads_curated.geojson>
```

## 9) One-shot all-in pipeline alternative

```powershell
& $PY $ROOT\scripts\populate_all_layers.py --bbox 8.95,47.20,13.95,50.65 --all-records --force --include-osm
```

## 10) Verify + restart

```powershell
& $PY $ROOT\scripts\layer_counts.py
& $PY $ROOT\scripts\system_control.py restart
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
& $PY $ROOT\scripts\update_from_git.py --check-only
```
