from __future__ import annotations

import requests

from data.ingestion.base import BaseProvider, ProviderResult


class ItinerEProvider(BaseProvider):
    source_key = "itiner_e"
    source_name = "Itiner-e Roman Roads"
    schema_name = "ancient"
    workspace_name = "itiner_e"

    ZENODO_API = "https://zenodo.org/api/records/17122148"

    def run(self, force: bool = False) -> ProviderResult:
        self.create_schema()

        response = requests.get(self.ZENODO_API, timeout=60)
        response.raise_for_status()
        data = response.json()
        version_label = data.get("metadata", {}).get("version", "unknown")

        zip_url = None
        for file_info in data.get("files", []):
            if file_info["key"].endswith(".zip"):
                zip_url = file_info["links"]["self"]
                break
        if not zip_url:
            raise RuntimeError("No ZIP file found for Itiner-e")

        zip_path = self.download_file(zip_url, self.workspace / "itiner_e_latest.zip")
        self.write_artifact_record("zip", zip_path, zip_url, version_label)

        extract_dir = self.extract_zip(zip_path, self.workspace / "extracted")
        gpkg_files = list(extract_dir.rglob("*.gpkg"))
        shp_files = list(extract_dir.rglob("*.shp"))

        table_name = "roman_roads"
        if gpkg_files:
            self.import_with_ogr2ogr(gpkg_files[0], table_name)
        elif shp_files:
            self.import_with_ogr2ogr(shp_files[0], table_name)
        else:
            raise RuntimeError("No GPKG or shapefile found in Itiner-e archive")

        self.register_layer(
            "ancient_roman_roads",
            "Roman Roads",
            "ancient.roman_roads",
            "LINESTRING",
            {"source_key": self.source_key, "version_label": version_label},
            sort_order=210,
        )

        return ProviderResult(
            source_key=self.source_key,
            status="success",
            message="Itiner-e imported",
            records_loaded=0,
            layer_keys=["ancient_roman_roads"],
            artifacts=[str(zip_path)],
            version_label=version_label,
        )
