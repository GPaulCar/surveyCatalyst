---
id: SC-011
title: Add HGIS Germany historical GIS support
priority: High
labels: data,historical,hgis
---

# SC-011 - Add HGIS Germany historical GIS support

**Priority:** High
**Labels:** data,historical,hgis

## Goal
Add HGIS Germany historical spatial datasets as temporal context layers.

## Layers
- `hgis_historical_boundaries`
- `hgis_historical_transport`
- `hgis_historical_states`

## Requirements
- Inspect available download formats.
- Prefer PostGIS ingestion for vector data.
- Preserve temporal fields: `year_start`, `year_end`, `period`, `source`, `confidence`.
- Do not implement time slider yet.
- Store enough metadata for future time slider.

## UI grouping
category `Historical`, subcategory `HGIS Germany`.

## Validation
- Layers ingest or register cleanly.
- Temporal fields retained.
- Layers toggle in UI.
