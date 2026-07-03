"""Service — grof gebruiksfeit `organisatiegebruik` (ADR-036, stap A). Puur registratief.

"Organisatie gebruikt applicatie" als op-zichzelf-vastlegbaar feit tussen twee bestaande
elementen (organisatie-partij + applicatie-component). Eén feit per (organisatie, applicatie) —
schema-geborgd via `UNIQUE(tenant, organisatie, applicatie)`. Onvolledig = geldig (organisatie +
applicatie volstaat). De gebruikersgroep is de fijne verfijning en verwijst hiernaar
(`gebruikersgroep.gebruik_id`); `ensure` is het get-or-create-pad zodat een afdeling-mét-
organisatie het grove feit automatisch borgt (geen dubbele invoer, geen duplicaat).

Engine-invariant (machine-geborgd via de offline import-afwezigheidstest): bewust GEEN import van
`lifecycle_service`/`herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade`/
`Checklistscore`. Tenant-scoped (RLS + expliciete `tenant_id`-filter — dubbele bescherming).
"""
import uuid

from sqlalchemy import and_, exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.models import Component, Gebruikersgroep, Organisatiegebruik, Partij
from schemas.organisatiegebruik import OrganisatiegebruikCreate
from services import partij_service
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict

_ENTITEIT = "organisatiegebruik"
_APPLICATIE_TYPE = "applicatie"


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def valideer_applicatie(session: AsyncSession, tid: uuid.UUID, applicatie_id) -> None:
    """Het doel moet een component met componenttype='applicatie' zijn (422 `ONGELDIGE_APPLICATIE`;
    ook niet-bestaand/cross-tenant → 422, geen lek van vreemd bestaan)."""
    ct = (
        await session.execute(
            select(Component.componenttype).where(
                Component.id == applicatie_id, Component.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if ct != _APPLICATIE_TYPE:
        raise OngeldigeRegistratie(
            "ONGELDIGE_APPLICATIE", "Het gebruiksfeit moet naar een applicatie verwijzen."
        )


async def _bestaand_id(session: AsyncSession, tid, organisatie_id, applicatie_id) -> uuid.UUID | None:
    return (
        await session.execute(
            select(Organisatiegebruik.id).where(
                Organisatiegebruik.tenant_id == tid,
                Organisatiegebruik.organisatie_id == organisatie_id,
                Organisatiegebruik.applicatie_id == applicatie_id,
            )
        )
    ).scalar_one_or_none()


async def ensure(session: AsyncSession, tenant_id, organisatie_id, applicatie_id) -> uuid.UUID:
    """Get-or-create het grove feit (organisatie, applicatie) → geeft de id terug. Valideert de
    organisatie (aard=organisatie) + de applicatie. **Silent reuse** bij bestaand — het pad van
    de afdeling-mét-organisatie (single source of truth, geen dubbele invoer). GEEN commit (de
    caller — bv. gebruikersgroep_service — commit als onderdeel van zijn transactie)."""
    tid = _tenant_uuid(tenant_id)
    await partij_service.valideer_organisatie(session, tid, organisatie_id)
    await valideer_applicatie(session, tid, applicatie_id)
    bestaand = await _bestaand_id(session, tid, organisatie_id, applicatie_id)
    if bestaand is not None:
        return bestaand
    obj = Organisatiegebruik(tenant_id=tid, organisatie_id=organisatie_id, applicatie_id=applicatie_id)
    session.add(obj)
    await session.flush()
    return obj.id


async def maak_aan(session: AsyncSession, tenant_id, data: OrganisatiegebruikCreate) -> dict:
    """Losse aanmaak van een grof feit. Bestaand (organisatie, applicatie) ⇒ 409 `GEBRUIK_BESTAAT`
    (nette afwijzing, geen duplicaat — de UNIQUE is de backstop)."""
    tid = _tenant_uuid(tenant_id)
    await partij_service.valideer_organisatie(session, tid, data.organisatie_id)
    await valideer_applicatie(session, tid, data.applicatie_id)
    if await _bestaand_id(session, tid, data.organisatie_id, data.applicatie_id) is not None:
        raise RegistratieConflict(
            "GEBRUIK_BESTAAT", "Deze organisatie is al geregistreerd als gebruiker van deze applicatie."
        )
    obj = Organisatiegebruik(tenant_id=tid, organisatie_id=data.organisatie_id, applicatie_id=data.applicatie_id)
    session.add(obj)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise RegistratieConflict(
            "GEBRUIK_BESTAAT", "Deze organisatie is al geregistreerd als gebruiker van deze applicatie."
        ) from exc
    await session.commit()
    await session.refresh(obj)
    return await _lees_een(session, tid, obj)


async def haal_op(session: AsyncSession, tenant_id, gebruik_id) -> Organisatiegebruik:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Organisatiegebruik).where(
                Organisatiegebruik.id == gebruik_id, Organisatiegebruik.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, gebruik_id)
    return obj


async def verwijder(session: AsyncSession, tenant_id, gebruik_id) -> None:
    """Verwijder een grof feit. De verfijning-FK (`gebruikersgroep.gebruik_id`) is ON DELETE
    SET NULL → onderliggende groepen worden organisatie-loos (blijven bestaan)."""
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, gebruik_id)
    await session.delete(obj)
    await session.commit()


async def _lees_een(session: AsyncSession, tid: uuid.UUID, obj: Organisatiegebruik) -> dict:
    org_naam = (
        await session.execute(
            select(Partij.naam).where(Partij.id == obj.organisatie_id, Partij.tenant_id == tid)
        )
    ).scalar_one_or_none()
    heeft = bool(
        (
            await session.execute(
                select(
                    exists(
                        select(Gebruikersgroep.id).where(
                            Gebruikersgroep.tenant_id == tid, Gebruikersgroep.gebruik_id == obj.id
                        )
                    )
                )
            )
        ).scalar()
    )
    return {
        "id": obj.id, "organisatie_id": obj.organisatie_id, "organisatie_naam": org_naam,
        "applicatie_id": obj.applicatie_id, "heeft_verfijning": heeft,
        "created_at": obj.created_at, "updated_at": obj.updated_at,
    }


async def lijst_voor_applicatie(session: AsyncSession, tenant_id, applicatie_id) -> list[dict]:
    """De grove feiten van één applicatie: welke organisaties gebruiken haar, mét org-naam en of
    er een verfijning (afdeling) onder hangt. Begrensde afgeleide lijst (aantal organisaties is
    klein/begrensd) → bewust ongepagineerd, consistent met de context-sub-endpoints. Read-only."""
    tid = _tenant_uuid(tenant_id)
    org = aliased(Partij)
    heeft = exists(
        select(Gebruikersgroep.id).where(
            Gebruikersgroep.tenant_id == tid, Gebruikersgroep.gebruik_id == Organisatiegebruik.id
        )
    ).label("heeft_verfijning")
    rijen = (
        await session.execute(
            select(
                Organisatiegebruik.id,
                Organisatiegebruik.organisatie_id,
                org.naam.label("organisatie_naam"),
                Organisatiegebruik.applicatie_id,
                heeft,
                Organisatiegebruik.created_at,
                Organisatiegebruik.updated_at,
            )
            .outerjoin(org, and_(org.id == Organisatiegebruik.organisatie_id, org.tenant_id == tid))
            .where(Organisatiegebruik.tenant_id == tid, Organisatiegebruik.applicatie_id == applicatie_id)
            .order_by(org.naam.asc(), Organisatiegebruik.id.asc())
        )
    ).all()
    return [
        {
            "id": r.id, "organisatie_id": r.organisatie_id, "organisatie_naam": r.organisatie_naam,
            "applicatie_id": r.applicatie_id, "heeft_verfijning": r.heeft_verfijning,
            "created_at": r.created_at, "updated_at": r.updated_at,
        }
        for r in rijen
    ]
