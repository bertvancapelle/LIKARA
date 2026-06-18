"""Service-laag — Gap + gap-leden + readiness-rollup (ADR-023 Fase E, E4).

Gap is een element-subtype (shared-PK); CRUD volgt het plateau/deliverable-patroon
(`Element('gap')` → subtype-rij; delete via het element-supertype, cascade). De gap draagt
**2-ariteit hard in het schema**: `baseline_plateau_id` + `doel_plateau_id` (beide NOT NULL,
composiet-FK → element). De service valideert dat beide verwezen elementen **plateau** zijn
(422 `ONGELDIG_PLATEAU`) en dat baseline ≠ doel (422 `BASELINE_GELIJK_AAN_DOEL`).

Gap-leden zijn een **facade over het unified relatiemodel** als `association`-relatie
(bron=gap → doel=lid) — zoals `component_contract_service`. Toegestane lid-typen in deze
slice: component en contract (anders 422 `ONGELDIG_LID`); dubbel lid → 409 `LID_BESTAAT`.

**Engine-onaangeroerd (Besluit: score = de ENIGE lifecycle-driver).** Deze module importeert
bewust GEEN `lifecycle_service`/`herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/
`Blokkade`/`Checklistscore`. De readiness-cijfers worden **puur read-only afgeleid**:
- *technisch*: de lifecycle-state van component-leden wordt read-only uit `component_profiel`
  gelezen via een platte SQL-leesquery (geen ORM-engine-import);
- *contractueel*: de bevestiging wordt read-only gelezen uit het **doel-plateau-lidmaatschap**
  (aggregation-kenmerk uit E1) — de enige bron, geen tweede opgeslagen bron.
Er wordt niets opgeslagen; de twee cijfers worden nooit vermengd tot één getal.
"""
import uuid
from datetime import datetime

from sqlalchemy import and_, bindparam, delete, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Component, Contract, Element, ElementType, Gap, Relatie
from schemas.gap import GapCreate, GapUpdate
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict
from services.pagination import decode_sort_cursor, encode_sort_cursor

_ENTITEIT = "gap"
_ASSOCIATION = "association"
_AGGREGATION = "aggregation"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100

# Toegestane lid-element-typen (DEFAULT — overrulebaar): component + contract.
_TOEGESTANE_LID_TYPES = frozenset({ElementType.component.value, ElementType.contract.value})

# Spiegelt LifecycleStatus.migratieklaar.value — bewust als string-constante zodat deze
# service de engine-enum niet hoeft te importeren (een offline test borgt de synchroniteit).
_MIGRATIEKLAAR = "migratieklaar"


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


# ── Gap-CRUD (element-subtype) ────────────────────────────────────────────────────

async def haal_op(session: AsyncSession, tenant_id, gap_id) -> Gap:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Gap).where(Gap.id == gap_id, Gap.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, gap_id)
    return obj


def _lees(obj: Gap) -> dict:
    return {
        "id": obj.id, "naam": obj.naam, "toelichting": obj.toelichting,
        "baseline_plateau_id": obj.baseline_plateau_id, "doel_plateau_id": obj.doel_plateau_id,
        "created_at": obj.created_at, "updated_at": obj.updated_at,
    }


async def _element_type(session: AsyncSession, tid: uuid.UUID, eid) -> str:
    et = (
        await session.execute(
            select(Element.element_type).where(Element.tenant_id == tid, Element.id == eid)
        )
    ).scalar_one_or_none()
    if et is None:
        raise NietGevonden("element", eid)
    return et.value if hasattr(et, "value") else str(et)


async def _valideer_plateaus(session: AsyncSession, tid: uuid.UUID, baseline_id, doel_id) -> None:
    """Gedeelde 2-ariteit-validatie (aanmaken én wijzigen): baseline ≠ doel, en beide verwijzen
    naar een plateau binnen de tenant. Foutcodes identiek over beide paden."""
    if baseline_id == doel_id:
        raise OngeldigeRegistratie(
            "BASELINE_GELIJK_AAN_DOEL", "Baseline- en doel-plateau mogen niet identiek zijn."
        )
    for plateau_id in (baseline_id, doel_id):
        if await _element_type(session, tid, plateau_id) != ElementType.plateau.value:
            raise OngeldigeRegistratie(
                "ONGELDIG_PLATEAU", "Baseline en doel moeten verwijzen naar een plateau."
            )


async def maak_aan(session: AsyncSession, tenant_id, data: GapCreate) -> dict:
    tid = _tenant_uuid(tenant_id)
    await _valideer_plateaus(session, tid, data.baseline_plateau_id, data.doel_plateau_id)
    elem = Element(tenant_id=tid, element_type=ElementType.gap)
    session.add(elem)
    await session.flush()
    obj = Gap(
        id=elem.id, tenant_id=tid, naam=data.naam, toelichting=data.toelichting,
        baseline_plateau_id=data.baseline_plateau_id, doel_plateau_id=data.doel_plateau_id,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _lees(obj)


async def lees_detail(session: AsyncSession, tenant_id, gap_id) -> dict:
    """Gap-detail met de twee gescheiden readiness-cijfers ingebed (read-only afgeleid)."""
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, gap_id)
    uit = _lees(obj)
    uit["readiness_technisch"] = await bereken_readiness_technisch(session, tid, gap_id)
    uit["readiness_contractueel"] = await bereken_readiness_contractueel(
        session, tid, gap_id, obj.doel_plateau_id
    )
    return uit


async def werk_bij(session: AsyncSession, tenant_id, gap_id, data: GapUpdate) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, gap_id)
    velden = data.model_dump(exclude_unset=True)
    # Baseline/doel wijzigbaar (UX-A4-4): valideer de effectieve waarden (nieuw of bestaand)
    # met exact dezelfde 2-ariteit-regel als bij aanmaken.
    if "baseline_plateau_id" in velden or "doel_plateau_id" in velden:
        nieuw_baseline = velden.get("baseline_plateau_id", obj.baseline_plateau_id)
        nieuw_doel = velden.get("doel_plateau_id", obj.doel_plateau_id)
        await _valideer_plateaus(session, tid, nieuw_baseline, nieuw_doel)
    for veld, waarde in velden.items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return _lees(obj)


async def verwijder(session: AsyncSession, tenant_id, gap_id) -> None:
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, gap_id)  # 404 kruis-tenant
    # Verwijder via het element-supertype: cascade element → gap (subtype) én de
    # association-lidmaatschapsrelaties (relatie-FK's → element, ON DELETE CASCADE).
    await session.execute(delete(Element).where(Element.tenant_id == tid, Element.id == gap_id))
    await session.commit()


async def lijst(
    session: AsyncSession, tenant_id, *, limit: int = _STANDAARD_LIMIT, after: str | None = None
) -> tuple[list[dict], str | None]:
    """Keyset-lijst binnen de tenant (created_at oplopend). Cursor-mismatch ⇒ ValueError (400)."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)
    stmt = select(Gap).where(Gap.tenant_id == tid)
    if after:
        _s, _o, waarde_str, c_id = decode_sort_cursor(after)
        c_waarde = datetime.fromisoformat(waarde_str)
        stmt = stmt.where(
            or_(
                Gap.created_at > c_waarde,
                and_(Gap.created_at == c_waarde, Gap.id > c_id),
            )
        )
    stmt = stmt.order_by(Gap.created_at.asc(), Gap.id.asc()).limit(limit + 1)
    rijen = list((await session.execute(stmt)).scalars().all())
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    volgende = (
        encode_sort_cursor(sort="created_at", order="asc", waarde=items[-1].created_at, id=items[-1].id)
        if heeft_meer else None
    )
    return [_lees(o) for o in items], volgende


# ── Gap-leden (facade over Relatie: association bron=gap → doel=lid) ───────────────

async def _lid_naam(session: AsyncSession, tid: uuid.UUID, lid_id, lid_type: str) -> str | None:
    if lid_type == ElementType.component.value:
        return (
            await session.execute(
                select(Component.naam).where(Component.tenant_id == tid, Component.id == lid_id)
            )
        ).scalar_one_or_none()
    if lid_type == ElementType.contract.value:
        return (
            await session.execute(
                select(Contract.contractnaam).where(Contract.tenant_id == tid, Contract.id == lid_id)
            )
        ).scalar_one_or_none()
    return None


async def maak_lid(session: AsyncSession, tenant_id, gap_id, lid_id) -> dict:
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, gap_id)  # 404 kruis-tenant; borgt dat het een gap is
    lid_type = await _element_type(session, tid, lid_id)
    if lid_type not in _TOEGESTANE_LID_TYPES:
        raise OngeldigeRegistratie(
            "ONGELDIG_LID", "Alleen componenten en contracten kunnen lid van een gap zijn."
        )
    obj = Relatie(tenant_id=tid, bron_id=gap_id, doel_id=lid_id, relatietype=_ASSOCIATION, kenmerken={})
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise RegistratieConflict("LID_BESTAAT", "Dit lid zit al in deze gap.") from exc
    await session.refresh(obj)
    return {
        "id": obj.id, "gap_id": obj.bron_id, "lid_id": obj.doel_id,
        "lid_element_type": lid_type, "naam": await _lid_naam(session, tid, lid_id, lid_type),
        "created_at": obj.created_at, "updated_at": obj.updated_at,
    }


async def verwijder_lid(session: AsyncSession, tenant_id, gap_id, lid_relatie_id) -> None:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Relatie).where(
                Relatie.id == lid_relatie_id, Relatie.tenant_id == tid,
                Relatie.relatietype == _ASSOCIATION, Relatie.bron_id == gap_id,
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden("gap_lid", lid_relatie_id)
    await session.delete(obj)
    await session.commit()


async def lijst_leden(session: AsyncSession, tenant_id, gap_id) -> list[dict]:
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, gap_id)  # 404 kruis-tenant
    rijen = (
        await session.execute(
            select(Relatie, Element.element_type)
            .join(Element, and_(Element.id == Relatie.doel_id, Element.tenant_id == tid))
            .where(
                Relatie.tenant_id == tid, Relatie.bron_id == gap_id,
                Relatie.relatietype == _ASSOCIATION,
            )
            .order_by(Relatie.created_at.asc(), Relatie.id.asc())
        )
    ).all()
    uit = []
    for rel, et in rijen:
        lid_type = et.value if hasattr(et, "value") else str(et)
        uit.append({
            "id": rel.id, "gap_id": rel.bron_id, "lid_id": rel.doel_id,
            "lid_element_type": lid_type,
            "naam": await _lid_naam(session, tid, rel.doel_id, lid_type),
            "created_at": rel.created_at, "updated_at": rel.updated_at,
        })
    return uit


# ── Readiness-rollup (puur read-only afgeleid; twee gescheiden cijfers) ────────────

def _cijfer(aantal_klaar: int, aantal_totaal: int) -> dict:
    """Telling + percentage. Lege noemer ⇒ percentage = None (niet 0), aantallen 0."""
    pct = round(aantal_klaar / aantal_totaal * 100, 1) if aantal_totaal > 0 else None
    return {"aantal_klaar": aantal_klaar, "aantal_totaal": aantal_totaal, "percentage": pct}


async def _lid_ids_van_type(session: AsyncSession, tid: uuid.UUID, gap_id, element_type: ElementType) -> list:
    """Gap-leden van één element-type (association bron=gap → doel=lid)."""
    rijen = (
        await session.execute(
            select(Element.id)
            .join(Relatie, and_(Relatie.doel_id == Element.id, Relatie.tenant_id == tid))
            .where(
                Relatie.bron_id == gap_id, Relatie.relatietype == _ASSOCIATION,
                Element.tenant_id == tid, Element.element_type == element_type,
            )
        )
    ).all()
    return [r[0] for r in rijen]


async def bereken_readiness_technisch(session: AsyncSession, tid: uuid.UUID, gap_id) -> dict:
    """Technische readiness: noemer = component-leden mét lifecycle-state (component_profiel);
    teller = daarvan die `migratieklaar` zijn. Component-leden zonder profiel vallen buiten de
    noemer. Read-only afgeleid; geen engine-import — de lifecycle-state wordt via een platte
    SQL-leesquery uit `component_profiel` gelezen."""
    comp_ids = await _lid_ids_van_type(session, tid, gap_id, ElementType.component)
    if not comp_ids:
        return _cijfer(0, 0)
    stmt = text(
        "SELECT lifecycle_status FROM component_profiel WHERE id IN :ids"
    ).bindparams(bindparam("ids", expanding=True))
    states = [
        row[0]
        for row in (await session.execute(stmt, {"ids": [str(c) for c in comp_ids]})).all()
    ]
    aantal_totaal = len(states)  # alleen component-leden MÉT profiel
    aantal_klaar = sum(1 for s in states if s == _MIGRATIEKLAAR)
    return _cijfer(aantal_klaar, aantal_totaal)


async def bereken_readiness_contractueel(
    session: AsyncSession, tid: uuid.UUID, gap_id, doel_plateau_id
) -> dict:
    """Contractuele readiness: noemer = contract-leden waarvoor een contractuele-
    bevestigingsregistratie bestaat op het **doel-plateau-lidmaatschap** (aggregation-relatie
    bron=doel_plateau → doel=contract); teller = daarvan die bevestigd zijn. Contract-leden
    zonder zo'n registratie vallen buiten de noemer (symmetrisch met de component-regel).
    Enige bron — geen tweede opgeslagen bron. Read-only afgeleid."""
    contract_ids = await _lid_ids_van_type(session, tid, gap_id, ElementType.contract)
    if not contract_ids:
        return _cijfer(0, 0)
    rijen = (
        await session.execute(
            select(Relatie.kenmerken).where(
                Relatie.tenant_id == tid, Relatie.bron_id == doel_plateau_id,
                Relatie.relatietype == _AGGREGATION, Relatie.doel_id.in_(contract_ids),
            )
        )
    ).all()
    aantal_totaal = len(rijen)  # alleen contract-leden MÉT doel-plateau-lidmaatschap
    aantal_klaar = sum(1 for (k,) in rijen if (k or {}).get("contractueel_bevestigd") is True)
    return _cijfer(aantal_klaar, aantal_totaal)
