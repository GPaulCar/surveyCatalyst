from __future__ import annotations

from core.db import build_backend


class GeometryValidationService:
    def __init__(self):
        self.backend = build_backend()

    def validate_table(self, qualified_table: str, geometry_column: str = "geom") -> dict:
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {qualified_table}")
            total = cur.fetchone()[0]

            cur.execute(f"SELECT COUNT(*) FROM {qualified_table} WHERE {geometry_column} IS NULL")
            null_geoms = cur.fetchone()[0]

            cur.execute(
                f"SELECT COUNT(*) FROM {qualified_table} "
                f"WHERE {geometry_column} IS NOT NULL AND NOT ST_IsValid({geometry_column})"
            )
            invalid_geoms = cur.fetchone()[0]

            cur.execute(
                f"SELECT COUNT(*) FROM {qualified_table} "
                f"WHERE {geometry_column} IS NOT NULL AND ST_SRID({geometry_column}) <> 4326"
            )
            wrong_srid = cur.fetchone()[0]

        return {
            "table": qualified_table,
            "geometry_column": geometry_column,
            "total_rows": total,
            "null_geometries": null_geoms,
            "invalid_geometries": invalid_geoms,
            "wrong_srid_rows": wrong_srid,
        }

    def repair_table(self, qualified_table: str, geometry_column: str = "geom") -> dict:
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                f'''
                UPDATE {qualified_table}
                SET {geometry_column} = ST_MakeValid({geometry_column})
                WHERE {geometry_column} IS NOT NULL
                  AND NOT ST_IsValid({geometry_column})
                '''
            )
            repaired_invalid = cur.rowcount

            cur.execute(
                f'''
                UPDATE {qualified_table}
                SET {geometry_column} = ST_SetSRID({geometry_column}, 4326)
                WHERE {geometry_column} IS NOT NULL
                  AND ST_SRID({geometry_column}) <> 4326
                '''
            )
            repaired_srid = cur.rowcount
        conn.commit()

        return {
            "table": qualified_table,
            "repaired_invalid": repaired_invalid,
            "repaired_srid": repaired_srid,
        }
