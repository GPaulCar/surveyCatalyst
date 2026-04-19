from __future__ import annotations

import json
from pathlib import Path

from core.db import build_backend


class BackupManifestService:
    def __init__(self):
        self.backend = build_backend()

    def build_manifest(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM surveys")
            surveys = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM survey_objects")
            survey_objects = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM external_features")
            external_features = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM ingestion_runs")
            ingestion_runs = cur.fetchone()[0]
        return {
            "surveys": surveys,
            "survey_objects": survey_objects,
            "external_features": external_features,
            "ingestion_runs": ingestion_runs,
        }

    def write_manifest(self, path: str | Path):
        path = Path(path)
        path.write_text(json.dumps(self.build_manifest(), indent=2), encoding="utf-8")
        return path
