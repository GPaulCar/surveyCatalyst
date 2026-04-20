from __future__ import annotations

from data.ingestion.base import BaseProvider, ProviderResult


class BLfDProvider(BaseProvider):
    source_key = "blfd"
    source_name = "BLfD Restricted Areas"
    schema_name = "legal"
    workspace_name = "blfd"

    SERVICE_PAGE = "https://geoportal.bayern.de/geoportalbayern/anwendungen/details?resId=752ebf39-f3eb-44be-893e-3b0624273061"
    WMS_URL = "https://gdiserv.bayern.de/srv24352/services/inspire_ps_denkmal_simpl-wms"
    WFS_URL = "https://gdiserv.bayern.de/srv24352/services/inspire_ps_denkmal_simpl-wfs"

    def dry_run(self) -> ProviderResult:
        return ProviderResult(
            source_key=self.source_key,
            status="success",
            message="BLfD service endpoints recorded",
            artifacts=[self.SERVICE_PAGE, self.WMS_URL, self.WFS_URL],
            metadata={"service_page": self.SERVICE_PAGE, "wms_url": self.WMS_URL, "wfs_url": self.WFS_URL},
        )

    def run(self, force: bool = False) -> ProviderResult:
        self.create_schema()
        self.register_layer(
            "legal_restricted_areas",
            "Restricted Areas",
            "legal.restricted_areas",
            "POLYGON",
            {"source_key": self.source_key, "wms_url": self.WMS_URL, "wfs_url": self.WFS_URL},
            sort_order=230,
        )
        return ProviderResult(
            source_key=self.source_key,
            status="success",
            message="BLfD endpoints recorded and legal layer registered; service-backed ingest step pending",
            records_loaded=0,
            layer_keys=["legal_restricted_areas"],
            artifacts=[self.WMS_URL, self.WFS_URL],
        )
