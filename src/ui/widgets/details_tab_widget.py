from __future__ import annotations

from ui.details_state_service import DetailsStateService


class DetailsTabWidget:
    def __init__(self, selection_contract):
        self.service = DetailsStateService(selection_contract)

    def load(self):
        return self.service.get_current_details()
