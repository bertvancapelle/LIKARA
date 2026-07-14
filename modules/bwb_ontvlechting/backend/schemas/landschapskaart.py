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
    leverancier_id: UUID | None = None       # partij-id van die externe partij (eenduidige UI-filtering)
    hosting_model: str | None = None        # hostingmodel van de component (enum-waarde)
    # ADR-028 — componentclassificatie (read-only afgeleid; alleen op component-nodes). Voedt
    # het rol-/BIV-filter + de randbehandeling (externe_dataprovider) client-side. None op
    # context-nodes (partij/contract/gebruikersgroep) → filter-exemptie.
    componentrol: str | None = None
    biv_beschikbaarheid: str | None = None
    biv_integriteit: str | None = None
    biv_vertrouwelijkheid: str | None = None
    # ADR-046 — levensfase van het component (in_ontwikkeling/in_productie/uitfaseren;
    # None = nog niet vastgelegd). Vervangt `plateau_dispositie` als kaart-signaal: één
    # waarheid op het component i.p.v. een niet-deterministisch "eerste plateau wint".
    levensfase: str | None = None
    blokkades_open: int = 0                 # aantal niet-opgeloste blokkades (read-only telling)
    # ADR-025 v4 (herzien ADR-046) — plateau-lidmaatschap als context: ALLE plateaus
    # waarvan dit component lid is, alfabetisch samengevoegd (deterministisch; meervoud
    # wordt getoond, nooit stil opgelost). De dispositie is afgebouwd (besluit 2).
    plateau_naam: str | None = None
    # ADR-031 — gebruikersgroep-node (ring 'gebruikers'): organisatie voor de groepeer-toggle +
    # ledental-badge. Alleen gevuld voor element_type='gebruikersgroep'.
    organisatie_id: UUID | None = None
    aantal_leden: int = 0
    # ADR-024 organisatie-scope (read-projectie, alleen op component-nodes):
    # - eigenaar_organisatie_id: de eigenaar-organisatie (bezit/aanbieden); None = zonder eigenaar.
    # - gebruikt_door_organisaties: organisatie-ids die dit component gebruiken (via serving aan hun
    #   gebruikersgroepen); leeg = door geen enkele organisatie.
    # ADR-038: `gebruikt_door_organisatieloos` is verwijderd — een groep heeft nu altijd een
    # organisatie, dus de vlag zou permanent False zijn.
    eigenaar_organisatie_id: UUID | None = None
    gebruikt_door_organisaties: list[UUID] = []


class ProcesHerkomstItem(BaseModel):
    """LI036 slice 2 — herkomst-regel op een doorgerolde procesvervulling-edge: het (deel)proces
    waar de koppelregel werkelijk op zit + het applicatiefunctie-label. Voedt de popup-uitsplitsing
    (stap 3) zonder de plaat te vervuilen."""

    proces_id: UUID
    proces_naam: str | None = None
    applicatiefunctie_label: str | None = None


class LandschapsEdge(BaseModel):
    bron_id: UUID
    doel_id: UUID
    relatietype: str                        # flow / assignment / association / serving / aggregation / roltoewijzing
    label: str                              # leesbaar: koppeling / draait op / valt onder / bestaat uit / <rol-naam>
    ring: str                               # applicaties / samenstelling / beheerorganisatie / contracten / infrastructuur / gebruikers
    # ADR-025 v4 — koppelingsdetails op flow-edges (uit relatie.kenmerken).
    richting: str | None = None             # eenrichting / tweerichting / bidirectioneel (gemengde groep)
    protocol: str | None = None             # bv. rest / soap / bestand / database (None bij gemengde groep)
    # ADR-023a Fase 3 — aantal samengetrokken flows op dit gericht paar (1 = enkele koppeling).
    aantal: int = 1
    # LI036 slice 2 — ALLEEN op procesvervulling-edges (ring 'processen'): de onderliggende
    # vervul-regels (deelproces + functie) van de doorgerolde component→hoofdproces-bundel.
    # Additief + nullable — bestaande edges dragen None.
    herkomst: list[ProcesHerkomstItem] | None = None


class LandschapskaartResponse(BaseModel):
    nodes: list[LandschapsNode]
    edges: list[LandschapsEdge]


class SubgraafRequest(BaseModel):
    """Set-scoped graaf-request: levert de gegeven component-ids (S) + hun directe buren (1 hop).
    POST i.p.v. GET met `?ids=` omdat de id-lijst lang wordt (URL-lengtelimiet)."""

    model_config = {"extra": "forbid"}

    component_ids: list[UUID]
    diepte: int = 1
