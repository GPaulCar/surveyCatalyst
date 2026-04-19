from __future__ import annotations

import json
from pathlib import Path

from export.export_service import ExportService


class LayerExportService:
    def __init__(self):
        self.exporter = ExportService()

    def write_layer_geojson(self, layer_key: str, out_path: str):
        data = self.exporter.export_layer_geojson(layer_key)
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path
