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

from sqlalchemy import String, and_, cast, column, func, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    Component,
    ComponentConfigDimensie,
    Contract,
    Partij,
    PartijAard,
    Plateau,
    Relatie,
    RelatieKenmerkDimensie,
    Roltoewijzing,
)
from schemas.landschapskaart import LandschapsEdge, LandschapskaartResponse, LandschapsNode
from services import componentconfig_catalog as comp_catalog
from services import relatiekenmerk_catalog as rk_catalog

# Lichtgewicht read-only handles op engine-tabellen — bewust GEEN ORM-import (de import-
# afwezigheidstest verbiedt `ComponentProfiel`/`Blokkade`). Alleen de gelezen kolommen.
_profiel = table("component_profiel", column("id"), column("tenant_id"), column("lifecycle_status"))
_blokkade = table("blokkade", column("component_id"), column("tenant_id"), column("status"))

_RK_BEHEERROL = RelatieKenmerkDimensie.beheerrol
# Rollen waaruit we een "leverancier" afleiden voor de node-verrijking.
_LEVERANCIER_ROLLEN = ("technisch_beheer", "contractbeheer")


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _val(x):
    """Enum → .value; overige waarden ongewijzigd (uniforme stringificatie)."""
    return getattr(x, "value", x)


async def haal_grafdata_op(session: AsyncSession, tenant_id, diepte: int = 1) -> LandschapskaartResponse:
    """Volledige landschapsgraaf (nodes + edges) voor de tenant.

    `diepte` is voorbereid voor een ego-gecentreerde sub-graaf (ADR-025 roadmap). Dit endpoint
    levert bewust de **volledige** graaf (zie de route-docstring), dus `diepte` heeft hier nog géén
    server-effect; de Landschapskaart past de stap-diepte client-side toe op de geladen graaf (de
    ego-view kent al alle nodes/edges). De parameter is forward-compatibel meegenomen.
    """
    tid = _tenant_uuid(tenant_id)
    typing = await comp_catalog.archimate_typing(session)  # {componenttype: {archimate_element, laag, aspect}}
    type_labels = await comp_catalog.labels(session, ComponentConfigDimensie.componenttype)

    # Verrijkingsmaps (read-only): open-blokkade-telling + afgeleide leverancier per component.
    blok_map = {
        r.component_id: r.aantal
        for r in (
            await session.execute(
                select(_blokkade.c.component_id, func.count().label("aantal"))
                # `status` is een PG-enum; via de lichtgewicht (untyped) kolom expliciet naar tekst
                # casten zodat de vergelijking met de string-literal een geldige operator heeft.
                .where(_blokkade.c.tenant_id == tid, cast(_blokkade.c.status, String) != "opgelost")
                .group_by(_blokkade.c.component_id)
            )
        ).all()
    }
    lev_map: dict[uuid.UUID, str] = {}
    for r in (
        await session.execute(
            select(Roltoewijzing.object_id, Partij.naam)
            .join(Partij, Partij.id == Roltoewijzing.partij_id)
            .where(
                Roltoewijzing.tenant_id == tid,
                Roltoewijzing.rol.in_(_LEVERANCIER_ROLLEN),
                Partij.aard == PartijAard.externe_partij,
            )
        )
    ).all():
        lev_map.setdefault(r.object_id, r.naam)  # eerste gevonden externe partij

    # Migratieplaatsing: eerste plateau per component via aggregation-lidmaatschap (bron=plateau →
    # doel=component); dispositie uit de relatie-kenmerken. Read-only.
    dispositie_labels = await rk_catalog.labels(session, RelatieKenmerkDimensie.dispositie)
    plateau_map: dict[uuid.UUID, dict] = {}
    for r in (
        await session.execute(
            select(Relatie.doel_id, Plateau.naam, Relatie.kenmerken)
            .join(Plateau, Plateau.id == Relatie.bron_id)
            .where(Relatie.tenant_id == tid, Relatie.relatietype == "aggregation")
        )
    ).all():
        disp = (r.kenmerken or {}).get("dispositie")
        plateau_map.setdefault(r.doel_id, {
            "naam": r.naam,
            "dispositie": rk_catalog.resolveer_een(disp, dispositie_labels) if disp else None,
        })

    nodes: list[LandschapsNode] = []
    component_ids: set[uuid.UUID] = set()
    contract_ids: set[uuid.UUID] = set()

    # ── Component-nodes (incl. applicaties) — typing uit de catalogus, lifecycle uit het profiel ──
    comp_rijen = (
        await session.execute(
            select(
                Component.id, Component.naam, Component.componenttype, Component.hostingmodel,
                _profiel.c.lifecycle_status.label("lifecycle_status"),
            )
            .outerjoin(_profiel, and_(_profiel.c.id == Component.id, _profiel.c.tenant_id == tid))
            .where(Component.tenant_id == tid)
        )
    ).all()
    for r in comp_rijen:
        component_ids.add(r.id)
        t = typing.get(r.componenttype, {})
        plaatsing = plateau_map.get(r.id, {})
        nodes.append(LandschapsNode(
            id=r.id, naam=r.naam, element_type=r.componenttype,
            laag=t.get("laag"), archimate_element=t.get("archimate_element"),
            lifecycle_status=_val(r.lifecycle_status),
            domein=comp_catalog.resolveer_een(r.componenttype, type_labels),
            leverancier_naam=lev_map.get(r.id),
            hosting_model=_val(r.hostingmodel),
            blokkades_open=blok_map.get(r.id, 0),
            plateau_naam=plaatsing.get("naam"),
            plateau_dispositie=plaatsing.get("dispositie"),
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
            select(Relatie.bron_id, Relatie.doel_id, Relatie.relatietype, Relatie.kenmerken).where(
                Relatie.tenant_id == tid
            )
        )
    ).all()
    # ADR-023a Fase 3 — flows per gericht paar (bron,doel) samentrekken tot één edge met `aantal`.
    # Volgorde-stabiel (eerste-gezien paar eerst); assignment/association blijven één-per-rij.
    flow_groepen: dict[tuple, list[dict]] = {}
    for r in rel_rijen:
        rt = _val(r.relatietype)
        if rt == "flow" and r.bron_id in component_ids and r.doel_id in component_ids:
            flow_groepen.setdefault((r.bron_id, r.doel_id), []).append(r.kenmerken or {})
        elif rt == "assignment" and r.doel_id in component_ids:
            # assignment = host → gehoste component (oriëntatie bron=host, doel=component).
            edges.append(LandschapsEdge(bron_id=r.bron_id, doel_id=r.doel_id,
                                        relatietype="assignment", label="draait op", ring="infrastructuur"))
        elif rt == "association" and r.doel_id in contract_ids:
            edges.append(LandschapsEdge(bron_id=r.bron_id, doel_id=r.doel_id,
                                        relatietype="association", label="valt onder", ring="contracten"))

    for (bron_id, doel_id), groep in flow_groepen.items():
        # Richting/protocol van de eerste flow; niet-uniform in de groep → fallback
        # ("bidirectioneel" resp. None) zodat een gemengde groep geen misleidende waarde toont.
        eerste = groep[0]
        r_eerste, p_eerste = eerste.get("richting"), eerste.get("protocol")
        richting = r_eerste if all(k.get("richting") == r_eerste for k in groep) else "bidirectioneel"
        protocol = p_eerste if all(k.get("protocol") == p_eerste for k in groep) else None
        edges.append(LandschapsEdge(bron_id=bron_id, doel_id=doel_id,
                                    relatietype="flow", label="koppeling", ring="applicaties",
                                    richting=richting, protocol=protocol, aantal=len(groep)))

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
