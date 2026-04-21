from __future__ import annotations

import json
from typing import Any

from core.db import build_backend


class SurveyEditService:
    def __init__(self):
        self.backend = build_backend()

    @staticmethod
    def _geometry_sql_from_inputs(geojson: dict[str, Any] | str | None = None, wkt: str | None = None) -> tuple[str, Any | None]:
        if geojson is not None:
            if isinstance(geojson, str):
                geometry_json = geojson
            else:
                geometry_json = json.dumps(geojson)
            return "ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)", geometry_json
        if wkt is not None:
            return "ST_GeomFromText(%s, 4326)", wkt
        return "NULL", None

    def _normalise_geometry_value(self, conn, geojson: dict[str, Any] | str | None = None, wkt: str | None = None) -> str | None:
        geom_sql, geom_value = self._geometry_sql_from_inputs(geojson=geojson, wkt=wkt)
        if geom_value is None:
            return None
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT ST_AsGeoJSON(
                    CASE
                        WHEN g IS NULL THEN NULL
                        WHEN ST_IsValid(g) THEN g
                        ELSE ST_MakeValid(g)
                    END
                )
                FROM (SELECT {geom_sql} AS g) q
                """,
                (geom_value,),
            )
            row = cur.fetchone()
        normalised = row[0] if row else None
        if normalised is None:
            raise RuntimeError("Unable to validate geometry")
        return normalised

    @staticmethod
    def _geojson_insert_sql() -> str:
        return "ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)"

    def create_survey(
        self,
        expedition_id: int,
        title: str,
        polygon_wkt: str | None = None,
        status: str = "planned",
        metadata: dict[str, Any] | None = None,
        geometry: dict[str, Any] | str | None = None,
    ):
        conn = self.backend.connect()
        try:
            normalised_geometry = self._normalise_geometry_value(conn, geojson=geometry, wkt=polygon_wkt) if (geometry is not None or polygon_wkt is not None) else None
            with conn.cursor() as cur:
                if normalised_geometry is None:
                    cur.execute(
                        """
                        INSERT INTO surveys (expedition_id, title, status, geom, metadata)
                        VALUES (%s, %s, %s, NULL, %s::jsonb)
                        RETURNING id
                        """,
                        [expedition_id, title, status, json.dumps(metadata or {})],
                    )
                else:
                    cur.execute(
                        f"""
                        INSERT INTO surveys (expedition_id, title, status, geom, metadata)
                        VALUES (%s, %s, %s, {self._geojson_insert_sql()}, %s::jsonb)
                        RETURNING id
                        """,
                        [expedition_id, title, status, normalised_geometry, json.dumps(metadata or {})],
                    )
                survey_id = cur.fetchone()[0]
                layer_key = f"survey_{survey_id}"

                cur.execute(
                    """
                    UPDATE surveys
                    SET layer_key = %s
                    WHERE id = %s
                    """,
                    (layer_key, survey_id),
                )

                cur.execute(
                    """
                    INSERT INTO layers_registry (
                        layer_key, layer_name, layer_group, source_table, geometry_type,
                        is_user_selectable, is_visible, opacity, sort_order, metadata
                    )
                    VALUES (
                        %s, %s, 'survey', 'survey_objects', 'GEOMETRY',
                        TRUE, TRUE, 1.0, 100,
                        jsonb_build_object('survey_id', %s)
                    )
                    ON CONFLICT (layer_key) DO UPDATE
                    SET layer_name = EXCLUDED.layer_name,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                    """,
                    (layer_key, title, survey_id),
                )
            conn.commit()
            return survey_id, layer_key
        finally:
            conn.close()

    def update_survey(
        self,
        survey_id: int,
        expedition_id: int | None = None,
        title: str | None = None,
        status: str | None = None,
        polygon_wkt: str | None = None,
        metadata: dict[str, Any] | None = None,
        geometry: dict[str, Any] | str | None = None,
    ):
        assignments: list[str] = []
        params: list[Any] = []

        if expedition_id is not None:
            assignments.append("expedition_id = %s")
            params.append(expedition_id)
        if title is not None:
            assignments.append("title = %s")
            params.append(title)
        if status is not None:
            assignments.append("status = %s")
            params.append(status)
        if metadata is not None:
            assignments.append("metadata = %s::jsonb")
            params.append(json.dumps(metadata))

        conn = self.backend.connect()
        try:
            if geometry is not None or polygon_wkt is not None:
                normalised_geometry = self._normalise_geometry_value(conn, geojson=geometry, wkt=polygon_wkt)
                assignments.append(f"geom = {self._geojson_insert_sql()}")
                params.append(normalised_geometry)

            if not assignments:
                return

            params.append(survey_id)
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE surveys
                    SET {', '.join(assignments)}
                    WHERE id = %s
                    """,
                    params,
                )
                if title is not None:
                    cur.execute(
                        """
                        UPDATE layers_registry
                        SET layer_name = %s,
                            updated_at = NOW()
                        WHERE metadata->>'survey_id' = %s
                           OR layer_key = %s
                        """,
                        (title, str(survey_id), f"survey_{survey_id}"),
                    )
            conn.commit()
        finally:
            conn.close()

    def delete_survey(self, survey_id: int):
        conn = self.backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT layer_key FROM surveys WHERE id = %s", (survey_id,))
                row = cur.fetchone()
                layer_key = row[0] if row else f"survey_{survey_id}"
                cur.execute("DELETE FROM survey_objects WHERE survey_id = %s", (survey_id,))
                cur.execute("DELETE FROM layers_registry WHERE layer_key = %s", (layer_key,))
                cur.execute("DELETE FROM surveys WHERE id = %s", (survey_id,))
            conn.commit()
        finally:
            conn.close()

    def update_survey_geometry(self, survey_id: int, polygon_wkt: str):
        self.update_survey(survey_id=survey_id, polygon_wkt=polygon_wkt)

    def create_survey_object(
        self,
        survey_id: int,
        expedition_id: int,
        obj_type: str,
        geom_wkt: str | None = None,
        properties: dict[str, Any] | None = None,
        geometry: dict[str, Any] | str | None = None,
        title: str | None = None,
        annotation: str | None = None,
        details: str | None = None,
    ):
        conn = self.backend.connect()
        try:
            normalised_geometry = self._normalise_geometry_value(conn, geojson=geometry, wkt=geom_wkt) if (geometry is not None or geom_wkt is not None) else None
            with conn.cursor() as cur:
                cur.execute('SELECT layer_key FROM surveys WHERE id = %s', (survey_id,))
                row = cur.fetchone()
                if not row:
                    raise RuntimeError(f"Survey {survey_id} not found")
                layer_key = row[0]
                merged_properties = dict(properties or {})
                if title is not None:
                    merged_properties["title"] = title
                if annotation is not None:
                    merged_properties["annotation"] = annotation
                if details is not None:
                    merged_properties["details"] = details

                if normalised_geometry is None:
                    raise RuntimeError("Survey object geometry is required")
                cur.execute(
                    f"""
                    INSERT INTO survey_objects (survey_id, expedition_id, layer_key, type, geom, properties, is_active)
                    VALUES (%s, %s, %s, %s, {self._geojson_insert_sql()}, %s::jsonb, TRUE)
                    RETURNING id
                    """,
                    (survey_id, expedition_id, layer_key, obj_type, normalised_geometry, json.dumps(merged_properties)),
                )
                object_id = cur.fetchone()[0]
            conn.commit()
            return object_id
        finally:
            conn.close()

    def update_survey_object(
        self,
        object_id: int,
        geom_wkt: str | None = None,
        properties: dict[str, Any] | None = None,
        geometry: dict[str, Any] | str | None = None,
        obj_type: str | None = None,
        title: str | None = None,
        annotation: str | None = None,
        details: str | None = None,
        is_active: bool | None = None,
    ):
        conn = self.backend.connect()
        try:
            normalised_geometry = None
            if geometry is not None or geom_wkt is not None:
                normalised_geometry = self._normalise_geometry_value(conn, geojson=geometry, wkt=geom_wkt)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT properties, type, is_active
                    FROM survey_objects
                    WHERE id = %s
                    """,
                    (object_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise RuntimeError(f"Survey object {object_id} not found")
                current_properties, current_type, current_active = row
                merged_properties = dict(current_properties or {})
                if properties is not None:
                    merged_properties.update(properties)
                if title is not None:
                    merged_properties["title"] = title
                if annotation is not None:
                    merged_properties["annotation"] = annotation
                if details is not None:
                    merged_properties["details"] = details

                assignments = ["properties = %s::jsonb", "type = %s", "is_active = %s"]
                params: list[Any] = [json.dumps(merged_properties), obj_type or current_type, current_active if is_active is None else is_active]

                if geometry is not None or geom_wkt is not None:
                    assignments.append(f"geom = {self._geojson_insert_sql()}")
                    params.append(normalised_geometry)

                params.append(object_id)
                cur.execute(
                    f"""
                    UPDATE survey_objects
                    SET {', '.join(assignments)}
                    WHERE id = %s
                    """,
                    params,
                )
            conn.commit()
        finally:
            conn.close()

    def archive_survey_object(self, object_id: int):
        self.update_survey_object(object_id=object_id, is_active=False)

    def delete_survey_object(self, object_id: int):
        conn = self.backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM survey_objects WHERE id = %s', (object_id,))
            conn.commit()
        finally:
            conn.close()

    def list_survey_hierarchy(self, survey_id: int):
        conn = self.backend.connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id,
                           expedition_id,
                           title,
                           status,
                           layer_key,
                           metadata,
                           ST_AsGeoJSON(geom)::jsonb,
                           CASE WHEN geom IS NOT NULL THEN ST_AsText(ST_Envelope(geom)) ELSE NULL END
                    FROM surveys
                    WHERE id = %s
                    """,
                    (survey_id,),
                )
                survey_row = cur.fetchone()
                if not survey_row:
                    raise RuntimeError(f"Survey {survey_id} not found")
                cur.execute(
                    """
                    SELECT id,
                           survey_id,
                           expedition_id,
                           type,
                           layer_key,
                           properties,
                           is_active,
                           ST_AsGeoJSON(geom)::jsonb
                    FROM survey_objects
                    WHERE survey_id = %s
                    ORDER BY id
                    """,
                    (survey_id,),
                )
                object_rows = cur.fetchall()

            objects = []
            for row in object_rows:
                props = dict(row[5] or {})
                objects.append({
                    "id": row[0],
                    "survey_id": row[1],
                    "expedition_id": row[2],
                    "type": row[3],
                    "layer_key": row[4],
                    "properties": props,
                    "title": props.get("title", ""),
                    "annotation": props.get("annotation", ""),
                    "details": props.get("details", ""),
                    "is_active": row[6],
                    "geometry": row[7],
                })

            survey_metadata = dict(survey_row[5] or {})
            return {
                "survey": {
                    "id": survey_row[0],
                    "expedition_id": survey_row[1],
                    "title": survey_row[2],
                    "status": survey_row[3],
                    "layer_key": survey_row[4],
                    "metadata": survey_metadata,
                    "geometry": survey_row[6],
                    "object_count": len(objects),
                },
                "objects": objects,
            }
        finally:
            conn.close()
