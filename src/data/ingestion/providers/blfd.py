from __future__ import annotations

from data.ingestion.base import BaseProvider, ProviderResult


class BLfDProvider(BaseProvider):
    source_key = "blfd"
    source_name = "BLfD Restricted Areas"
    schema_name = "legal"
    workspace_name = "blfd"

    WMS_URL = "https://gdiserv.bayern.de/srv24352/services/inspire_ps_denkmal_simpl-wms"
    WFS_URL = "https://gdiserv.bayern.de/srv24352/services/inspire_ps_denkmal_simpl-wfs"

    def run(self, force: bool = False) -> ProviderResult:
        self.create_schema()

        backend = self.backend
        conn = backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {self.schema_name}.restricted_areas CASCADE")
                cur.execute(
                    f'''
                    CREATE TABLE {self.schema_name}.restricted_areas (
                        id SERIAL PRIMARY KEY,
                        name TEXT,
                        category TEXT,
                        source TEXT NOT NULL DEFAULT 'manual_or_wfs',
                        geom geometry(POLYGON, 4326),
                        properties JSONB NOT NULL DEFAULT '{{}}'::jsonb
                    )
                    '''
                )
                cur.execute(f"CREATE INDEX IF NOT EXISTS idx_restricted_areas_geom ON {self.schema_name}.restricted_areas USING GIST (geom)")
            conn.commit()
        finally:
            backend.close()

        self.register_layer(
            "legal_restricted_areas",
            "Restricted Areas",
            "legal.restricted_areas",
            "POLYGON",
            {"source_key": self.source_key, "wfs_url": self.WFS_URL, "wms_url": self.WMS_URL},
            sort_order=230,
        )

        return ProviderResult(
            source_key=self.source_key,
            status="success",
            message="BLfD table prepared (manual or WFS ingest target)",
            records_loaded=0,
            layer_keys=["legal_restricted_areas"],
            artifacts=[],
            version_label="date_based",
        )
