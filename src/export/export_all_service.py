import json
from core.db import build_backend


class ExportAllService:
    def run(self, path):
        conn = build_backend().connect()
        with conn.cursor() as cur:
            cur.execute("SELECT layer, ST_AsGeoJSON(geom) FROM external_features")
            rows = cur.fetchall()

        data = {}
        for layer, geom in rows:
            data.setdefault(layer, []).append(json.loads(geom) if geom else None)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return path
