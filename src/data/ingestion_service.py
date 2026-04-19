from __future__ import annotations

from data.ingestion_registry import IngestionRegistry


class IngestionService:
    def __init__(self):
        self.registry = IngestionRegistry()

    def status(self):
        return {"sources": self.registry.list_sources(), "mode": "planned"}
