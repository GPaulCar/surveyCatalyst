# Codex Execution Guardrails for SurveyCatalyst

These rules override individual ticket wording where there is a conflict.

## Prime directive

The tickets describe intended outcomes, not mandatory file edits.

Codex must inspect the current repository before changing anything and must choose the safest implementation path based on the current codebase.

## Required workflow for every ticket

1. Read the ticket.
2. Inspect the repository before editing.
3. Identify the actual files/functions currently responsible.
4. Produce a short implementation plan.
5. Make the smallest coherent change.
6. Run validation commands.
7. Commit only if validation passes.
8. Do not start the next ticket until the current ticket is validated and committed.

## Never blindly follow file paths

Ticket file paths are hints only.

If a ticket says to edit a file that is no longer the right location, Codex must:
- locate the current implementation,
- use the current architecture,
- note the changed file choice in the final summary.

## Do not break working flows

Before and after each ticket, preserve these flows unless the ticket specifically targets them:

- API starts.
- `GET /api/surveys` works.
- Survey dropdown loads surveys.
- Selecting a survey loads features.
- Zoom works.
- Create survey persists, appears, auto-selects, and displays geometry.
- Existing layers still render.
- Existing map interaction still works.

## No override stacking

Do not add:
- duplicate `surveyBody`
- duplicate `leftBody`
- duplicate `rightBody`
- duplicate `loadSurveys`
- duplicate `update_survey_object`
- IIFE runtime override blocks appended to `ui_boot.js`

Modify the existing source of truth instead.

## No broad rewrites

Avoid:
- framework rewrites,
- unrelated UI redesign,
- system-control rewrites unless directly required,
- large formatting churn,
- changes across many files without justification.

## File safety

Before editing high-risk files, inspect and understand them:
- `src/survey/edit_service.py`
- `src/api/app.py`
- `src/api/schemas.py`
- `app/static/ui_boot.js`
- `scripts/system_control.py`

If a file has syntax errors before the ticket starts, fix syntax first and commit that separately if needed.

## Ticket interpretation rules

Each ticket has:
- Goal = required outcome.
- Scope = likely area, not fixed target.
- Tasks = preferred approach, not blind instructions.
- Validation = mandatory checks.

If current code already satisfies part of a ticket, do not reimplement it. Document that it already exists.

## Stop conditions

Stop and report instead of guessing if:
- validation fails twice,
- there are duplicate conflicting implementations,
- a source endpoint/license is unclear,
- a data provider has no accessible machine-readable endpoint,
- implementing the ticket would require a broad redesign.

## Required final response per ticket

Codex must report:

- Ticket ID.
- Files inspected.
- Files changed.
- Actual implementation chosen.
- Why that implementation fits the current codebase.
- Validation commands run.
- Validation results.
- Remaining risks or limitations.
- Commit hash if committed.

## Commit rules

One ticket = one commit, unless a preliminary repair is needed.

Recommended commit message format:

`SC-001 Stabilise survey edit service`

Do not bundle unrelated tickets into one commit.
