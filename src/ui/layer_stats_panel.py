from data.layer_stats_service import LayerStatsService


class LayerStatsPanel:
    def load(self):
        return LayerStatsService().summary()
