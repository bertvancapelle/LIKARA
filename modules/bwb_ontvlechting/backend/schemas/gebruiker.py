"""Pydantic v2-schemas — gebruikersbeheer (ADR-029 Fase 2).

`GebruikerAanmakenRequest` bevat BEWUST geen wachtwoord-veld: de backend genereert een sterk
tijdelijk wachtwoord en geeft het éénmalig terug in `GebruikerAangemaaktResponse`. Email als
plain `str` + lichte format-validatie (consistent met de partij-schema's; geen harde
email-validator-dependency).
"""
import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from schemas._validators import _verplichte_tekst

_EMAIL_PATROON = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class GebruikerAanmakenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    naam: str
    email: str
    afdeling_id: uuid.UUID | None = None
    functietitel: str | None = None
    rol: Literal["medewerker", "viewer"] = "medewerker"

    @field_validator("naam")
    @classmethod
    def _naam(cls, v: str) -> str:
        return _verplichte_tekst(v, "naam", 255)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = _verplichte_tekst(v, "email", 255).lower()
        if not _EMAIL_PATROON.match(v):
            raise ValueError("Geef een geldig e-mailadres op.")
        return v

    @field_validator("functietitel")
    @classmethod
    def _functietitel(cls, v: str | None) -> str | None:
        return v if v is None else _verplichte_tekst(v, "functietitel", 150)


class GebruikerPersoonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    keycloak_sub: str
    persoon_id: uuid.UUID
    naam: str
    email: str | None = None
    aangemaakt_op: datetime
    # ADR-029 Fase 2b — verrijking uit Keycloak (best-effort; None als onbekend/onbereikbaar):
    # de huidige realm-rol + de account-status, zodat de voorkant per rij rol + status toont.
    rol: str | None = None
    enabled: bool | None = None


class GebruikerAangemaaktResponse(BaseModel):
    """201-respons bij aanmaak. `tijdelijk_wachtwoord` wordt éénmalig getoond aan de
    beheerder en NOOIT opgeslagen of gelogd."""

    gebruiker: GebruikerPersoonRead
    tijdelijk_wachtwoord: str


# ── ADR-029 Fase 2b — beheeracties op een bestaande gebruiker ────────────────────────

class GebruikerRolWijzigRequest(BaseModel):
    """Rol wijzigen — alle vier tenant-rollen toewijsbaar."""

    model_config = ConfigDict(extra="forbid")

    rol: Literal["viewer", "medewerker", "beheerder", "auditor"]


class GebruikerStatusRequest(BaseModel):
    """In- (`actief=true`) of uitschakelen (`actief=false`) — nooit verwijderen."""

    model_config = ConfigDict(extra="forbid")

    actief: bool


class GebruikerCorrectieRequest(BaseModel):
    """Naam/e-mail van een bestaande gebruiker corrigeren (typefout/naamswijziging)."""

    model_config = ConfigDict(extra="forbid")

    naam: str
    email: str

    @field_validator("naam")
    @classmethod
    def _naam(cls, v: str) -> str:
        return _verplichte_tekst(v, "naam", 255)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = _verplichte_tekst(v, "email", 255).lower()
        if not _EMAIL_PATROON.match(v):
            raise ValueError("Geef een geldig e-mailadres op.")
        return v


class GebruikerWachtwoordResponse(BaseModel):
    """Respons bij wachtwoord-reset: het nieuwe tijdelijke wachtwoord, éénmalig getoond,
    NOOIT opgeslagen of gelogd."""

    tijdelijk_wachtwoord: str
