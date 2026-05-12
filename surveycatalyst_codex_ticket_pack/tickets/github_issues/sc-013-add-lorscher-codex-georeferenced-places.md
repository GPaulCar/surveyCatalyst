---
id: SC-013
title: Add Lorscher Codex georeferenced places
priority: Medium
labels: data,historical,medieval
---

# SC-013 - Add Lorscher Codex georeferenced places

**Priority:** Medium
**Labels:** data,historical,medieval

## Goal
Add Lorscher Codex georeferenced historical places as medieval context.

## Requirements
- Add source registry entry.
- Inspect available export/API/download.
- Ingest georeferenced locations into `data_layers.lorscher_codex_places`.
- Preserve historical_name, modern_name, reference, document_id, dating, uncertainty/confidence if available.
- Register as vector-tile layer.

## UI grouping
category `Historical`, subcategory `Medieval Sources`.

## Validation
- Layer appears in `/api/layers`.
- Places render.
- Metadata visible in Details panel.
