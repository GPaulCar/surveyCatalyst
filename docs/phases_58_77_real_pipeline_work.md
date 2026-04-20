# Phases 58-77 — Real Pipeline Work Conversion

This replaces the earlier placeholder block with actual pipeline work.

## Principle

These phases are no longer generic placeholders. They are now defined as real data-pipeline work items that extend the current PostGIS-first architecture.

The build direction remains:

1. source data first
2. PostGIS normalisation
3. registry + rendering alignment
4. interface and interaction after data confidence

---

## Phase 58 — Source acquisition hardening
### Goal
Make source downloads deterministic and resumable.

### Deliverables
- download manifest per source
- checksum capture
- local artifact naming convention
- retry/backoff for remote fetch

### Success criteria
- each source download is reproducible
- artifacts are recorded in ingestion_artifacts
- failures are resumable without corrupting state

---

## Phase 59 — Staging area standardisation
### Goal
Introduce a strict staging convention before import into database tables.

### Deliverables
- source-specific staging folders
- extracted/raw/processed subfolders
- promoted artifact marker files
- cleanup policy

### Success criteria
- raw downloads and extracted content are separated
- providers can be rerun safely without manual cleanup

---

## Phase 60 — Source schema inspection
### Goal
Inspect incoming columns/geometry before import.

### Deliverables
- source schema snapshot JSON
- geometry column detection
- WKT/GPKG/SHP type profiling
- import precheck report

### Success criteria
- provider can report expected vs actual schema before loading

---

## Phase 61 — Geometry validation pipeline
### Goal
Validate and normalise geometry before final insert.

### Deliverables
- null geometry checks
- invalid geometry checks
- SRID verification
- repair pass where possible

### Success criteria
- imported geometries are valid enough for spatial indexing and querying

---

## Phase 62 — Version and change tracking
### Goal
Track source versions and detect changes between runs.

### Deliverables
- provider version resolver
- ingestion comparison against last run
- changed/unchanged source detection
- version label persistence

### Success criteria
- unnecessary reloads can be skipped
- changed runs are visible in ingestion history

---

## Phase 63 — BLfD restricted area real ingest
### Goal
Move the legal layer from empty target table into real populated workflow.

### Deliverables
- WFS import path if available
- manual fallback path
- legal.restricted_areas load
- layer registry update

### Success criteria
- legal layer contains actual records, not only an empty target table

---

## Phase 64 — GESIS mining/economic ingest
### Goal
Move economic layer from target schema to actual loaded records.

### Deliverables
- raw record persistence
- mining-location extraction path
- optional manual geocoding staging support
- economic layer registration

### Success criteria
- economic layer can render actual point records in PostGIS

---

## Phase 65 — Itiner-e production ingest
### Goal
Make ancient roads import production-safe.

### Deliverables
- archive download + extraction
- ogr2ogr import validation
- ancient.roman_roads registry integration
- artifact/version persistence

### Success criteria
- Roman roads render from real imported source data

---

## Phase 66 — Viabundus production ingest
### Goal
Make medieval nodes/edges import production-safe.

### Deliverables
- nodes import
- edges import
- geometry index creation
- separate layer registration for nodes and edges

### Success criteria
- medieval network layers render from real records

---

## Phase 67 — Unified source run reporting
### Goal
Provide a consistent post-run summary across all providers.

### Deliverables
- records loaded
- artifacts written
- layers registered
- warnings/errors summary

### Success criteria
- one run summary can be shown in management or logs

---

## Phase 68 — External feature projection layer
### Goal
Unify context source tables into external feature serving where needed.

### Deliverables
- projection/import path into external_features
- source_table + source_id linkage
- registry-aware serving logic

### Success criteria
- rendering path can support either source table or external_features projection

---

## Phase 69 — Viewport-aware source loading
### Goal
Load only needed source data for current viewport.

### Deliverables
- bbox query integration
- layer-specific viewport filtering
- reduced full-table fetching

### Success criteria
- context layer rendering no longer requires full-dataset reads

---

## Phase 70 — Source-layer styling rules
### Goal
Move ad hoc style logic into a maintainable rule set.

### Deliverables
- layer style registry
- source-group-specific defaults
- geometry-aware styling

### Success criteria
- legal/economic/ancient/medieval layers style consistently

---

## Phase 71 — Data quality dashboard inputs
### Goal
Expose pipeline-quality signals for interface consumption.

### Deliverables
- missing geometry counts
- invalid record counts
- source run failures
- stale source indicators

### Success criteria
- UI can report pipeline confidence per source

---

## Phase 72 — Survey/context intersection analysis
### Goal
Relate user surveys to ingested context data.

### Deliverables
- survey intersects context features
- per-survey source summaries
- source counts by survey

### Success criteria
- a survey can surface relevant roads, sites, restricted areas, mining points

---

## Phase 73 — Persisted analysis snapshots
### Goal
Store analysis outputs so survey state is reproducible.

### Deliverables
- snapshot table or persisted JSON artifact
- timestamped survey analysis runs
- survey-to-analysis linkage

### Success criteria
- re-opening a survey can restore prior analysis context

---

## Phase 74 — Export pack generation
### Goal
Generate portable survey/source packs.

### Deliverables
- survey JSON export
- linked object export
- analysis snapshot export
- optional source summary export

### Success criteria
- survey work can be moved or archived cleanly

---

## Phase 75 — Runtime validation and repair
### Goal
Detect broken runtime assumptions before app use.

### Deliverables
- Postgres/PostGIS health checks
- required table checks
- migration level check
- repair guidance

### Success criteria
- app startup can fail fast with actionable reasons

---

## Phase 76 — Management commands for data ops
### Goal
Add real operational commands around pipeline work.

### Deliverables
- run one source
- run all sources
- inspect source status
- build backup manifest
- export survey pack

### Success criteria
- operational work is scriptable and consistent

---

## Phase 77 — First data-driven release gate
### Goal
Define minimum data completeness before calling the app usable.

### Deliverables
- release checklist
- source completeness thresholds
- runtime validation checklist
- export/backup verification

### Success criteria
- release candidate is judged by real data readiness, not scaffolding completion

---

## Recommended implementation batches

### Batch A
58-61

### Batch B
62-66

### Batch C
67-72

### Batch D
73-77

This is the correct conversion path for the existing project state.
