from __future__ import annotations

from ui.drawing_ingest_controller import DrawingIngestController


class SurveyObjectWorkflowService:
    def __init__(self, selection_contract):
        self.controller = DrawingIngestController(selection_contract)

    def create_object(self, survey_id: int, expedition_id: int, obj_type: str, geom_wkt: str, properties: dict | None = None):
        return self.controller.add_object_to_survey(survey_id, expedition_id, obj_type, geom_wkt, properties)

    def update_object(self, object_id: int, geom_wkt: str, properties: dict | None = None):
        self.controller.update_object(object_id, geom_wkt, properties)
        return {"object_id": object_id, "updated": True}

    def archive_object(self, object_id: int):
        self.controller.archive_object(object_id)
        return {"object_id": object_id, "archived": True}
