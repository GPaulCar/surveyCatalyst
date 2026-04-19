from __future__ import annotations

from ui.drawing_ingest_controller import DrawingIngestController


class SurveyWorkflowService:
    def __init__(self, selection_contract):
        self.controller = DrawingIngestController(selection_contract)

    def create_survey(self, expedition_id: int, title: str, polygon_wkt: str):
        return self.controller.create_survey_from_polygon(expedition_id, title, polygon_wkt)

    def update_boundary(self, survey_id: int, polygon_wkt: str):
        self.controller.edit.update_survey_geometry(survey_id, polygon_wkt)
        return {"survey_id": survey_id, "updated": True}
