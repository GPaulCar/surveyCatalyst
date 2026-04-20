from __future__ import annotations

from data.ingestion.base import BaseProvider, ProviderResult


class GESISProvider(BaseProvider):
    source_key = "gesis"
    source_name = "GESIS Bavaria Economy"
    schema_name = "economic"
    workspace_name = "gesis"

    LANDING_URL = "https://www.gesis.org/en/landingpage/data-gesis"

    def dry_run(self) -> ProviderResult:
        return ProviderResult(
            source_key=self.source_key,
            status="success",
            message="GESIS landing page recorded; exact dataset endpoint still manual-assisted",
            artifacts=[self.LANDING_URL],
            metadata={"landing_url": self.LANDING_URL},
        )

    def run(self, force: bool = False) -> ProviderResult:
        self.create_schema()
        self.register_layer(
            "economic_mining_locations",
            "Mining Locations",
            "economic.mining_locations",
            "POINT",
            {"source_key": self.source_key, "landing_url": self.LANDING_URL, "mode": "manual_assisted"},
            sort_order=240,
        )
        return ProviderResult(
            source_key=self.source_key,
            status="success",
            message="GESIS economic layer registered; dataset acquisition remains manual-assisted",
            records_loaded=0,
            layer_keys=["economic_mining_locations"],
            artifacts=[self.LANDING_URL],
        )
