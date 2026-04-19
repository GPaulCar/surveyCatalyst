import json
from core.db import build_backend

class ExportService:
    def __init__(self):
        self.backend = build_backend()

    def export_layer(self, layer_key, path):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ST_AsGeoJSON(geom) FROM external_features WHERE layer=%s",
                (layer_key,)
            )
            features = [json.loads(r[0]) for r in cur.fetchall()]
        with open(path, "w") as f:
            json.dump({"type": "FeatureCollection", "features": features}, f)
        return path
