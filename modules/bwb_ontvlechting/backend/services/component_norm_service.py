"""Service — tenant-norm voor harde componentfeiten (ADR-052 slice 1).

Twee dingen:
1. **De norm lezen** (`haal_norm`): per hard feit of de tenant het verplicht heeft gesteld.
2. **De "is dit vastgesteld?"-leesbron** (`norm_status`): per VERPLICHT feit of het op een component
   is *vastgesteld* — een ECHT antwoord (ADR-052 besluit 2): een leeg veld én een sentinel die
   "geen antwoord" betekent (`hostingmodel = onbekend`) tellen als NIET vastgesteld.

De norm is een LAT, geen poort: ze gatet uitsluitend de menselijke klaarverklaring (ADR-027, al
engine-gescheiden) en RAAKT DE ENGINE NOOIT — bewust GEEN import van/schrijf naar `lifecycle_service`/
`herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade`/`Checklistscore`. Puur SELECT;
RLS scoopt op de tenant (dubbele bescherming met de expliciete `tenant_id`-filter).

Één bron, geen tweede afleiding: voor de vijf feiten met een bestaand registratiegat-signaal komt het
"vastgesteld"-oordeel uit dezelfde per-component signaal-leesbron (`registratiegaten_service.
badge_voor_component`) — de mapping `_FEIT_SIGNAAL` verwijst rechtstreeks naar diens signaal-constanten,
dus er kan niets driften.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Component, ComponentNorm, HostingModel
from services import registratiegaten_service

# ── De kiesbare set van harde feiten (code-eigen; ADR-052 subknoop 3) ──────────────────────────
# Eigen componentvelden met betekenisvolle afwezigheid + de relationele feiten. `componentrol` valt
# af: NOT NULL met server_default → nooit leeg → een norm erop is moot.
FEIT_EIGENAAR = "eigenaar"
FEIT_VERANTWOORDELIJKE = "verantwoordelijke"
FEIT_BIV = "biv"
FEIT_GEBRUIKERSGROEP = "gebruikersgroep"
FEIT_BEDRIJFSFUNCTIE = "bedrijfsfunctie"
FEIT_LEVENSFASE = "levensfase"
FEIT_BEDOELING = "bedoeling"          # component.migratiepad
FEIT_HOSTING = "hosting"              # component.hostingmodel (sentinel `onbekend` telt niet mee)
FEIT_KOPPELINGEN = "koppelingen"
FEIT_CONTRACT = "contract"

HARDE_FEITEN: tuple[str, ...] = (
    FEIT_EIGENAAR, FEIT_VERANTWOORDELIJKE, FEIT_BIV, FEIT_GEBRUIKERSGROEP,
    FEIT_BEDRIJFSFUNCTIE, FEIT_LEVENSFASE, FEIT_BEDOELING, FEIT_HOSTING,
    FEIT_KOPPELINGEN, FEIT_CONTRACT,
)

# ADR-052 subknoop 2 — de meegeleverde platform-default (GENERIEK, elke tenant): deze vijf op
# verplicht=true, de rest false. GÉÉN tenant-uitzondering in de default (BvoWB past later zelf aan
# via het beheerscherm, slice 4 — dat is tenant-configuratie, geen platformkeuze).
DEFAULT_VERPLICHT: frozenset[str] = frozenset({
    FEIT_EIGENAAR, FEIT_VERANTWOORDELIJKE, FEIT_BIV, FEIT_CONTRACT, FEIT_KOPPELINGEN,
})

# Statussen van de "is dit vastgesteld?"-lezing.
VASTGESTELD = "vastgesteld"
NIET_VASTGESTELD = "niet_vastgesteld"
# Contract + koppelingen: hun "vastgesteld"-oordeel hangt af van de "bewust geen"-bevinding
# (ADR-052 besluit 3), die pas in slice 2 wordt gebouwd. Tot dan expliciet TOETSING_VOLGT — nooit
# onterecht als gat gerekend (dat zou componenten vals als onvolledig tonen zonder route).
TOETSING_VOLGT = "toetsing_volgt"

_UITGESTELD: frozenset[str] = frozenset({FEIT_CONTRACT, FEIT_KOPPELINGEN})

# Feiten met een bestaand registratiegat-signaal: "vastgesteld" ⟺ het signaal is AFWEZIG in
# `badge_voor_component`. Verwijst rechtstreeks naar de signaal-constanten van
# `registratiegaten_service` — één bron, geen tweede afleiding die kan driften.
_FEIT_SIGNAAL: dict[str, str] = {
    FEIT_EIGENAAR: registratiegaten_service._SIG_EIGENAAR,
    FEIT_VERANTWOORDELIJKE: registratiegaten_service._SIG_VERANTWOORDELIJKE,
    FEIT_BIV: registratiegaten_service._SIG_BIV,
    FEIT_GEBRUIKERSGROEP: registratiegaten_service._SIG_GG,
    FEIT_BEDRIJFSFUNCTIE: registratiegaten_service._SIG_GEEN_BF,
}


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def haal_norm(session: AsyncSession, tenant_id) -> dict[str, bool]:
    """De opgeslagen norm als ``{feit_sleutel: verplicht}`` over de volledige `HARDE_FEITEN`-set.

    Een feit zónder rij telt als NIET verplicht: geen norm = geen eis (degradeert netjes — ADR-052:
    het overzicht werkt óók zonder ingerichte norm). Read-only."""
    tid = _tenant_uuid(tenant_id)
    rijen = (
        await session.execute(
            select(ComponentNorm.feit_sleutel, ComponentNorm.verplicht).where(
                ComponentNorm.tenant_id == tid
            )
        )
    ).all()
    opgeslagen = {r.feit_sleutel: bool(r.verplicht) for r in rijen}
    return {feit: opgeslagen.get(feit, False) for feit in HARDE_FEITEN}


async def norm_status(session: AsyncSession, tenant_id, component_id) -> dict:
    """Per VERPLICHT feit: is het vastgesteld op dít component? Read-only, engine-onaangeroerd.

    Retour: ``{"component_id": ..., "feiten": {feit_sleutel: status}}`` met status ∈
    {``vastgesteld``, ``niet_vastgesteld``, ``toetsing_volgt``}. Alleen de door de tenant verplicht
    gestelde feiten staan in ``feiten`` (niet-verplichte feiten doen niet mee aan de norm).

    Component buiten de tenant (of onbestaand) ⇒ lege ``feiten`` (geen lek)."""
    tid = _tenant_uuid(tenant_id)
    comp = (
        await session.execute(
            select(Component.hostingmodel, Component.levensfase, Component.migratiepad).where(
                Component.tenant_id == tid, Component.id == component_id
            )
        )
    ).one_or_none()
    if comp is None:
        return {"component_id": component_id, "feiten": {}}

    verplicht = {feit for feit, v in (await haal_norm(session, tid)).items() if v}

    # Eén (gedeelde) signaal-lezing, alleen als een signaal-gedekt feit verplicht is.
    signalen: set[str] = set()
    if verplicht & set(_FEIT_SIGNAAL):
        badge = await registratiegaten_service.badge_voor_component(session, tid, component_id)
        signalen = set(badge.get("signalen", []))

    def _status(feit: str) -> str:
        if feit in _UITGESTELD:
            return TOETSING_VOLGT
        if feit in _FEIT_SIGNAAL:
            return NIET_VASTGESTELD if _FEIT_SIGNAAL[feit] in signalen else VASTGESTELD
        if feit == FEIT_HOSTING:
            # Sentinel `onbekend` = "geen antwoord" → NIET vastgesteld (kolom is NOT NULL).
            vast = comp.hostingmodel not in (HostingModel.onbekend, HostingModel.onbekend.value)
        elif feit == FEIT_LEVENSFASE:
            vast = comp.levensfase is not None
        elif feit == FEIT_BEDOELING:
            vast = comp.migratiepad is not None
        else:  # onbereikbaar: verplicht ⊆ HARDE_FEITEN, alle takken gedekt
            vast = True
        return VASTGESTELD if vast else NIET_VASTGESTELD

    return {"component_id": component_id, "feiten": {feit: _status(feit) for feit in sorted(verplicht)}}
