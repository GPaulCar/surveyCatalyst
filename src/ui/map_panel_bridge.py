from __future__ import annotations


class MapPanelBridge:
    def __init__(self, selection_contract, renderer):
        self.selection = selection_contract
        self.renderer = renderer
        self.selection.subscribe(self._on_selection)

    def _on_selection(self, item):
        item_type = item.get("item_type")
        item_id = item.get("item_id")
        payload = item.get("payload")

        if item_type == "survey":
            survey_row = payload.get("survey") if isinstance(payload, dict) else None
            if survey_row and len(survey_row) >= 5:
                geom_wkt = survey_row[4]
                self.renderer.focus_geometry(geom_wkt)
                self.renderer.set_selected("survey", item_id)

        elif item_type == "survey_object":
            geom_wkt = payload[5] if isinstance(payload, (list, tuple)) and len(payload) >= 6 else None
            layer_key = payload[3] if isinstance(payload, (list, tuple)) and len(payload) >= 4 else None
            self.renderer.focus_geometry(geom_wkt)
            self.renderer.highlight_feature(layer_key or "survey_objects", item_id)
            self.renderer.set_selected("survey_object", item_id)
