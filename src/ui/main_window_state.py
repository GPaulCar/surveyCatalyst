from __future__ import annotations

from ui.selection_contract import SelectionContract
from ui.details_state_service import DetailsStateService
from ui.survey_browser_service import SurveyBrowserService
from ui.layers_panel_service import LayersPanelService
from ui.console_renderer import ConsoleRenderer
from ui.map_panel_bridge import MapPanelBridge
from ui.layer_selection_bridge import LayerSelectionBridge
from ui.survey_panel_bridge import SurveyPanelBridge
from map.controller import MapController


class MainWindowState:
    def __init__(self):
        self.selection = SelectionContract()
        self.renderer = ConsoleRenderer()
        self.map_controller = MapController(self.renderer, self.selection)

        self.details = DetailsStateService(self.selection)
        self.survey_browser = SurveyBrowserService(self.selection)
        self.layers_panel = LayersPanelService(self.selection, self.map_controller)

        self.map_bridge = MapPanelBridge(self.selection, self.renderer)
        self.layer_bridge = LayerSelectionBridge(self.selection, self.renderer)
        self.survey_bridge = SurveyPanelBridge(self.selection, self.renderer)

    def load(self):
        return {
            "layers": self.layers_panel.load_panel_state(),
            "surveys": self.survey_browser.list_surveys_with_objects(),
            "details": self.details.get_current_details(),
        }
