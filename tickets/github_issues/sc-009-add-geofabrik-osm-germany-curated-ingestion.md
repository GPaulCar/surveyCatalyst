---
id: SC-009
title: Add Geofabrik OSM Germany curated ingestion
priority: High
labels: data,osm,ingestion
---

# SC-009 - Add Geofabrik OSM Germany curated ingestion

**Priority:** High
**Labels:** data,osm,ingestion

## Goal
Ingest curated OSM Germany layers from Geofabrik.

## Source
`https://download.geofabrik.de/europe/germany-latest.osm.pbf`

## Script
Create:
- `scripts/ingest_osm_geofabrik.py`

## Curated layers
`osm_historic_sites`, `osm_ruins`, `osm_castles`, `osm_churches`, `osm_tracks_paths`, `osm_roads`, `osm_abandoned_railways`, `osm_waterways`, `osm_landuse`, `osm_settlements`

## Preserve tags
`historic`, `ruins`, `archaeological_site`, `site_type`, `old_name`, `abandoned`, `railway`, `highway`, `waterway`, `landuse`, `name`

## Requirements
- Use `osm2pgsql` if available.
- If not available, fail clearly with install instructions.
- Store curated outputs in `data_layers`.
- Add GIST indexes.
- Register vector-tile layers.
- Do not expose raw full OSM tables directly.

## Validation
- Curated layers appear in `/api/layers`.
- Layers toggle in UI.
