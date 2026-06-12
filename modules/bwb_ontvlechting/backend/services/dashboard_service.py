"""Service-laag voor het tenant-brede dashboard (CD014, #9).

Read-only aggregatie over de applicaties van de tenant: telling per reële
lifecycle-status, aantal open blokkades en de recentst gewijzigde applicaties.

Elke query draait binnen de tenant-sessie (RLS-context via `get_tenant_session`)
ÉN filtert expliciet op `tenant_id` — dubbele tenant-bescherming
(complidata-security). Strikt tenant-scoped: nooit een tenant-overschrijdende
telling.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    ACTIEVE_BLOKKADE_STATUSSEN,
    Applicatie,
    Blokkade,
    Component,
    ComponentProfiel,
    LifecycleStatus,
)

# Vast server-side limiet voor "recent gewijzigd" — geen client-input, dus geen
# extra validatie-oppervlak.
_RECENT_LIMIT = 5

# De reële lifecycle-statussen die het dashboard telt. `checklist_compleet` is
# transient (ADR-013 B4 — nooit opgeslagen) en valt hier bewust buiten, zodat de
# UI-vorm stabiel is en geen "dode" status toont.
_GETOONDE_STATUSSEN = (
    LifecycleStatus.concept,
    LifecycleStatus.in_inventarisatie,
    LifecycleStatus.geblokkeerd,
    LifecycleStatus.migratieklaar,
)


def _tenant_uuid(tenant_id) -> uuid.UUID:
    """Normaliseer de tenant-id (uit de sessie een str) naar UUID."""
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def haal_dashboard(session: AsyncSession, tenant_id) -> dict:
    """Stel het tenant-brede dashboard-overzicht samen (tenant-scoped).

    Returnt een dict in de vorm van `DashboardRead`:
    `lifecycle_telling` (4 reële statussen, 0-default), `open_blokkades` en
    `recent_gewijzigd` (≤ `_RECENT_LIMIT`, gesorteerd op `updated_at` aflopend).
    """
    tid = _tenant_uuid(tenant_id)

    # 1. Telling per lifecycle-status — geseed op de getoonde statussen.
    telling = {status.value: 0 for status in _GETOONDE_STATUSSEN}
    # ADR-022 Fase A: lifecycle_status leeft op het profiel (1-op-1 met applicatie).
    rijen = (
        await session.execute(
            select(ComponentProfiel.lifecycle_status, func.count())
            .where(ComponentProfiel.tenant_id == tid)
            .group_by(ComponentProfiel.lifecycle_status)
        )
    ).all()
    for status, aantal in rijen:
        sleutel = status.value if isinstance(status, LifecycleStatus) else str(status)
        if sleutel in telling:  # transient checklist_compleet (zou 0 zijn) genegeerd
            telling[sleutel] = aantal

    # 2. Open blokkades (ADR-013-definitie: open of in_behandeling).
    open_blokkades = (
        await session.execute(
            select(func.count())
            .select_from(Blokkade)
            .where(
                Blokkade.tenant_id == tid,
                Blokkade.status.in_(ACTIEVE_BLOKKADE_STATUSSEN),
            )
        )
    ).scalar_one()

    # 3. Recentst gewijzigde applicaties (vast limiet; kolom-select, geen volledige ORM).
    recent_rijen = (
        await session.execute(
            select(
                Applicatie.id,
                Component.naam,  # naam verhuisde naar de component (ADR-021)
                ComponentProfiel.lifecycle_status,  # lifecycle verhuisde naar het profiel (ADR-022)
                Applicatie.updated_at,
            )
            .join(Component, Component.id == Applicatie.id)
            .join(ComponentProfiel, ComponentProfiel.id == Applicatie.id)
            .where(Applicatie.tenant_id == tid)
            .order_by(Applicatie.updated_at.desc(), Applicatie.id.desc())
            .limit(_RECENT_LIMIT)
        )
    ).all()
    recent = [
        {
            "id": rij.id,
            "naam": rij.naam,
            "lifecycle_status": rij.lifecycle_status,
            "gewijzigd_op": rij.updated_at,
        }
        for rij in recent_rijen
    ]

    return {
        "lifecycle_telling": telling,
        "open_blokkades": open_blokkades,
        "recent_gewijzigd": recent,
    }
