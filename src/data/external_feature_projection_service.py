from __future__ import annotations

import json

from core.db import build_backend


class ExternalFeatureProjectionService:
    def __init__(self):
        self.backend = build_backend()

    def project_from_source_table(
        self,
        source_table: str,
        layer_key: str,
        geometry_column: str = "geom",
        property_columns: list[str] | None = None,
        source_id_column: str | None = "id",
    ):
        property_columns = property_columns or []
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT to_regclass(%s)",
                (source_table,),
            )
            if cur.fetchone()[0] is None:
                raise RuntimeError(f"Source table not found: {source_table}")

            cur.execute("DELETE FROM external_features WHERE layer = %s", (layer_key,))

            props_expr_parts = []
            for col in property_columns:
                props_expr_parts.append(f"'{col}'")
                props_expr_parts.append(col)
            props_expr = "jsonb_build_object(" + ", ".join(props_expr_parts) + ")" if props_expr_parts else "'{}'::jsonb"

            source_id_expr = source_id_column if source_id_column else "NULL"

            cur.execute(
                f'''
                INSERT INTO external_features (layer, source_table, source_id, geom, properties)
                SELECT %s,
                       %s,
                       {source_id_expr}::text,
                       {geometry_column},
                       {props_expr}
                FROM {source_table}
                WHERE {geometry_column} IS NOT NULL
                '''
                ,
                (layer_key, source_table),
            )
            inserted = cur.rowcount
        conn.commit()
        return {"layer_key": layer_key, "source_table": source_table, "inserted": inserted}
