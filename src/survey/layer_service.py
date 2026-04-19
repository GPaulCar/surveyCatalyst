from __future__ import annotations

import json

from core.db import build_backend


class SurveyLayerService:
    def __init__(self):
        self.backend = build_backend()

    def create_survey_layer(self, expedition_id: int, title: str):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO surveys (expedition_id, title, metadata)
                VALUES (%s, %s, '{}'::jsonb)
                RETURNING id
                ''',
                (expedition_id, title),
            )
            survey_id = cur.fetchone()[0]
            layer_key = f"survey_{survey_id}"

            cur.execute(
                '''
                UPDATE surveys
                SET layer_key = %s
                WHERE id = %s
                ''',
                (layer_key, survey_id),
            )

            cur.execute(
                '''
                INSERT INTO layers_registry (
                    layer_key, layer_name, layer_group, source_table, geometry_type,
                    is_user_selectable, is_visible, opacity, sort_order, metadata
                )
                VALUES (
                    %s, %s, 'survey', 'survey_objects', 'GEOMETRY',
                    TRUE, TRUE, 1.0, 100,
                    jsonb_build_object('survey_id', %s)
                )
                ON CONFLICT (layer_key) DO NOTHING
                ''',
                (layer_key, title, survey_id),
            )
        conn.commit()
        return survey_id, layer_key

    def list_objects_for_layer(self, layer_key: str):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT id, survey_id, expedition_id, type, properties, ST_AsText(geom)
                FROM survey_objects
                WHERE layer_key = %s
                ORDER BY id
                ''',
                (layer_key,),
            )
            return cur.fetchall()

    def create_survey_object(self, survey_id: int, expedition_id: int, obj_type: str, geom_wkt: str, properties: dict | None = None):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute('SELECT layer_key FROM surveys WHERE id = %s', (survey_id,))
            row = cur.fetchone()
            if not row:
                raise RuntimeError(f"Survey {survey_id} not found")
            layer_key = row[0]

            cur.execute(
                '''
                INSERT INTO survey_objects (survey_id, expedition_id, layer_key, type, geom, properties)
                VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326), %s::jsonb)
                RETURNING id
                ''',
                (survey_id, expedition_id, layer_key, obj_type, geom_wkt, json.dumps(properties or {})),
            )
            object_id = cur.fetchone()[0]
        conn.commit()
        return object_id, layer_key
