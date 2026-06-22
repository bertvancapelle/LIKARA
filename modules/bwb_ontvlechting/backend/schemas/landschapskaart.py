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
    # ADR-025 v3 — verrijking voor zoeken/filteren/detail in de UI.
    domein: str | None = None               # componenttype-label (proxy voor functioneel domein)
    leverancier_naam: str | None = None     # externe partij via roltoewijzing (technisch/contractbeheer)
    hosting_model: str | None = None        # hostingmodel van de component (enum-waarde)
    blokkades_open: int = 0                 # aantal niet-opgeloste blokkades (read-only telling)
    # ADR-025 v4 — migratieplaatsing (eerste plateau via aggregation-lidmaatschap, met dispositie).
    plateau_naam: str | None = None
    plateau_dispositie: str | None = None


class LandschapsEdge(BaseModel):
    bron_id: UUID
    doel_id: UUID
    relatietype: str                        # flow / assignment / association / roltoewijzing
    label: str                              # leesbaar: koppeling / draait op / valt onder / <rol-naam>
    ring: str                               # applicaties / beheerorganisatie / contracten / infrastructuur
    # ADR-025 v4 — koppelingsdetails op flow-edges (uit relatie.kenmerken).
    richting: str | None = None             # eenrichting / tweerichting / bidirectioneel (gemengde groep)
    protocol: str | None = None             # bv. rest / soap / bestand / database (None bij gemengde groep)
    # ADR-023a Fase 3 — aantal samengetrokken flows op dit gericht paar (1 = enkele koppeling).
    aantal: int = 1


class LandschapskaartResponse(BaseModel):
    nodes: list[LandschapsNode]
    edges: list[LandschapsEdge]
