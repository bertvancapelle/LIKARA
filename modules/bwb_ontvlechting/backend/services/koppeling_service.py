"""Service-laag voor de entiteit Koppeling (P5-vervolg, ADR-009).

Twee ouder-relaties naar Component, zonder lifecycle. Beide ouders worden bij
aanmaken tenant-scoped gevalideerd (`applicatie_service.haal_op`) → ontbrekend/
kruis-tenant ⇒ 404 `NIET_GEVONDEN`. `bron ≠ doel` is al op schema-niveau
afgedwongen; de DB-`CHECK ck_koppeling_bron_ne_doel` is backstop: een
`IntegrityError` wordt teruggerold en als `KoppelingConflict` (409) gemeld,
zodat er nooit een rauwe DB-melding lekt. Geen unieke index → geen dubbele-
koppeling-conflict. Ouder-FK's zijn immutabel (niet in Update).
"""
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    Component,
    ImpactVerbreking,
    Koppeling,
    Koppelprotocol,
    Koppelrichting,
)
from schemas.koppeling import KoppelingCreate, KoppelingUpdate
from services import applicatie_service
from services.errors import KoppelingConflict, NietGevonden
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "koppeling"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100

# Default-sortering = exact het pre-CD020-gedrag (created_at oplopend).
_STANDAARD_SORT = "created_at"
_STANDAARD_ORDER = "asc"

# Allowlist-kolommen (ADR-017 B2) — single source naast `KoppelingSorteerveld`.
# `tegenpartij_naam` → de gejoinde `Component.naam` (zie `_tegenpartij_fk`).
_SORTEERBARE_KOLOMMEN = {
    "created_at": Koppeling.created_at,
    "tegenpartij_naam": Component.naam,
    "richting": Koppeling.richting,
    "protocol": Koppeling.protocol,
    "impact_bij_verbreking": Koppeling.impact_bij_verbreking,
}
_WAARDE_PARSERS = {
    "created_at": datetime.fromisoformat,
    "tegenpartij_naam": str,
    "richting": Koppelrichting,
    "protocol": Koppelprotocol,
    "impact_bij_verbreking": ImpactVerbreking,
}


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _tegenpartij_fk(bron_applicatie_id, doel_applicatie_id):
    """De applicatie aan de ándere kant dan het filter is de 'tegenpartij' (CD020).

    Filter op bron (uitgaand) ⇒ tegenpartij = doel; filter op doel (inkomend) ⇒
    tegenpartij = bron. Zonder filter (of beide) = uitgaand-perspectief (doel) als
    deterministische default — de UI filtert altijd op precies één kant. De join
    op deze FK levert `tegenpartij_naam` én is de sorteer-/keyset-kolom voor naam.
    """
    if doel_applicatie_id is not None and bron_applicatie_id is None:
        return Koppeling.bron_applicatie_id
    return Koppeling.doel_applicatie_id


def enum_opties() -> dict[str, list[str]]:
    """Read-only keuzewaarden per Koppeling-enumveld (single source, DB-vrij).

    Bron/doel zijn applicatie-pickers (geen enum) en horen hier niet.
    """
    return {
        "richting": [e.value for e in Koppelrichting],
        "protocol": [e.value for e in Koppelprotocol],
        "impact_bij_verbreking": [e.value for e in ImpactVerbreking],
    }


async def lijst(
    session: AsyncSession,
    tenant_id,
    *,
    limit: int = _STANDAARD_LIMIT,
    after: str | None = None,
    bron_applicatie_id: uuid.UUID | None = None,
    doel_applicatie_id: uuid.UUID | None = None,
    sort: str = _STANDAARD_SORT,
    order: str = _STANDAARD_ORDER,
) -> tuple[list[dict], str | None]:
    """Server-side sorteerbare keyset-lijst binnen de tenant (ADR-017 + CD020).

    Join op `Component` voor de **tegenpartij-naam** (de andere kant dan het
    filter; zie `_tegenpartij_fk`), zodat sorteren op naam overeenstemt met wat
    getoond wordt. Default (geen `sort`/`order`) = exact het pre-CD020-gedrag
    (`created_at` oplopend). Uniform NULLS-LAST-pad (CD016; alle allowlist-kolommen
    NOT NULL → no-op IS NULL-tak). `Koppeling.id` = tiebreaker. Cursor die niet bij
    `sort`/`order` past ⇒ `ValueError` (route ⇒ 400).
    """
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    if sort not in _SORTEERBARE_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    kolom = _SORTEERBARE_KOLOMMEN[sort]
    tegenpartij_fk = _tegenpartij_fk(bron_applicatie_id, doel_applicatie_id)

    stmt = (
        select(
            Koppeling.id.label("id"),
            Koppeling.bron_applicatie_id.label("bron_applicatie_id"),
            Koppeling.doel_applicatie_id.label("doel_applicatie_id"),
            Component.naam.label("tegenpartij_naam"),
            Koppeling.richting.label("richting"),
            Koppeling.protocol.label("protocol"),
            Koppeling.impact_bij_verbreking.label("impact_bij_verbreking"),
            Koppeling.omschrijving.label("omschrijving"),
            Koppeling.created_at.label("created_at"),
            Koppeling.updated_at.label("updated_at"),
        )
        .join(Component, Component.id == tegenpartij_fk)
        .where(Koppeling.tenant_id == tid)
    )
    if bron_applicatie_id is not None:
        stmt = stmt.where(Koppeling.bron_applicatie_id == bron_applicatie_id)
    if doel_applicatie_id is not None:
        stmt = stmt.where(Koppeling.doel_applicatie_id == doel_applicatie_id)
    if after:
        c_sort, c_order, c_is_null, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_is_null else _WAARDE_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(
                kolom, Koppeling.id, order=order, is_null=c_is_null,
                waarde=c_waarde, cursor_id=c_id,
            )
        )
    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, Koppeling.id, order)).limit(limit + 1)

    rijen = (await session.execute(stmt)).all()
    heeft_meer = len(rijen) > limit
    zichtbaar = rijen[:limit]
    items = [
        {
            "id": r.id,
            "bron_applicatie_id": r.bron_applicatie_id,
            "doel_applicatie_id": r.doel_applicatie_id,
            "tegenpartij_naam": r.tegenpartij_naam,
            "richting": r.richting,
            "protocol": r.protocol,
            "impact_bij_verbreking": r.impact_bij_verbreking,
            "omschrijving": r.omschrijving,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
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


async def haal_op(session: AsyncSession, tenant_id, koppeling_id) -> Koppeling:
    tid = _tenant_uuid(tenant_id)
    stmt = select(Koppeling).where(
        Koppeling.id == koppeling_id,
        Koppeling.tenant_id == tid,
    )
    obj = (await session.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, koppeling_id)
    return obj


async def maak_aan(session: AsyncSession, tenant_id, data: KoppelingCreate) -> Koppeling:
    tid = _tenant_uuid(tenant_id)
    # Beide ouders tenant-scoped valideren — ontbrekend/kruis-tenant ⇒ 404.
    await applicatie_service.haal_op(session, tenant_id, data.bron_applicatie_id)
    await applicatie_service.haal_op(session, tenant_id, data.doel_applicatie_id)

    obj = Koppeling(tenant_id=tid, **data.model_dump())
    session.add(obj)
    try:
        await session.commit()
    except IntegrityError as exc:
        # Backstop voor de DB-CHECK (bron <> doel); nooit rauwe DB-melding lekken.
        await session.rollback()
        raise KoppelingConflict() from exc
    await session.refresh(obj)
    return obj


async def werk_bij(
    session: AsyncSession, tenant_id, koppeling_id, data: KoppelingUpdate
) -> Koppeling:
    obj = await haal_op(session, tenant_id, koppeling_id)
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return obj


async def verwijder(session: AsyncSession, tenant_id, koppeling_id) -> None:
    obj = await haal_op(session, tenant_id, koppeling_id)
    await session.delete(obj)
    await session.commit()
