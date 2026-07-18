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

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    AuditLog,
    Component,
    ComponentBevindingSoort,
    ComponentKlaarverklaring,
    ComponentNorm,
    HostingModel,
    KlaarverklaringStatus,
)
from services import actor_resolutie, component_bevinding_service, registratiegaten_service

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
# (ADR-052 slice 2: contract + koppelingen zijn nu volwaardig toetsbaar — echte registratie OF de
# "bewust geen"-bevinding. De tijdelijke `toetsing_volgt`-stand uit slice 1 is daarmee vervallen.)

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
    {``vastgesteld``, ``niet_vastgesteld``}. Alleen de door de tenant verplicht gestelde feiten staan
    in ``feiten`` (niet-verplichte feiten doen niet mee aan de norm).

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

    # ADR-052 slice 2 — koppelingen/contract: vastgesteld zodra er een ÉCHTE registratie is (die
    # WINT — geen tegenspraak) OF een "bewust geen"-bevinding staat. De "heeft registratie"-lezer én
    # de bevindingen komen uit component_bevinding_service (single source; geen tweede afleiding).
    rel_feiten = verplicht & {FEIT_KOPPELINGEN, FEIT_CONTRACT}
    rel_vast: dict[str, bool] = {}
    if rel_feiten:
        bevinding_soorten = await component_bevinding_service.soorten_van_component(
            session, tid, component_id
        )
        for feit in rel_feiten:
            rel_vast[feit] = (
                feit in bevinding_soorten
                or await component_bevinding_service.heeft_echte_registratie(
                    session, tid, component_id, feit
                )
            )

    def _status(feit: str) -> str:
        vast = _beslis_vastgesteld(
            feit, hostingmodel=comp.hostingmodel, levensfase=comp.levensfase,
            migratiepad=comp.migratiepad, signalen=signalen, rel_vast=rel_vast,
        )
        return VASTGESTELD if vast else NIET_VASTGESTELD

    return {"component_id": component_id, "feiten": {feit: _status(feit) for feit in sorted(verplicht)}}


def _beslis_vastgesteld(feit: str, *, hostingmodel, levensfase, migratiepad, signalen, rel_vast) -> bool:
    """DE determinatie per feit — pure functie, DE ENE bron (norm_status én de impact-voorspelling
    lezen deze; geen tweede telling). `signalen` = de signaal-sleutels op dit component; `rel_vast` =
    {feit: bool} voor de relationele feiten (bewust geen / echte registratie)."""
    if feit in _FEIT_SIGNAAL:
        return _FEIT_SIGNAAL[feit] not in signalen
    if feit in rel_vast:
        return rel_vast[feit]
    if feit == FEIT_HOSTING:
        # Sentinel `onbekend` = "geen antwoord" → NIET vastgesteld (kolom is NOT NULL).
        return hostingmodel not in (HostingModel.onbekend, HostingModel.onbekend.value)
    if feit == FEIT_LEVENSFASE:
        return levensfase is not None
    if feit == FEIT_BEDOELING:
        return migratiepad is not None
    return True  # onbereikbaar: feit ⊆ HARDE_FEITEN, alle takken gedekt


async def feit_vastgesteld(session: AsyncSession, tenant_id, component_id, feit) -> bool | None:
    """Is dít ene feit vastgesteld op dit component? None als het component niet bestaat. Read-only.
    Zelfde determinatie (`_beslis_vastgesteld`) als norm_status — voedt de impact-voorspelling zonder
    een tweede afleiding. Alleen de voor dít feit relevante bron wordt gelezen."""
    tid = _tenant_uuid(tenant_id)
    comp = (
        await session.execute(
            select(Component.hostingmodel, Component.levensfase, Component.migratiepad).where(
                Component.tenant_id == tid, Component.id == component_id
            )
        )
    ).one_or_none()
    if comp is None:
        return None
    signalen: set[str] = set()
    if feit in _FEIT_SIGNAAL:
        badge = await registratiegaten_service.badge_voor_component(session, tid, component_id)
        signalen = set(badge.get("signalen", []))
    rel_vast: dict[str, bool] = {}
    if feit in (FEIT_KOPPELINGEN, FEIT_CONTRACT):
        soorten = await component_bevinding_service.soorten_van_component(session, tid, component_id)
        rel_vast[feit] = feit in soorten or await component_bevinding_service.heeft_echte_registratie(
            session, tid, component_id, feit
        )
    return _beslis_vastgesteld(
        feit, hostingmodel=comp.hostingmodel, levensfase=comp.levensfase,
        migratiepad=comp.migratiepad, signalen=signalen, rel_vast=rel_vast,
    )


async def norm_definitie(session: AsyncSession, tenant_id) -> list[dict]:
    """De volledige norm voor het beheerscherm: per hard feit of het verplicht is, en of er een
    'bewust geen'-antwoord mogelijk is (relationeel feit) of niet (eigen veld/signaal — dat bepaalt
    wat de consultant straks kan antwoorden). Read-only."""
    norm = await haal_norm(session, tenant_id)
    bewust_geen = {s.value for s in ComponentBevindingSoort}  # koppelingen, contract
    return [
        {"feit": feit, "verplicht": norm[feit], "bewust_geen_mogelijk": feit in bewust_geen}
        for feit in HARDE_FEITEN
    ]


# ── ADR-052 besluiten 8-11 (LI045) — de verschoven lat onderscheiden van de bewuste afwijking ─────
# ÉÉN afleiding, twee vensters (componentscherm + werkvoorraad): de LIVE niet-vastgestelde verplichte
# feiten van een klaar-verklaard component, verdeeld tegen de BEVROREN snapshot van zijn verklaring.
# Geen nieuwe opslag, geen derde bron (het audit-log wordt NIET gelezen): puur snapshot × live norm.
BEWUST = "bewust"          # feit stónd in de snapshot → bewust afgewogen bij het verklaren (amber)
VERSCHOVEN = "verschoven"  # feit stond er NIET in → de lat verschoof ná het verklaren (neutraal)


def splits_afwijking(live_niet_vastgesteld: list[str], snapshot) -> dict:
    """DE gedeelde afleiding (beide vensters lezen deze, nooit een tweede berekening ernaast):
    verdeel de live-open verplichte feiten over ``bewust`` (stond in de bevroren snapshot) en
    ``verschoven`` (stond er niet in). Wat de snapshot niet noemde, is nooit een bewust besluit
    geweest (ADR-052 besluiten 8/9). Pure functie — DB-vrij testbaar."""
    snap = set(snapshot or [])
    bewust: list[str] = []
    verschoven: list[str] = []
    for feit in live_niet_vastgesteld:
        (bewust if feit in snap else verschoven).append(feit)
    return {BEWUST: bewust, VERSCHOVEN: verschoven}


async def _live_niet_vastgesteld(session: AsyncSession, tid: uuid.UUID, component_id) -> list[str]:
    """De verplichte feiten die NU niet vastgesteld zijn op dit component — uit `norm_status`
    (dezelfde bron, geen duplicaat). Al gesorteerd."""
    status = await norm_status(session, tid, component_id)
    return [feit for feit, s in status["feiten"].items() if s == NIET_VASTGESTELD]


async def _levende_snapshot(session: AsyncSession, tid: uuid.UUID, component_id):
    """De bevroren open-feiten-snapshot van de LEVENDE (status=klaar) klaarverklaring, of None als er
    geen klaar-verklaring is. Read-only."""
    rij = (
        await session.execute(
            select(ComponentKlaarverklaring.open_feiten, ComponentKlaarverklaring.status).where(
                ComponentKlaarverklaring.tenant_id == tid,
                ComponentKlaarverklaring.component_id == component_id,
            )
        )
    ).first()
    if rij is None or rij.status != KlaarverklaringStatus.klaar:
        return None
    return rij.open_feiten or []


async def afwijking_voor_component(session: AsyncSession, tenant_id, component_id) -> dict:
    """Componentvenster: ``{component_id, bewust:[...], verschoven:[...]}`` voor de levende
    klaarverklaring. Geen klaar-verklaring ⇒ beide leeg (niets te tonen). Read-only,
    engine-onaangeroerd."""
    tid = _tenant_uuid(tenant_id)
    snapshot = await _levende_snapshot(session, tid, component_id)
    if snapshot is None:
        return {"component_id": component_id, BEWUST: [], VERSCHOVEN: []}
    live = await _live_niet_vastgesteld(session, tid, component_id)
    return {"component_id": component_id, **splits_afwijking(live, snapshot)}


async def verschoven_lat_overzicht(session: AsyncSession, tenant_id) -> list[dict]:
    """Werkvoorraadvenster: per verplicht gesteld feit de klaar-verklaarde componenten waar de LAT
    VERSCHOOF (feit nu verplicht+open, maar niet in hun bevroren snapshot) — één gebundelde regel per
    feit. Dezelfde `splits_afwijking` als het componentvenster. Read-only, engine-onaangeroerd.

    Retour: ``[{feit, aantal, componenten:[{id, naam}]}]`` gesorteerd op feit; leeg ⇒ geen sectie."""
    tid = _tenant_uuid(tenant_id)
    rijen = (
        await session.execute(
            select(
                ComponentKlaarverklaring.component_id,
                ComponentKlaarverklaring.open_feiten,
                Component.naam,
            )
            .join(
                Component,
                and_(Component.id == ComponentKlaarverklaring.component_id, Component.tenant_id == tid),
            )
            .where(
                ComponentKlaarverklaring.tenant_id == tid,
                ComponentKlaarverklaring.status == KlaarverklaringStatus.klaar,
            )
        )
    ).all()
    per_feit: dict[str, list[dict]] = {}
    for cid, snapshot, naam in rijen:
        live = await _live_niet_vastgesteld(session, tid, cid)
        for feit in splits_afwijking(live, snapshot)[VERSCHOVEN]:
            per_feit.setdefault(feit, []).append({"id": cid, "naam": naam})
    resultaat: list[dict] = []
    for feit, comps in sorted(per_feit.items()):
        meta = await _lat_verschoven_metadata(session, tid, feit)  # wanneer/door wie (besluit 5)
        resultaat.append({
            "feit": feit,
            "aantal": len(comps),
            "componenten": sorted(comps, key=lambda c: c["naam"] or ""),
            **meta,
        })
    return resultaat


async def _lat_verschoven_metadata(session: AsyncSession, tid: uuid.UUID, feit: str) -> dict:
    """ADR-052 slice 4b (besluit 5) — WANNEER en DOOR WIE dit feit het laatst verplicht is gesteld,
    uit het bestaande audit-spoor (component_norm staat in AUDIT_TENANT_ENTITEITEN). Read-only, geen
    nieuwe opslag. Leeg dict als er geen toggle-gebeurtenis is — dan draagt de regel enkel feit/
    aantal/doorklik, zoals in slice 4a. Dit raakt de CLASSIFICATIE niet (die blijft snapshot × live
    norm); het audit-log voedt alléén deze metadata."""
    rij_id = (
        await session.execute(
            select(ComponentNorm.id).where(
                ComponentNorm.tenant_id == tid, ComponentNorm.feit_sleutel == feit
            )
        )
    ).scalar_one_or_none()
    if rij_id is None:
        return {}
    rec = (
        await session.execute(
            select(AuditLog.tijdstip, AuditLog.actor_sub, AuditLog.actor_email)
            .where(
                AuditLog.tenant_id == tid,
                AuditLog.entiteit_type == "component_norm",
                AuditLog.entiteit_id == rij_id,
                AuditLog.wijziging["verplicht"]["nieuw"].astext == "true",
            )
            .order_by(AuditLog.tijdstip.desc())
            .limit(1)
        )
    ).first()
    if rec is None:
        return {}
    naam = await actor_resolutie.resolveer_naam(session, tid, sub=rec.actor_sub, email=rec.actor_email)
    return {"verschoven_op": rec.tijdstip, "verschoven_door": naam or rec.actor_email}
