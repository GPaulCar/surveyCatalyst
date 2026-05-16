# Validation Report

Generated: 2026-05-16T12:07:18.601757+00:00

## Inputs
- Pre: C:\Users\Paul\Desktop\dev\surveyCatalyst\assessment\output
- Post: C:\Users\Paul\Desktop\dev\surveyCatalyst\assessment\output
- Plan: C:\Users\Paul\Desktop\dev\surveyCatalyst\assessment\plans\optimization_plan.json
- Execution log: C:\Users\Paul\Desktop\dev\surveyCatalyst\assessment\logs\execution_log.json

## Before/After Summary
- PG settings rows: pre=403 post=403
- Extensions rows: pre=3 post=3
- pg_stat_statements total_exec_time: pre=22963.41 post=22963.41
- pg_stat_statements mean_exec_per_call: pre=10.371912 post=10.371912
- pg_stat_statements temp_blocks: pre=0.00 post=0.00
- Dead tuple tables (ratio>=0.2): pre=2 post=2

## Decision
- Recommendation: keep

## Monitoring Notes
- If total execution time increased materially, inspect top workload findings and rollback high-risk approved changes first.
- Track dead tuple table count trend and index usage trend over multiple runs before final keep/revert decision.
