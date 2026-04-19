from core.db import build_backend


class AggregationService:
    def __init__(self):
        self.backend = build_backend()

    def count_by_layer(self):
        conn = self.backend.connect()
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
