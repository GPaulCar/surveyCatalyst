from __future__ import annotations

import json
from pathlib import Path

from core.db import build_backend


class ExportPackService:
    def __init__(self):
        self.backend = build_backend()

    def export_all_layers(self, target_dir: Path):
        target_dir.mkdir(parents=True, exist_ok=True)

        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT layer FROM external_features ORDER BY layer")
            layers = [r[0] for r in cur.fetchall()]

        outputs = []
        for layer in layers:
            data = self._export_layer(layer)
            out_file = target_dir / f"{layer}.geojson"
            out_file.write_text(json.dumps(data))
            outputs.append(str(out_file))

        return outputs

    def _export_layer(self, layer_key: str):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT jsonb_build_object(
                    'type','FeatureCollection',
                    'features', COALESCE(jsonb_agg(
                        jsonb_build_object(
                            'type','Feature',
                            'geometry', ST_AsGeoJSON(geom)::jsonb,
                            'properties', properties
                        )
                    ), '[]'::jsonb)
                )
                FROM external_features
                WHERE layer = %s
                ''',
                (layer_key,)
            )
            return cur.fetchone()[0]
