# Rebuild Layers (Line by Line)

Run from repo root.

```powershell
cd C:\Users\klenk\desktop\surveyCatalyst_repo
```

Use venv Python directly.

```powershell
$PY="C:\Users\klenk\desktop\surveyCatalyst_repo\.surveyCatalyst_venv\Scripts\python.exe"
```

## 1) Core DB + registry

```powershell
& $PY .\scripts\run_migrations.py
& $PY .\scripts\import_layer_registry_master.py
```

## 2) Master registry load (Bavaria full extent, all records)

```powershell
& $PY .\scripts\load_master_registry_data.py run --bbox 8.95,47.20,13.95,50.65 --all-records --force --include-osm
```

## 3) Provider ingestions (all configured)

```powershell
& $PY .\scripts\run_ingestion_source.py blfd --force
& $PY .\scripts\run_ingestion_source.py itiner_e --force
& $PY .\scripts\run_ingestion_source.py viabundus --force
& $PY .\scripts\run_ingestion_source.py gesis --force
```

## 4) Special ingestions

```powershell
& $PY .\scripts\ingest_state_boundaries_de.py
& $PY .\scripts\ingest_hydrology_osm.py
& $PY .\scripts\ingest_historical_enrichment_osm.py
& $PY .\scripts\ingest_parcel_boundaries_osm.py
& $PY .\scripts\ingest_roman_roads_osm.py
& $PY .\scripts\restore_legal_restricted_layer.py
```

## 5) Bavaria DGM acquisition

```powershell
& $PY .\scripts\acquire_bavaria_dgm.py --product dgm1 --product dgm5
```

## 6) Derived/build layers

```powershell
& $PY .\scripts\build_bundle_hydrology_core.py
& $PY .\scripts\build_historical_enrichment_layers.py
& $PY .\scripts\build_hydrology_protection_layers.py
& $PY .\scripts\build_phase_3_parcel_permission.py
& $PY .\scripts\build_roman_roads_confidence.py
```

## 7) Optional manual GeoJSON layers (run only if you have files)

```powershell
& $PY .\scripts\load_field_names_geojson.py <path-to-field_names.geojson>
& $PY .\scripts\load_geonames_geojson.py <path-to-geonames.geojson>
& $PY .\scripts\load_old_creeks_geojson.py <path-to-old_creeks.geojson>
& $PY .\scripts\load_old_channels_geojson.py <path-to-old_channels.geojson>
& $PY .\scripts\load_wetland_history_geojson.py <path-to-wetland_history.geojson>
& $PY .\scripts\load_rivers_streams_geojson.py <path-to-rivers_streams.geojson>
& $PY .\scripts\load_waterbodies_geojson.py <path-to-waterbodies.geojson>
& $PY .\scripts\load_floodplains_geojson.py <path-to-floodplains.geojson>
& $PY .\scripts\load_parcel_boundaries_geojson.py <path-to-parcel_boundaries.geojson>
& $PY .\scripts\load_protection_buffers_geojson.py <path-to-protection_buffers.geojson>
& $PY .\scripts\load_roman_roads_curated.py <path-to-roman_roads_curated.geojson>
```

## 8) One-shot all-in pipeline alternative

```powershell
& $PY .\scripts\populate_all_layers.py --bbox 8.95,47.20,13.95,50.65 --all-records --force --include-osm
```

## 9) Verify loaded layer counts

```powershell
& $PY .\scripts\layer_counts.py
```

## 10) Start services

```powershell
& $PY .\scripts\system_control.py restart
```
