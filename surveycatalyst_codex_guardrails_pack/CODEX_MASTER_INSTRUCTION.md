# Codex Master Instruction

Work from `CODEX_BACKLOG.md`, but treat every ticket as an outcome specification rather than a literal edit script.

Before executing any ticket, read:

1. `CODEX_EXECUTION_GUARDRAILS.md`
2. the selected ticket
3. the current implementation in the repository

Then follow this process:

1. Inspect current files and identify the real implementation points.
2. State the minimal implementation plan.
3. Modify only what is necessary.
4. Run the validation listed in the ticket.
5. Commit only if validation passes.
6. Stop before starting the next ticket.

Do not blindly edit files named in a ticket if the current codebase shows a better location.
Do not append override blocks.
Do not duplicate functions.
Do not make broad rewrites.
Do not continue if validation fails.
