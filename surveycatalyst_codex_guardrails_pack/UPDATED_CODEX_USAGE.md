# Updated Usage

Copy these files into the repo root together with the ticket pack:

- `CODEX_EXECUTION_GUARDRAILS.md`
- `CODEX_MASTER_INSTRUCTION.md`

Then commit:

```bash
git add CODEX_EXECUTION_GUARDRAILS.md CODEX_MASTER_INSTRUCTION.md CODEX_BACKLOG.md tickets
git commit -m "Add governed Codex backlog"
```

Then tell Codex:

```text
Read CODEX_MASTER_INSTRUCTION.md first. Work one ticket at a time from CODEX_BACKLOG.md. Treat tickets as outcome specifications, not literal file-edit instructions. Inspect the current codebase before each ticket, choose the safest implementation path, validate, commit, and stop before the next ticket.
```
