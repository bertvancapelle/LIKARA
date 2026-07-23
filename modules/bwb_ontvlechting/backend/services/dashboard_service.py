"""Service-laag voor het tenant-brede dashboard (CD014, #9; ADR-022 Fase F).

Read-only aggregatie binnen één tenant (RLS-context via `get_tenant_session` ÉN
expliciete `tenant_id`-filter — dubbele tenant-bescherming). Strikt tenant-scoped.

ADR-022 Fase F (Besluit 3): de readiness wordt **per componenttype** uitgesplitst —
géén gefuseerd gereedheidscijfer over heterogene typen. Alleen checklist-dragende
componenten hebben een `component_profiel`; kale typen (zonder profiel) verschijnen
dus vanzelf niet in de rollup. `recent_gewijzigd` is type-generiek (alle
profiel-dragende componenten, niet langer alleen `applicatie`).
"""
import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services import actieve_vraag
from models.models import (
    ACTIEVE_BLOKKADE_STATUSSEN,
    Blokkade,
    Component,
    ComponentConfigDimensie,
    ComponentKlaarverklaring,
    ComponentProfiel,
    KlaarverklaringStatus,
    LifecycleStatus,
)
from services import componentconfig_catalog as catalog

# Vast server-side limiet voor "recent gewijzigd" — geen client-input.
_RECENT_LIMIT = 5

# ADR-027 — lifecycle-statussen die "checklist compleet" betekenen (alle vragen gescoord).
# Een klaar-verklaring op een component dáárbuiten = het afwijkingsgeval. Dit hergebruikt de
# bestaande engine-status als vragen-volledigheid-signaal — GEEN tweede vragen-telling.
_VRAGEN_COMPLEET_STATUSSEN = (LifecycleStatus.migratieklaar, LifecycleStatus.geblokkeerd)

# De reële lifecycle-statussen die het dashboard telt. `checklist_compleet` is
# transient (ADR-013 B4 — nooit opgeslagen) en valt hier bewust buiten.
_GETOONDE_STATUSSEN = (
    LifecycleStatus.concept,
    LifecycleStatus.in_inventarisatie,
    LifecycleStatus.geblokkeerd,
    LifecycleStatus.migratieklaar,
)
_MIGRATIEKLAAR = LifecycleStatus.migratieklaar.value


def _tenant_uuid(tenant_id) -> uuid.UUID:
    """Normaliseer de tenant-id (uit de sessie een str) naar UUID."""
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def haal_dashboard(session: AsyncSession, tenant_id) -> dict:
    """Stel het tenant-brede dashboard-overzicht samen (tenant-scoped).

    Returnt een dict in de vorm van `DashboardRead`:
    `readiness_per_type` (per checklist-dragend type: statusverdeling + totaal +
    migratieklaar), `open_blokkades`, en `recent_gewijzigd` (≤ `_RECENT_LIMIT`,
    alle profiel-dragende componenten, `updated_at` aflopend).
    """
    tid = _tenant_uuid(tenant_id)

    # 1. Readiness PER TYPE — join Component voor het type; alleen profiel-dragende
    #    (checklist-dragende) componenten tellen mee (Besluit 3: geen mengcijfer).
    rijen = (
        await session.execute(
            select(
                Component.componenttype,
                ComponentProfiel.lifecycle_status,
                func.count(),
            )
            .join(ComponentProfiel, ComponentProfiel.id == Component.id)
            .where(Component.tenant_id == tid)
            .group_by(Component.componenttype, ComponentProfiel.lifecycle_status)
        )
    ).all()

    type_labels = await catalog.labels(session, ComponentConfigDimensie.componenttype)
    per_type: dict[str, dict[str, int]] = {}
    for componenttype, status, aantal in rijen:
        sleutel = status.value if isinstance(status, LifecycleStatus) else str(status)
        bucket = per_type.setdefault(
            componenttype, {s.value: 0 for s in _GETOONDE_STATUSSEN}
        )
        if sleutel in bucket:  # transient checklist_compleet (zou 0 zijn) genegeerd
            bucket[sleutel] = aantal

    readiness_per_type = [
        {
            "componenttype": ct,
            "componenttype_label": catalog.resolveer_een(ct, type_labels),
            "telling": telling,
            "totaal": sum(telling.values()),
            "migratieklaar": telling.get(_MIGRATIEKLAAR, 0),
        }
        for ct, telling in sorted(per_type.items())
    ]

    # 2. Open blokkades (ADR-013-definitie: open of in_behandeling), tenant-breed.
    open_blokkades = (
        await session.execute(
            select(func.count())
            .select_from(Blokkade)
            .where(
                Blokkade.tenant_id == tid,
                Blokkade.status.in_(ACTIEVE_BLOKKADE_STATUSSEN),
                # LI050: knelpunten van uitgezette vragen tellen niet mee (gedeelde afleiding).
                actieve_vraag.blokkade_telt_mee(Blokkade.checklistscore_id),
            )
        )
    ).scalar_one()

    # 3. Recentst gewijzigde profiel-dragende componenten (type-generiek, ADR-022 Fase F).
    recent_rijen = (
        await session.execute(
            select(
                Component.id,
                Component.naam,
                ComponentProfiel.lifecycle_status,
                Component.updated_at,
            )
            .join(ComponentProfiel, ComponentProfiel.id == Component.id)
            .where(Component.tenant_id == tid)
            .order_by(Component.updated_at.desc(), Component.id.desc())
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

    # 4. ADR-027 slice 3 — klaarverklaring-voortgang (read-only afgeleid; raakt de engine niet).
    #    `klaar_verklaard` = componenten met een levende verklaring status=klaar.
    klaar_verklaard = (
        await session.execute(
            select(func.count())
            .select_from(ComponentKlaarverklaring)
            .where(
                ComponentKlaarverklaring.tenant_id == tid,
                ComponentKlaarverklaring.status == KlaarverklaringStatus.klaar,
            )
        )
    ).scalar_one()

    #    `klaar_met_afwijking` = daarvan de componenten waarvan de checklist NOG NIET compleet is
    #    (lifecycle ∉ {migratieklaar, geblokkeerd}). INNER join op het profiel → kale componenten
    #    (geen checklist) tellen niet mee. Puur de join klaar-status × bestaande lifecycle: geen
    #    tweede vragen-telling, geen herberekening.
    klaar_met_afwijking = (
        await session.execute(
            select(func.count())
            .select_from(ComponentKlaarverklaring)
            .join(
                ComponentProfiel,
                and_(
                    ComponentProfiel.id == ComponentKlaarverklaring.component_id,
                    ComponentProfiel.tenant_id == tid,
                ),
            )
            .where(
                ComponentKlaarverklaring.tenant_id == tid,
                ComponentKlaarverklaring.status == KlaarverklaringStatus.klaar,
                ComponentProfiel.lifecycle_status.notin_(_VRAGEN_COMPLEET_STATUSSEN),
            )
        )
    ).scalar_one()

    return {
        "readiness_per_type": readiness_per_type,
        "open_blokkades": open_blokkades,
        "recent_gewijzigd": recent,
        "klaar_verklaard": klaar_verklaard,
        "klaar_met_afwijking": klaar_met_afwijking,
    }
