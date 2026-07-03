"""Service-laag voor de entiteit Blokkade (ADR-009/013, Model A).

Blokkades zijn systeem-afgeleid: **geen** `maak_aan`/`verwijder` via de gebruiker
(auto-creatie gebeurt in `checklistscore_service`; opruimen via DB-cascade). De
gebruiker beheert de opvolging via `werk_bij`. `opgelost_op` wordt afgeleid uit
de resulterende `status`. Na elke wijziging draait `herbereken_lifecycle`
(ADR-013): zodra de laatste open blokkade is opgelost en alles gescoord is, wordt
de applicatie `migratieklaar`.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.models import (
    ACTIEVE_BLOKKADE_STATUSSEN,
    Component,
    ComponentConfigDimensie,
    ComponentConfigOptie,
    Blokkade,
    BlokkadeStatus,
    ChecklistVraag,
    Checklistscore,
    Partij,
)
from schemas.blokkade import BlokkadeUpdate
from services import lifecycle_service
from services import partij_service
from services.errors import NietGevonden, OngeldigeStatusovergang

# ADR-037 — afgeleide verantwoordelijke van het onderliggende antwoord (leeslaag, read-only):
# Blokkade → Checklistscore.verantwoordelijke_id → partij (afdeling/persoon), en bij een persoon de
# afdeling-partij. Module-level aliassen zodat dezelfde gelabelde kolom in select én sorteer-allowlist
# gebruikt wordt (`kolom.key` == label → keyset-cursor blijft kloppen). Geen engine-raakvlak.
_VERANTW = aliased(Partij, name="verantw")
_VERANTW_AFD = aliased(Partij, name="verantw_afd")
_VERANTW_NAAM = _VERANTW.naam.label("verantwoordelijke_naam")
_VERANTW_AFD_NAAM = _VERANTW_AFD.naam.label("verantwoordelijke_afdeling")


def _join_verantwoordelijke(stmt, tid):
    """LEFT JOIN naar de verantwoordelijke-partij (via de reeds-gejoinde Checklistscore) + de
    afdeling-partij bij een persoon. Read-only; verandert het aantal blokkade-rijen niet (outer)."""
    return stmt.join(
        _VERANTW,
        and_(_VERANTW.id == Checklistscore.verantwoordelijke_id, _VERANTW.tenant_id == tid),
        isouter=True,
    ).join(
        _VERANTW_AFD,
        and_(_VERANTW_AFD.id == _VERANTW.afdeling_id, _VERANTW_AFD.tenant_id == tid),
        isouter=True,
    )
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "blokkade"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100

# ── Tenant-breed overzicht (CD016, consument ADR-017) ───────────────────────────

_STANDAARD_OVERZICHT_SORT = "applicatie_naam"
_STANDAARD_OVERZICHT_ORDER = "asc"

# Allowlist-kolommen (ADR-017 B2) — single source naast de schema-enum
# `BlokkadeSorteerveld`. `applicatie_naam`/`vraag_code` zijn gejoinde kolommen;
# de keyset-tiebreaker blijft `Blokkade.id`. `gewijzigd_op` mapt op `updated_at`.
_OVERZICHT_KOLOMMEN = {
    "applicatie_naam": Component.naam,
    "vraag_code": ChecklistVraag.code,
    "status": Blokkade.status,
    "toelichting": Blokkade.toelichting,
    "verantwoordelijke_naam": _VERANTW_NAAM,
    "opgelost_op": Blokkade.opgelost_op,
    "gewijzigd_op": Blokkade.updated_at,
}

# Parsers die een cursor-waarde (tekst) terug naar het kolomtype brengen.
_OVERZICHT_PARSERS = {
    "applicatie_naam": str,
    "vraag_code": str,
    "status": BlokkadeStatus,
    "toelichting": str,
    "verantwoordelijke_naam": str,
    "opgelost_op": datetime.fromisoformat,
    "gewijzigd_op": datetime.fromisoformat,
}


# ── Per-applicatie lijst (CD020 sorteer-retrofit) ───────────────────────────────
#
# Allowlist voor `GET /blokkades` = de overzicht-allowlist mínus de join-only
# velden (`applicatie_naam`/`vraag_code`): de per-app `lijst` joint niet en die
# velden zijn betekenisloos binnen één applicatie. `gewijzigd_op` → `updated_at`.

_STANDAARD_LIJST_SORT = "created_at"
_STANDAARD_LIJST_ORDER = "asc"

_LIJST_KOLOMMEN = {
    "created_at": Blokkade.created_at,
    "status": Blokkade.status,
    "toelichting": Blokkade.toelichting,
    "verantwoordelijke_naam": _VERANTW_NAAM,
    "opgelost_op": Blokkade.opgelost_op,
    "gewijzigd_op": Blokkade.updated_at,
}
_LIJST_PARSERS = {
    "created_at": datetime.fromisoformat,
    "status": BlokkadeStatus,
    "toelichting": str,
    "verantwoordelijke_naam": str,
    "opgelost_op": datetime.fromisoformat,
    "gewijzigd_op": datetime.fromisoformat,
}


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def enum_opties() -> dict[str, list[str]]:
    """Read-only keuzewaarden voor de blokkade-status (single source, DB-vrij)."""
    return {"status": [e.value for e in BlokkadeStatus]}


async def lijst(
    session: AsyncSession,
    tenant_id,
    *,
    limit: int = _STANDAARD_LIMIT,
    after: str | None = None,
    component_id: uuid.UUID | None = None,
    status: BlokkadeStatus | None = None,
    sort: str = _STANDAARD_LIJST_SORT,
    order: str = _STANDAARD_LIJST_ORDER,
) -> tuple[list[dict], str | None]:
    """Server-side sorteerbare per-applicatie blokkade-lijst (ADR-017 + CD020).

    Additief bovenop het CD016-bevroren contract: `sort`/`order` weglaten = exact
    het pre-CD020-gedrag (`created_at` oplopend). Uniform NULLS-LAST-pad (CD016);
    `Blokkade.id` = tiebreaker. Het tenant-brede `lijst_overzicht` (join) blijft
    ongemoeid. Cursor die niet bij `sort`/`order` past ⇒ `ValueError` (route ⇒ 400).
    """
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    if sort not in _LIJST_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_LIJST_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    kolom = _LIJST_KOLOMMEN[sort]

    # Herkomst-verrijking (DOORLOOP): join op de bestaande verplichte FK-keten
    # Blokkade.checklistscore_id → Checklistscore → ChecklistVraag, zodat de
    # per-component lijst de veroorzakende vraag (code + tekst) + de blokkerende score
    # meelevert (zelfde patroon als `lijst_overzicht`). Read-only — geen engine-raakvlak.
    # De sortable kolommen zijn gelabeld op hun `kolom.key`, zodat de keyset-cursor
    # `getattr(row, kolom.key)` blijft werken (ongewijzigd sorteergedrag/allowlist).
    stmt = (
        select(
            Blokkade.id.label("id"),
            Blokkade.checklistscore_id.label("checklistscore_id"),
            Blokkade.component_id.label("component_id"),
            Blokkade.status.label("status"),
            Blokkade.toelichting.label("toelichting"),
            _VERANTW_NAAM,
            _VERANTW_AFD_NAAM,
            Blokkade.opgelost_op.label("opgelost_op"),
            Blokkade.created_at.label("created_at"),
            Blokkade.updated_at.label("updated_at"),
            Checklistscore.checklistvraag_id.label("checklistvraag_id"),
            Checklistscore.score.label("score"),
            ChecklistVraag.code.label("vraag_code"),
            ChecklistVraag.vraag.label("vraag"),
        )
        .join(Checklistscore, Checklistscore.id == Blokkade.checklistscore_id)
        .join(ChecklistVraag, ChecklistVraag.id == Checklistscore.checklistvraag_id)
        .where(Blokkade.tenant_id == tid)
    )
    stmt = _join_verantwoordelijke(stmt, tid)
    if component_id is not None:
        stmt = stmt.where(Blokkade.component_id == component_id)
    if status is not None:
        stmt = stmt.where(Blokkade.status == status)
    if after:
        c_sort, c_order, c_is_null, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_is_null else _LIJST_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(
                kolom, Blokkade.id, order=order, is_null=c_is_null,
                waarde=c_waarde, cursor_id=c_id,
            )
        )
    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, Blokkade.id, order)).limit(limit + 1)

    rijen = (await session.execute(stmt)).all()
    heeft_meer = len(rijen) > limit
    zichtbaar = rijen[:limit]
    items = [
        {
            "id": r.id,
            "checklistscore_id": r.checklistscore_id,
            "component_id": r.component_id,
            "status": r.status,
            "toelichting": r.toelichting,
            "verantwoordelijke_naam": r.verantwoordelijke_naam,
            "verantwoordelijke_afdeling": r.verantwoordelijke_afdeling,
            "opgelost_op": r.opgelost_op,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "checklistvraag_id": r.checklistvraag_id,
            "vraag_code": r.vraag_code,
            "vraag": r.vraag,
            "score": r.score,
        }
        for r in zichtbaar
    ]
    volgende = (
        encode_sort_cursor_nullable(
            sort=sort, order=order, waarde=getattr(zichtbaar[-1], kolom.key), id=zichtbaar[-1].id
        )
        if heeft_meer
        else None
    )
    return items, volgende


def _pas_statusfilter_toe(stmt, status_filter: str):
    """Statusfilter voor het overzicht. `actief` = gedeelde constante; `alle` = niets."""
    if status_filter == "actief":
        return stmt.where(Blokkade.status.in_(ACTIEVE_BLOKKADE_STATUSSEN))
    if status_filter == "alle":
        return stmt
    return stmt.where(Blokkade.status == BlokkadeStatus(status_filter))


async def lijst_overzicht(
    session: AsyncSession,
    tenant_id,
    *,
    limit: int = _STANDAARD_LIMIT,
    after: str | None = None,
    status_filter: str = "actief",
    sort: str = _STANDAARD_OVERZICHT_SORT,
    order: str = _STANDAARD_OVERZICHT_ORDER,
) -> tuple[list[dict], str | None]:
    """Tenant-breed blokkadesoverzicht over alle applicaties (CD016, ADR-017).

    Join op `Component` (naam) en `Checklistscore` (vraag_code). Server-side
    sorteerbaar met NULLS-LAST-keyset (nullable: `toelichting`/`verantwoordelijke_naam`/
    `opgelost_op`); `Blokkade.id` is de stabiele tiebreaker. Tenant-scoped via RLS
    + expliciete `tenant_id`-filter (dubbele bescherming). Een `after` die niet bij
    `sort`/`order` past ⇒ `ValueError` (route ⇒ 400).
    """
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    if sort not in _OVERZICHT_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_OVERZICHT_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    kolom = _OVERZICHT_KOLOMMEN[sort]

    stmt = (
        select(
            Blokkade.id.label("id"),
            Blokkade.component_id.label("component_id"),
            Component.naam.label("applicatie_naam"),
            # ADR-024-vervolg: het componenttype (sleutel) voor de type-tag + type-afhankelijke
            # doorklik (applicatie → applicatie-detail; overige typen → component-detail), plus
            # het leesbare type-label via een LEFT JOIN op de platform-catalogus (één query).
            Component.componenttype.label("componenttype"),
            ComponentConfigOptie.label.label("componenttype_label"),
            ChecklistVraag.code.label("vraag_code"),
            Blokkade.status.label("status"),
            Blokkade.toelichting.label("toelichting"),
            _VERANTW_NAAM,
            _VERANTW_AFD_NAAM,
            Blokkade.opgelost_op.label("opgelost_op"),
            Blokkade.updated_at.label("gewijzigd_op"),
        )
        # component_id == component.id (shared-PK profiel) → join op de component voor de naam.
        .join(Component, Component.id == Blokkade.component_id)
        .join(Checklistscore, Checklistscore.id == Blokkade.checklistscore_id)
        .join(ChecklistVraag, ChecklistVraag.id == Checklistscore.checklistvraag_id)
        # Platform-brede typecatalogus (geen RLS) voor het leesbare label; LEFT zodat een
        # (onverwacht) onbekend type de rij niet laat verdwijnen.
        .join(
            ComponentConfigOptie,
            and_(
                ComponentConfigOptie.optie_sleutel == Component.componenttype,
                ComponentConfigOptie.dimensie == ComponentConfigDimensie.componenttype,
            ),
            isouter=True,
        )
        .where(Blokkade.tenant_id == tid)
    )
    stmt = _join_verantwoordelijke(stmt, tid)
    stmt = _pas_statusfilter_toe(stmt, status_filter)

    if after:
        c_sort, c_order, c_is_null, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_is_null else _OVERZICHT_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(
                kolom, Blokkade.id, order=order, is_null=c_is_null, waarde=c_waarde, cursor_id=c_id
            )
        )

    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, Blokkade.id, order)).limit(limit + 1)

    rijen = (await session.execute(stmt)).all()
    heeft_meer = len(rijen) > limit
    zichtbaar = rijen[:limit]
    items = [
        {
            "id": r.id,
            "component_id": r.component_id,
            "applicatie_naam": r.applicatie_naam,
            "componenttype": r.componenttype,
            # Fallback naar de sleutel als de catalogus (onverwacht) geen label heeft.
            "componenttype_label": r.componenttype_label or r.componenttype,
            "vraag_code": r.vraag_code,
            "status": r.status,
            "toelichting": r.toelichting,
            "verantwoordelijke_naam": r.verantwoordelijke_naam,
            "verantwoordelijke_afdeling": r.verantwoordelijke_afdeling,
            "opgelost_op": r.opgelost_op,
            "gewijzigd_op": r.gewijzigd_op,
        }
        for r in zichtbaar
    ]
    volgende = (
        encode_sort_cursor_nullable(
            sort=sort, order=order, waarde=getattr(zichtbaar[-1], sort), id=zichtbaar[-1].id
        )
        if heeft_meer
        else None
    )
    return items, volgende


async def _verrijk(session: AsyncSession, tid: uuid.UUID, obj: Blokkade) -> Blokkade:
    """ADR-037 — zet de afgeleide verantwoordelijke (`verantwoordelijke_naam`/`-afdeling`) op de
    blokkade, herleid uit het onderliggende antwoord (`checklistscore_id` →
    `Checklistscore.verantwoordelijke_id`). Read-only; geen schrijfpad naar blokkade/engine.
    Transient attrs die `BlokkadeRead` (from_attributes) uitleest."""
    vid = (
        await session.execute(
            select(Checklistscore.verantwoordelijke_id).where(
                Checklistscore.id == obj.checklistscore_id, Checklistscore.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    info = (await partij_service.resolve_verantwoordelijken(session, tid, [vid])).get(vid)
    obj.verantwoordelijke_naam = info["naam"] if info else None
    obj.verantwoordelijke_afdeling = info["afdeling"] if info else None
    return obj


async def haal_op(session: AsyncSession, tenant_id, blokkade_id) -> Blokkade:
    tid = _tenant_uuid(tenant_id)
    stmt = select(Blokkade).where(
        Blokkade.id == blokkade_id,
        Blokkade.tenant_id == tid,
    )
    obj = (await session.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, blokkade_id)
    return obj


async def lees_detail(session: AsyncSession, tenant_id, blokkade_id) -> Blokkade:
    """Read-pad voor de route: haal_op + afgeleide verantwoordelijke-velden (ADR-037)."""
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, blokkade_id)
    return await _verrijk(session, tid, obj)


async def werk_bij(
    session: AsyncSession, tenant_id, blokkade_id, data: BlokkadeUpdate
) -> Blokkade:
    """Handmatige statusprogressie + afgeleide `opgelost_op` + herberekening.

    `opgelost` ⇒ `opgelost_op` wordt gezet (behoudt een bestaande tijd bij een
    toelichting-only-edit); terug naar `open`/`in_behandeling` ⇒ `opgelost_op`
    weer leeg.
    """
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, blokkade_id)

    # ADR-016: handmatig alleen `open ↔ in_behandeling`. `opgelost` ontstaat
    # UITSLUITEND via de auto-logica (Checklistscore `ja`/`nvt`), die buiten dit
    # pad om loopt (checklistscore_service._synchroniseer_blokkade).
    if data.status == BlokkadeStatus.opgelost:
        raise OngeldigeStatusovergang(obj.status, BlokkadeStatus.opgelost)

    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(obj, veld, waarde)

    if obj.status == BlokkadeStatus.opgelost:
        if obj.opgelost_op is None:
            obj.opgelost_op = datetime.now(timezone.utc)
    else:
        obj.opgelost_op = None

    await session.flush()
    await lifecycle_service.herbereken_lifecycle(session, tid, obj.component_id)
    await session.commit()
    await session.refresh(obj)
    return await _verrijk(session, tid, obj)
