---
id: SC-014
title: Add Bavaria orthophoto overlay support
priority: High
labels: data,imagery,wms
---

# SC-014 - Add Bavaria orthophoto overlay support

**Priority:** High
**Labels:** data,imagery,wms

## Goal
Add Bavaria DOP and historical orthophoto overlays separate from basemaps.

## Layers
- `bavaria_dop20`
- `bavaria_historical_orthophoto`

## Requirements
- Use WMS/WMTS/external tile registration.
- Do not ingest imagery into PostGIS unless project already supports raster ingestion.
- These are overlays, not basemaps.
- Ensure survey vectors remain visible above imagery.
- Do not reset map view when toggled.

## UI grouping
category `Imagery`, subcategory `Bavaria Orthophotos`.

## Validation
- Layers listed in `/api/layers`.
- Overlays toggle above basemap.
- Survey vectors remain visible.
