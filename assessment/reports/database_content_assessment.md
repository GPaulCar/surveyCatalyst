# Database Content Assessment

Generated: 2026-05-16T11:22:58.861830+00:00

## Scope
- Baseline CSV outputs only
- No schema/data changes applied

## Summary
- Total findings: 44
- Confirmed: 1
- Candidate: 43

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

### 35. dead_tuple_pressure (medium)
- Table: bkg_vg250_boundaries
- Action status: candidate
- Evidence: `{"n_live_tup": 7, "n_dead_tup": 14, "dead_ratio": 2.0}`
- Recommendation: Investigate vacuum/analyze cadence for this table.

### 36. dead_tuple_pressure (medium)
- Table: bkg_vg25_boundaries
- Action status: candidate
- Evidence: `{"n_live_tup": 7, "n_dead_tup": 14, "dead_ratio": 2.0}`
- Recommendation: Investigate vacuum/analyze cadence for this table.

### 37. missing_spatial_index_candidate (high)
- Table: bkg_vg250_boundaries
- Action status: candidate
- Evidence: `{"index_match_probe": " on bkg_vg250_boundaries using gist (geom"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

### 38. missing_spatial_index_candidate (high)
- Table: bkg_vg25_boundaries
- Action status: candidate
- Evidence: `{"index_match_probe": " on bkg_vg25_boundaries using gist (geom"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

### 39. missing_spatial_index_candidate (high)
- Table: mining_locations
- Action status: candidate
- Evidence: `{"index_match_probe": " on mining_locations using gist (geom"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

### 40. missing_spatial_index_candidate (high)
- Table: restricted_areas
- Action status: candidate
- Evidence: `{"index_match_probe": " on restricted_areas using gist (geom"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

### 41. missing_spatial_index_candidate (high)
- Table: external_features
- Action status: candidate
- Evidence: `{"index_match_probe": " on external_features using gist (geom"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

### 42. missing_spatial_index_candidate (high)
- Table: spsde:simplifiedbavarianmonument
- Action status: candidate
- Evidence: `{"index_match_probe": " on spsde:simplifiedbavarianmonument using gist (geometry"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

### 43. missing_spatial_index_candidate (high)
- Table: survey_objects
- Action status: candidate
- Evidence: `{"index_match_probe": " on survey_objects using gist (geom"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

### 44. missing_spatial_index_candidate (high)
- Table: surveys
- Action status: candidate
- Evidence: `{"index_match_probe": " on surveys using gist (geom"}`
- Recommendation: Confirm whether a GiST/SP-GiST index exists or should be created.

## Notes
- Duplicate/overlap findings are review candidates until usage and plan review complete.
- No indexes were created/dropped by this assessment.
