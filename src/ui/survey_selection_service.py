from survey.query_service import SurveyQueryService


class SurveySelectionService:
    def __init__(self, selection_contract, renderer):
        self.selection = selection_contract
        self.renderer = renderer
        self.query = SurveyQueryService()

    def select_survey(self, survey_id: int):
        survey = self.query.get_survey(survey_id)
        if survey is None:
            raise RuntimeError(f"Survey {survey_id} not found")

        self.selection.select("survey", survey_id, survey)
        return survey

    def select_survey_object(self, object_row):
        object_id = object_row[0]
        layer_key = object_row[2]  # assumes layer_key is column 2

        self.selection.select("survey_object", object_id, object_row)
        self.renderer.highlight_feature(layer_key, object_id)

        return object_row
