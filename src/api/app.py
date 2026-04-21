from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from core.db import build_backend
from map.live_db_map_service import LiveDBMapService
from survey.query_service import SurveyQueryService
from api.schemas import ApiInfoResponse, HealthResponse, LayerRecord, SurveyRecord

APP_VERSION = "0.1.0"


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


def create_app() -> FastAPI:
    app = FastAPI(title="surveyCatalyst API", version=APP_VERSION)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    map_service = LiveDBMapService()
    survey_service = SurveyQueryService()

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
                "/api/surveys",
                "/api/surveys/{survey_id}",
                "/api/layers/{layer_key}/geojson?bbox=minx,miny,maxx,maxy&limit=5000",
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

    return app


app = create_app()
