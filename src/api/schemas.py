from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SurveyCreate(BaseModel):
    expedition_id: int
    title: str
    status: str = "planned"
    geometry: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SurveyUpdate(BaseModel):
    expedition_id: int | None = None
    title: str | None = None
    status: str | None = None
    geometry: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class SurveyObjectCreate(BaseModel):
    expedition_id: int
    type: str
    geometry: dict[str, Any]
    title: str | None = None
    annotation: str | None = None
    details: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)


class SurveyObjectUpdate(BaseModel):
    type: str | None = None
    geometry: dict[str, Any] | None = None
    title: str | None = None
    annotation: str | None = None
    details: str | None = None
    properties: dict[str, Any] | None = None
    is_active: bool | None = None
