from __future__ import annotations

import json

from core.db import build_backend


class ManualSeedService:
    def __init__(self):
        self.backend = build_backend()

    def seed_restricted_area(self, name: str, polygon_wkt: str, category: str = "protected"):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO legal.restricted_areas (name, category, source, geom, properties)
                VALUES (%s, %s, 'manual_seed', ST_GeomFromText(%s, 4326), %s::jsonb)
                RETURNING id
                ''',
                (name, category, polygon_wkt, json.dumps({"seeded": True, "name": name})),
            )
            rid = cur.fetchone()[0]
        conn.commit()
        return rid

    def seed_mining_location(self, location_name: str, point_wkt: str, mineral_type: str = "unknown", year: int = 1700):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO economic.mining_locations (year, location_name, production_value, mineral_type, geom, notes)
                VALUES (%s, %s, NULL, %s, ST_GeomFromText(%s, 4326), 'manual_seed')
                RETURNING id
                ''',
                (year, location_name, mineral_type, point_wkt),
            )
            mid = cur.fetchone()[0]
        conn.commit()
        return mid
