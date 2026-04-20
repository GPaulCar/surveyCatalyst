from __future__ import annotations

import requests

from data.ingestion.base import BaseProvider, ProviderResult


class ItinerEProvider(BaseProvider):
    source_key = "itiner_e"
    source_name = "Itiner-e Roman Roads"
    schema_name = "ancient"
    workspace_name = "itiner_e"

    ZENODO_API = "https://zenodo.org/api/records/17122148"

    def _metadata(self):
        response = requests.get(self.ZENODO_API, timeout=60)
        response.raise_for_status()
        data = response.json()

        version_label = data.get("metadata", {}).get("version", "unknown")
        files = data.get("files", [])

        zip_url = None
        zip_name = None
        record_files = []

        for file_info in files:
            key = file_info.get("key", "")
            link = file_info.get("links", {}).get("self")
            if link:
                record_files.append({"key": key, "url": link})
            if key.endswith(".zip") and link:
                zip_url = link
                zip_name = key

        if zip_url:
            mode = "zip"
        elif record_files:
            mode = "direct_files"
        else:
            raise RuntimeError("No downloadable files found for Itiner-e")

        return {
            "version_label": version_label,
            "mode": mode,
            "zip_url": zip_url,
            "zip_name": zip_name,
            "record_files": record_files,
        }

    def dry_run(self) -> ProviderResult:
        meta = self._metadata()
        artifacts = [meta["zip_url"]] if meta["zip_url"] else [f["url"] for f in meta["record_files"][:10]]
        return ProviderResult(
            source_key=self.source_key,
            status="success",
            message=f"Itiner-e metadata resolved ({meta['mode']})",
            version_label=meta["version_label"],
            artifacts=[a for a in artifacts if a],
            metadata=meta,
        )

    def run(self, force: bool = False) -> ProviderResult:
        self.create_schema()
        meta = self._metadata()

        artifacts = []
        if meta["mode"] == "zip":
            zip_path = self.download_file(meta["zip_url"], self.workspace / meta["zip_name"])
            self.write_artifact_record("zip", zip_path, meta["zip_url"], meta["version_label"])
            artifacts.append(str(zip_path))
            message = "Itiner-e zip downloaded and layer registered; import step pending local ogr2ogr"
        else:
            for file_info in meta["record_files"]:
                key = file_info["key"]
                url = file_info["url"]
                target = self.workspace / key
                downloaded = self.download_file(url, target)
                self.write_artifact_record("file", downloaded, url, meta["version_label"])
                artifacts.append(str(downloaded))
            message = "Itiner-e record files downloaded and layer registered; assemble/import step pending local ogr2ogr"

        self.register_layer(
            "ancient_roman_roads",
            "Roman Roads",
            "ancient.roman_roads",
            "LINESTRING",
            {
                "source_key": self.source_key,
                "version_label": meta["version_label"],
                "mode": meta["mode"],
                "artifacts": artifacts,
            },
            sort_order=210,
        )

        return ProviderResult(
            source_key=self.source_key,
            status="success",
            message=message,
            records_loaded=0,
            layer_keys=["ancient_roman_roads"],
            artifacts=artifacts,
            version_label=meta["version_label"],
            metadata=meta,
        )
