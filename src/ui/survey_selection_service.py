from __future__ import annotations

from survey.query_service import SurveyQueryService
from ui.selection_contract import SelectionContract


class SurveySelectionService:
    def __init__(self, selection_contract: SelectionContract):
        self.selection = selection_contract
        self.query = SurveyQueryService()

    def select_survey(self, survey_id: int):
        survey = self.query.get_survey(survey_id)
        if survey is None:
            raise RuntimeError(f"Survey {survey_id} not found")
        self.selection.select("survey", survey_id, survey)
        return survey

    def select_survey_object(self, object_row):
        object_id = object_row[0]
        self.selection.select("survey_object", object_id, object_row)
        return object_row
