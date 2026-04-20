from __future__ import annotations


class SourceStyleRegistry:
    def style_for_layer(self, layer_key: str):
        if layer_key.startswith("legal_"):
            return {"stroke": "#b00020", "fill": "#ffdde3", "weight": 2}
        if layer_key.startswith("economic_"):
            return {"marker": "circle", "radius": 6}
        if layer_key.startswith("ancient_"):
            return {"stroke": "#7b4f2a", "weight": 2}
        if layer_key.startswith("medieval_"):
            return {"stroke": "#355caa", "weight": 2}
        return {"stroke": "#666666", "weight": 1}
