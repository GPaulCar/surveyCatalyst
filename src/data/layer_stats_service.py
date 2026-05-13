from layers.layer_usage_service import LayerUsageService


class LayerStatsService:
    def summary(self):
        return LayerUsageService().list_layers()
