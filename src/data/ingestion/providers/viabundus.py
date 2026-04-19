from __future__ import annotations

import pandas as pd

from data.ingestion.base import BaseProvider, ProviderResult


class ViabundusProvider(BaseProvider):
    source_key = "viabundus"
    source_name = "Viabundus Transport"
    schema_name = "medieval"
    workspace_name = "viabundus"

    DOWNLOAD_URL = "https://zenodo.org/records/10828107/files/viabundus-1-3.zip"

    def run(self, force: bool = False) -> ProviderResult:
        self.create_schema()
        version_label = "1.3"

        zip_path = self.download_file(self.DOWNLOAD_URL, self.workspace / "viabundus.zip")
        self.write_artifact_record("zip", zip_path, self.DOWNLOAD_URL, version_label)

        extract_dir = self.extract_zip(zip_path, self.workspace / "extracted")
        nodes_csv = next(iter(extract_dir.rglob("nodes.csv")), None)
        edges_csv = next(iter(extract_dir.rglob("edges.csv")), None)
        if nodes_csv is None:
            raise RuntimeError("nodes.csv not found in Viabundus archive")

        nodes = pd.read_csv(nodes_csv)
        if "wkt_geom" not in nodes.columns:
            raise RuntimeError("Viabundus nodes.csv missing wkt_geom column")

        nodes_records = 0
        backend = self.backend
        conn = backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(f"DROP TABLE IF EXISTS {self.schema_name}.viabundus_nodes CASCADE")
                cur.execute(
                    f'''
                    CREATE TABLE {self.schema_name}.viabundus_nodes (
                        id SERIAL PRIMARY KEY,
                        source_id TEXT,
                        name TEXT,
                        node_type TEXT,
                        region TEXT,
                        geom geometry(POINT, 4326)
                    )
                    '''
                )
                for _, row in nodes.iterrows():
                    cur.execute(
                        f'''
                        INSERT INTO {self.schema_name}.viabundus_nodes (source_id, name, node_type, region, geom)
                        VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326))
                        ''',
                        (
                            str(row.get("id", "")),
                            row.get("name"),
                            row.get("node_type"),
                            row.get("region"),
                            row.get("wkt_geom"),
                        ),
                    )
                    nodes_records += 1

                cur.execute(f"CREATE INDEX IF NOT EXISTS idx_viabundus_nodes_geom ON {self.schema_name}.viabundus_nodes USING GIST (geom)")

                edges_records = 0
                if edges_csv is not None:
                    edges = pd.read_csv(edges_csv)
                    if "wkt_geom" in edges.columns:
                        cur.execute(f"DROP TABLE IF EXISTS {self.schema_name}.viabundus_edges CASCADE")
                        cur.execute(
                            f'''
                            CREATE TABLE {self.schema_name}.viabundus_edges (
                                id SERIAL PRIMARY KEY,
                                source_id TEXT,
                                edge_type TEXT,
                                geom geometry(LINESTRING, 4326)
                            )
                            '''
                        )
                        for _, row in edges.iterrows():
                            cur.execute(
                                f'''
                                INSERT INTO {self.schema_name}.viabundus_edges (source_id, edge_type, geom)
                                VALUES (%s, %s, ST_GeomFromText(%s, 4326))
                                ''',
                                (
                                    str(row.get("id", "")),
                                    row.get("edge_type"),
                                    row.get("wkt_geom"),
                                ),
                            )
                            edges_records += 1
                        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_viabundus_edges_geom ON {self.schema_name}.viabundus_edges USING GIST (geom)")
            conn.commit()
        finally:
            backend.close()

        self.register_layer("medieval_viabundus_nodes", "Viabundus Nodes", "medieval.viabundus_nodes", "POINT", {"source_key": self.source_key}, sort_order=220)
        if edges_csv is not None:
            self.register_layer("medieval_viabundus_edges", "Viabundus Edges", "medieval.viabundus_edges", "LINESTRING", {"source_key": self.source_key}, sort_order=221)

        return ProviderResult(
            source_key=self.source_key,
            status="success",
            message="Viabundus imported",
            records_loaded=nodes_records,
            layer_keys=["medieval_viabundus_nodes", "medieval_viabundus_edges"],
            artifacts=[str(zip_path)],
            version_label=version_label,
        )
