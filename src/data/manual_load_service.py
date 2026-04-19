from __future__ import annotations

import json
from pathlib import Path

from core.db import build_backend


class ManualLoadService:
    def __init__(self):
        self.backend = build_backend()

    def load_geojson_file(self, layer_key: str, geojson_path: str):
        path = Path(geojson_path)
        if not path.exists():
            raise RuntimeError(f"Missing file: {path}")

        payload = json.loads(path.read_text(encoding="utf-8"))
        features = payload.get("features", [])

        conn = self.backend.connect()
        inserted = 0
        with conn.cursor() as cur:
            for feature in features:
                geometry = feature.get("geometry")
                properties = feature.get("properties") or {}
                geometry_json = json.dumps(geometry)
                cur.execute(
                    '''
                    INSERT INTO external_features (layer, geom, properties)
                    VALUES (%s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326), %s::jsonb)
                    RETURNING id
                    ''',
                    (layer_key, geometry_json, json.dumps(properties)),
                )
                cur.fetchone()
                inserted += 1
        conn.commit()
        return inserted
