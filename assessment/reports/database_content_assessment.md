# Database Content Assessment

Generated: 2026-05-16T09:58:39.268760+00:00

## Scope
- Baseline CSV outputs only
- No schema/data changes applied

## Summary
- Total findings: 59
- Confirmed: 1
- Candidate: 58

## Findings

### 1. overlapping_spatial_indexes (high)
- Table: external_features
- Action status: confirmed
- Evidence: `["CREATE INDEX idx_external_features_geom_gist ON public.external_features USING gist (geom)", "CREATE INDEX idx_external_features_geom ON public.external_features USING gist (geom)", "CREATE INDEX idx_external_features_layer_geom_gist ON public.external_features USING gist (geom)"]`
- Recommendation: Validate per-index usage and consolidate redundant GiST indexes.

### 2. unused_index (medium)
- Table: layers_registry
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 3. unused_index (medium)
- Table: surveys
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 4. unused_index (medium)
- Table: surveys
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 5. unused_index (medium)
- Table: layers_registry
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 6. unused_index (medium)
- Table: survey_objects
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 7. unused_index (medium)
- Table: external_features
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 8. unused_index (medium)
- Table: ingestion_sources
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 9. unused_index (medium)
- Table: ingestion_sources
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 10. unused_index (medium)
- Table: ingestion_runs
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 11. unused_index (medium)
- Table: ingestion_artifacts
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 12. unused_index (medium)
- Table: restricted_areas
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 13. unused_index (medium)
- Table: bavaria_economy_raw
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 14. unused_index (medium)
- Table: mining_locations
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 15. unused_index (medium)
- Table: mining_locations
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 16. unused_index (medium)
- Table: raw_test
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 17. unused_index (medium)
- Table: spsde:simplifiedbavarianmonument
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 18. unused_index (medium)
- Table: spsde:simplifiedbavarianmonument
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 19. unused_index (medium)
- Table: restricted_areas
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 20. unused_index (medium)
- Table: surveys
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 21. unused_index (medium)
- Table: survey_objects
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 22. unused_index (medium)
- Table: external_features
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 23. unused_index (medium)
- Table: survey_objects
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 24. unused_index (medium)
- Table: external_features
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 25. unused_index (medium)
- Table: permission_requests
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 26. unused_index (medium)
- Table: permission_requests
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 27. unused_index (medium)
- Table: permission_requests
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 28. unused_index (medium)
- Table: layer_registry
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 29. unused_index (medium)
- Table: layer_registry
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 30. unused_index (medium)
- Table: bkg_vg250_boundaries
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 31. unused_index (medium)
- Table: bkg_vg25_boundaries
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 32. unused_index (medium)
- Table: survey_objects
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 33. unused_index (medium)
- Table: surveys
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 34. unused_index (medium)
- Table: external_features
- Action status: candidate
- Evidence: `{"idx_scan": 0}`
- Recommendation: Review whether index is still needed; avoid blind drops without query-history window.

### 35. never_analyzed (medium)
- Table: spsde:simplifiedbavarianmonument
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 36. never_analyzed (medium)
- Table: ingestion_runs
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 37. never_analyzed (medium)
- Table: layer_registry
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 38. never_analyzed (medium)
- Table: bkg_vg250_boundaries
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 39. never_analyzed (medium)
- Table: ingestion_sources
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 40. never_analyzed (medium)
- Table: ingestion_artifacts
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 41. never_analyzed (medium)
- Table: bkg_vg25_boundaries
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 42. never_analyzed (medium)
- Table: external_features
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 43. never_analyzed (medium)
- Table: permission_requests
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 44. never_analyzed (medium)
- Table: bavaria_economy_raw
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 45. never_analyzed (medium)
- Table: survey_objects
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 46. never_analyzed (medium)
- Table: mining_locations
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 47. never_analyzed (medium)
- Table: surveys
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 48. never_analyzed (medium)
- Table: raw_test
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 49. never_analyzed (medium)
- Table: restricted_areas
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 50. never_analyzed (medium)
- Table: layers_registry
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 51. never_analyzed (medium)
- Table: spatial_ref_sys
- Action status: candidate
- Evidence: `{"last_analyze": "", "last_autoanalyze": ""}`
- Recommendation: Ensure ANALYZE/autovacuum analyze runs for planner statistics quality.

### 52. missing_spatial_index_candidate (high)
- Table: bkg_vg250_boundaries
- Action status: candidate
- Evidence: `{"index_match_probe": " on bkg_vg250_boundaries using gist (geom"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

### 53. missing_spatial_index_candidate (high)
- Table: bkg_vg25_boundaries
- Action status: candidate
- Evidence: `{"index_match_probe": " on bkg_vg25_boundaries using gist (geom"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

### 54. missing_spatial_index_candidate (high)
- Table: mining_locations
- Action status: candidate
- Evidence: `{"index_match_probe": " on mining_locations using gist (geom"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

### 55. missing_spatial_index_candidate (high)
- Table: restricted_areas
- Action status: candidate
- Evidence: `{"index_match_probe": " on restricted_areas using gist (geom"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

### 56. missing_spatial_index_candidate (high)
- Table: external_features
- Action status: candidate
- Evidence: `{"index_match_probe": " on external_features using gist (geom"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

### 57. missing_spatial_index_candidate (high)
- Table: spsde:simplifiedbavarianmonument
- Action status: candidate
- Evidence: `{"index_match_probe": " on spsde:simplifiedbavarianmonument using gist (geometry"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

### 58. missing_spatial_index_candidate (high)
- Table: survey_objects
- Action status: candidate
- Evidence: `{"index_match_probe": " on survey_objects using gist (geom"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

### 59. missing_spatial_index_candidate (high)
- Table: surveys
- Action status: candidate
- Evidence: `{"index_match_probe": " on surveys using gist (geom"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

## Notes
- Duplicate/overlap findings are review candidates until usage and plan review complete.
- No indexes were created/dropped by this assessment.
