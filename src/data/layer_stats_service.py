from core.db import build_backend


class LayerStatsService:
    def summary(self):
        conn = build_backend().connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT layer, COUNT(*)
                FROM external_features
                GROUP BY layer
                ORDER BY layer
                '''
            )
            return cur.fetchall()
