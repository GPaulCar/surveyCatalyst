# Server Configuration Assessment

Generated: 2026-05-16T11:22:58.734584+00:00

## Scope
- Input: assessment/output/postgres_settings.csv
- Input: assessment/output/system_baseline.json
- No changes applied (analysis only).

## Findings

### 1. shared_buffers
- Current: 16 MB
- Recommended: 488114 MB
- Confidence: candidate
- Risk: medium
- Requires: restart
- Pending restart flag: False
- Rationale: shared_buffers below typical target can increase disk reads.
- Validation: Compare buffer cache hit ratio and query latency after restart.
- Rollback: Restore shared_buffers to 163848kB.

### 2. effective_cache_size
- Current: 512 MB
- Recommended: 1171475 MB
- Confidence: candidate
- Risk: low
- Requires: reload
- Pending restart flag: False
- Rationale: effective_cache_size drives planner assumptions for index scans.
- Validation: Check plan changes for top queries and index usage.
- Rollback: Restore effective_cache_size to 5242888kB.

### 3. maintenance_work_mem
- Current: 64 MB
- Recommended: 97622 MB
- Confidence: candidate
- Risk: low
- Requires: reload
- Pending restart flag: False
- Rationale: maintenance operations can be slow with too-small maintenance_work_mem.
- Validation: Observe VACUUM/CREATE INDEX runtime after change.
- Rollback: Restore maintenance_work_mem to 65536kB.

### 4. max_parallel_workers_per_gather
- Current: 2
- Recommended: 2
- Confidence: candidate
- Risk: low
- Requires: reload
- Pending restart flag: False
- Rationale: parallel execution can improve scans on large analytical reads.
- Validation: Check EXPLAIN plans for Gather nodes and execution time.
- Rollback: Restore max_parallel_workers_per_gather to 2.

### 5. checkpoint_completion_target
- Current: 0.9
- Recommended: 0.9
- Confidence: candidate
- Risk: low
- Requires: reload
- Pending restart flag: False
- Rationale: higher checkpoint_completion_target smooths checkpoint I/O bursts.
- Validation: Track checkpoint write spikes and latency variance.
- Rollback: Restore checkpoint_completion_target to 0.9.

### 6. wal_buffers
- Current: 5128kB
- Recommended: auto or higher explicit value if WAL contention observed
- Confidence: candidate
- Risk: low
- Requires: restart
- Pending restart flag: False
- Rationale: WAL buffer size can affect write-heavy workloads.
- Validation: Observe WAL write waits and transaction latency during write bursts.
- Rollback: Restore wal_buffers to 5128kB.

## Notes
- Recommendations are candidate values and must be approved before execution.
- Restart/reload requirements are explicit per setting.
- This report intentionally does not edit postgresql.conf or run ALTER SYSTEM.
