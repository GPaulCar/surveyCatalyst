from __future__ import annotations


class SelectionSyncService:
    def __init__(self, selection_contract, renderer):
        self.selection = selection_contract
        self.renderer = renderer
        self.selection.subscribe(self._on_selection)

    def _on_selection(self, item):
        item_type = item.get("item_type")
        item_id = item.get("item_id")
        payload = item.get("payload")

        if item_type == "survey":
            geom_wkt = None
            if isinstance(payload, dict):
                survey = payload.get("survey")
                if isinstance(survey, (list, tuple)) and len(survey) >= 5:
                    geom_wkt = survey[4]
            elif isinstance(payload, (list, tuple)) and len(payload) >= 5:
                geom_wkt = payload[4]
            self.renderer.focus_geometry(geom_wkt)
            self.renderer.set_selected("survey", item_id)

        elif item_type == "survey_object":
            geom_wkt = None
            layer_key = "survey_objects"
            if isinstance(payload, dict):
                geom_wkt = payload.get("geom")
                layer_key = payload.get("layer_key", layer_key)
            elif isinstance(payload, (list, tuple)):
                if len(payload) >= 6:
                    geom_wkt = payload[5]
                if len(payload) >= 3 and isinstance(payload[2], str):
                    layer_key = payload[2]
            self.renderer.focus_geometry(geom_wkt)
            self.renderer.highlight_feature(layer_key, item_id)
            self.renderer.set_selected("survey_object", item_id)
