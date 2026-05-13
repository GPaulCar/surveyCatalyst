from __future__ import annotations

from typing import Any

from core.db import build_backend


class LayerUsageService:
    def __init__(self):
        self.backend = build_backend()

    def _external_counts(self, cur) -> dict[str, int]:
        cur.execute(
            """
            SELECT layer, COUNT(*)
            FROM external_features
            GROUP BY layer
            """
        )
        return {str(layer): int(count or 0) for layer, count in cur.fetchall()}

    def _data_layer_count(self, cur, source_table: str) -> int:
        cur.execute(f"SELECT COUNT(*) FROM {source_table} WHERE geom IS NOT NULL")
        row = cur.fetchone()
        return int((row[0] if row else 0) or 0)

    def _count_summary(self, *, source_table: str | None, geometry_type: str | None, external_count: int, metadata: dict[str, Any] | None) -> dict[str, Any]:
        geometry_type = str(geometry_type or "").upper()
        source_table = str(source_table or "")
        metadata = metadata or {}

        if source_table.startswith("data_layers."):
            return {
                "object_count": external_count,
                "count_kind": "data_layer",
                "count_label": str(external_count),
            }

        if source_table.startswith("http://") or source_table.startswith("https://"):
            return {
                "object_count": None,
                "count_kind": "service_backed",
                "count_label": "service",
            }

        if geometry_type == "RASTER" and source_table == "external_features":
            return {
                "object_count": external_count,
                "count_kind": "registry_only",
                "count_label": "registry",
            }

        if metadata.get("service_url") and source_table == "external_features":
            return {
                "object_count": None,
                "count_kind": "service_backed",
                "count_label": "service",
            }

        if source_table == "external_features":
            if external_count > 0:
                return {
                    "object_count": external_count,
                    "count_kind": "loaded",
                    "count_label": str(external_count),
                }
            return {
                "object_count": 0,
                "count_kind": "not_loaded",
                "count_label": "not loaded",
            }

        return {
            "object_count": external_count if external_count > 0 else None,
            "count_kind": "registry_only",
            "count_label": "registry",
        }

    def list_layers(self) -> list[dict[str, Any]]:
        conn = self.backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT layer_key,
                           layer_name,
                           layer_group,
                           source_table,
                           geometry_type,
                           is_visible,
                           opacity,
                           sort_order,
                           metadata
                    FROM layers_registry
                    ORDER BY layer_group, sort_order, layer_name
                    """
                )
                rows = cur.fetchall()
                external_counts = self._external_counts(cur)
                out: list[dict[str, Any]] = []
                for row in rows:
                    metadata = row[8] or {}
                    external_count = external_counts.get(str(row[0]), 0)
                    source_table = str(row[3] or "")
                    external_value = external_count
                    if source_table.startswith("data_layers."):
                        external_value = self._data_layer_count(cur, source_table)
                    count_summary = self._count_summary(
                        source_table=row[3],
                        geometry_type=row[4],
                        external_count=external_value,
                        metadata=metadata if isinstance(metadata, dict) else {},
                    )
                    out.append(
                        {
                            "layer_key": row[0],
                            "layer_name": row[1],
                            "layer_group": row[2],
                            "source_table": row[3],
                            "geometry_type": row[4],
                            "is_visible": row[5],
                            "opacity": row[6],
                            "sort_order": row[7],
                            "metadata": metadata or {},
                            "object_count": count_summary["object_count"],
                            "count_kind": count_summary["count_kind"],
                            "count_label": count_summary["count_label"],
                        }
                    )
                return out
        finally:
            conn.close()

    def count_summary_for_layer(self, layer_key: str) -> dict[str, Any] | None:
        conn = self.backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT layer_key,
                           source_table,
                           geometry_type,
                           metadata
                    FROM layers_registry
                    WHERE layer_key = %s
                    """,
                    (layer_key,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                metadata = row[3] or {}
                source_table = row[1]
                geometry_type = row[2]
                if str(source_table or "").startswith("data_layers."):
                    external_count = self._data_layer_count(cur, str(source_table))
                else:
                    external_counts = self._external_counts(cur)
                    external_count = external_counts.get(str(layer_key), 0)
                return self._count_summary(
                    source_table=source_table,
                    geometry_type=geometry_type,
                    external_count=external_count,
                    metadata=metadata if isinstance(metadata, dict) else {},
                )
        finally:
            conn.close()
