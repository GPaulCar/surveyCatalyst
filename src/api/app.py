from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend
from map.live_db_map_service import LiveDBMapService
from survey.edit_service import SurveyEditService
from api.schemas import (
    ApiInfoResponse,
    HealthResponse,
    LayerRecord,
    SurveyObjectCreateRequest,
    SurveyObjectResponse,
    SurveyObjectUpdateRequest,
    SurveyRecord,
)

APP_VERSION = "0.3.0"
MVT_EXTENT = 4096
MVT_BUFFER = 256


def _parse_bounds(bbox: str | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    parts = [p.strip() for p in bbox.split(",") if p.strip()]
    if len(parts) != 4:
        raise HTTPException(status_code=400, detail="bbox must be minx,miny,maxx,maxy")
    try:
        minx, miny, maxx, maxy = [float(p) for p in parts]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="bbox values must be numeric") from exc
    if minx >= maxx or miny >= maxy:
        raise HTTPException(status_code=400, detail="bbox must satisfy minx < maxx and miny < maxy")
    return minx, miny, maxx, maxy


def _layer_row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    metadata = row[8] if len(row) > 8 and row[8] is not None else {}
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = {"raw": metadata}
    return {
        "layer_key": row[0],
        "layer_name": row[1],
        "layer_group": row[2],
        "source_table": row[3],
        "geometry_type": row[4],
        "is_visible": bool(row[5]),
        "opacity": float(row[6]) if row[6] is not None else None,
        "sort_order": int(row[7]) if row[7] is not None else None,
        "metadata": metadata if isinstance(metadata, dict) else {},
    }


def _survey_row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "id": int(row[0]),
        "expedition_id": int(row[1]) if row[1] is not None else None,
        "title": row[2],
        "status": row[3],
        "layer_key": row[4] if len(row) > 4 else None,
    }


def _get_external_layer_catalog(map_service: LiveDBMapService) -> list[dict[str, Any]]:
    rows = map_service.list_layers()
    result = [_layer_row_to_dict(row) for row in rows]
    return [
        row
        for row in result
        if not row["layer_key"].startswith("survey_") and row["layer_key"] not in {"surveys", "survey_objects"}
    ]


def create_app() -> FastAPI:
    app = FastAPI(title="surveyCatalyst API", version=APP_VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    map_service = LiveDBMapService()
    edit_service = SurveyEditService()

    @app.get("/", response_class=HTMLResponse)
    def openlayers_client() -> str:
        html_path = ROOT / "app" / "openlayers_map.html"
        return html_path.read_text(encoding="utf-8")

    @app.get("/api", response_model=ApiInfoResponse)
    def api_info() -> ApiInfoResponse:
        return ApiInfoResponse(
            name="surveyCatalyst API",
            version=APP_VERSION,
            endpoints=[
                "/health",
                "/api/layers",
                "/api/context-layers",
                "/api/surveys",
                "/api/surveys/{survey_id}",
                "/api/surveys/{survey_id}/features?bbox=minx,miny,maxx,maxy&limit=5000",
                "/api/layers/{layer_key}/geojson?bbox=minx,miny,maxx,maxy&limit=5000",
                "/api/layers/{layer_key}/tiles/{z}/{x}/{y}.mvt",
                "/api/surveys/{survey_id}/objects",
                "/api/survey-objects/{object_id}",
            ],
        )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        conn = None
        try:
            conn = build_backend().connect()
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            return HealthResponse(status="ok", database="connected")
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc
        finally:
            if conn is not None:
                conn.close()

    @app.get("/api/layers", response_model=list[LayerRecord])
    def list_layers(layer_group: str | None = None) -> list[LayerRecord]:
        rows = map_service.list_layers()
        result = [_layer_row_to_dict(row) for row in rows]
        if layer_group:
            result = [row for row in result if row["layer_group"] == layer_group]
        return [LayerRecord.model_validate(row) for row in result]

    @app.get("/api/context-layers", response_model=list[LayerRecord])
    def list_context_layers() -> list[LayerRecord]:
        return [LayerRecord.model_validate(row) for row in _get_external_layer_catalog(map_service)]

    @app.get("/api/surveys", response_model=list[SurveyRecord])
    def list_surveys() -> list[SurveyRecord]:
        conn = build_backend().connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT id, expedition_id, title, status, layer_key
                    FROM surveys
                    ORDER BY id
                    '''
                )
                rows = cur.fetchall()
            return [SurveyRecord.model_validate(_survey_row_to_dict(row)) for row in rows]
        finally:
            conn.close()

    @app.get("/api/surveys/{survey_id}")
    def get_survey(survey_id: int) -> dict[str, Any]:
        conn = build_backend().connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT id, expedition_id, title, status, layer_key,
                           CASE WHEN geom IS NOT NULL THEN ST_AsGeoJSON(geom)::jsonb ELSE NULL END AS geometry
                    FROM surveys
                    WHERE id = %s
                    ''',
                    (survey_id,),
                )
                row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"survey {survey_id} not found")
            return {
                "id": row[0],
                "expedition_id": row[1],
                "title": row[2],
                "status": row[3],
                "layer_key": row[4],
                "geometry": row[5],
            }
        finally:
            conn.close()

    @app.get("/api/surveys/{survey_id}/features")
    def get_survey_features(
        survey_id: int,
        bbox: str | None = Query(default=None, description="minx,miny,maxx,maxy in EPSG:4326"),
        limit: int = Query(default=5000, ge=1, le=50000),
    ) -> dict[str, Any]:
        bounds = _parse_bounds(bbox)
        layer_key = f"survey_{survey_id}"
        if not hasattr(map_service, "get_survey_layer_geojson"):
            raise HTTPException(
                status_code=500,
                detail="survey layer support is not available in LiveDBMapService; apply the survey layer refactor first",
            )
        try:
            payload = map_service.get_survey_layer_geojson(layer_key=layer_key, bounds=bounds, limit=limit)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
            raise HTTPException(status_code=500, detail="survey query did not return a GeoJSON FeatureCollection")
        return payload


    @app.post("/api/surveys/{survey_id}/objects", response_model=SurveyObjectResponse)
    def create_survey_object(survey_id: int, payload: SurveyObjectCreateRequest) -> SurveyObjectResponse:
        conn = build_backend().connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT expedition_id, title
                    FROM surveys
                    WHERE id = %s
                    """,
                    (survey_id,),
                )
                row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"survey {survey_id} not found")
            expedition_id = payload.expedition_id if payload.expedition_id is not None else row[0]
            if expedition_id is None:
                raise HTTPException(status_code=400, detail="expedition_id is required for this survey")
        finally:
            conn.close()

        geom_wkt = f"POINT({payload.lon} {payload.lat})"
        try:
            object_id = edit_service.create_survey_object(
                survey_id=survey_id,
                expedition_id=expedition_id,
                obj_type=payload.obj_type,
                geom_wkt=geom_wkt,
                properties=payload.properties,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return SurveyObjectResponse(
            id=int(object_id),
            survey_id=int(survey_id),
            expedition_id=int(expedition_id),
            obj_type=payload.obj_type,
            lon=payload.lon,
            lat=payload.lat,
            properties=payload.properties,
            status="created",
        )

    @app.patch("/api/survey-objects/{object_id}", response_model=SurveyObjectResponse)
    def update_survey_object(object_id: int, payload: SurveyObjectUpdateRequest) -> SurveyObjectResponse:
        conn = build_backend().connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, survey_id, expedition_id, type,
                           ST_X(ST_Transform(geom, 4326)) AS lon,
                           ST_Y(ST_Transform(geom, 4326)) AS lat,
                           COALESCE(properties, '{}'::jsonb) AS properties
                    FROM survey_objects
                    WHERE id = %s AND is_active = TRUE
                    """,
                    (object_id,),
                )
                row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"survey object {object_id} not found")

            lon = payload.lon if payload.lon is not None else float(row[4])
            lat = payload.lat if payload.lat is not None else float(row[5])
            properties = payload.properties if payload.properties is not None else (row[6] or {})
        finally:
            conn.close()

        geom_wkt = f"POINT({lon} {lat})"
        try:
            edit_service.update_survey_object(object_id=object_id, geom_wkt=geom_wkt, properties=properties)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return SurveyObjectResponse(
            id=int(row[0]),
            survey_id=int(row[1]),
            expedition_id=int(row[2]) if row[2] is not None else None,
            obj_type=row[3],
            lon=lon,
            lat=lat,
            properties=properties,
            status="updated",
        )

    @app.delete("/api/survey-objects/{object_id}")
    def archive_survey_object(object_id: int) -> dict[str, Any]:
        conn = build_backend().connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT survey_id
                    FROM survey_objects
                    WHERE id = %s AND is_active = TRUE
                    """,
                    (object_id,),
                )
                row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"survey object {object_id} not found")
        finally:
            conn.close()

        try:
            edit_service.archive_survey_object(object_id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return {"status": "archived", "id": object_id, "survey_id": int(row[0])}

    @app.get("/api/layers/{layer_key}/geojson")
    def layer_geojson(
        layer_key: str,
        bbox: str | None = Query(default=None, description="minx,miny,maxx,maxy in EPSG:4326"),
        limit: int = Query(default=5000, ge=1, le=50000),
    ) -> dict[str, Any]:
        bounds = _parse_bounds(bbox)
        try:
            payload = map_service.get_layer_geojson(layer_key, bounds=bounds, limit=limit)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        if not isinstance(payload, dict) or payload.get("type") != "FeatureCollection":
            raise HTTPException(status_code=500, detail="layer query did not return a GeoJSON FeatureCollection")
        return payload

    @app.get("/api/layers/{layer_key}/tiles/{z}/{x}/{y}.mvt")
    def layer_tiles(layer_key: str, z: int, x: int, y: int) -> Response:
        conn = build_backend().connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT EXISTS (
                        SELECT 1
                        FROM layers_registry
                        WHERE layer_key = %s
                    )
                    ''',
                    (layer_key,),
                )
                exists = cur.fetchone()[0]
                if not exists:
                    raise HTTPException(status_code=404, detail=f"layer {layer_key} not found")

                cur.execute(
                    '''
                    WITH tile AS (
                        SELECT ST_TileEnvelope(%s, %s, %s) AS geom_3857
                    ),
                    mvtgeom AS (
                        SELECT
                            id,
                            source_id,
                            source_table,
                            ST_AsMVTGeom(
                                ST_Transform(ef.geom, 3857),
                                tile.geom_3857,
                                %s,
                                %s,
                                true
                            ) AS geom,
                            COALESCE(ef.properties, '{}'::jsonb) AS properties
                        FROM external_features ef
                        CROSS JOIN tile
                        WHERE ef.layer = %s
                          AND ef.geom IS NOT NULL
                          AND ST_Intersects(ST_Transform(ef.geom, 3857), tile.geom_3857)
                    )
                    SELECT COALESCE(
                        ST_AsMVT(mvtgeom, %s, %s, 'geom'),
                        ''::bytea
                    )
                    FROM mvtgeom
                    WHERE geom IS NOT NULL
                    ''',
                    (z, x, y, MVT_EXTENT, MVT_BUFFER, layer_key, layer_key, MVT_EXTENT),
                )
                tile_bytes = cur.fetchone()[0]
            return Response(content=bytes(tile_bytes), media_type="application/vnd.mapbox-vector-tile")
        finally:
            conn.close()

    return app


app = create_app()
