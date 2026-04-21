from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    database: str


class LayerRecord(BaseModel):
    layer_key: str
    layer_name: str
    layer_group: str
    source_table: str | None = None
    geometry_type: str | None = None
    is_visible: bool
    opacity: float | None = None
    sort_order: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SurveyRecord(BaseModel):
    id: int
    expedition_id: int | None = None
    title: str
    status: str | None = None
    layer_key: str | None = None


class ApiInfoResponse(BaseModel):
    name: str
    version: str
    endpoints: list[str]
