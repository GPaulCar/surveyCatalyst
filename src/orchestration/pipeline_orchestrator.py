from __future__ import annotations

from data.ingestion.service import RealIngestionService
from reporting.run_summary_service import RunSummaryService


class PipelineOrchestrator:
    def __init__(self):
        self.ingest = RealIngestionService()
        self.summary = RunSummaryService()

    def run_all_sources(self, force: bool = False):
        results = []
        for source in ["blfd", "itiner_e", "viabundus", "gesis"]:
            try:
                results.append(self.ingest.run_one(source, force=force))
            except Exception as exc:
                results.append({"source_key": source, "status": "failed", "message": str(exc)})
        return results

    def latest_summary(self):
        return self.summary.latest_runs(10)
