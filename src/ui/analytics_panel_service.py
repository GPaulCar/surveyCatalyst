from analytics.aggregation_service import AggregationService

class AnalyticsPanelService:
    def summary(self):
        return AggregationService().count_by_layer()
