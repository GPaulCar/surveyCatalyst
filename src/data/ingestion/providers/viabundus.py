from __future__ import annotations

from data.ingestion.base import BaseProvider, ProviderResult


class ViabundusProvider(BaseProvider):
    source_key = "viabundus"
    source_name = "Viabundus Transport Network"
    schema_name = "medieval"
    workspace_name = "viabundus"

    DOWNLOAD_URL = "https://zenodo.org/records/10828107"
    VERSION_LABEL = "1.3"

    def dry_run(self) -> ProviderResult:
        return ProviderResult(
            source_key=self.source_key,
            status="success",
            message="Viabundus download URL resolved",
            version_label=self.VERSION_LABEL,
            artifacts=[self.DOWNLOAD_URL],
            metadata={"download_url": self.DOWNLOAD_URL, "version_label": self.VERSION_LABEL},
        )

    def run(self, force: bool = False) -> ProviderResult:
        self.create_schema()
        zip_path = self.download_file(self.DOWNLOAD_URL, self.workspace / "viabundus-1-3.zip")
        self.write_artifact_record("zip", zip_path, self.DOWNLOAD_URL, self.VERSION_LABEL)

        self.register_layer(
            "medieval_viabundus_nodes",
            "Viabundus Nodes",
            "medieval.viabundus_nodes",
            "POINT",
            {"source_key": self.source_key, "artifact": str(zip_path)},
            sort_order=220,
        )
        self.register_layer(
            "medieval_viabundus_edges",
            "Viabundus Edges",
            "medieval.viabundus_edges",
            "LINESTRING",
            {"source_key": self.source_key, "artifact": str(zip_path)},
            sort_order=221,
        )
        return ProviderResult(
            source_key=self.source_key,
            status="success",
            message="Viabundus archive downloaded and layers registered; CSV import step pending",
            records_loaded=0,
            layer_keys=["medieval_viabundus_nodes", "medieval_viabundus_edges"],
            artifacts=[str(zip_path)],
            version_label=self.VERSION_LABEL,
        )
