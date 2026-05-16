# Unified Optimization Plan

Generated: 2026-05-16T09:58:39.501399+00:00

## Group Summary
- server_config: 6
- database_optimization: 59
- database_content_cleanup: 0
- application_query_optimization: 5
- validation: 1
- monitoring: 1

## Ordered Changes

### 1. [server_config] Adjust setting: shared_buffers
- Risk: medium
- Dependencies: baseline_collected
- Restart/Downtime: restart
- Affects next parcel: True
- Validation: Compare buffer cache hit ratio and query latency after restart.
- Rollback: Restore shared_buffers to 163848kB.
- Notes: shared_buffers below typical target can increase disk reads.

### 2. [server_config] Adjust setting: effective_cache_size
- Risk: low
- Dependencies: baseline_collected
- Restart/Downtime: reload
- Affects next parcel: True
- Validation: Check plan changes for top queries and index usage.
- Rollback: Restore effective_cache_size to 5242888kB.
- Notes: effective_cache_size drives planner assumptions for index scans.

### 3. [server_config] Adjust setting: maintenance_work_mem
- Risk: low
- Dependencies: baseline_collected
- Restart/Downtime: reload
- Affects next parcel: True
- Validation: Observe VACUUM/CREATE INDEX runtime after change.
- Rollback: Restore maintenance_work_mem to 65536kB.
- Notes: maintenance operations can be slow with too-small maintenance_work_mem.

### 4. [server_config] Adjust setting: max_parallel_workers_per_gather
- Risk: low
- Dependencies: baseline_collected
- Restart/Downtime: reload
- Affects next parcel: True
- Validation: Check EXPLAIN plans for Gather nodes and execution time.
- Rollback: Restore max_parallel_workers_per_gather to 2.
- Notes: parallel execution can improve scans on large analytical reads.

### 5. [server_config] Adjust setting: checkpoint_completion_target
- Risk: low
- Dependencies: baseline_collected
- Restart/Downtime: reload
- Affects next parcel: True
- Validation: Track checkpoint write spikes and latency variance.
- Rollback: Restore checkpoint_completion_target to 0.9.
- Notes: higher checkpoint_completion_target smooths checkpoint I/O bursts.

### 6. [server_config] Adjust setting: wal_buffers
- Risk: low
- Dependencies: baseline_collected
- Restart/Downtime: restart
- Affects next parcel: True
- Validation: Observe WAL write waits and transaction latency during write bursts.
- Rollback: Restore wal_buffers to 5128kB.
- Notes: WAL buffer size can affect write-heavy workloads.

### 7. [database_optimization] overlapping_spatial_indexes on external_features
- Risk: high
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Validate per-index usage and consolidate redundant GiST indexes.

### 8. [database_optimization] unused_index on layers_registry
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 9. [database_optimization] unused_index on surveys
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 10. [database_optimization] unused_index on surveys
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 11. [database_optimization] unused_index on layers_registry
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 12. [database_optimization] unused_index on survey_objects
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 13. [database_optimization] unused_index on external_features
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 14. [database_optimization] unused_index on ingestion_sources
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 15. [database_optimization] unused_index on ingestion_sources
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 16. [database_optimization] unused_index on ingestion_runs
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 17. [database_optimization] unused_index on ingestion_artifacts
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 18. [database_optimization] unused_index on restricted_areas
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 19. [database_optimization] unused_index on bavaria_economy_raw
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 20. [database_optimization] unused_index on mining_locations
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 21. [database_optimization] unused_index on mining_locations
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 22. [database_optimization] unused_index on raw_test
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 23. [database_optimization] unused_index on spsde:simplifiedbavarianmonument
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 24. [database_optimization] unused_index on spsde:simplifiedbavarianmonument
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 25. [database_optimization] unused_index on restricted_areas
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 26. [database_optimization] unused_index on surveys
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 27. [database_optimization] unused_index on survey_objects
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 28. [database_optimization] unused_index on external_features
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 29. [database_optimization] unused_index on survey_objects
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 30. [database_optimization] unused_index on external_features
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 31. [database_optimization] unused_index on permission_requests
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 32. [database_optimization] unused_index on permission_requests
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 33. [database_optimization] unused_index on permission_requests
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 34. [database_optimization] unused_index on layer_registry
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 35. [database_optimization] unused_index on layer_registry
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 36. [database_optimization] unused_index on bkg_vg250_boundaries
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 37. [database_optimization] unused_index on bkg_vg25_boundaries
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 38. [database_optimization] unused_index on survey_objects
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 39. [database_optimization] unused_index on surveys
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 40. [database_optimization] unused_index on external_features
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Review whether index is still needed; avoid blind drops without query-history window.

### 41. [database_optimization] never_analyzed on spsde:simplifiedbavarianmonument
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 42. [database_optimization] never_analyzed on ingestion_runs
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 43. [database_optimization] never_analyzed on layer_registry
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 44. [database_optimization] never_analyzed on bkg_vg250_boundaries
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 45. [database_optimization] never_analyzed on ingestion_sources
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 46. [database_optimization] never_analyzed on ingestion_artifacts
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 47. [database_optimization] never_analyzed on bkg_vg25_boundaries
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 48. [database_optimization] never_analyzed on external_features
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 49. [database_optimization] never_analyzed on permission_requests
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 50. [database_optimization] never_analyzed on bavaria_economy_raw
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 51. [database_optimization] never_analyzed on survey_objects
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 52. [database_optimization] never_analyzed on mining_locations
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 53. [database_optimization] never_analyzed on surveys
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 54. [database_optimization] never_analyzed on raw_test
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 55. [database_optimization] never_analyzed on restricted_areas
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 56. [database_optimization] never_analyzed on layers_registry
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 57. [database_optimization] never_analyzed on spatial_ref_sys
- Risk: medium
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 58. [database_optimization] missing_spatial_index_candidate on bkg_vg250_boundaries
- Risk: high
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Confirm whether a GiST/SP-GiST index exists or should be created.

### 59. [database_optimization] missing_spatial_index_candidate on bkg_vg25_boundaries
- Risk: high
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Confirm whether a GiST/SP-GiST index exists or should be created.

### 60. [database_optimization] missing_spatial_index_candidate on mining_locations
- Risk: high
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Confirm whether a GiST/SP-GiST index exists or should be created.

### 61. [database_optimization] missing_spatial_index_candidate on restricted_areas
- Risk: high
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Confirm whether a GiST/SP-GiST index exists or should be created.

### 62. [database_optimization] missing_spatial_index_candidate on external_features
- Risk: high
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Confirm whether a GiST/SP-GiST index exists or should be created.

### 63. [database_optimization] missing_spatial_index_candidate on spsde:simplifiedbavarianmonument
- Risk: high
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Confirm whether a GiST/SP-GiST index exists or should be created.

### 64. [database_optimization] missing_spatial_index_candidate on survey_objects
- Risk: high
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Confirm whether a GiST/SP-GiST index exists or should be created.

### 65. [database_optimization] missing_spatial_index_candidate on surveys
- Risk: high
- Dependencies: server_config_reviewed
- Restart/Downtime: none_or_reload
- Affects next parcel: True
- Validation: Compare pg_stat_user_indexes, pg_stat_user_tables, and query latency before/after.
- Rollback: Recreate dropped index / restore previous vacuum settings / revert migration.
- Notes: Confirm whether a GiST/SP-GiST index exists or should be created.

### 66. [application_query_optimization] expensive_external_features_layer_count_query
- Risk: high
- Dependencies: database_optimization_started
- Restart/Downtime: app_restart_possible
- Affects next parcel: True
- Validation: Compare pg_stat_statements before/after for target query classes.
- Rollback: Revert application query changes and disable new cache/materialized query path.
- Notes: Replace repeated live COUNT(*) GROUP BY layer with cached/materialized counts refreshed on ingest/update events.

### 67. [application_query_optimization] expensive_external_features_layer_count_query
- Risk: high
- Dependencies: database_optimization_started
- Restart/Downtime: app_restart_possible
- Affects next parcel: True
- Validation: Compare pg_stat_statements before/after for target query classes.
- Rollback: Revert application query changes and disable new cache/materialized query path.
- Notes: Replace repeated live COUNT(*) GROUP BY layer with cached/materialized counts refreshed on ingest/update events.

### 68. [application_query_optimization] high_total_time_queries
- Risk: high
- Dependencies: database_optimization_started
- Restart/Downtime: app_restart_possible
- Affects next parcel: True
- Validation: Compare pg_stat_statements before/after for target query classes.
- Rollback: Revert application query changes and disable new cache/materialized query path.
- Notes: Target top total time queries first for latency/cost reduction.

### 69. [application_query_optimization] high_mean_time_queries
- Risk: medium
- Dependencies: database_optimization_started
- Restart/Downtime: app_restart_possible
- Affects next parcel: True
- Validation: Compare pg_stat_statements before/after for target query classes.
- Rollback: Revert application query changes and disable new cache/materialized query path.
- Notes: Investigate plans for high mean execution time outliers.

### 70. [application_query_optimization] high_block_read_queries
- Risk: medium
- Dependencies: database_optimization_started
- Restart/Downtime: app_restart_possible
- Affects next parcel: True
- Validation: Compare pg_stat_statements before/after for target query classes.
- Rollback: Revert application query changes and disable new cache/materialized query path.
- Notes: Review indexing/plans and cache effectiveness for read-heavy SQL.

### 71. [validation] Run post-change baseline and compare against pre-change baseline
- Risk: low
- Dependencies: all_approved_changes_applied
- Restart/Downtime: none
- Affects next parcel: False
- Validation: Execute validate_and_monitor.py and review validation_report.md.
- Rollback: Use change-specific rollback procedures if regression thresholds are exceeded.
- Notes: Validation gate for keep/revert decisions.

### 72. [monitoring] Establish recurring health/performance checks
- Risk: low
- Dependencies: validation_passed
- Restart/Downtime: none
- Affects next parcel: False
- Validation: Confirm checks run and produce actionable outputs.
- Rollback: Disable monitoring jobs if they create operational noise.
- Notes: Track query latency, dead tuples, index usage, lock pressure, and cache effectiveness.
