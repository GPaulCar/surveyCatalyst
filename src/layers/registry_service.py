from __future__ import annotations

from core.db import build_backend


class LayerRegistryService:
    def __init__(self):
        self.backend = build_backend()

    def list_layers(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT layer_key, layer_name, layer_group, source_table, geometry_type,
                       is_user_selectable, is_visible, opacity, sort_order, metadata
                FROM layers_registry
                ORDER BY layer_group, sort_order, layer_name
                '''
            )
            return cur.fetchall()

    def list_group(self, layer_group: str):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT layer_key, layer_name, source_table, geometry_type,
                       is_visible, opacity, sort_order
                FROM layers_registry
                WHERE layer_group = %s
                ORDER BY sort_order, layer_name
                ''',
                (layer_group,),
            )
            return cur.fetchall()

    def set_visibility(self, layer_key: str, visible: bool):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE layers_registry
                SET is_visible = %s, updated_at = NOW()
                WHERE layer_key = %s
                ''',
                (visible, layer_key),
            )
        conn.commit()

    def set_opacity(self, layer_key: str, opacity: float):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                UPDATE layers_registry
                SET opacity = %s, updated_at = NOW()
                WHERE layer_key = %s
                ''',
                (opacity, layer_key),
            )
        conn.commit()
