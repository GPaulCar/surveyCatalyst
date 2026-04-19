from __future__ import annotations

from survey.edit_service import SurveyEditService
from survey.query_service import SurveyQueryService
from ui.selection_contract import SelectionContract


class DrawingIngestController:
    def __init__(self, selection_contract: SelectionContract):
        self.selection = selection_contract
        self.edit = SurveyEditService()
        self.query = SurveyQueryService()

    def create_survey_from_polygon(self, expedition_id: int, title: str, polygon_wkt: str):
        survey_id, layer_key = self.edit.create_survey(expedition_id, title, polygon_wkt)
        survey = self.query.get_survey(survey_id)
        self.selection.select("survey", survey_id, survey)
        return {
            "survey_id": survey_id,
            "layer_key": layer_key,
            "survey": survey,
        }

    def add_object_to_survey(self, survey_id: int, expedition_id: int, obj_type: str, geom_wkt: str, properties: dict | None = None):
        object_id = self.edit.create_survey_object(survey_id, expedition_id, obj_type, geom_wkt, properties)
        row = None
        objects = self.query.list_survey_objects(survey_id)
        for candidate in objects:
            if candidate[0] == object_id:
                row = candidate
                break
        self.selection.select("survey_object", object_id, row)
        return object_id

    def update_object(self, object_id: int, geom_wkt: str, properties: dict | None = None):
        self.edit.update_survey_object(object_id, geom_wkt, properties)

    def archive_object(self, object_id: int):
        self.edit.archive_survey_object(object_id)
