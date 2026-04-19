from __future__ import annotations


class SurveyPanelBridge:
    def __init__(self, selection_contract, renderer):
        self.selection = selection_contract
        self.renderer = renderer
        self.selection.subscribe(self._on_select)

    def _on_select(self, item):
        if item["item_type"] == "survey_object":
            payload = item.get("payload") or {}
            geom = payload.get("geom")
            self.renderer.focus_geometry(geom)
