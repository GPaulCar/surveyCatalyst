from __future__ import annotations

from ui.selection_contract import SelectionContract


class MapSelectionBridge:
    def __init__(self, selection_contract: SelectionContract, map_controller):
        self.selection = selection_contract
        self.map_controller = map_controller
        self.selection.subscribe(self._on_select)

    def _on_select(self, item):
        item_type = item.get("item_type")
        payload = item.get("payload")
        if item_type == "survey" and payload:
            self.map_controller.focus_geometry(payload[-1])
        elif item_type == "survey_object" and payload:
            geom = payload[-1] if isinstance(payload, (list, tuple)) and payload else None
            self.map_controller.focus_geometry(geom)
