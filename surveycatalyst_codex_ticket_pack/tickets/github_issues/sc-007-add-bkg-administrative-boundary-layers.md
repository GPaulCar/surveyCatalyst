---
id: SC-007
title: Add BKG administrative boundary layers
priority: High
labels: data,bkg,administrative
---

# SC-007 - Add BKG administrative boundary layers

**Priority:** High
**Labels:** data,bkg,administrative

## Goal
Add BKG administrative boundary layers to SurveyCatalyst.

## Dataset
BKG Verwaltungsgebiete VG250 / VG25 where available.

## Tasks
- Add registry rows for `bkg_vg250_boundaries` and `bkg_vg25_boundaries` if available.
- Prefer PostGIS vector ingestion from GeoPackage/Shapefile/WFS.
- Store in `data_layers`.
- Register vector-tile layers.
- UI category `Administrative`, subcategory `Boundaries`.

## Validation
- `/api/layers` includes BKG boundaries.
- Boundaries toggle in UI.
- Boundaries render above basemap and below survey data.
