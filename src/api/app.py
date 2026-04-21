from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response

from core.db import build_backend
from map.live_db_map_service import LiveDBMapService
from survey.edit_service import SurveyEditService
from survey.service import SurveyService
from .schemas import SurveyCreate, SurveyObjectCreate, SurveyObjectUpdate, SurveyUpdate

BASE_DIR = Path(__file__).resolve().parents[2]
APP_HTML = BASE_DIR / "app" / "openlayers_map.html"
MVT_EXTENT = 4096
MVT_BUFFER = 64

app = FastAPI(title="surveyCatalyst API", version="0.4.7")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    parts = [float(part) for part in bbox.split(",")]
    if len(parts) != 4:
        raise HTTPException(status_code=400, detail="bbox must contain minx,miny,maxx,maxy")
    return parts[0], parts[1], parts[2], parts[3]


def survey_layer_geojson(survey_id: int, bounds=None, limit: int = 5000):
    service = LiveDBMapService()
    layer_key = f"survey_{survey_id}"
    if hasattr(service, "get_survey_layer_geojson"):
        return service.get_survey_layer_geojson(layer_key=layer_key, bounds=bounds, limit=limit)

    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            params: list[Any] = [survey_id]
            boundary_filter = "WHERE id = %s"
            object_filter = "WHERE survey_id = %s AND is_active = TRUE"
            if bounds:
                minx, miny, maxx, maxy = bounds
                envelope = "ST_MakeEnvelope(%s, %s, %s, %s, 4326)"
                boundary_filter += f" AND geom IS NOT NULL AND geom && {envelope} AND ST_Intersects(geom, {envelope})"
                object_filter += f" AND geom IS NOT NULL AND geom && {envelope} AND ST_Intersects(geom, {envelope})"
                params.extend([minx, miny, maxx, maxy, minx, miny, maxx, maxy])
                object_params = [survey_id, minx, miny, maxx, maxy, minx, miny, maxx, maxy, limit]
            else:
                object_params = [survey_id, limit]
            cur.execute(
                f'''
                SELECT id, title, status, layer_key, expedition_id, metadata, ST_AsGeoJSON(geom)::jsonb
                FROM surveys
                {boundary_filter}
                LIMIT 1
                ''',
                params,
            )
            survey = cur.fetchone()
            if not survey:
                raise HTTPException(status_code=404, detail="Survey not found")
            if bounds:
                cur.execute(
                    f'''
                    SELECT id, survey_id, expedition_id, type, layer_key, properties, ST_AsGeoJSON(geom)::jsonb
                    FROM survey_objects
                    {object_filter}
                    LIMIT %s
                    ''',
                    object_params,
                )
            else:
                cur.execute(
                    '''
                    SELECT id, survey_id, expedition_id, type, layer_key, properties, ST_AsGeoJSON(geom)::jsonb
                    FROM survey_objects
                    WHERE survey_id = %s AND is_active = TRUE
                    LIMIT %s
                    ''',
                    object_params,
                )
            objects = cur.fetchall()
    finally:
        conn.close()

    features = []
    if survey[6] is not None:
        features.append(
            {
                "type": "Feature",
                "geometry": survey[6],
                "properties": {
                    "id": survey[0],
                    "survey_id": survey[0],
                    "title": survey[1],
                    "status": survey[2],
                    "layer_key": survey[3],
                    "expedition_id": survey[4],
                    "feature_role": "survey_boundary",
                    "metadata": survey[5] or {},
                },
            }
        )
    for row in objects:
        props = dict(row[5] or {})
        props.update(
            {
                "id": row[0],
                "survey_id": row[1],
                "expedition_id": row[2],
                "type": row[3],
                "layer_key": row[4],
                "feature_role": "survey_object",
            }
        )
        features.append({"type": "Feature", "geometry": row[6], "properties": props})
    return {"type": "FeatureCollection", "features": features}


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    return HTMLResponse(APP_HTML.read_text(encoding="utf-8"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api")
def api_root():
    return {"name": "surveyCatalyst API", "version": "0.4.7"}


@app.get("/api/layers")
def list_layers():
    service = LiveDBMapService()
    rows = service.list_layers()
    return [
        {
            "layer_key": row[0],
            "layer_name": row[1],
            "layer_group": row[2],
            "source_table": row[3],
            "geometry_type": row[4],
            "is_visible": row[5],
            "opacity": row[6],
            "sort_order": row[7],
            "metadata": row[8] or {},
        }
        for row in rows
    ]


@app.get("/api/context-layers")
def list_context_layers():
    layers = list_layers()
    return [layer for layer in layers if layer["layer_group"] == "context"]


@app.get("/api/layers/{layer_key}/geojson")
def layer_geojson(layer_key: str, bbox: str | None = None, limit: int = Query(default=5000, ge=1, le=20000)):
    service = LiveDBMapService()
    return service.get_layer_geojson(layer_key=layer_key, bounds=parse_bbox(bbox), limit=limit)


@app.get("/api/layers/{layer_key}/tiles/{z}/{x}/{y}.mvt")
def layer_tiles(layer_key: str, z: int, x: int, y: int):
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''
                WITH tile AS (
                    SELECT ST_TileEnvelope(%s, %s, %s) AS geom
                ),
                mvtgeom AS (
                    SELECT ST_AsMVTGeom(
                        ST_Transform(f.geom, 3857),
                        tile.geom,
                        %s,
                        %s,
                        TRUE
                    ) AS geom,
                    f.id,
                    f.layer,
                    f.source_table,
                    f.source_id,
                    COALESCE(f.properties, '{}'::jsonb) AS properties
                    FROM external_features f
                    CROSS JOIN tile
                    WHERE f.layer = %s
                      AND f.geom IS NOT NULL
                      AND ST_Intersects(ST_Transform(f.geom, 3857), tile.geom)
                )
                SELECT ST_AsMVT(mvtgeom, %s, %s)
                FROM mvtgeom
                WHERE geom IS NOT NULL
                ''',
                (z, x, y, MVT_EXTENT, MVT_BUFFER, layer_key, layer_key, MVT_EXTENT),
            )
            row = cur.fetchone()
            payload = row[0] if row else None
    finally:
        conn.close()
    return Response(content=bytes(payload or b""), media_type="application/vnd.mapbox-vector-tile")


@app.get("/api/surveys")
def list_surveys():
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT id, expedition_id, title, status, layer_key, metadata,
                       COUNT(so.id) FILTER (WHERE so.is_active = TRUE) AS object_count
                FROM surveys s
                LEFT JOIN survey_objects so ON so.survey_id = s.id
                GROUP BY id, expedition_id, title, status, layer_key, metadata
                ORDER BY id
                '''
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [
        {
            "id": row[0],
            "expedition_id": row[1],
            "title": row[2],
            "status": row[3],
            "layer_key": row[4],
            "metadata": row[5] or {},
            "object_count": row[6],
        }
        for row in rows
    ]


@app.get("/api/surveys/{survey_id}")
def get_survey(survey_id: int):
    hierarchy = SurveyEditService().list_survey_hierarchy(survey_id)
    return hierarchy["survey"]


@app.get("/api/surveys/{survey_id}/features")
def get_survey_features(survey_id: int, bbox: str | None = None, limit: int = Query(default=5000, ge=1, le=20000)):
    return survey_layer_geojson(survey_id=survey_id, bounds=parse_bbox(bbox), limit=limit)


@app.get("/api/surveys/{survey_id}/hierarchy")
def get_survey_hierarchy(survey_id: int):
    try:
        return SurveyEditService().list_survey_hierarchy(survey_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/surveys")
def create_survey(payload: SurveyCreate):
    service = SurveyEditService()
    survey_id, layer_key = service.create_survey(
        expedition_id=payload.expedition_id,
        title=payload.title,
        status=payload.status,
        geometry=payload.geometry,
        metadata=payload.metadata,
    )
    return {"survey_id": survey_id, "layer_key": layer_key}


@app.patch("/api/surveys/{survey_id}")
def update_survey(survey_id: int, payload: SurveyUpdate):
    SurveyEditService().update_survey(
        survey_id=survey_id,
        expedition_id=payload.expedition_id,
        title=payload.title,
        status=payload.status,
        geometry=payload.geometry,
        metadata=payload.metadata,
    )
    return {"ok": True}


@app.delete("/api/surveys/{survey_id}")
def delete_survey(survey_id: int):
    SurveyEditService().delete_survey(survey_id)
    return {"ok": True}


@app.post("/api/surveys/{survey_id}/objects")
def create_survey_object(survey_id: int, payload: SurveyObjectCreate):
    object_id = SurveyEditService().create_survey_object(
        survey_id=survey_id,
        expedition_id=payload.expedition_id,
        obj_type=payload.type,
        geometry=payload.geometry,
        properties=payload.properties,
        title=payload.title,
        annotation=payload.annotation,
        details=payload.details,
    )
    return {"object_id": object_id}


@app.patch("/api/survey-objects/{object_id}")
def update_survey_object(object_id: int, payload: SurveyObjectUpdate):
    SurveyEditService().update_survey_object(
        object_id=object_id,
        geometry=payload.geometry,
        obj_type=payload.type,
        properties=payload.properties,
        title=payload.title,
        annotation=payload.annotation,
        details=payload.details,
        is_active=payload.is_active,
    )
    return {"ok": True}


@app.delete("/api/survey-objects/{object_id}")
def delete_survey_object(object_id: int):
    SurveyEditService().delete_survey_object(object_id)
    return {"ok": True}



def create_app() -> FastAPI:
    return app
