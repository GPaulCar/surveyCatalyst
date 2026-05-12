---
id: SC-004
title: Create layer registry master spreadsheet
priority: High
labels: data,registry,spreadsheet
---

# SC-004 - Create layer registry master spreadsheet

**Priority:** High
**Labels:** data,registry,spreadsheet

## Goal
Create a complete layer registry spreadsheet for SurveyCatalyst data-source planning and ingestion.

## Output
- `docs/data/layer_registry_master.csv`
- Optional: `docs/data/layer_registry_master.xlsx`

## Required columns
`category`, `subcategory`, `layer_name`, `description`, `geometry_type`, `source_provider`, `source_type`, `endpoint_url`, `ingestion_method`, `priority`, `region_scope`, `notes`

## Required categories
Archaeology, Historical Maps, Terrain, Hydrology, Soil & Geology, Legal / Restrictions, Infrastructure, Remote Sensing, Detection Intelligence, Base Maps, Administrative, Historical GIS, Derived Analytics.

## Requirements
- Minimum 50 rows; target 80-120 rows.
- No placeholder rows.
- Use real usable sources where possible.
- Mark derived layers as `postgis_derived`.
- Use snake_case layer names.

## Validation
- CSV opens cleanly.
- No duplicate `layer_name`.
- All rows have required fields.
