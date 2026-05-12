---
id: SC-015
title: Add derived survey intelligence layer framework
priority: High
labels: analytics,postgis,derived-layers
---

# SC-015 - Add derived survey intelligence layer framework

**Priority:** High
**Labels:** analytics,postgis,derived-layers

## Goal
Create PostGIS-derived analytical layers for survey planning.

## Script
Create:
- `scripts/build_derived_layers.py`

## Derived layers
- `distance_to_water`
- `distance_to_roman_roads`
- `distance_to_historic_settlements`
- `distance_to_archaeological_sites`
- `slope_accessibility`
- `lidar_anomaly_candidates`
- `survey_priority_score`

## Requirements
- Use PostGIS views or materialised views.
- Register each derived layer in `/api/layers`.
- Mark `ingestion_method = postgis_derived`.
- Script must be idempotent.
- Do not require external downloads.
- Do not break survey editing.

## Validation
- Derived layers appear in `/api/layers`.
- Views/materialised views refresh safely.
- Layers toggle in UI.
