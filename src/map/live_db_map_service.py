from __future__ import annotations

from core.db import build_backend


class LiveDBMapService:
    def __init__(self):
        self.backend = build_backend()

    def list_layers(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
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
                '''
            )
            return cur.fetchall()

    def list_survey_layers(self):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT s.layer_key,
                       s.id AS survey_id,
                       s.title,
                       s.status,
                       s.expedition_id,
                       COALESCE(lr.is_visible, TRUE) AS is_visible,
                       COUNT(so.id) FILTER (WHERE so.is_active = TRUE) AS object_count,
                       ST_AsGeoJSON(ST_Envelope(s.geom))::jsonb AS extent_geojson
                FROM surveys s
                LEFT JOIN layers_registry lr ON lr.layer_key = s.layer_key
                LEFT JOIN survey_objects so ON so.survey_id = s.id
                WHERE s.layer_key IS NOT NULL
                GROUP BY s.layer_key, s.id, s.title, s.status, s.expedition_id, lr.is_visible, s.geom
                ORDER BY s.id
                '''
            )
            return cur.fetchall()

    def get_layer_geojson(self, layer_key: str, bounds: tuple[float, float, float, float] | None = None, limit: int = 5000):
        if layer_key == "surveys":
            return self._surveys_geojson(bounds=bounds, limit=limit)
        if layer_key.startswith("survey_"):
            return self._survey_layer_geojson(layer_key, bounds=bounds, limit=limit)
        if layer_key == "survey_objects":
            return self._survey_objects_geojson(layer_key, bounds=bounds, limit=limit)
        return self._external_features_geojson(layer_key, bounds=bounds, limit=limit)

    def get_survey_layer_geojson(self, layer_key: str, bounds: tuple[float, float, float, float] | None = None, limit: int = 5000):
        return self._survey_layer_geojson(layer_key, bounds=bounds, limit=limit)

    def _surveys_geojson(self, bounds=None, limit: int = 5000):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            if bounds:
                minx, miny, maxx, maxy = bounds
                cur.execute(
                    '''
                    WITH env AS (
                        SELECT ST_MakeEnvelope(%s, %s, %s, %s, 4326) AS bbox
                    )
                    SELECT jsonb_build_object(
                        'type', 'FeatureCollection',
                        'features', COALESCE(
                            jsonb_agg(
                                jsonb_build_object(
                                    'type', 'Feature',
                                    'geometry', ST_AsGeoJSON(geom)::jsonb,
                                    'properties', jsonb_build_object(
                                        'id', id,
                                        'title', title,
                                        'status', status,
                                        'layer_key', layer_key,
                                        'expedition_id', expedition_id,
                                        'feature_role', 'survey_boundary'
                                    )
                                )
                            ),
                            '[]'::jsonb
                        )
                    )
                    FROM (
                        SELECT id, title, status, layer_key, expedition_id, geom
                        FROM surveys, env
                        WHERE geom IS NOT NULL
                          AND geom && env.bbox
                          AND ST_Intersects(geom, env.bbox)
                        LIMIT %s
                    ) q
                    ''',
                    (minx, miny, maxx, maxy, limit),
                )
            else:
                cur.execute(
                    '''
                    SELECT jsonb_build_object(
                        'type', 'FeatureCollection',
                        'features', COALESCE(
                            jsonb_agg(
                                jsonb_build_object(
                                    'type', 'Feature',
                                    'geometry', ST_AsGeoJSON(geom)::jsonb,
                                    'properties', jsonb_build_object(
                                        'id', id,
                                        'title', title,
                                        'status', status,
                                        'layer_key', layer_key,
                                        'expedition_id', expedition_id,
                                        'feature_role', 'survey_boundary'
                                    )
                                )
                            ),
                            '[]'::jsonb
                        )
                    )
                    FROM (
                        SELECT id, title, status, layer_key, expedition_id, geom
                        FROM surveys
                        WHERE geom IS NOT NULL
                        LIMIT %s
                    ) q
                    ''',
                    (limit,),
                )
            return cur.fetchone()[0]

    def _survey_layer_geojson(self, layer_key: str, bounds=None, limit: int = 5000):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            if bounds:
                minx, miny, maxx, maxy = bounds
                cur.execute(
                    '''
                    WITH env AS (
                        SELECT ST_MakeEnvelope(%s, %s, %s, %s, 4326) AS bbox
                    ),
                    survey_boundary AS (
                        SELECT jsonb_build_object(
                            'type', 'Feature',
                            'geometry', ST_AsGeoJSON(s.geom)::jsonb,
                            'properties', jsonb_build_object(
                                'id', s.id,
                                'survey_id', s.id,
                                'title', s.title,
                                'status', s.status,
                                'layer_key', s.layer_key,
                                'expedition_id', s.expedition_id,
                                'feature_role', 'survey_boundary'
                            )
                        ) AS feature
                        FROM surveys s, env
                        WHERE s.layer_key = %s
                          AND s.geom IS NOT NULL
                          AND s.geom && env.bbox
                          AND ST_Intersects(s.geom, env.bbox)
                    ),
                    survey_objects_limited AS (
                        SELECT jsonb_build_object(
                            'type', 'Feature',
                            'geometry', ST_AsGeoJSON(so.geom)::jsonb,
                            'properties', COALESCE(so.properties, '{}'::jsonb) || jsonb_build_object(
                                'id', so.id,
                                'survey_id', so.survey_id,
                                'expedition_id', so.expedition_id,
                                'type', so.type,
                                'layer_key', so.layer_key,
                                'feature_role', 'survey_object'
                            )
                        ) AS feature
                        FROM survey_objects so, env
                        WHERE so.layer_key = %s
                          AND so.is_active = TRUE
                          AND so.geom IS NOT NULL
                          AND so.geom && env.bbox
                          AND ST_Intersects(so.geom, env.bbox)
                        LIMIT %s
                    )
                    SELECT jsonb_build_object(
                        'type', 'FeatureCollection',
                        'features', COALESCE(
                            (
                                SELECT jsonb_agg(feature)
                                FROM (
                                    SELECT feature FROM survey_boundary
                                    UNION ALL
                                    SELECT feature FROM survey_objects_limited
                                ) all_features
                            ),
                            '[]'::jsonb
                        )
                    )
                    ''',
                    (minx, miny, maxx, maxy, layer_key, layer_key, limit),
                )
            else:
                cur.execute(
                    '''
                    WITH survey_boundary AS (
                        SELECT jsonb_build_object(
                            'type', 'Feature',
                            'geometry', ST_AsGeoJSON(s.geom)::jsonb,
                            'properties', jsonb_build_object(
                                'id', s.id,
                                'survey_id', s.id,
                                'title', s.title,
                                'status', s.status,
                                'layer_key', s.layer_key,
                                'expedition_id', s.expedition_id,
                                'feature_role', 'survey_boundary'
                            )
                        ) AS feature
                        FROM surveys s
                        WHERE s.layer_key = %s
                          AND s.geom IS NOT NULL
                    ),
                    survey_objects_limited AS (
                        SELECT jsonb_build_object(
                            'type', 'Feature',
                            'geometry', ST_AsGeoJSON(so.geom)::jsonb,
                            'properties', COALESCE(so.properties, '{}'::jsonb) || jsonb_build_object(
                                'id', so.id,
                                'survey_id', so.survey_id,
                                'expedition_id', so.expedition_id,
                                'type', so.type,
                                'layer_key', so.layer_key,
                                'feature_role', 'survey_object'
                            )
                        ) AS feature
                        FROM survey_objects so
                        WHERE so.layer_key = %s
                          AND so.is_active = TRUE
                          AND so.geom IS NOT NULL
                        LIMIT %s
                    )
                    SELECT jsonb_build_object(
                        'type', 'FeatureCollection',
                        'features', COALESCE(
                            (
                                SELECT jsonb_agg(feature)
                                FROM (
                                    SELECT feature FROM survey_boundary
                                    UNION ALL
                                    SELECT feature FROM survey_objects_limited
                                ) all_features
                            ),
                            '[]'::jsonb
                        )
                    )
                    ''',
                    (layer_key, layer_key, limit),
                )
            return cur.fetchone()[0]

    def _survey_objects_geojson(self, layer_key: str, bounds=None, limit: int = 5000):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            if bounds:
                minx, miny, maxx, maxy = bounds
                cur.execute(
                    '''
                    WITH env AS (
                        SELECT ST_MakeEnvelope(%s, %s, %s, %s, 4326) AS bbox
                    )
                    SELECT jsonb_build_object(
                        'type', 'FeatureCollection',
                        'features', COALESCE(
                            jsonb_agg(
                                jsonb_build_object(
                                    'type', 'Feature',
                                    'geometry', ST_AsGeoJSON(geom)::jsonb,
                                    'properties', COALESCE(properties, '{}'::jsonb) || jsonb_build_object(
                                        'id', id,
                                        'survey_id', survey_id,
                                        'expedition_id', expedition_id,
                                        'type', type,
                                        'layer_key', layer_key,
                                        'feature_role', 'survey_object'
                                    )
                                )
                            ),
                            '[]'::jsonb
                        )
                    )
                    FROM (
                        SELECT id, survey_id, expedition_id, type, layer_key, properties, geom
                        FROM survey_objects, env
                        WHERE is_active = TRUE
                          AND geom IS NOT NULL
                          AND geom && env.bbox
                          AND ST_Intersects(geom, env.bbox)
                        LIMIT %s
                    ) q
                    ''',
                    (minx, miny, maxx, maxy, limit),
                )
            else:
                cur.execute(
                    '''
                    SELECT jsonb_build_object(
                        'type', 'FeatureCollection',
                        'features', COALESCE(
                            jsonb_agg(
                                jsonb_build_object(
                                    'type', 'Feature',
                                    'geometry', ST_AsGeoJSON(geom)::jsonb,
                                    'properties', COALESCE(properties, '{}'::jsonb) || jsonb_build_object(
                                        'id', id,
                                        'survey_id', survey_id,
                                        'expedition_id', expedition_id,
                                        'type', type,
                                        'layer_key', layer_key,
                                        'feature_role', 'survey_object'
                                    )
                                )
                            ),
                            '[]'::jsonb
                        )
                    )
                    FROM (
                        SELECT id, survey_id, expedition_id, type, layer_key, properties, geom
                        FROM survey_objects
                        WHERE is_active = TRUE
                          AND geom IS NOT NULL
                        LIMIT %s
                    ) q
                    ''',
                    (limit,),
                )
            return cur.fetchone()[0]

    def _external_features_geojson(self, layer_key: str, bounds=None, limit: int = 5000):
        conn = self.backend.connect()
        with conn.cursor() as cur:
            if bounds:
                minx, miny, maxx, maxy = bounds
                cur.execute(
                    '''
                    WITH env AS (
                        SELECT ST_MakeEnvelope(%s, %s, %s, %s, 4326) AS bbox
                    )
                    SELECT jsonb_build_object(
                        'type', 'FeatureCollection',
                        'features', COALESCE(
                            jsonb_agg(
                                jsonb_build_object(
                                    'type', 'Feature',
                                    'geometry', ST_AsGeoJSON(geom)::jsonb,
                                    'properties', COALESCE(properties, '{}'::jsonb) || jsonb_build_object(
                                        'id', id,
                                        'layer', layer,
                                        'source_table', source_table,
                                        'source_id', source_id
                                    )
                                )
                            ),
                            '[]'::jsonb
                        )
                    )
                    FROM (
                        SELECT id, layer, source_table, source_id, geom, properties
                        FROM external_features, env
                        WHERE layer = %s
                          AND geom IS NOT NULL
                          AND geom && env.bbox
                          AND ST_Intersects(geom, env.bbox)
                        LIMIT %s
                    ) q
                    ''',
                    (minx, miny, maxx, maxy, layer_key, limit),
                )
            else:
                cur.execute(
                    '''
                    SELECT jsonb_build_object(
                        'type', 'FeatureCollection',
                        'features', COALESCE(
                            jsonb_agg(
                                jsonb_build_object(
                                    'type', 'Feature',
                                    'geometry', ST_AsGeoJSON(geom)::jsonb,
                                    'properties', COALESCE(properties, '{}'::jsonb) || jsonb_build_object(
                                        'id', id,
                                        'layer', layer,
                                        'source_table', source_table,
                                        'source_id', source_id
                                    )
                                )
                            ),
                            '[]'::jsonb
                        )
                    )
                    FROM (
                        SELECT id, layer, source_table, source_id, geom, properties
                        FROM external_features
                        WHERE layer = %s
                          AND geom IS NOT NULL
                        LIMIT %s
                    ) q
                    ''',
                    (layer_key, limit),
                )
            return cur.fetchone()[0]
