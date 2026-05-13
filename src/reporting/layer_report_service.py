from __future__ import annotations

from layers.layer_usage_service import LayerUsageService


class LayerReportService:
    def summary(self):
        return LayerUsageService().list_layers()
