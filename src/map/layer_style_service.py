from __future__ import annotations


class LayerStyleService:
    def style_for_layer(self, layer_key: str):
        if layer_key.startswith("legal_"):
            return {"stroke": "#cc0000", "fill": "#ffcccc", "weight": 2}
        if layer_key.startswith("economic_"):
            return {"marker": "circle", "radius": 6}
        if layer_key.startswith("ancient_"):
            return {"stroke": "#8b5a2b", "weight": 2}
        if layer_key.startswith("medieval_"):
            return {"stroke": "#4b6cb7", "weight": 2}
        if layer_key.startswith("survey_") or layer_key == "surveys":
            return {"stroke": "#009966", "fill": "#ccffdd", "weight": 2}
        return {"stroke": "#666666", "weight": 1}
