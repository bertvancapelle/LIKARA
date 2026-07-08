"""Pydantic v2-schemas — persoonlijke gebruikersvoorkeur (ADR-041 slice 1).

De voorkeur-laag is GENERIEK: hij kent de betekenis van een voorkeur niet, alleen een sleutel + een
klein JSON-blob. De `sub` (eigenaar) staat NOOIT in de invoer — die stempelt de service server-side.
De `voorkeur_sleutel` reist via het URL-pad (route-validatie), niet via de body.

Deze laag borgt uitsluitend de VORM: een JSON-serialiseerbare waarde met een grootte-guard (geen vrije
opslag). De SEMANTISCHE validatie (welke waarde geldig is voor een specifieke sleutel) hoort bij de
consument (slice 2), niet hier.
"""
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

# Grootte-guard: een voorkeur is een kleine standaard-keuze, geen documentopslag.
MAX_WAARDE_BYTES = 4096


class VoorkeurUpsert(BaseModel):
    """Body van de upsert: uitsluitend de waarde (de sleutel zit in het pad)."""

    model_config = ConfigDict(extra="forbid")

    waarde: Any

    @field_validator("waarde")
    @classmethod
    def _v_waarde(cls, v: Any) -> Any:
        try:
            blob = json.dumps(v)
        except (TypeError, ValueError):
            raise ValueError("waarde moet JSON-serialiseerbaar zijn")
        if len(blob.encode("utf-8")) > MAX_WAARDE_BYTES:
            raise ValueError(f"waarde te groot (max {MAX_WAARDE_BYTES} bytes)")
        return v


class VoorkeurRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    voorkeur_sleutel: str
    waarde: Any
    updated_at: datetime
