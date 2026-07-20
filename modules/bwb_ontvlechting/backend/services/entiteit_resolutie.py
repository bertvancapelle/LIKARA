"""Entiteit-naam-resolutie (LI019) — leesbare objectnaam voor het audit-spoor.

Batch-resolutie van (entiteit_type, entiteit_id) → objectnaam, tenant-scoped en N+1-vrij:
per naam-dragende tabel één query. Entiteiten zonder natuurlijke naam (component_profiel/
checklistscore/blokkade/component_klaarverklaring/roltoewijzing/gebruiker_persoon) staan niet
in de map → de UI valt terug op het entiteit_id.

ENGINE-INVARIANT: read-only naam-lookup; importeert GEEN lifecycle/score-symbolen
(`lifecycle_service`/`herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade`/
`Checklistscore`).
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Component, Contract, Deliverable, Gap, Partij, Plateau, Relatie, WorkPackage


def _tid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


# entiteit_type → (Model, naam-kolom). `applicatie` wijst naar DEZELFDE rij als `component`
# (LI059: geen subtabel meer — een component met `componenttype='applicatie'` ís de applicatie);
# het aparte entiteit_type blijft bestaan voor historische audit-records.
_BRONNEN = {
    "component": (Component, Component.naam),
    "applicatie": (Component, Component.naam),
    "contract": (Contract, Contract.contractnaam),
    "partij": (Partij, Partij.naam),
    "plateau": (Plateau, Plateau.naam),
    "deliverable": (Deliverable, Deliverable.naam),
    "work_package": (WorkPackage, WorkPackage.naam),
    "gap": (Gap, Gap.naam),
    "relatie": (Relatie, Relatie.naam),  # naam alleen gevuld bij flow-koppelingen → anders fallback
}


async def resolveer_namen(session: AsyncSession, tenant_id, paren) -> dict[tuple[str, str], str]:
    """Batch: `{(entiteit_type, str(id)): naam}` voor naam-dragende entiteiten (tenant-scoped).

    `paren` = iterable van `(entiteit_type, entiteit_id)`. Onbekende typen, ontbrekende ids of
    naamloze rijen ontbreken in de map (de aanroeper valt dan terug op het id)."""
    tid = _tid(tenant_id)
    # ids groeperen per bron (component+applicatie delen Component → één query).
    per_bron: dict = {}
    for etype, eid in paren:
        bron = _BRONNEN.get(etype)
        if not bron or eid is None:
            continue
        per_bron.setdefault(bron, set()).add(str(eid))

    typen_per_bron: dict = {}
    for etype, bron in _BRONNEN.items():
        typen_per_bron.setdefault(bron, []).append(etype)

    uit: dict[tuple[str, str], str] = {}
    for bron, ids in per_bron.items():
        model, naamcol = bron
        rijen = (
            await session.execute(
                select(model.id, naamcol).where(
                    model.tenant_id == tid, model.id.in_([uuid.UUID(i) for i in ids])
                )
            )
        ).all()
        id_naam = {str(rid): naam for rid, naam in rijen if naam}
        for etype in typen_per_bron[bron]:
            for sid, naam in id_naam.items():
                uit[(etype, sid)] = naam
    return uit
