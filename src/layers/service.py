class LayerService:
    def __init__(self):
        self.layers = []

    def add_layer(self, name, group):
        self.layers.append({"name": name, "group": group, "visible": True, "opacity": 1.0})

    def list_layers(self):
        return self.layers

    def set_visibility(self, name, visible):
        for l in self.layers:
            if l["name"] == name:
                l["visible"] = visible

    def set_opacity(self, name, opacity):
        for l in self.layers:
            if l["name"] == name:
                l["opacity"] = opacity
