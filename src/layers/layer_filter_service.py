from __future__ import annotations

from core.db import build_backend


class LayerFilterService:
    def __init__(self):
        self.backend = build_backend()

    def list_layers(
        self,
        layer_group: str | None = None,
        geometry_type: str | None = None,
        visible_only: bool = False,
    ):
        conn = self.backend.connect()
        sql = '''
            SELECT layer_key, layer_name, layer_group, source_table, geometry_type,
                   is_visible, opacity, sort_order, metadata
            FROM layers_registry
            WHERE 1=1
        '''
        params = []

        if layer_group:
            sql += " AND layer_group = %s"
            params.append(layer_group)
        if geometry_type:
            sql += " AND geometry_type = %s"
            params.append(geometry_type)
        if visible_only:
            sql += " AND is_visible = TRUE"

        sql += " ORDER BY layer_group, sort_order, layer_name"

        with conn.cursor() as cur:
            cur.execute(sql, tuple(params))
            return cur.fetchall()

    def visible_context_layers(self):
        return self.list_layers(layer_group="context", visible_only=True)
