from __future__ import annotations

import pandas as pd

from data.ingestion.base import BaseProvider, ProviderResult


class GESISProvider(BaseProvider):
    source_key = "gesis"
    source_name = "GESIS Bavaria Economy"
    schema_name = "economic"
    workspace_name = "gesis"

    MANUAL_DOWNLOAD_NOTES = "Manual download may still be required for the GESIS dataset archive."

    def run(self, force: bool = False) -> ProviderResult:
        self.create_schema()

        backend = self.backend
        conn = backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {self.schema_name}.bavaria_economy_raw CASCADE")
                cur.execute(
                    f'''
                    CREATE TABLE {self.schema_name}.bavaria_economy_raw (
                        id SERIAL PRIMARY KEY,
                        source_record JSONB NOT NULL
                    )
                    '''
                )
                cur.execute(f"DROP TABLE IF EXISTS {self.schema_name}.mining_locations CASCADE")
                cur.execute(
                    f'''
                    CREATE TABLE {self.schema_name}.mining_locations (
                        id SERIAL PRIMARY KEY,
                        year INTEGER,
                        location_name TEXT,
                        production_value DOUBLE PRECISION,
                        mineral_type TEXT,
                        geom geometry(POINT, 4326),
                        notes TEXT
                    )
                    '''
                )
                cur.execute(f"CREATE INDEX IF NOT EXISTS idx_mining_locations_geom ON {self.schema_name}.mining_locations USING GIST (geom)")
            conn.commit()
        finally:
            backend.close()

        self.register_layer(
            "economic_mining_locations",
            "Mining Locations",
            "economic.mining_locations",
            "POINT",
            {"source_key": self.source_key, "notes": self.MANUAL_DOWNLOAD_NOTES},
            sort_order=240,
        )

        return ProviderResult(
            source_key=self.source_key,
            status="success",
            message="GESIS target tables prepared; manual source load still required",
            records_loaded=0,
            layer_keys=["economic_mining_locations"],
            artifacts=[],
            version_label="1.0.0",
        )
