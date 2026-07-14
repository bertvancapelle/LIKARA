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

from sqlalchemy import and_, exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.models import Component, Gebruikersgroep, Organisatiegebruik, Partij
from schemas.organisatiegebruik import OrganisatiegebruikCreate
from services import partij_service
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict

_ENTITEIT = "organisatiegebruik"


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def valideer_component(session: AsyncSession, tid: uuid.UUID, applicatie_id) -> None:
    """ADR-041 slice 2 (herzien) — het doel moet een bestaand COMPONENT van de tenant zijn.

    Organisatiegebruik is **component-breed en tenant-gelijk**: elk componenttype mag als gebruik worden
    geregistreerd — geen persoonlijke invoerregel. Een persoonlijke voorkeur is een KIJKFILTER (frontend,
    bepaalt alleen wat je standaard ziet), nooit een schrijf-slot. Een niet-component (partij/contract) /
    niet-bestaand / cross-tenant doel → 422 `ONGELDIG_COMPONENT` (geen lek van vreemd bestaan)."""
    ct = (
        await session.execute(
            select(Component.componenttype).where(
                Component.id == applicatie_id, Component.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if ct is None:
        raise OngeldigeRegistratie(
            "ONGELDIG_COMPONENT", "Het gebruiksfeit moet naar een bestaand component verwijzen."
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
    await valideer_component(session, tid, applicatie_id)
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
    await valideer_component(session, tid, data.applicatie_id)
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
    """Verwijder een grof feit — alléén als er geen verfijning onder hangt.

    ADR-038/046: de verfijning-FK (`gebruikersgroep.gebruik_id`) is NOT NULL + ON DELETE
    **RESTRICT** (de oude SET NULL-docstring was stale) — een feit met gebruikersgroepen
    kan dus structureel niet stil verdwijnen, en cascaden over veldwerk is verboden.
    Pre-check → 409 `GEBRUIK_HEEFT_VERFIJNING` met de telling (de gebruiker verwijdert of
    verplaatst eerst bewust de groepen); de DB-RESTRICT is de backstop."""
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, gebruik_id)
    aantal_groepen = (
        await session.execute(
            select(func.count()).select_from(Gebruikersgroep).where(
                Gebruikersgroep.tenant_id == tid, Gebruikersgroep.gebruik_id == obj.id
            )
        )
    ).scalar_one()
    if aantal_groepen:
        raise RegistratieConflict(
            "GEBRUIK_HEEFT_VERFIJNING",
            f"Deze organisatie heeft {aantal_groepen} gebruikersgroep(en) op dit component; "
            "verwijder of verplaats die eerst — een verfijnde registratie verdwijnt nooit stil.",
        )
    try:
        await session.delete(obj)
        await session.commit()
    except IntegrityError as exc:  # RESTRICT-backstop (race met een gelijktijdige verfijning)
        await session.rollback()
        raise RegistratieConflict(
            "GEBRUIK_HEEFT_VERFIJNING",
            "Deze organisatie heeft gebruikersgroepen op dit component; "
            "verwijder of verplaats die eerst — een verfijnde registratie verdwijnt nooit stil.",
        ) from exc


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


async def _afdelingen_per_gebruik(
    session: AsyncSession, tid: uuid.UUID, gebruik_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[str]]:
    """ADR-046 stuk 2 — per grof feit de bekende afdelingsnamen uit de verfijnende
    gebruikersgroepen (distinct, gesorteerd). Groepen zonder afdeling leveren niets: de
    UI toont dan rustig "afdeling onbekend" (het normale geval na een eerste workshop —
    geen fout). Eén batch-query (N+1-vrij), read-only."""
    if not gebruik_ids:
        return {}
    afd = aliased(Partij)
    rijen = (
        await session.execute(
            select(Gebruikersgroep.gebruik_id, afd.naam)
            .join(afd, and_(afd.id == Gebruikersgroep.afdeling_id, afd.tenant_id == tid))
            .where(Gebruikersgroep.tenant_id == tid, Gebruikersgroep.gebruik_id.in_(gebruik_ids))
            .order_by(afd.naam.asc())
        )
    ).all()
    uit: dict[uuid.UUID, list[str]] = {}
    for gebruik_id, naam in rijen:
        lijst = uit.setdefault(gebruik_id, [])
        if naam not in lijst:
            lijst.append(naam)
    return uit


async def lijst_voor_applicatie(session: AsyncSession, tenant_id, applicatie_id) -> list[dict]:
    """De grove feiten van één applicatie: welke organisaties gebruiken haar, mét org-naam, of
    er een verfijning (afdeling) onder hangt én de bekende afdelingsnamen (ADR-046 stuk 2 —
    "één regel per organisatie, afdeling(en) indien bekend"). Begrensde afgeleide lijst (aantal
    organisaties is klein/begrensd) → bewust ongepagineerd, consistent met de
    context-sub-endpoints. Read-only."""
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
    afdelingen = await _afdelingen_per_gebruik(session, tid, [r.id for r in rijen])
    return [
        {
            "id": r.id, "organisatie_id": r.organisatie_id, "organisatie_naam": r.organisatie_naam,
            "applicatie_id": r.applicatie_id, "heeft_verfijning": r.heeft_verfijning,
            "afdelingen": afdelingen.get(r.id, []),
            "created_at": r.created_at, "updated_at": r.updated_at,
        }
        for r in rijen
    ]


async def lijst_voor_organisatie(session: AsyncSession, tenant_id, organisatie_id) -> list[dict]:
    """De applicaties die één organisatie gebruikt: het grove feit gefilterd op `organisatie_id`,
    gejoined met de applicatie-component voor naam + type, plus `verfijnd` = of er minstens één
    gebruikersgroep (afdeling-verfijning) ónder dit feit hangt (False = grof-only, "nog niet
    verfijnd"). Inclusief grof-only feiten (organisatie zónder afdeling/groep). Elke applicatie
    precies één keer (UNIQUE(tenant, org, app)). Levert de **gedeelde rij-vorm**
    (`component_id`/`component_naam`/`componenttype`/`verfijnd`) die zowel het "Gebruikte
    applicaties"-blok als de Landschapskaart-subgraaf voedt. Begrensde afgeleide lijst (bewust geen
    keyset — het aantal applicaties per organisatie is klein/begrensd, consistent met de zuster-
    context-endpoints). Read-only."""
    tid = _tenant_uuid(tenant_id)
    verfijnd = exists(
        select(Gebruikersgroep.id).where(
            Gebruikersgroep.tenant_id == tid, Gebruikersgroep.gebruik_id == Organisatiegebruik.id
        )
    ).label("verfijnd")
    rijen = (
        await session.execute(
            select(
                Organisatiegebruik.applicatie_id.label("component_id"),
                Component.naam.label("component_naam"),
                Component.componenttype.label("componenttype"),
                verfijnd,
            )
            .join(Component, and_(Component.id == Organisatiegebruik.applicatie_id, Component.tenant_id == tid))
            .where(Organisatiegebruik.tenant_id == tid, Organisatiegebruik.organisatie_id == organisatie_id)
            .order_by(Component.naam.asc(), Organisatiegebruik.applicatie_id.asc())
        )
    ).all()
    return [
        {
            "component_id": r.component_id, "component_naam": r.component_naam,
            "componenttype": r.componenttype, "verfijnd": bool(r.verfijnd),
        }
        for r in rijen
    ]
