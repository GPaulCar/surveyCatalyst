# surveyCatalyst 0.6.0

Minor release adding the master geospatial layer registry.

- Added `layer_registry_master.csv` with 102 real layer records across archaeology, historical maps, terrain, hydrology, soil/geology, legal restrictions, infrastructure, remote sensing, detection intelligence, and base maps.
- Added database seeding for the complete registry through `db/migrations/0004_master_layer_registry.sql`.
- Added `MasterLayerRegistryService` plus `scripts/import_layer_registry_master.py` for validating and importing the registry into an existing database.
- Registry metadata now carries source type, endpoint URL, provider, ingestion method, priority, region scope, notes, service URL, and service layer identifiers where applicable.
