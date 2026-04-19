from __future__ import annotations


class DetailsStateService:
    def __init__(self, selection_contract):
        self.selection = selection_contract
        self.current = None
        self.selection.subscribe(self._on_select)

    def _on_select(self, item):
        self.current = item

    def get_current_details(self):
        return self.current
