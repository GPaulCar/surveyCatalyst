---
id: SC-006
title: Implement automatic layer ingestion router
priority: High
labels: data,ingestion,backend
---

# SC-006 - Implement automatic layer ingestion router

**Priority:** High
**Labels:** data,ingestion,backend

## Goal
Route layer registry rows to appropriate ingestion or external tile registration behaviour.

## Scope
Create:
- `src/data/ingestion/layer_ingestion_router.py`
- `scripts/build_all_layers.py`

## Routing rules
- `WFS` -> existing WFS ingestion path if available.
- `REST` / ArcGIS FeatureServer -> Esri REST ingestion.
- `OSM` -> Overpass or Geofabrik import path.
- `WMS`, `WMTS`, `XYZ` -> register as external tile layer, do not ingest into PostGIS.
- `postgis_derived` -> skip external ingestion; handled by derived-layer builder.

## Storage
For ingested vectors:
- schema: `data_layers`
- table: `data_layers.<layer_name>`
- columns: `id SERIAL`, `geom GEOMETRY`, `properties JSONB`
- add GIST index on `geom`

## Validation
- `python scripts/build_all_layers.py`
- idempotent re-run.
- Failed sources logged but do not crash whole run.
