from __future__ import annotations

from survey.query_service import SurveyQueryService
from ui.selection_contract import SelectionContract


class SurveyBrowserService:
    def __init__(self, selection_contract: SelectionContract):
        self.selection = selection_contract
        self.query = SurveyQueryService()

    def list_surveys_with_objects(self):
        surveys = self.query.list_surveys()
        result = []
        for survey in surveys:
            survey_id = survey[0]
            objects = self.query.list_survey_objects(survey_id)
            result.append(
                {
                    "survey": survey,
                    "objects": objects,
                    "object_count": len(objects),
                }
            )
        return result

    def select_survey(self, survey_id: int):
        survey = self.query.get_survey(survey_id)
        if survey is None:
            raise RuntimeError(f"Survey {survey_id} not found")

        objects = self.query.list_survey_objects(survey_id)
        features = self.query.linked_and_contained_features(survey_id)

        payload = {
            "survey": survey,
            "objects": objects,
            "features": features,
        }
        self.selection.select("survey", survey_id, payload)
        return payload

    def select_object(self, survey_id: int, object_id: int):
        objects = self.query.list_survey_objects(survey_id)
        selected = None
        for row in objects:
            if row[0] == object_id:
                selected = row
                break
        if selected is None:
            raise RuntimeError(f"Survey object {object_id} not found in survey {survey_id}")

        self.selection.select("survey_object", object_id, selected)
        return selected
