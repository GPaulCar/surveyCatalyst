# Operations Assessment Workflow

This document is the authoritative operational workflow for cross-host PostgreSQL/PostGIS assessment, planning, execution, and validation.

## Scope

- Works across multiple servers with different resource profiles.
- Uses one repo as the only exchange channel.
- Separates portable improvements from host-specific tuning.

## Required principles

1. No unilateral execution of tuning changes.
2. Assessment is read-only by default.
3. Every phase is tagged in Git.
4. Host artifacts are committed under `assessment/`.
5. Execution changes must be reproducible and rollback-aware.

## Repository paths

- `assessment/registry.json` orchestration source of truth
- `assessment/scripts/collect_full_baseline.py`
- `assessment/scripts/analyze_server_config.py`
- `assessment/scripts/analyze_database_content.py`
- `assessment/scripts/analyze_workload.py`
- `assessment/scripts/create_unified_plan.py`
- `assessment/scripts/apply_approved_fixes.py`
- `assessment/scripts/validate_and_monitor.py`
- `assessment/scripts/run_assessment_block.py`
- `scripts/tag_phase.ps1`

## End-to-end run block

```powershell
python assessment\scripts\run_assessment_block.py --dotenv assessment\.env.example
python assessment\scripts\apply_approved_fixes.py --dry-run
python assessment\scripts\validate_and_monitor.py
```

## Git artifact exchange (required)

```powershell
git add assessment
git commit -m "assessment: host run artifacts"
git push origin main
```

## Tagging model

Two tag families:

- Code/refinement tags:
  - `sc-base-YYYYMMDD.N`
  - `sc-refine-YYYYMMDD.N`
- Result tags:
  - `sc-assess-<host>-YYYYMMDD-HHMM`
  - `sc-validate-<host>-YYYYMMDD-HHMM`

Create tags with helper:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\tag_phase.ps1 -Phase code -PreviousTag sc-base-20260516.1 -Number 2
powershell -ExecutionPolicy Bypass -File .\scripts\tag_phase.ps1 -Phase assess
powershell -ExecutionPolicy Bypass -File .\scripts\tag_phase.ps1 -Phase validate
```

Push tags:

```powershell
git push origin <tag-name>
```

## Multi-host comparison workflow

1. Run assessment block on Server A.
2. Commit/push artifacts.
3. Run assessment block on Server B.
4. Commit/push artifacts.
5. Generate/compare host-specific findings and classify:
   - portable
   - host_specific
   - reject
6. Apply approved changes per host.
7. Re-run validation/monitoring.

## Drift control

Lock each host to the same deployment tag before comparing:

```powershell
git fetch --tags origin
git checkout --detach tags/<deploy-tag>
git reset --hard tags/<deploy-tag>
git clean -fd
```

## Notes

- `apply_approved_fixes.py --dry-run` is simulation only.
- Real apply requires approved statuses in `assessment/plans/optimization_plan.json`.
- Never treat dev host tuning as automatically valid for production hosts.
