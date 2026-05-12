---
id: SC-005
title: Implement layer registry DB table and CSV loader
priority: High
labels: data,backend,postgres
---

# SC-005 - Implement layer registry DB table and CSV loader

**Priority:** High
**Labels:** data,backend,postgres

## Goal
Load `layer_registry_master.csv` into Postgres idempotently.

## Scope
- `scripts/load_layer_registry.py`
- database schema setup logic

## Table
Create table if not exists:
```sql
layer_registry (
    id SERIAL PRIMARY KEY,
    category TEXT,
    subcategory TEXT,
    layer_name TEXT UNIQUE,
    description TEXT,
    geometry_type TEXT,
    source_provider TEXT,
    source_type TEXT,
    endpoint_url TEXT,
    ingestion_method TEXT,
    priority TEXT,
    region_scope TEXT,
    notes TEXT,
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Tasks
- Read `docs/data/layer_registry_master.csv`.
- Upsert by `layer_name`.
- Normalise names to snake_case.
- Safe to re-run.
- Print inserted/updated/skipped counts.

## Validation
```powershell
python scripts\load_layer_registry.py
```
