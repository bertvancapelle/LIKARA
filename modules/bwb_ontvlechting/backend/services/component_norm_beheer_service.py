"""Service — BEHEER van de tenant-norm (ADR-052 slice 4b): de beheerder zet per hard feit de
verplicht-vlag, met een impact-voorspelling vóór het opslaan.

Bewust GESCHEIDEN van de read-only `component_norm_service` (die is de leeslaag; een bronscan-test
bewaakt dat ze niets muteert). De SCHRIJFkant leeft hier. `zet_verplicht` schrijft ORM → wordt
automatisch geaudit (`component_norm` staat in `AUDIT_TENANT_ENTITEITEN`) — zo ontstaat het
"wanneer/door wie" waar de werkvoorraadregel (slice 4a) op leunt (besluit 5).

Engine onaangeroerd: importeert géén lifecycle/score/blokkade/profiel-symbolen. De impact leest
exact dezelfde determinatie als de norm (`component_norm_service.feit_vastgesteld`) — geen tweede
telling (besluit 3).
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    Component,
    ComponentKlaarverklaring,
    ComponentNorm,
    KlaarverklaringStatus,
)
from services import component_norm_service
from services.errors import NietGevonden


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _valideer_feit(feit_sleutel: str) -> None:
    if feit_sleutel not in component_norm_service.HARDE_FEITEN:
        raise NietGevonden("component_norm", feit_sleutel)


async def zet_verplicht(session: AsyncSession, tenant_id, feit_sleutel: str, verplicht: bool) -> dict:
    """Zet de verplicht-vlag voor één hard feit. ORM (geen core-upsert) → de audit vangt de omslag
    (wie/wanneer). 404 als het feit onbekend is. Ontbreekt de rij (nog niet geseed), dan wordt hij
    aangemaakt — degradeert netjes."""
    _valideer_feit(feit_sleutel)
    tid = _tenant_uuid(tenant_id)
    rij = (
        await session.execute(
            select(ComponentNorm).where(
                ComponentNorm.tenant_id == tid, ComponentNorm.feit_sleutel == feit_sleutel
            )
        )
    ).scalar_one_or_none()
    if rij is None:
        rij = ComponentNorm(tenant_id=tid, feit_sleutel=feit_sleutel, verplicht=verplicht)
        session.add(rij)
    else:
        rij.verplicht = verplicht
    await session.commit()
    return {"feit": feit_sleutel, "verplicht": verplicht}


async def impact_voor_feit(
    session: AsyncSession, tenant_id, feit_sleutel: str, verplicht_doel: bool
) -> dict:
    """Voorspelling vóór opslaan (besluit 3) — géén blokkade, alleen "wat richt ik aan". Read-only.

    - ``componenten_geraakt``: componenten waar dit feit NIET vastgesteld is (aanzetten: voldoen
      daardoor niet meer; uitzetten: hun signaal vervalt).
    - ``klaarverklaringen_geraakt``: hoeveel daarvan eerder klaar zijn verklaard.
    - ``componenten_nu_compleet`` (alleen bij UITZETTEN): componenten die alsnog volledig voldoen
      omdat dit hun énige open feit was.

    Dezelfde determinatie als de norm (`feit_vastgesteld`) — geen tweede telling."""
    _valideer_feit(feit_sleutel)
    tid = _tenant_uuid(tenant_id)
    comp_ids = [
        r[0] for r in (
            await session.execute(select(Component.id).where(Component.tenant_id == tid))
        ).all()
    ]
    open_ids = [
        cid for cid in comp_ids
        if (await component_norm_service.feit_vastgesteld(session, tid, cid, feit_sleutel)) is False
    ]
    klaar_ids = {
        r[0] for r in (
            await session.execute(
                select(ComponentKlaarverklaring.component_id).where(
                    ComponentKlaarverklaring.tenant_id == tid,
                    ComponentKlaarverklaring.status == KlaarverklaringStatus.klaar,
                )
            )
        ).all()
    }
    resultaat = {
        "feit": feit_sleutel,
        "verplicht_doel": verplicht_doel,
        "componenten_geraakt": len(open_ids),
        "klaarverklaringen_geraakt": sum(1 for c in open_ids if c in klaar_ids),
    }
    if not verplicht_doel:
        # Uitzetten: hoeveel worden alsnog volledig compleet (dit feit was hun énige open feit)?
        nu_compleet = 0
        for cid in open_ids:
            status = await component_norm_service.norm_status(session, tid, cid)
            open_feiten = {
                f for f, s in status["feiten"].items()
                if s == component_norm_service.NIET_VASTGESTELD
            }
            if open_feiten == {feit_sleutel}:
                nu_compleet += 1
        resultaat["componenten_nu_compleet"] = nu_compleet
    return resultaat
