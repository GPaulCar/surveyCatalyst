from __future__ import annotations

import json

from core.db import build_backend
from data.ingestion.registry import PROVIDERS, get_provider


class IngestionService:
    def __init__(self):
        self.backend = build_backend()

    def _start_run(self, source_key: str) -> int:
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO ingestion_runs (source_key, status, message)
                VALUES (%s, 'running', 'started')
                RETURNING id
                ''',
                (source_key,),
            )
            run_id = cur.fetchone()[0]
        conn.commit()
        return run_id

    def _finish_run(self, run_id: int, status: str, message: str, records_loaded: int = 0, layer_keys: list[str] | None = None):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE ingestion_runs
                SET completed_at = NOW(),
                    status = %s,
                    message = %s,
                    records_loaded = %s,
                    layer_keys = %s::jsonb
                WHERE id = %s
                ''',
                (status, message, records_loaded, json.dumps(layer_keys or []), run_id),
            )
        conn.commit()

    def run_one(self, source_key: str, force: bool = False):
        provider = get_provider(source_key)()
        run_id = self._start_run(source_key)
        try:
            result = provider.run(force=force)
            self._finish_run(
                run_id,
                result.status,
                result.message,
                result.records_loaded,
                result.layer_keys,
            )
            return result
        except Exception as exc:
            self._finish_run(run_id, "failed", str(exc), 0, [])
            raise

    def run_all(self, force: bool = False):
        results = {}
        for source_key in PROVIDERS:
            try:
                results[source_key] = self.run_one(source_key, force=force)
            except Exception as exc:
                results[source_key] = {"status": "failed", "message": str(exc)}
        return results
