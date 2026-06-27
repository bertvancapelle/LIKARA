"""Pydantic v2 read-schemas — Fase B slice 2a (LI022): context-routes naar componenten.

`ContextComponentRead` is de gedeelde "component-verwijzing" (id + naam + type) die zowel de
contract→componenten- als de gebruiker-context→componenten-route teruggeven, zodat de frontend de
set component-ids rechtstreeks in `POST /landschapskaart/subgraaf` kan voeden.

`GebruikerContextRead` is de picker-bron: een distinct `(organisatie, afdeling)`-gebruikercontext
(beide nullable — bv. "— / Burgers" of "Gemeente Tiel / —"), met de geresolveerde organisatie-naam
en een telling van bijbehorende componenten.
"""
import uuid

from pydantic import BaseModel, ConfigDict


class ContextComponentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    component_id: uuid.UUID
    component_naam: str
    componenttype: str


class GebruikerContextRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organisatie_id: uuid.UUID | None = None
    organisatie_naam: str | None = None
    afdeling: str | None = None
    aantal_componenten: int
