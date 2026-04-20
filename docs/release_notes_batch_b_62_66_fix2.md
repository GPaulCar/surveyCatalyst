# Batch B (62-66) Fix 2

## Fixed
- Itiner-e provider no longer assumes Zenodo must expose a ZIP
- falls back to direct-file mode when the record exposes individual downloadable files
- dry-run now succeeds when the record contains files but no archive
