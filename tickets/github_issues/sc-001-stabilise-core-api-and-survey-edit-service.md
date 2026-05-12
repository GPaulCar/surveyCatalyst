---
id: SC-001
title: Stabilise core API and survey edit service
priority: Critical
labels: stabilisation,backend,critical
---

# SC-001 - Stabilise core API and survey edit service

**Priority:** Critical
**Labels:** stabilisation,backend,critical

## Goal
Restore backend stability and stabilise the core survey object edit path.

## Context
The API has previously failed to start because `src/survey/edit_service.py` contained duplicate/malformed `update_survey_object` definitions and an `IndentationError`. Before that, `PATCH /api/survey-objects/{object_id}` returned HTTP 500 during Save Geometry.

## Scope
Files to inspect:
- `src/survey/edit_service.py`
- `src/api/app.py`
- `src/api/schemas.py`

## Tasks
- Repair `src/survey/edit_service.py` so it compiles.
- Ensure `SurveyEditService.update_survey_object` exists exactly once.
- Keep the method inside `class SurveyEditService` with correct 4-space method indentation.
- Ensure the method accepts frontend payload fields: `geometry`, `type`, `properties`, `title`, `annotation`, `details`, `is_active`.
- Ensure GeoJSON geometry persists correctly to PostGIS.
- Preserve existing create/delete/list behaviour.
- Improve error visibility in the API route only if necessary.

## Validation
```powershell
python -m py_compile src\survey\edit_service.py
python -m py_compile src\api\app.py
python -m py_compile src\api\schemas.py
python scripts\system_control.py restart
```

Functional:
- API starts.
- `GET /api/surveys` returns records.
- Select survey object.
- Edit geometry.
- Save geometry.
- `PATCH /api/survey-objects/{object_id}` returns 200.
- Reload confirms geometry persisted.

## Do not
- Rewrite frontend UI.
- Add duplicate service methods.
- Add placeholder code.
