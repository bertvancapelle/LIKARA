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
    Component,
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
    """Pure canonieke afleiding (ADR-013, per-type vragenset ADR-022 Fase B).
    Zet nooit terug naar `concept`.

    - `concept` blijft `concept` (alleen handmatige start verlaat die vloer);
    - **lege vragenset** (`aantal_vragen == 0`): een checklist-dragend type zónder
      vragen kan per definitie nooit "compleet" zijn en mag dus nooit vals-positief
      als gereed tellen → blijft `in_inventarisatie` (niet-groen, buiten de
      readiness-schaal). Bewust binnen de bestaande ADR-013-enum: geen sentinel,
      geen nieuwe waarde (ADR-022 Fase B structurele bewaking);
    - niet alle vragen gescoord → `in_inventarisatie`;
    - alles gescoord + ≥1 open blokkade → `geblokkeerd`;
    - alles gescoord + geen open blokkade → `migratieklaar`.
    """
    if huidige == LifecycleStatus.concept:
        return LifecycleStatus.concept
    if aantal_vragen <= 0:
        return LifecycleStatus.in_inventarisatie  # lege vragenset → nooit gereed
    if aantal_gescoord < aantal_vragen:
        return LifecycleStatus.in_inventarisatie
    if aantal_open_blokkades > 0:
        return LifecycleStatus.geblokkeerd
    return LifecycleStatus.migratieklaar


async def herbereken_lifecycle(
    session: AsyncSession, tenant_id, component_id
) -> LifecycleStatus:
    """Herbereken en zet de canonieke `lifecycle_status` (tenant-scoped).

    Het anker is het generieke `ComponentProfiel`
    (`component_profiel.id == component.id == applicatie.id`, shared-PK). Leest de
    actuele tellingen (autoflush zorgt dat een net toegevoegde score/blokkade
    meetelt), past `bepaal_lifecycle` toe en schrijft het resultaat op het profiel.
    De aanroepende service commit. Profiel buiten de tenant ⇒ `NietGevonden`.

    ADR-022 Fase B: de vragenset-telling is **per type** — het aantal vragen voor
    een component is het aantal `ChecklistVraag`-rijen waarvan `componenttype` gelijk
    is aan het componenttype van dít component (niet langer de globale set). Het type
    leeft op `component` (Besluit 1b); we joinen via het profiel-anker.
    """
    tid = _tenant_uuid(tenant_id)

    rij = (
        await session.execute(
            select(ComponentProfiel, Component.componenttype)
            .join(Component, Component.id == ComponentProfiel.id)
            .where(ComponentProfiel.id == component_id, ComponentProfiel.tenant_id == tid)
        )
    ).first()
    if rij is None:
        raise NietGevonden("component_profiel", component_id)
    profiel, componenttype = rij

    # Per-type, tenant-eigen, ACTIEVE vragenset (ADR-022 Fase B + W1): alleen de
    # actieve vragen van het componenttype van dít component tellen mee. `checklistvraag`
    # is sinds W1 tenant-scoped (RLS) → de telling auto-scopet op de tenant; `actief`
    # sluit soft-gedeactiveerde vragen uit `aantal_vragen` (en daarmee uit "gereed").
    aantal_vragen = (
        await session.execute(
            select(func.count())
            .select_from(ChecklistVraag)
            .where(
                ChecklistVraag.componenttype == componenttype,
                ChecklistVraag.actief.is_(True),
            )
        )
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
