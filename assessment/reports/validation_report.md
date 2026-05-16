# Validation Report

Generated: 2026-05-16T11:22:59.325044+00:00

## Inputs
- Pre: C:\Users\Paul\Desktop\dev\surveyCatalyst\assessment\output
- Post: C:\Users\Paul\Desktop\dev\surveyCatalyst\assessment\output
- Plan: C:\Users\Paul\Desktop\dev\surveyCatalyst\assessment\plans\optimization_plan.json
- Execution log: C:\Users\Paul\Desktop\dev\surveyCatalyst\assessment\logs\execution_log.json

## Before/After Summary
- PG settings rows: pre=403 post=403
- Extensions rows: pre=3 post=3
- pg_stat_statements total_exec_time: pre=20012.71 post=20012.71
- pg_stat_statements mean_exec_per_call: pre=9.256571 post=9.256571
- pg_stat_statements temp_blocks: pre=0.00 post=0.00
- Dead tuple tables (ratio>=0.2): pre=2 post=2

## Decision
- Recommendation: keep

## Monitoring Notes
- If total execution time increased materially, inspect top workload findings and rollback high-risk approved changes first.
- Track dead tuple table count trend and index usage trend over multiple runs before final keep/revert decision.
