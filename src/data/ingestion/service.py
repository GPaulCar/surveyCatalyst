from __future__ import annotations

import json

from core.db import build_backend
from data.ingestion.registry import PROVIDERS, get_provider


class RealIngestionService:
    def __init__(self):
        self.backend = build_backend()

    def _start_run(self, source_key: str, mode: str) -> int:
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO ingestion_runs (source_key, status, message, layer_keys)
                VALUES (%s, 'running', %s, '[]'::jsonb)
                RETURNING id
                ''',
                (source_key, mode),
            )
            run_id = cur.fetchone()[0]
        conn.commit()
        return run_id

    def _finish_run(self, run_id: int, result) -> None:
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
                (
                    result.status,
                    result.message,
                    result.records_loaded,
                    json.dumps(result.layer_keys),
                    run_id,
                ),
            )
        conn.commit()

    def dry_run_one(self, source_key: str):
        provider = get_provider(source_key)()
        run_id = self._start_run(source_key, "dry_run")
        try:
            result = provider.dry_run()
            self._finish_run(run_id, result)
            return result
        except Exception as exc:
            class Failed:
                status = "failed"
                message = str(exc)
                records_loaded = 0
                layer_keys = []
            self._finish_run(run_id, Failed())
            raise

    def run_one(self, source_key: str, force: bool = False):
        provider = get_provider(source_key)()
        run_id = self._start_run(source_key, "run")
        try:
            result = provider.run(force=force)
            self._finish_run(run_id, result)
            return result
        except Exception as exc:
            class Failed:
                status = "failed"
                message = str(exc)
                records_loaded = 0
                layer_keys = []
            self._finish_run(run_id, Failed())
            raise

    def list_sources(self):
        return sorted(PROVIDERS.keys())
