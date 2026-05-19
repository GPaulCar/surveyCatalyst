$ROOT="C:\Users\Paul\Desktop\dev\surveyCatalyst"
$PY="$ROOT\.surveyCatalyst_venv\Scripts\python.exe"

git -C $ROOT fetch --tags origin
git -C $ROOT checkout --detach deploy-2026-05-16
git -C $ROOT reset --hard deploy-2026-05-16
git -C $ROOT clean -fd

& $PY "$ROOT\assessment\scripts\run_assessment_block.py" --dotenv "$ROOT\assessment\.env.example"

& $PY "$ROOT\assessment\scripts\apply_approved_fixes.py" --dry-run
& $PY "$ROOT\assessment\scripts\apply_approved_fixes.py"
& $PY "$ROOT\assessment\scripts\validate_and_monitor.py"

& $PY "$ROOT\scripts\run_migrations.py"
& $PY "$ROOT\scripts\import_layer_registry_master.py"
& $PY "$ROOT\scripts\load_master_registry_data.py" run --bbox 8.95,47.20,13.95,50.65 --all-records --force --include-osm

& $PY "$ROOT\scripts\run_ingestion_source.py" blfd --force
& $PY "$ROOT\scripts\run_ingestion_source.py" itiner_e --force
& $PY "$ROOT\scripts\run_ingestion_source.py" viabundus --force
& $PY "$ROOT\scripts\run_ingestion_source.py" gesis --force

& $PY "$ROOT\scripts\ingest_state_boundaries_de.py"
& $PY "$ROOT\scripts\ingest_hydrology_osm.py"
& $PY "$ROOT\scripts\ingest_historical_enrichment_osm.py"
& $PY "$ROOT\scripts\ingest_parcel_boundaries_osm.py"
& $PY "$ROOT\scripts\ingest_roman_roads_osm.py"
& $PY "$ROOT\scripts\restore_legal_restricted_layer.py"

& $PY "$ROOT\scripts\build_bundle_hydrology_core.py"
& $PY "$ROOT\scripts\build_historical_enrichment_layers.py"
& $PY "$ROOT\scripts\build_hydrology_protection_layers.py"
& $PY "$ROOT\scripts\build_phase_3_parcel_permission.py"
& $PY "$ROOT\scripts\build_roman_roads_confidence.py"

& $PY "$ROOT\scripts\layer_counts.py"
& $PY "$ROOT\scripts\system_control.py" restart
Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
