---
id: SC-010
title: Add Destatis Regionalatlas support
priority: Medium
labels: data,statistics,regionalatlas
---

# SC-010 - Add Destatis Regionalatlas support

**Priority:** Medium
**Labels:** data,statistics,regionalatlas

## Goal
Add Destatis Regionalatlas statistical geodata as contextual layers.

## Tasks
- Add registry entries for Regionalatlas-compatible layers.
- Support GeoJSON/Shapefile download where available.
- Support WMS registration where only map service is available.
- Store imported vector/statistical data in `data_layers.destatis_regionalatlas`.

## Preserve fields
region id, region name, year, topic, value, unit.

## UI grouping
category `Socioeconomic / Regional`, subcategory `Regionalatlas`.

## Validation
- Appears in `/api/layers`.
- Renders as vector tile if imported.
- Registers as external tile if WMS only.
