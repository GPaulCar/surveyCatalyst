---
id: SC-002
title: Stabilise frontend survey/object selection pipeline and edit panel
priority: Critical
labels: frontend,ui,stabilisation
---

# SC-002 - Stabilise frontend survey/object selection pipeline and edit panel

**Priority:** Critical
**Labels:** frontend,ui,stabilisation

## Goal
Make the Edit panel reliably recognise selected surveys and selected survey objects.

## Scope
File:
- `app/static/ui_boot.js`

## Tasks
- Identify all competing selection variables.
- Consolidate to one canonical selection model:
```javascript
state.selection = {
  type: null,
  surveyId: null,
  objectId: null,
  feature: null,
  properties: null
}
```
- Repair `map.on("singleclick", ...)` so it populates `state.selection` consistently.
- Object clicks populate `type: "object"`, `surveyId`, `objectId`, `feature`, `properties`.
- Survey boundary clicks populate `type: "survey"`, `surveyId`, `feature`, `properties`.
- Render Edit tab from `state.selection` only.
- No selection: show clear empty state.
- Survey selected: show survey editor/summary.
- Object selected: show title/note/type/geometry controls.
- Avoid duplicate `surveyBody`, `leftBody`, `loadSurveys`, or runtime override blocks.

## Validation
- Clicking survey boundary updates edit/details state.
- Clicking survey object updates edit/details state.
- Edit tab renders full controls for selected object.
- Save attributes works.
- Save geometry works once SC-001 is complete.
- No blank edit panel.
- No console syntax errors.
