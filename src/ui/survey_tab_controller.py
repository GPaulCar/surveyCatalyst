from __future__ import annotations

from survey.query_service import SurveyQueryService
from ui.selection_contract import SelectionContract


class SurveyTabController:
    def __init__(self, selection_contract: SelectionContract):
        self.selection = selection_contract
        self.surveys = SurveyQueryService()

    def list_surveys(self):
        return self.surveys.list_surveys()

    def open_survey(self, survey_id: int):
        survey = self.surveys.get_survey(survey_id)
        objects = self.surveys.list_survey_objects(survey_id)
        features = self.surveys.linked_and_contained_features(survey_id)
        self.selection.select("survey", survey_id, survey)
        return {
            "survey": survey,
            "objects": objects,
            "features": features,
        }

    def select_object(self, object_id: int, payload=None):
        self.selection.select("survey_object", object_id, payload)
