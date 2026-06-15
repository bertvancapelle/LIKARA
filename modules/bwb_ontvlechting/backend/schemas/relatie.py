"""Pydantic v2 schemas — relatiemodel (ADR-023 Fase B)."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class RelatieCreate(BaseModel):
    model_config = {"extra": "forbid"}

    bron_id: uuid.UUID
    doel_id: uuid.UUID
    relatietype: str = Field(min_length=1, max_length=40)
    kenmerken: dict = Field(default_factory=dict)
    omschrijving: str | None = Field(default=None, max_length=2000)

    @field_validator("relatietype")
    @classmethod
    def _strip_type(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("relatietype mag niet leeg zijn")
        return v


class RelatieUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    kenmerken: dict | None = None
    omschrijving: str | None = Field(default=None, max_length=2000)


class RelatieRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    bron_id: uuid.UUID
    doel_id: uuid.UUID
    relatietype: str
    kenmerken: dict
    omschrijving: str | None = None
    created_at: datetime
    updated_at: datetime


class RelatiePagina(BaseModel):
    items: list[RelatieRead]
    volgende_cursor: str | None = None
