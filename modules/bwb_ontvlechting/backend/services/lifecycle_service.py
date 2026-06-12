"""Lifecycle-herberekening (Model A, ADR-013).

Eén deterministische afleiding van `Applicatie.lifecycle_status` uit de feiten:
het aantal gescoorde vragen vs. de actieve vragenset en het aantal open
blokkades. Draait na elke Checklistscore-/Blokkade-mutatie en na de handmatige
`start-inventarisatie`.

De pure beslisregel (`bepaal_lifecycle`) is DB-vrij en apart gehouden — net als
`volgende_status_na_start` bij Applicatie — zodat hij volledig testbaar is.

`concept` is de enige niet-afgeleide vloer: de herberekening zet de status nooit
terug naar `concept` (detectie op de huidige status). Reverse tussen de afgeleide
statussen is wél toegestaan (pure her-afleiding, geen forward-only machine).
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    ACTIEVE_BLOKKADE_STATUSSEN,
    Blokkade,
    ChecklistVraag,
    Checklistscore,
    ComponentProfiel,
    LifecycleStatus,
)
from services.errors import NietGevonden


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def bepaal_lifecycle(
    huidige: LifecycleStatus,
    aantal_gescoord: int,
    aantal_vragen: int,
    aantal_open_blokkades: int,
) -> LifecycleStatus:
    """Pure canonieke afleiding (ADR-013). Zet nooit terug naar `concept`.

    - `concept` blijft `concept` (alleen handmatige start verlaat die vloer);
    - niet alle vragen gescoord (of lege vragenset) → `in_inventarisatie`;
    - alles gescoord + ≥1 open blokkade → `geblokkeerd`;
    - alles gescoord + geen open blokkade → `migratieklaar`.
    """
    if huidige == LifecycleStatus.concept:
        return LifecycleStatus.concept
    if aantal_vragen <= 0 or aantal_gescoord < aantal_vragen:
        return LifecycleStatus.in_inventarisatie
    if aantal_open_blokkades > 0:
        return LifecycleStatus.geblokkeerd
    return LifecycleStatus.migratieklaar


async def herbereken_lifecycle(
    session: AsyncSession, tenant_id, component_id
) -> LifecycleStatus:
    """Herbereken en zet de canonieke `lifecycle_status` (tenant-scoped).

    ADR-022 Fase A: het anker is het generieke `ComponentProfiel`
    (`component_profiel.id == component.id == applicatie.id`, shared-PK). Leest de
    actuele tellingen (autoflush zorgt dat een net toegevoegde score/blokkade
    meetelt), past `bepaal_lifecycle` toe en schrijft het resultaat op het profiel.
    De aanroepende service commit. Profiel buiten de tenant ⇒ `NietGevonden`.

    De vragenset-telling is in Fase A nog GLOBAAL (alle `ChecklistVraag`) — de
    per-type scoping volgt in Fase B; alleen het anker verschuift hier.
    """
    tid = _tenant_uuid(tenant_id)

    profiel = (
        await session.execute(
            select(ComponentProfiel).where(
                ComponentProfiel.id == component_id, ComponentProfiel.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if profiel is None:
        raise NietGevonden("component_profiel", component_id)

    # Actieve vragenset is platform-breed (ChecklistVraag, geen tenant/RLS).
    aantal_vragen = (
        await session.execute(select(func.count()).select_from(ChecklistVraag))
    ).scalar_one()
    aantal_gescoord = (
        await session.execute(
            select(func.count())
            .select_from(Checklistscore)
            .where(
                Checklistscore.tenant_id == tid,
                Checklistscore.component_id == component_id,
            )
        )
    ).scalar_one()
    aantal_open_blokkades = (
        await session.execute(
            select(func.count())
            .select_from(Blokkade)
            .where(
                Blokkade.tenant_id == tid,
                Blokkade.component_id == component_id,
                Blokkade.status.in_(ACTIEVE_BLOKKADE_STATUSSEN),
            )
        )
    ).scalar_one()

    nieuwe = bepaal_lifecycle(
        profiel.lifecycle_status, aantal_gescoord, aantal_vragen, aantal_open_blokkades
    )
    if nieuwe != profiel.lifecycle_status:
        profiel.lifecycle_status = nieuwe
    return nieuwe
