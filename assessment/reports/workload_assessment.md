# Workload Assessment

Generated: 2026-05-16T12:07:18.100475+00:00

## Scope
- Input: assessment/output/pg_stat_statements.csv
- Optional plans directory not required for this pass
- No database/app modifications applied

## Summary
- Total findings: 5
- Confirmed: 5
- Candidate: 0

## Findings

### 1. expensive_external_features_layer_count_query (high)
- Status: confirmed
- Scope: application + database
- Recommendation: Replace repeated live COUNT(*) GROUP BY layer with cached/materialized counts refreshed on ingest/update events.

### 2. expensive_external_features_layer_count_query (high)
- Status: confirmed
- Scope: application + database
- Recommendation: Replace repeated live COUNT(*) GROUP BY layer with cached/materialized counts refreshed on ingest/update events.

### 3. high_total_time_queries (high)
- Status: confirmed
- Scope: application + database
- Recommendation: Target top total time queries first for latency/cost reduction.

### 4. high_mean_time_queries (medium)
- Status: confirmed
- Scope: database
- Recommendation: Investigate plans for high mean execution time outliers.

### 5. high_block_read_queries (medium)
- Status: confirmed
- Scope: database
- Recommendation: Review indexing/plans and cache effectiveness for read-heavy SQL.
