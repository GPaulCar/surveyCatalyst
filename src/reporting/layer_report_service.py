from __future__ import annotations

from core.db import build_backend


class LayerReportService:
    def __init__(self):
        self.backend = build_backend()

    def summary(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT lr.layer_key,
                       lr.layer_name,
                       lr.layer_group,
                       lr.is_visible,
                       lr.opacity,
                       lr.sort_order,
                       COALESCE(COUNT(ef.id), 0) AS feature_count
                FROM layers_registry lr
                LEFT JOIN external_features ef
                  ON ef.layer = lr.layer_key
                GROUP BY lr.layer_key, lr.layer_name, lr.layer_group, lr.is_visible, lr.opacity, lr.sort_order
                ORDER BY lr.layer_group, lr.sort_order, lr.layer_name
                '''
            )
            return cur.fetchall()
