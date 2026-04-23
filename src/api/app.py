from __future__ import annotations

import hashlib
import json
import logging
from collections import deque
import shutil
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response

from core.db import build_backend
from map.live_db_map_service import LiveDBMapService
from survey.edit_service import SurveyEditService
from .schemas import SurveyCreate, SurveyObjectCreate, SurveyObjectUpdate, SurveyUpdate

BASE_DIR = Path(__file__).resolve().parents[2]
APP_HTML = BASE_DIR / "app" / "openlayers_map.html"
MVT_EXTENT = 4096
MVT_BUFFER = 64
TILE_CACHE_DIR = BASE_DIR / ".cache" / "mvt"
TILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


logger = logging.getLogger(__name__)

API_LOG_BUFFER: deque[str] = deque(maxlen=200)

class InMemoryLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            API_LOG_BUFFER.append(self.format(record))
        except Exception:
            pass

_memory_log_handler = InMemoryLogHandler()
_memory_log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
if not any(isinstance(h, InMemoryLogHandler) for h in logger.handlers):
    logger.addHandler(_memory_log_handler)
logger.setLevel(logging.INFO)

SPATIAL_INDEXES = [
    {"table": "surveys", "column": "geom", "index_name": "idx_surveys_geom_gist"},
    {"table": "survey_objects", "column": "geom", "index_name": "idx_survey_objects_geom_gist"},
    {"table": "external_features", "column": "geom", "index_name": "idx_external_features_geom_gist"},
]


def _structured_error(status_code: int, code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    return {
        "error": {
            "status_code": status_code,
            "code": code,
            "message": message,
            "details": details,
        }
    }


def _clear_tile_cache(layer_key: str | None = None) -> dict[str, Any]:
    if layer_key:
        layer_hash = hashlib.sha1(layer_key.encode("utf-8")).hexdigest()[:16]
        target = TILE_CACHE_DIR / layer_hash
        removed = 0
        if target.exists():
            removed = sum(1 for _ in target.rglob("*.mvt"))
            shutil.rmtree(target, ignore_errors=True)
        return {"scope": "layer", "layer_key": layer_key, "removed_tiles": removed}
    removed = 0
    if TILE_CACHE_DIR.exists():
        removed = sum(1 for _ in TILE_CACHE_DIR.rglob("*.mvt"))
        shutil.rmtree(TILE_CACHE_DIR, ignore_errors=True)
    TILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return {"scope": "all", "removed_tiles": removed}


def _tile_cache_status() -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    total_tiles = 0
    if TILE_CACHE_DIR.exists():
        for layer_dir in sorted([p for p in TILE_CACHE_DIR.iterdir() if p.is_dir()]):
            count = sum(1 for _ in layer_dir.rglob("*.mvt"))
            total_tiles += count
            entries.append({"cache_bucket": layer_dir.name, "tiles": count})
    return {
        "cache_root": str(TILE_CACHE_DIR),
        "layers": entries,
        "layer_buckets": len(entries),
        "total_tiles": total_tiles,
    }


def _fetch_one_value(query: str, params: tuple[Any, ...]) -> Any | None:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def _get_survey_layer_key(survey_id: int) -> str | None:
    value = _fetch_one_value("SELECT layer_key FROM surveys WHERE id = %s", (survey_id,))
    return str(value) if value else None


def _get_object_survey_layer_key(object_id: int) -> str | None:
    value = _fetch_one_value(
        """
        SELECT s.layer_key
        FROM survey_objects so
        JOIN surveys s ON s.id = so.survey_id
        WHERE so.id = %s
        """,
        (object_id,),
    )
    return str(value) if value else None


def _clear_tile_cache_for_layers(layer_keys: list[str] | tuple[str, ...]) -> dict[str, Any]:
    unique_layer_keys: list[str] = []
    for key in layer_keys:
        if key and key not in unique_layer_keys:
            unique_layer_keys.append(key)
    if not unique_layer_keys:
        return {"scope": "none", "layers": [], "removed_tiles": 0}
    cleared = [_clear_tile_cache(layer_key=key) for key in unique_layer_keys]
    return {
        "scope": "layers",
        "layers": unique_layer_keys,
        "removed_tiles": sum(item["removed_tiles"] for item in cleared),
        "details": cleared,
    }


def _get_spatial_index_status() -> list[dict[str, Any]]:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT schemaname, tablename, indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = ANY (current_schemas(false))
                """
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    statuses = []
    for spec in SPATIAL_INDEXES:
        matches = [
            row for row in rows
            if row[1] == spec["table"]
            and "using gist" in row[3].lower()
            and spec["column"].lower() in row[3].lower()
        ]
        statuses.append({
            "table": spec["table"],
            "column": spec["column"],
            "expected_index": spec["index_name"],
            "present": bool(matches),
            "indexes": [m[2] for m in matches],
        })
    return statuses


def _ensure_spatial_indexes() -> list[dict[str, Any]]:
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            for spec in SPATIAL_INDEXES:
                cur.execute(
                    f'CREATE INDEX IF NOT EXISTS {spec["index_name"]} ON {spec["table"]} USING GIST ({spec["column"]})'
                )
        conn.commit()
    finally:
        conn.close()
    return _get_spatial_index_status()

app = FastAPI(title="surveyCatalyst API", version="0.5.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_log_middleware(request: Request, call_next):
    response = await call_next(request)
    try:
        logger.info("%s %s -> %s", request.method, request.url.path, response.status_code)
    except Exception:
        pass
    return response


@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail:
        payload = detail
    else:
        payload = _structured_error(exc.status_code, "http_error", str(detail), None)
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=_structured_error(422, "validation_error", "Request validation failed", exc.errors()),
    )


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled API error")
    return JSONResponse(
        status_code=500,
        content=_structured_error(500, "internal_error", "Internal server error", {"type": exc.__class__.__name__}),
    )


def parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if not bbox:
        return None
    parts = [float(part) for part in bbox.split(",")]
    if len(parts) != 4:
        raise HTTPException(status_code=400, detail="bbox must contain minx,miny,maxx,maxy")
    return parts[0], parts[1], parts[2], parts[3]


def _cache_file_for_tile(layer_key: str, z: int, x: int, y: int) -> Path:
    layer_hash = hashlib.sha1(layer_key.encode("utf-8")).hexdigest()[:16]
    path = TILE_CACHE_DIR / layer_hash / str(z) / str(x)
    path.mkdir(parents=True, exist_ok=True)
    return path / f"{y}.mvt"


def _read_cached_tile(layer_key: str, z: int, x: int, y: int) -> bytes | None:
    cache_file = _cache_file_for_tile(layer_key, z, x, y)
    if cache_file.exists():
        return cache_file.read_bytes()
    return None


def _write_cached_tile(layer_key: str, z: int, x: int, y: int, payload: bytes) -> None:
    _cache_file_for_tile(layer_key, z, x, y).write_bytes(payload)


def _bbox_simplification_tolerance(bounds: tuple[float, float, float, float] | None) -> float:
    if not bounds:
        return 0.0
    minx, miny, maxx, maxy = bounds
    span = max(abs(maxx - minx), abs(maxy - miny))
    if span <= 0.02:
        return 0.0
    if span <= 0.2:
        return 0.00001
    if span <= 1.0:
        return 0.00005
    if span <= 5.0:
        return 0.0002
    return 0.001


def _geojson_geom_sql(column: str, tolerance: float) -> str:
    if tolerance <= 0.0:
        return f"ST_AsGeoJSON({column})::jsonb"
    return f"ST_AsGeoJSON(ST_SimplifyPreserveTopology({column}, {tolerance}))::jsonb"


def survey_layer_geojson(survey_id: int, bounds=None, limit: int = 5000):
    service = LiveDBMapService()
    layer_key = f"survey_{survey_id}"
    if hasattr(service, "get_survey_layer_geojson"):
        return service.get_survey_layer_geojson(layer_key=layer_key, bounds=bounds, limit=limit)

    backend = build_backend()
    simplify_tolerance = _bbox_simplification_tolerance(bounds)
    survey_geom_sql = _geojson_geom_sql("geom", simplify_tolerance)
    object_geom_sql = _geojson_geom_sql("geom", simplify_tolerance)
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            boundary_filter = "WHERE id = %s"
            object_filter = "WHERE survey_id = %s AND is_active = TRUE"
            if bounds:
                minx, miny, maxx, maxy = bounds
                envelope = "ST_MakeEnvelope(%s, %s, %s, %s, 4326)"
                boundary_filter += f" AND geom IS NOT NULL AND geom && {envelope} AND ST_Intersects(geom, {envelope})"
                object_filter += f" AND geom IS NOT NULL AND geom && {envelope} AND ST_Intersects(geom, {envelope})"
                boundary_params: list[Any] = [survey_id, minx, miny, maxx, maxy, minx, miny, maxx, maxy]
                object_params: list[Any] = [survey_id, minx, miny, maxx, maxy, minx, miny, maxx, maxy, limit]
            else:
                boundary_params = [survey_id]
                object_params = [survey_id, limit]

            cur.execute(
                f"""
                SELECT id, title, status, layer_key, expedition_id, metadata, {survey_geom_sql}
                FROM surveys
                {boundary_filter}
                LIMIT 1
                """,
                boundary_params,
            )
            survey = cur.fetchone()
            if not survey:
                raise HTTPException(status_code=404, detail="Survey not found")

            if bounds:
                cur.execute(
                    f"""
                    SELECT id, survey_id, expedition_id, type, layer_key, properties, is_active, {object_geom_sql}
                    FROM survey_objects
                    {object_filter}
                    LIMIT %s
                    """,
                    object_params,
                )
            else:
                cur.execute(
                    f"""
                    SELECT id, survey_id, expedition_id, type, layer_key, properties, is_active, {object_geom_sql}
                    FROM survey_objects
                    WHERE survey_id = %s AND is_active = TRUE
                    LIMIT %s
                    """,
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
                "is_active": row[6],
            }
        )
        features.append({"type": "Feature", "geometry": row[7], "properties": props})
    return {"type": "FeatureCollection", "features": features}


def build_survey_export_bundle(
    survey_id: int,
    include_boundary: bool = True,
    include_objects: bool = True,
    include_archived: bool = False,
    include_geometry: bool = True,
    include_properties: bool = True,
) -> dict[str, Any]:
    hierarchy = SurveyEditService().list_survey_hierarchy(survey_id)
    survey = dict(hierarchy["survey"])
    objects = []
    for obj in hierarchy["objects"]:
        if not include_archived and not obj.get("is_active", True):
            continue
        filtered = dict(obj)
        if not include_geometry:
            filtered.pop("geometry", None)
        if not include_properties:
            filtered.pop("properties", None)
        objects.append(filtered)

    if not include_geometry:
        survey.pop("geometry", None)

    layer_features = []
    if include_boundary and include_objects:
        layer_geojson = survey_layer_geojson(survey_id=survey_id, bounds=None, limit=20000)
        layer_features = list(layer_geojson.get("features", []))
    elif include_boundary or include_objects:
        layer_geojson = survey_layer_geojson(survey_id=survey_id, bounds=None, limit=20000)
        for feature in layer_geojson.get("features", []):
            role = (feature.get("properties") or {}).get("feature_role")
            if include_boundary and role == "survey_boundary":
                layer_features.append(feature)
            elif include_objects and role == "survey_object":
                obj_props = feature.get("properties") or {}
                if include_archived or obj_props.get("is_active", True):
                    layer_features.append(feature)

    return {
        "survey": survey,
        "objects": objects if include_objects else [],
        "layer": {"type": "FeatureCollection", "features": layer_features},
    }


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    return HTMLResponse(APP_HTML.read_text(encoding="utf-8"))



@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/admin/logs")
def get_logs(limit: int = Query(100, ge=1, le=500)):
    return {"lines": list(API_LOG_BUFFER)[-limit:]}


@app.get("/api")
def api_root():
    return {"name": "surveyCatalyst API", "version": "0.5.0"}


@app.get("/api/admin/index-status")
def index_status():
    return {"indexes": _get_spatial_index_status()}


@app.post("/api/admin/ensure-spatial-indexes")
def ensure_spatial_indexes():
    return {"indexes": _ensure_spatial_indexes()}


@app.get("/api/cache/status")
def tile_cache_status():
    return {"ok": True, **_tile_cache_status()}


@app.delete("/api/cache/tiles")
def clear_all_tile_cache():
    return {"ok": True, **_clear_tile_cache()}


@app.delete("/api/cache/tiles/{layer_key}")
def clear_layer_tile_cache(layer_key: str):
    return {"ok": True, **_clear_tile_cache(layer_key=layer_key)}


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
    bounds = parse_bbox(bbox)
    service = LiveDBMapService()
    return service.get_layer_geojson(layer_key=layer_key, bounds=bounds, limit=limit)


@app.get("/api/layers/{layer_key}/tiles/{z}/{x}/{y}.mvt")
def layer_tiles(layer_key: str, z: int, x: int, y: int):
    cached = _read_cached_tile(layer_key, z, x, y)
    if cached is not None:
        return Response(content=cached, media_type="application/vnd.mapbox-vector-tile", headers={"X-Tile-Cache": "HIT"})

    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            simplify_tolerance = 0
            if z <= 8:
                simplify_tolerance = 50
            elif z <= 10:
                simplify_tolerance = 10
            elif z <= 12:
                simplify_tolerance = 2

            cur.execute(
                """
                WITH tile AS (
                    SELECT ST_TileEnvelope(%s, %s, %s) AS geom
                ),
                candidate AS (
                    SELECT
                        CASE
                            WHEN %s > 0 THEN ST_SimplifyPreserveTopology(ST_Transform(f.geom, 3857), %s)
                            ELSE ST_Transform(f.geom, 3857)
                        END AS geom,
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
                ),
                mvtgeom AS (
                    SELECT ST_AsMVTGeom(
                        candidate.geom,
                        tile.geom,
                        %s,
                        %s,
                        TRUE
                    ) AS geom,
                    id,
                    layer,
                    source_table,
                    source_id,
                    properties
                    FROM candidate
                    CROSS JOIN tile
                )
                SELECT ST_AsMVT(mvtgeom, %s, %s)
                FROM mvtgeom
                WHERE mvtgeom.geom IS NOT NULL
                """,
                (z, x, y, simplify_tolerance, simplify_tolerance, layer_key, MVT_EXTENT, MVT_BUFFER, layer_key, MVT_EXTENT),
            )
            row = cur.fetchone()
            payload = bytes(row[0] or b"") if row else b""
    finally:
        conn.close()

    _write_cached_tile(layer_key, z, x, y, payload)
    return Response(content=payload, media_type="application/vnd.mapbox-vector-tile", headers={"X-Tile-Cache": "MISS"})


@app.get("/api/surveys")
def list_surveys():
    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.id, s.expedition_id, s.title, s.status, s.layer_key, s.metadata,
                       COUNT(so.id) FILTER (WHERE so.is_active = TRUE) AS object_count
                FROM surveys s
                LEFT JOIN survey_objects so ON so.survey_id = s.id
                GROUP BY s.id, s.expedition_id, s.title, s.status, s.layer_key, s.metadata
                ORDER BY s.id
                """
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
    invalidation = _clear_tile_cache_for_layers([layer_key])
    return {"survey_id": survey_id, "layer_key": layer_key, "cache_invalidation": invalidation}


@app.patch("/api/surveys/{survey_id}")
def update_survey(survey_id: int, payload: SurveyUpdate):
    layer_key = _get_survey_layer_key(survey_id)
    SurveyEditService().update_survey(
        survey_id=survey_id,
        expedition_id=payload.expedition_id,
        title=payload.title,
        status=payload.status,
        geometry=payload.geometry,
        metadata=payload.metadata,
    )
    invalidation = _clear_tile_cache_for_layers([layer_key] if layer_key else [])
    return {"ok": True, "cache_invalidation": invalidation}


@app.delete("/api/surveys/{survey_id}")
def delete_survey(survey_id: int):
    layer_key = _get_survey_layer_key(survey_id)
    SurveyEditService().delete_survey(survey_id)
    invalidation = _clear_tile_cache_for_layers([layer_key] if layer_key else [])
    return {"ok": True, "cache_invalidation": invalidation}


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
    layer_key = _get_survey_layer_key(survey_id)
    invalidation = _clear_tile_cache_for_layers([layer_key] if layer_key else [])
    return {"object_id": object_id, "cache_invalidation": invalidation}


@app.patch("/api/survey-objects/{object_id}")
def update_survey_object(object_id: int, payload: SurveyObjectUpdate):
    layer_key = _get_object_survey_layer_key(object_id)
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
    invalidation = _clear_tile_cache_for_layers([layer_key] if layer_key else [])
    return {"ok": True, "cache_invalidation": invalidation}


@app.delete("/api/survey-objects/{object_id}")
def delete_survey_object(object_id: int):
    layer_key = _get_object_survey_layer_key(object_id)
    SurveyEditService().delete_survey_object(object_id)
    invalidation = _clear_tile_cache_for_layers([layer_key] if layer_key else [])
    return {"ok": True, "cache_invalidation": invalidation}


@app.get("/api/surveys/{survey_id}/export/layer.geojson")
def export_survey_layer(
    survey_id: int,
    include_boundary: bool = True,
    include_objects: bool = True,
    include_archived: bool = False,
):
    bundle = build_survey_export_bundle(
        survey_id=survey_id,
        include_boundary=include_boundary,
        include_objects=include_objects,
        include_archived=include_archived,
        include_geometry=True,
        include_properties=True,
    )
    return bundle["layer"]


@app.get("/api/surveys/{survey_id}/export/data.json")
def export_survey_data(
    survey_id: int,
    include_boundary: bool = True,
    include_objects: bool = True,
    include_archived: bool = False,
    include_geometry: bool = True,
    include_properties: bool = True,
):
    bundle = build_survey_export_bundle(
        survey_id=survey_id,
        include_boundary=include_boundary,
        include_objects=include_objects,
        include_archived=include_archived,
        include_geometry=include_geometry,
        include_properties=include_properties,
    )
    return {
        "survey": bundle["survey"],
        "objects": bundle["objects"],
        "options": {
            "include_boundary": include_boundary,
            "include_objects": include_objects,
            "include_archived": include_archived,
            "include_geometry": include_geometry,
            "include_properties": include_properties,
        },
    }


@app.get("/api/surveys/{survey_id}/export/document.json")
def export_survey_document_data(
    survey_id: int,
    include_boundary: bool = True,
    include_objects: bool = True,
    include_archived: bool = False,
    include_geometry: bool = False,
    include_properties: bool = True,
):
    bundle = build_survey_export_bundle(
        survey_id=survey_id,
        include_boundary=include_boundary,
        include_objects=include_objects,
        include_archived=include_archived,
        include_geometry=include_geometry,
        include_properties=include_properties,
    )
    survey = bundle["survey"]
    objects = bundle["objects"]
    active_count = sum(1 for obj in objects if obj.get("is_active", True))
    archived_count = sum(1 for obj in objects if not obj.get("is_active", True))
    return {
        "survey": survey,
        "objects": objects,
        "summary": {
            "object_count": len(objects),
            "active_count": active_count,
            "archived_count": archived_count,
        },
        "options": {
            "include_boundary": include_boundary,
            "include_objects": include_objects,
            "include_archived": include_archived,
            "include_geometry": include_geometry,
            "include_properties": include_properties,
        },
    }


@app.on_event("startup")
def startup_index_check() -> None:
    statuses = _get_spatial_index_status()
    missing = [s for s in statuses if not s["present"]]
    if missing:
        logger.warning("Missing spatial indexes: %s", missing)


def create_app() -> FastAPI:
    return app


# === surveyCatalyst storage/export extension ===
def _sc_storage_root():
    from pathlib import Path
    root = Path.cwd() / "workspace"
    (root / "downloads" / "raw" / "osm").mkdir(parents=True, exist_ok=True)
    (root / "downloads" / "curated" / "itinere").mkdir(parents=True, exist_ok=True)
    (root / "exports").mkdir(parents=True, exist_ok=True)
    return root

def _sc_slugify(value: str | None, default: str = "export") -> str:
    import re
    raw = (value or "").strip().lower()
    raw = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return raw or default

@app.get("/api/storage/summary")
def sc_storage_summary():
    root = _sc_storage_root()
    return {
        "workspace": str(root),
        "downloads_raw": str(root / "downloads" / "raw"),
        "downloads_curated": str(root / "downloads" / "curated"),
        "exports": str(root / "exports"),
    }

@app.post("/api/exports/save")
def sc_save_export(payload: dict):
    import base64
    from datetime import datetime
    from pathlib import Path

    root = _sc_storage_root()
    description = payload.get("description") or "export"
    kind = payload.get("kind") or "export"
    filename = payload.get("filename") or f"{kind}.bin"
    content_b64 = payload.get("content_base64") or ""
    survey_id = payload.get("survey_id")
    folder_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_sc_slugify(description, default='export')}"
    folder = root / "exports" / folder_name
    folder.mkdir(parents=True, exist_ok=True)

    target = folder / filename
    target.write_bytes(base64.b64decode(content_b64))

    meta = {
        "description": description,
        "kind": kind,
        "filename": filename,
        "mime_type": payload.get("mime_type"),
        "survey_id": survey_id,
        "saved_at": datetime.now().isoformat(),
        "path": str(target),
    }
    (folder / "export_meta.json").write_text(__import__("json").dumps(meta, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "folder": str(folder),
        "path": str(target),
        "filename": filename,
    }
\n
# === surveyCatalyst UI parcel permission export ===
@app.post("/api/permissions/export")
def export_permission(payload: dict):
    import json
    import re
    from datetime import datetime
    from pathlib import Path

    layer = str(payload.get("layer") or "").strip()
    source_id = str(payload.get("source_id") or "").strip()
    description = str(payload.get("description") or "ui parcel export").strip()

    if not layer or not source_id:
        return {"ok": False, "error": "missing layer or source_id"}

    def _slugify(value: str) -> str:
        raw = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
        return raw or "permission-export"

    backend = build_backend()
    conn = backend.connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT layer, source_id, source_table, properties, ST_AsGeoJSON(geom)
                FROM external_features
                WHERE layer = %s AND source_id = %s
                LIMIT 1
                """,
                (layer, source_id),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return {"ok": False, "error": "feature not found"}

    root = Path.cwd() / "workspace" / "permissions" / "requests"
    root.mkdir(parents=True, exist_ok=True)

    folder = root / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_slugify(description)}"
    folder.mkdir(parents=True, exist_ok=True)

    payload_out = {
        "layer": row[0],
        "source_id": row[1],
        "source_table": row[2],
        "properties": row[3],
        "geometry": json.loads(row[4]) if row[4] else None,
        "description": description,
        "saved_at": datetime.now().isoformat(),
    }

    out = folder / "permission_candidate.json"
    out.write_text(json.dumps(payload_out, indent=2), encoding="utf-8")

    return {"ok": True, "folder": str(folder)}
\n