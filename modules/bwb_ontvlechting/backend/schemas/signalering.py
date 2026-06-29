"""Pydantic v2-schemas — Signalering registratiegaten (ADR-035).

De `/registratiegaten`-respons is een gegroepeerde dict (kritiek/aandacht → signaaltype → items)
en wordt zonder response_model geserialiseerd. Alleen de badge heeft een vast schema.
"""
from pydantic import BaseModel


class BadgeRead(BaseModel):
    signalen: list[str]
    kritiek: int
    aandacht: int
