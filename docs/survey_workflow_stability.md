# Survey Workflow Stability

Updated after the geometry-edit repair and API/schema alignment.

## Stable flow

1. Start the local stack with `python scripts/system_control.py restart`.
2. Load `/api/surveys` and select the survey you want to work on.
3. Create a survey with GeoJSON geometry.
4. Select the survey context, then load and zoom to the survey.
5. Create a survey object with GeoJSON geometry.
6. Select the object, use `Edit geometry`, then `Save geometry`.
7. Reload the survey hierarchy or features to confirm the geometry persisted.
8. Use the Basemap panel to switch background maps while keeping survey and object layers intact.

## Request limit

The survey feature endpoints use a bounded `limit` query parameter:

- `/api/surveys/{survey_id}/features`
- `/api/layers/{layer_key}/tiles/{z}/{x}/{y}.mvt`

The server defaults to `5000` features and caps the request at `20000`.
The current UI requests `20000` features when loading a survey so the visible working set stays predictable without pulling unbounded GeoJSON.

## Notes

- Survey geometry updates are persisted through the survey object PATCH endpoint.
- The frontend sends GeoJSON geometry, `type`, `properties`, `title`, `annotation`, `details`, and `is_active`.
- Basemap selection is a client-side background change in the Basemap panel, not a survey data change.
- Large background layers should continue to use the tile-backed path rather than direct JSON expansion.
