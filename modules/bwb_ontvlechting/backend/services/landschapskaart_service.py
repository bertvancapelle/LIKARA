"""Service-laag — Landschapskaart (ADR-025, read-only grafprojectie).

Bouwt de volledige landschapsgraaf (nodes + edges) uit BESTAANDE data:
- nodes: componenten (incl. applicaties; met catalogus-typing + lifecycle-kleur), partijen, contracten;
- edges: vier "ringen" — applicaties (flow), infrastructuur (assignment), contracten (association),
  beheerorganisatie (roltoewijzing).

Puur read-only, afgeleid — geen schema/migratie. **Engine onaangeroerd**: dit bestand importeert
GEEN `lifecycle_service`/`herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade`/
`Checklistscore` en schrijft niets (geen `session.add`/`commit`/`flush`/`delete`). `lifecycle_status`
wordt read-only gelezen via een lichtgewicht tabel-constructie op `component_profiel` (LEFT JOIN),
bewust zónder de ORM-klasse te importeren (zie het engine-invariant in complidata-domeinmodel §6).
"""
import uuid

from sqlalchemy import and_, column, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    Component,
    Contract,
    Partij,
    Relatie,
    RelatieKenmerkDimensie,
    Roltoewijzing,
)
from schemas.landschapskaart import LandschapsEdge, LandschapskaartResponse, LandschapsNode
from services import componentconfig_catalog as comp_catalog
from services import relatiekenmerk_catalog as rk_catalog

# Lichtgewicht read-only handle op de engine-tabel `component_profiel` — bewust GEEN ORM-import
# (de import-afwezigheidstest verbiedt `ComponentProfiel`). Alleen de twee kolommen die we lezen.
_profiel = table("component_profiel", column("id"), column("tenant_id"), column("lifecycle_status"))

_RK_BEHEERROL = RelatieKenmerkDimensie.beheerrol


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _val(x):
    """Enum → .value; overige waarden ongewijzigd (uniforme stringificatie)."""
    return getattr(x, "value", x)


async def haal_grafdata_op(session: AsyncSession, tenant_id) -> LandschapskaartResponse:
    tid = _tenant_uuid(tenant_id)
    typing = await comp_catalog.archimate_typing(session)  # {componenttype: {archimate_element, laag, aspect}}

    nodes: list[LandschapsNode] = []
    component_ids: set[uuid.UUID] = set()
    contract_ids: set[uuid.UUID] = set()

    # ── Component-nodes (incl. applicaties) — typing uit de catalogus, lifecycle uit het profiel ──
    comp_rijen = (
        await session.execute(
            select(
                Component.id, Component.naam, Component.componenttype,
                _profiel.c.lifecycle_status.label("lifecycle_status"),
            )
            .outerjoin(_profiel, and_(_profiel.c.id == Component.id, _profiel.c.tenant_id == tid))
            .where(Component.tenant_id == tid)
        )
    ).all()
    for r in comp_rijen:
        component_ids.add(r.id)
        t = typing.get(r.componenttype, {})
        nodes.append(LandschapsNode(
            id=r.id, naam=r.naam, element_type=r.componenttype,
            laag=t.get("laag"), archimate_element=t.get("archimate_element"),
            lifecycle_status=_val(r.lifecycle_status),
        ))

    # ── Partij-nodes — business-laag, aard als `soort` ──
    partij_rijen = (
        await session.execute(
            select(Partij.id, Partij.naam, Partij.aard).where(Partij.tenant_id == tid)
        )
    ).all()
    for r in partij_rijen:
        nodes.append(LandschapsNode(
            id=r.id, naam=r.naam, element_type="partij", laag="business",
            archimate_element="business_actor", soort=_val(r.aard),
        ))

    # ── Contract-nodes — business-laag ──
    contract_rijen = (
        await session.execute(
            select(Contract.id, Contract.contractnaam).where(Contract.tenant_id == tid)
        )
    ).all()
    for r in contract_rijen:
        contract_ids.add(r.id)
        nodes.append(LandschapsNode(
            id=r.id, naam=r.contractnaam, element_type="contract", laag="business",
            archimate_element="contract",
        ))

    edges: list[LandschapsEdge] = []

    # ── Ringen 1–3 — uit het relatiemodel (membership-classificatie op de id-sets) ──
    rel_rijen = (
        await session.execute(
            select(Relatie.bron_id, Relatie.doel_id, Relatie.relatietype).where(Relatie.tenant_id == tid)
        )
    ).all()
    for r in rel_rijen:
        rt = _val(r.relatietype)
        if rt == "flow" and r.bron_id in component_ids and r.doel_id in component_ids:
            edges.append(LandschapsEdge(bron_id=r.bron_id, doel_id=r.doel_id,
                                        relatietype="flow", label="koppeling", ring="applicaties"))
        elif rt == "assignment" and r.doel_id in component_ids:
            # assignment = host → gehoste component (oriëntatie bron=host, doel=component).
            edges.append(LandschapsEdge(bron_id=r.bron_id, doel_id=r.doel_id,
                                        relatietype="assignment", label="draait op", ring="infrastructuur"))
        elif rt == "association" and r.doel_id in contract_ids:
            edges.append(LandschapsEdge(bron_id=r.bron_id, doel_id=r.doel_id,
                                        relatietype="association", label="valt onder", ring="contracten"))

    # ── Ring 4 — beheerorganisatie uit de roltoewijzingen (label = rol-naam) ──
    rol_labels = await rk_catalog.labels(session, _RK_BEHEERROL)
    rt_rijen = (
        await session.execute(
            select(Roltoewijzing.partij_id, Roltoewijzing.object_id, Roltoewijzing.rol).where(
                Roltoewijzing.tenant_id == tid
            )
        )
    ).all()
    for r in rt_rijen:
        edges.append(LandschapsEdge(
            bron_id=r.partij_id, doel_id=r.object_id, relatietype="roltoewijzing",
            label=rk_catalog.resolveer_een(r.rol, rol_labels), ring="beheerorganisatie",
        ))

    return LandschapskaartResponse(nodes=nodes, edges=edges)
