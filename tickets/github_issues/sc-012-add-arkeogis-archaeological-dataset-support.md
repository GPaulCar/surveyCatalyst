---
id: SC-012
title: Add ArkeoGIS archaeological dataset support
priority: High
labels: data,archaeology,arkeogis
---

# SC-012 - Add ArkeoGIS archaeological dataset support

**Priority:** High
**Labels:** data,archaeology,arkeogis

## Goal
Add ArkeoGIS archaeological data where legally accessible/open.

## Requirements
- Add source registry entry.
- Inspect API/download/export options.
- Ingest only legally accessible/open datasets.
- Store in `data_layers.arkeogis_sites`.
- Preserve period, site_type, dating, confidence, source, reference id.
- Register as vector-tile layer.
- Keep as context layer, not survey data.

## UI grouping
category `Archaeology`, subcategory `ArkeoGIS`.

## Validation
- Layer appears in `/api/layers`.
- Data renders.
- Metadata visible in Details panel.
