---
id: SC-008
title: Add Bavaria DGM LiDAR terrain layer support
priority: Critical
labels: data,terrain,lidar
---

# SC-008 - Add Bavaria DGM LiDAR terrain layer support

**Priority:** Critical
**Labels:** data,terrain,lidar

## Goal
Add terrain intelligence support for Bavarian DGM/LiDAR layers.

## Registry rows
- `bavaria_dgm1`
- `bavaria_dgm5`
- `bavaria_hillshade`
- `bavaria_slope`
- `bavaria_local_relief_model`

## Requirements
- Treat DGM as raster/source dataset.
- Do not force large rasters into vector tables.
- Use external raster/tile registration where service tiles exist.
- If downloadable raster files are supported, create metadata and optional derivative-processing script.
- Derived outputs use `ingestion_method = raster_derived`.
- UI category `Terrain`, subcategory `LiDAR / DGM`.

## Validation
- Terrain layers appear in `/api/layers`.
- Toggle does not crash if source unavailable.
