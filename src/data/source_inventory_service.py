from __future__ import annotations

from core.db import build_backend


class SourceInventoryService:
    def __init__(self):
        self.backend = build_backend()

    def inventory(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT source_key, source_name, provider_class, is_enabled, default_schema_name
                FROM ingestion_sources
                ORDER BY source_key
                '''
            )
            return cur.fetchall()
