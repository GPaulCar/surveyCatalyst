from __future__ import annotations

from ui.survey_browser_service import SurveyBrowserService


class SurveyTabWidget:
    def __init__(self, selection_contract):
        self.service = SurveyBrowserService(selection_contract)

    def load(self):
        return self.service.list_surveys_with_objects()

    def open_survey(self, survey_id: int):
        return self.service.select_survey(survey_id)

    def open_object(self, survey_id: int, object_id: int):
        return self.service.select_object(survey_id, object_id)
