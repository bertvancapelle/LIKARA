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
    Gebruikersgroep,
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
    # (partij_id, naam) van de eerste gevonden externe partij — id voor eenduidige UI-filtering
    # (gelijknamige partijen), naam voor weergave.
    lev_map: dict[uuid.UUID, tuple[uuid.UUID, str]] = {}
    for r in (
        await session.execute(
            select(Roltoewijzing.object_id, Partij.id.label("partij_id"), Partij.naam)
            .join(Partij, Partij.id == Roltoewijzing.partij_id)
            .where(
                Roltoewijzing.tenant_id == tid,
                Roltoewijzing.rol.in_(_LEVERANCIER_ROLLEN),
                Partij.aard == PartijAard.externe_partij,
            )
        )
    ).all():
        lev_map.setdefault(r.object_id, (r.partij_id, r.naam))  # eerste gevonden externe partij

    # LI019 — leverancier óók afleiden via de contract-keten: component → association-relatie →
    # contract → contract.leverancier_id. Vult de gaten waar geen directe roltoewijzing-leverancier
    # bestaat (setdefault behoudt de roltoewijzing-leverancier waar die er wél is). Deterministisch
    # op relatie-id (eerste contract wint) zodat een component met meerdere contracten stabiel is.
    for r in (
        await session.execute(
            select(Relatie.bron_id, Contract.leverancier_id.label("partij_id"), Partij.naam)
            .join(Contract, Contract.id == Relatie.doel_id)
            .join(Partij, Partij.id == Contract.leverancier_id)
            .where(Relatie.tenant_id == tid, Relatie.relatietype == "association")
            .order_by(Relatie.id)
        )
    ).all():
        lev_map.setdefault(r.bron_id, (r.partij_id, r.naam))

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
            leverancier_naam=lev_map.get(r.id, (None, None))[1],
            leverancier_id=lev_map.get(r.id, (None, None))[0],
            hosting_model=_val(r.hostingmodel),
            blokkades_open=blok_map.get(r.id, 0),
            plateau_naam=plaatsing.get("naam"),
            plateau_dispositie=plaatsing.get("dispositie"),
        ))

    # ── Partij-nodes — business-laag, aard als `soort` ──
    # `organisatie_id`/`afdeling_id` (ADR-024 "hoort bij") worden meegelezen voor de
    # Organisatiestructuur-ring (read-only; gebruikt onder bij ring 5). Geen extra query.
    partij_rijen = (
        await session.execute(
            select(
                Partij.id, Partij.naam, Partij.aard, Partij.organisatie_id, Partij.afdeling_id
            ).where(Partij.tenant_id == tid)
        )
    ).all()
    partij_info = {r.id: r for r in partij_rijen}  # id → rij (aard + lidmaatschap-FK's)
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

    # ── Gebruikersgroep-nodes (ADR-031, ring 'gebruikers') — business actor/role ──
    # Naam: afdeling (bv. "Burgers") of anders de organisatie-naam; ledental uit `aantal_gebruikers`.
    # `organisatie_id` reist mee voor de client-side "groepeer per organisatie"-toggle.
    partij_naam = {r.id: r.naam for r in partij_rijen}
    gebruikersgroep_ids: set[uuid.UUID] = set()
    gg_rijen = (
        await session.execute(
            select(
                Gebruikersgroep.id, Gebruikersgroep.organisatie_id,
                Gebruikersgroep.afdeling, Gebruikersgroep.aantal_gebruikers,
            ).where(Gebruikersgroep.tenant_id == tid)
        )
    ).all()
    for r in gg_rijen:
        gebruikersgroep_ids.add(r.id)
        naam = r.afdeling or partij_naam.get(r.organisatie_id) or "Gebruikersgroep"
        nodes.append(LandschapsNode(
            id=r.id, naam=naam, element_type="gebruikersgroep", laag="business",
            archimate_element="business_role",
            organisatie_id=r.organisatie_id, aantal_leden=r.aantal_gebruikers or 0,
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
        elif rt == "serving" and r.bron_id in component_ids and r.doel_id in gebruikersgroep_ids:
            # ADR-031 — applicatie → gebruikersgroep (wie gebruikt deze applicatie).
            edges.append(LandschapsEdge(bron_id=r.bron_id, doel_id=r.doel_id,
                                        relatietype="serving", label="gebruikt door", ring="gebruikers"))
        elif rt == "aggregation" and r.bron_id in component_ids and r.doel_id in component_ids:
            # ADR-033 1b — samenstelling: component↔component aggregatie (bron=geheel → doel=onderdeel).
            # Bewust géén afleiding (ADR-023 besluit 7): exact de geregistreerde structuurrelatie, dezelfde
            # bron die component_service.structuur_overzicht/impact_analyse leest. Plateau-lidmaatschap
            # (bron=plateau) valt buiten deze guard (bron is geen component) en blijft uitsluitend de
            # migratieplaatsing-verrijking (plateau_map) voeden.
            edges.append(LandschapsEdge(bron_id=r.bron_id, doel_id=r.doel_id,
                                        relatietype="aggregation", label="bestaat uit", ring="samenstelling"))

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

    # ── Ring 5 — Organisatiestructuur (ADR-024 "hoort bij") ──
    # Read-only projectie van de geregistreerde lidmaatschap-FK's (partij.organisatie_id/
    # afdeling_id) — géén afleiding (ADR-023 besluit 7), exact de geregistreerde keten.
    # CONTEXT, geen impact: bewust NIET in de impact-relaties (zie IMPACT_RINGEN frontend).
    # Afbakening: ALLEEN personen-die-een-rol-vervullen (een roltoewijzing als bron), van
    # ONDERAF opgebouwd — een afdeling/organisatie verschijnt uitsluitend via zo'n persoon
    # (geen lege takken). Het "persoon direct onder de organisatie"-geval (afdeling_id NULL)
    # levert een directe lijn persoon → organisatie.
    # ONTWERP-UITGANGSPUNT (ADR-024): "persoon" betreft hier de beheer-/verantwoordelijke-
    # personen (rol-vervullers). Worden er ooit échte eindgebruikers toegevoegd (potentieel
    # honderden), dan krijgen die een aparte, filterbare aard/soort (bv. "applicatiegebruiker")
    # die STRUCTUREEL buiten deze ring valt — als onderscheid in de aard/soort, niet via een
    # losse conventie. Die categorie bestaat nog niet en wordt hier NIET gebouwd.
    rol_partij_ids = {r.partij_id for r in rt_rijen}
    gezien_os: set[tuple] = set()

    def _os_edge(bron, doel):
        if bron is None or doel is None or (bron, doel) in gezien_os:
            return
        gezien_os.add((bron, doel))
        edges.append(LandschapsEdge(
            bron_id=bron, doel_id=doel, relatietype="hoort_bij",
            label="hoort bij", ring="organisatiestructuur",
        ))

    for pid in rol_partij_ids:
        info = partij_info.get(pid)
        if info is None or info.aard != PartijAard.persoon:
            continue  # uitsluitend personen-met-rol
        if info.afdeling_id is not None:
            _os_edge(pid, info.afdeling_id)  # persoon → afdeling
            afd = partij_info.get(info.afdeling_id)
            if afd is not None:
                _os_edge(info.afdeling_id, afd.organisatie_id)  # afdeling → organisatie
        elif info.organisatie_id is not None:
            _os_edge(pid, info.organisatie_id)  # persoon → organisatie (afdeling onbekend)

    return LandschapskaartResponse(nodes=nodes, edges=edges)
