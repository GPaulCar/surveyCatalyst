# Phase 30 - Proper Ingestion Pipeline

This replaces the placeholder ingestion phase with a modular data-first ingestion pipeline.

## Added
- ingestion metadata tables
- provider registry
- provider base class
- provider implementations for:
  - Itiner-e
  - Viabundus
  - BLfD
  - GESIS
- orchestration service
- scripts to run one source or all sources

## Result
The application can now be built around source data and PostGIS-backed layers first, then interface and interactions second.
