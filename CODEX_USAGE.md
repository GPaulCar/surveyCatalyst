# Codex Usage

Preferred workflow:

1. Copy this pack into the repository root.
2. Commit the backlog and tickets:
   ```bash
   git add CODEX_BACKLOG.md tickets/github_issues scripts/create_github_issues.py ticket_manifest.json
   git commit -m "Add SurveyCatalyst Codex backlog tickets"
   ```
3. Either point Codex at `CODEX_BACKLOG.md`, or import the tickets to GitHub Issues.

## Import to GitHub Issues

Dry run:
```bash
python scripts/create_github_issues.py --dry-run
```

Create all issues:
```bash
python scripts/create_github_issues.py
```

Create first issue only:
```bash
python scripts/create_github_issues.py --limit 1
```

## Codex instruction

Ask Codex:

Work one ticket at a time from CODEX_BACKLOG.md. Do not start the next ticket until validation passes and the previous ticket is committed.
