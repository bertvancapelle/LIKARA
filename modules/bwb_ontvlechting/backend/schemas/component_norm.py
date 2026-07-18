"""Schemas — tenant-norm beheer (ADR-052 slice 4b)."""
from pydantic import BaseModel, ConfigDict


class NormVerplichtZet(BaseModel):
    """PUT-body voor het zetten van de verplicht-vlag op één hard feit."""

    model_config = ConfigDict(extra="forbid")

    verplicht: bool
