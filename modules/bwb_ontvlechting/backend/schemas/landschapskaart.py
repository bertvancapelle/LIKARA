"""Pydantic v2-schemas — Landschapskaart (ADR-025, read-only grafprojectie).

Levert de volledige graaf (nodes + edges) van het ICT-landschap in één respons, afgeleid
uit bestaande data (elementen, relaties, roltoewijzingen). Puur read-only; geen schema/
migratie, engine onaangeroerd.
"""
from uuid import UUID

from pydantic import BaseModel


class LandschapsNode(BaseModel):
    id: UUID
    naam: str
    element_type: str                       # applicatie, database, partij, contract, server, …
    laag: str | None = None                 # business / application / technology / implementation_migration
    archimate_element: str | None = None
    lifecycle_status: str | None = None     # concept / in_inventarisatie / geblokkeerd / migratieklaar
    soort: str | None = None                # voor partijen: externe_partij / organisatie / …


class LandschapsEdge(BaseModel):
    bron_id: UUID
    doel_id: UUID
    relatietype: str                        # flow / assignment / association / roltoewijzing
    label: str                              # leesbaar: koppeling / draait op / valt onder / <rol-naam>
    ring: str                               # applicaties / beheerorganisatie / contracten / infrastructuur


class LandschapskaartResponse(BaseModel):
    nodes: list[LandschapsNode]
    edges: list[LandschapsEdge]
