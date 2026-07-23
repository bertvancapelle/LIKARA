"""Service-laag — Landschapskaart (ADR-025, read-only grafprojectie).

Bouwt de volledige landschapsgraaf (nodes + edges) uit BESTAANDE data:
- nodes: componenten (incl. applicaties; met catalogus-typing + lifecycle-kleur), partijen, contracten;
- edges: vier "ringen" — applicaties (flow), infrastructuur (assignment), contracten (association),
  beheerorganisatie (roltoewijzing).

Puur read-only, afgeleid — geen schema/migratie. **Engine onaangeroerd**: dit bestand importeert
GEEN `lifecycle_service`/`herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade`/
`Checklistscore` en schrijft niets (geen `session.add`/`commit`/`flush`/`delete`). `lifecycle_status`
wordt read-only gelezen via een lichtgewicht tabel-constructie op `component_profiel` (LEFT JOIN),
bewust zónder de ORM-klasse te importeren (zie het engine-invariant in likara-domeinmodel §6).
"""
import uuid

from sqlalchemy import String, and_, cast, column, func, or_, select, table, true
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    Bedrijfsfunctie,
    Component,
    ComponentConfigDimensie,
    Contract,
    Gebruikersgroep,
    Organisatiegebruik,
    Partij,
    PartijAard,
    Plateau,
    Relatie,
    RelatieKenmerkDimensie,
    Roltoewijzing,
)
from schemas.landschapskaart import (
    LandschapsEdge,
    LandschapskaartResponse,
    LandschapsNode,
)
from services import actieve_vraag
from services import bedrijfsfunctie_service
from services import componentconfig_catalog as comp_catalog
from services import functievervulling_service
from services import gebruikersgroep_service
from services import relatiekenmerk_catalog as rk_catalog

# Lichtgewicht read-only handles op engine-tabellen — bewust GEEN ORM-import (de import-
# afwezigheidstest verbiedt `ComponentProfiel`/`Blokkade`). Alleen de gelezen kolommen.
_profiel = table("component_profiel", column("id"), column("tenant_id"), column("lifecycle_status"))
_blokkade = table("blokkade", column("component_id"), column("tenant_id"), column("status"), column("checklistscore_id"))

_RK_BEHEERROL = RelatieKenmerkDimensie.beheerrol
# Rollen waaruit we een "leverancier" afleiden voor de node-verrijking.
_LEVERANCIER_ROLLEN = ("technisch_beheer", "contractbeheer")


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _val(x):
    """Enum → .value; overige waarden ongewijzigd (uniforme stringificatie)."""
    return getattr(x, "value", x)


async def haal_grafdata_op(
    session: AsyncSession, tenant_id, *, component_ids=None, diepte: int = 1,
) -> LandschapskaartResponse:
    """Landschapsgraaf (nodes + edges) voor de tenant.

    `component_ids=None` (default) → de **volledige** graaf (back-compat: de GET-route + bestaande
    tests). Een lijst component-ids → **set-scoped**: alleen die set S + hun **directe buren** (1 hop)
    + de edges daartussen. De classificatie is overal `bron/doel ∈ id-set` (geen transitieve
    afleiding), dus set-scoping = de tenant-brede where-clausules een S-filter geven. Read-only;
    engine onaangeroerd. `diepte` is forward-compatibel (de stap-diepte wordt client-side toegepast).
    """
    tid = _tenant_uuid(tenant_id)
    typing = await comp_catalog.archimate_typing(session)  # {componenttype: {archimate_element, laag, aspect}}
    type_labels = await comp_catalog.labels(session, ComponentConfigDimensie.componenttype)

    # ── Set-scoping (alleen als component_ids gegeven): bouw `scope_ids` = S + alle 1-hop-buren +
    # de org-hiërarchie (hoort-bij) + eigenaar-organisaties. Daarna filtert `_sc(col)` elke query
    # op `col ∈ scope_ids`; bij `scope_ids=None` is `_sc` een no-op (volledige graaf). ──
    scope_ids: set[uuid.UUID] | None = None
    if component_ids is not None:
        S = {c if isinstance(c, uuid.UUID) else uuid.UUID(str(c)) for c in component_ids}
        scope_ids = set(S)
        # Directe buren via élke incidente relatie (beide endpoints meenemen).
        for r in (await session.execute(
            select(Relatie.bron_id, Relatie.doel_id)
            .where(Relatie.tenant_id == tid, or_(Relatie.bron_id.in_(S), Relatie.doel_id.in_(S)))
        )).all():
            scope_ids.add(r.bron_id); scope_ids.add(r.doel_id)
        # Rol-vervullende partijen op S (object∈S) — buren + bron voor de organisatiestructuur-ring.
        rol_holder_ids: set[uuid.UUID] = set()
        for r in (await session.execute(
            select(Roltoewijzing.partij_id).where(Roltoewijzing.tenant_id == tid, Roltoewijzing.object_id.in_(S))
        )).all():
            scope_ids.add(r.partij_id); rol_holder_ids.add(r.partij_id)
        # Eigenaar-organisaties van S (A3: "is eigendom van"-edge als 1-hop-context).
        for (oid,) in (await session.execute(
            select(Component.eigenaar_organisatie_id)
            .where(Component.tenant_id == tid, Component.id.in_(S), Component.eigenaar_organisatie_id.isnot(None))
        )).all():
            scope_ids.add(oid)
        # LI033b — gebruiker-organisaties van S (grof feit "organisatie gebruikt applicatie"): de org-node
        # moet meekomen zodat de afgeleide "gebruikt"-edge (org → applicatie) niet-dangling is. Spiegel van
        # de eigenaar-scope-add hierboven.
        for (oid,) in (await session.execute(
            select(Organisatiegebruik.organisatie_id)
            .where(Organisatiegebruik.tenant_id == tid, Organisatiegebruik.applicatie_id.in_(S))
        )).all():
            scope_ids.add(oid)
        # Organisatiestructuur-hiërarchie: afdeling + organisatie van de rol-personen (+ de
        # organisatie ván die afdeling), zodat de hoort-bij-keten persoon→afdeling→organisatie sluit.
        if rol_holder_ids:
            afd_ids: set[uuid.UUID] = set()
            for p in (await session.execute(
                select(Partij.id, Partij.aard, Partij.organisatie_id, Partij.afdeling_id)
                .where(Partij.tenant_id == tid, Partij.id.in_(rol_holder_ids))
            )).all():
                if p.aard == PartijAard.persoon:
                    if p.afdeling_id is not None:
                        scope_ids.add(p.afdeling_id); afd_ids.add(p.afdeling_id)
                    if p.organisatie_id is not None:
                        scope_ids.add(p.organisatie_id)
            if afd_ids:
                for (oid,) in (await session.execute(
                    select(Partij.organisatie_id)
                    .where(Partij.tenant_id == tid, Partij.id.in_(afd_ids), Partij.organisatie_id.isnot(None))
                )).all():
                    scope_ids.add(oid)
        # LI034 slice 3 — leverancier-partijen van contracten-in-scope (P4 scope-add, spiegel van de
        # eigenaar-/gebruikt-scope-add): het contract komt via de association-relatie al in scope, maar
        # `contract.leverancier_id` is een directe FK — de leverancier-partij komt NIET vanzelf mee. Voeg
        # haar toe zodat de afgeleide contract→leverancier-edge (hieronder) niet dangling wordt.
        for (lid,) in (await session.execute(
            select(Contract.leverancier_id)
            .where(Contract.tenant_id == tid, Contract.id.in_(scope_ids), Contract.leverancier_id.isnot(None))
        )).all():
            scope_ids.add(lid)

    def _sc(col):
        """Scope-filter: `col ∈ scope_ids` bij set-scoping, anders altijd-waar (volledige graaf)."""
        return col.in_(scope_ids) if scope_ids is not None else true()

    # Verrijkingsmaps (read-only): open-blokkade-telling + afgeleide leverancier per component.
    blok_map = {
        r.component_id: r.aantal
        for r in (
            await session.execute(
                select(_blokkade.c.component_id, func.count().label("aantal"))
                # `status` is een PG-enum; via de lichtgewicht (untyped) kolom expliciet naar tekst
                # casten zodat de vergelijking met de string-literal een geldige operator heeft.
                # LI050: knelpunten van uitgezette vragen tellen niet mee — anders zegt de
                # kaart-badge "1 open" waar de status net terecht groen werd (gedeelde afleiding).
                .where(_blokkade.c.tenant_id == tid, cast(_blokkade.c.status, String) != "opgelost",
                       actieve_vraag.blokkade_telt_mee(_blokkade.c.checklistscore_id),
                       _sc(_blokkade.c.component_id))
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
                _sc(Roltoewijzing.object_id),
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
            .where(Relatie.tenant_id == tid, Relatie.relatietype == "association", _sc(Relatie.bron_id))
            .order_by(Relatie.id)
        )
    ).all():
        lev_map.setdefault(r.bron_id, (r.partij_id, r.naam))

    # Plateau-lidmaatschap als context (ADR-046): ÁLLE plateaus per component, alfabetisch
    # samengevoegd — deterministisch (meervoud wordt getoond, nooit stil opgelost). De
    # vroegere "eerste plateau wint"-setdefault (geen ORDER BY → niet-deterministisch) en
    # het dispositie-kenmerk zijn vervallen; het uitfaseer-signaal is nu `Component.levensfase`.
    _plateau_namen: dict[uuid.UUID, set[str]] = {}
    for r in (
        await session.execute(
            select(Relatie.doel_id, Plateau.naam)
            .join(Plateau, Plateau.id == Relatie.bron_id)
            .where(Relatie.tenant_id == tid, Relatie.relatietype == "aggregation", _sc(Relatie.doel_id))
        )
    ).all():
        _plateau_namen.setdefault(r.doel_id, set()).add(r.naam)
    plateau_map: dict[uuid.UUID, str] = {
        cid: " · ".join(sorted(namen)) for cid, namen in _plateau_namen.items()
    }

    nodes: list[LandschapsNode] = []
    component_ids: set[uuid.UUID] = set()
    contract_ids: set[uuid.UUID] = set()

    # ── Component-nodes (incl. applicaties) — typing uit de catalogus, lifecycle uit het profiel ──
    comp_rijen = (
        await session.execute(
            select(
                Component.id, Component.naam, Component.componenttype, Component.hostingmodel,
                Component.eigenaar_organisatie_id,
                # ADR-028 — classificatie read-only mee (voor filter + randbehandeling).
                Component.componentrol,
                Component.biv_beschikbaarheid, Component.biv_integriteit, Component.biv_vertrouwelijkheid,
                # ADR-046 — levensfase (vervangt de plateau-dispositie als kaart-signaal).
                Component.levensfase,
                _profiel.c.lifecycle_status.label("lifecycle_status"),
            )
            .outerjoin(_profiel, and_(_profiel.c.id == Component.id, _profiel.c.tenant_id == tid))
            .where(Component.tenant_id == tid, _sc(Component.id))
        )
    ).all()
    # ADR-024 organisatie-scope: per component de gebruik-afleiding na de relatie-pass invullen.
    comp_node: dict[uuid.UUID, LandschapsNode] = {}
    for r in comp_rijen:
        component_ids.add(r.id)
        t = typing.get(r.componenttype, {})
        node = LandschapsNode(
            id=r.id, naam=r.naam, element_type=r.componenttype,
            laag=t.get("laag"), archimate_element=t.get("archimate_element"),
            lifecycle_status=_val(r.lifecycle_status),
            domein=comp_catalog.resolveer_een(r.componenttype, type_labels),
            leverancier_naam=lev_map.get(r.id, (None, None))[1],
            leverancier_id=lev_map.get(r.id, (None, None))[0],
            hosting_model=_val(r.hostingmodel),
            # ADR-028 — classificatie (registratief; engine onaangeroerd).
            componentrol=r.componentrol,
            biv_beschikbaarheid=r.biv_beschikbaarheid,
            biv_integriteit=r.biv_integriteit,
            biv_vertrouwelijkheid=r.biv_vertrouwelijkheid,
            # ADR-046 — levensfase op de node (None = nog niet vastgelegd).
            levensfase=_val(r.levensfase),
            blokkades_open=blok_map.get(r.id, 0),
            plateau_naam=plateau_map.get(r.id),
            # Bezit/aanbieden: het bestaande directe veld (None = component zonder eigenaar → buiten scope).
            eigenaar_organisatie_id=r.eigenaar_organisatie_id,
        )
        nodes.append(node)
        comp_node[r.id] = node

    # ── Partij-nodes — business-laag, aard als `soort` ──
    # `organisatie_id`/`afdeling_id` (ADR-024 "hoort bij") worden meegelezen voor de
    # Organisatiestructuur-ring (read-only; gebruikt onder bij ring 5). Geen extra query.
    partij_rijen = (
        await session.execute(
            select(
                Partij.id, Partij.naam, Partij.aard, Partij.organisatie_id, Partij.afdeling_id
            ).where(Partij.tenant_id == tid, _sc(Partij.id))
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
            select(Contract.id, Contract.contractnaam).where(Contract.tenant_id == tid, _sc(Contract.id))
        )
    ).all()
    for r in contract_rijen:
        contract_ids.add(r.id)
        nodes.append(LandschapsNode(
            id=r.id, naam=r.contractnaam, element_type="contract", laag="business",
            archimate_element="contract",
        ))

    # ── Gebruikersgroep-nodes (ADR-031, ring 'gebruikers') — business actor/role ──
    # Naam (ADR-036 stap D): "afdeling — organisatie" (bv. "Burgerzaken — Tiel"); terugvallen op
    # alleen afdeling / alleen organisatie / generiek. Ledental uit `aantal_gebruikers`.
    # `organisatie_id` reist mee voor de client-side "groepeer per organisatie"-toggle.
    partij_naam = {r.id: r.naam for r in partij_rijen}
    gebruikersgroep_ids: set[uuid.UUID] = set()
    # ADR-036 — de organisatie leeft op het grove feit; LEFT JOIN het feit via `gebruik_id`
    # (gedrag identiek aan de oude `organisatie_id`-kolom: org-loze groep → NULL).
    # ADR-036a — de afdeling is een `organisatie_eenheid`-partij; join haar direct voor de naam
    # (de gescoopte `partij_naam`-map dekt de afdeling-partij niet noodzakelijk).
    gg_rijen = (
        await session.execute(
            select(
                Gebruikersgroep.id, Organisatiegebruik.organisatie_id.label("organisatie_id"),
                Partij.naam.label("afdeling_naam"), Gebruikersgroep.aantal_gebruikers,
            )
            .outerjoin(
                Organisatiegebruik,
                and_(Organisatiegebruik.id == Gebruikersgroep.gebruik_id, Organisatiegebruik.tenant_id == tid),
            )
            .outerjoin(Partij, and_(Partij.id == Gebruikersgroep.afdeling_id, Partij.tenant_id == tid))
            .where(Gebruikersgroep.tenant_id == tid, _sc(Gebruikersgroep.id))
        )
    ).all()
    for r in gg_rijen:
        gebruikersgroep_ids.add(r.id)
        naam = gebruikersgroep_service.identiteit(r.afdeling_naam, partij_naam.get(r.organisatie_id))
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
                Relatie.tenant_id == tid, _sc(Relatie.bron_id), _sc(Relatie.doel_id)
            )
        )
    ).all()
    # ADR-023a Fase 3 — flows per gericht paar (bron,doel) samentrekken tot één edge met `aantal`.
    # Volgorde-stabiel (eerste-gezien paar eerst); assignment/association blijven één-per-rij.
    flow_groepen: dict[tuple, list[dict]] = {}
    # ADR-036 stap B — "gebruikt door organisatie(s)" = de grove gebruiksfeiten (organisatiegebruik)
    # op de applicatie, NIET meer afgeleid uit de groepen. Elke organisatie precies één keer
    # (UNIQUE(tenant, org, app)); een grof-only feit (organisatie zónder afdeling) verschijnt óók.
    # De organisaties van afdelingen-mét-organisatie zitten per single-source-of-truth (ADR-036) al
    # in deze grove feiten → geen dubbeltelling. Org-loze groepen tellen NIET mee (aparte weergave).
    comp_gebruik_orgs: dict[uuid.UUID, set[uuid.UUID]] = {}
    for r_og in (
        await session.execute(
            select(Organisatiegebruik.applicatie_id, Organisatiegebruik.organisatie_id).where(
                Organisatiegebruik.tenant_id == tid, _sc(Organisatiegebruik.applicatie_id)
            )
        )
    ).all():
        comp_gebruik_orgs.setdefault(r_og.applicatie_id, set()).add(r_og.organisatie_id)
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
            # ADR-036 stap B — de org-toerekening loopt via de grove feiten (hierboven).
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

    # ADR-036 stap B — de afgeleide gebruik-data per component-node invullen (read-only): organisaties
    # uit de grove feiten (ADR-038: geen org-loze-flag meer — een groep heeft altijd een organisatie).
    for cid, node in comp_node.items():
        node.gebruikt_door_organisaties = sorted(comp_gebruik_orgs.get(cid, set()), key=str)

    # ── Ring 4 — beheerorganisatie uit de roltoewijzingen (label = rol-naam) ──
    rol_labels = await rk_catalog.labels(session, _RK_BEHEERROL)
    rt_rijen = (
        await session.execute(
            select(Roltoewijzing.partij_id, Roltoewijzing.object_id, Roltoewijzing.rol).where(
                Roltoewijzing.tenant_id == tid, _sc(Roltoewijzing.object_id), _sc(Roltoewijzing.partij_id)
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

    # ── Ring 6 — Eigenaar ("is eigendom van") ──
    # Read-only projectie van het bestaande `Component.eigenaar_organisatie_id`-veld als edge
    # organisatie → component (géén nieuwe relatie-registratie). CONTEXT, geen impact: bewust NIET
    # in IMPACT_RINGEN (frontend). Dit dekt tevens het geparkeerde "scopebalk-tekent-organisaties"-
    # spoor af (zelfde "is eigendom van"-projectie). Alleen als de eigenaar-organisatie als knoop
    # meekomt (in `partij_info` → emitted), zodat de edge geen dangling endpoint krijgt.
    for cid, node in comp_node.items():
        oid = node.eigenaar_organisatie_id
        if oid is not None and oid in partij_info:
            edges.append(LandschapsEdge(
                bron_id=oid, doel_id=cid, relatietype="eigenaar",
                label="is eigendom van", ring="eigenaar",
            ))

    # ── Ring 7 — Gebruikt ("organisatie gebruikt applicatie", LI033b) ──
    # Read-only projectie van het grove feit `organisatiegebruik` als edge organisatie → applicatie —
    # spiegel van de eigenaar-edge, géén nieuwe relatie-registratie. NAAST de bestaande node-projectie
    # `gebruikt_door_organisaties`: dit maakt het gebruik óók als LIJN zichtbaar. Bezit+gebruik levert
    # bewust TWEE lijnen (eigenaar + gebruikt) — niet onderdrukken. Alleen als beide endpoints als
    # knoop meekomen (org in `partij_info`, applicatie in `comp_node`) → geen dangling endpoint.
    for r_og in (
        await session.execute(
            select(Organisatiegebruik.organisatie_id, Organisatiegebruik.applicatie_id).where(
                Organisatiegebruik.tenant_id == tid, _sc(Organisatiegebruik.applicatie_id)
            )
        )
    ).all():
        if r_og.organisatie_id in partij_info and r_og.applicatie_id in comp_node:
            edges.append(LandschapsEdge(
                bron_id=r_og.organisatie_id, doel_id=r_og.applicatie_id,
                relatietype="gebruikt", label="gebruikt", ring="gebruikt",
            ))

    # ── Ring — Contract → leverancier (LI034 slice 3) ──
    # Read-only projectie van het bestaande feit `contract.leverancier_id` als edge contract →
    # leverancier — spiegel van de eigenaar-/gebruikt-edge, géén nieuwe relatie-registratie. INGEBED in
    # de contracten-ring (ring="contracten"), zodat de hele keten component→contract→leverancier samen
    # togglet en op de praatplaat default meekomt. Zo wordt de leverancier niet alleen node-metadata
    # (`leverancier_naam`) maar óók een zichtbare relatie. Dangling-guard: alleen als BEIDE endpoints als
    # knoop meekomen (contract in `contract_ids`, leverancier-partij in `partij_info`); de leverancier-
    # partij komt via de scope-add hierboven in de subgraaf-scope.
    for r in (
        await session.execute(
            select(Contract.id, Contract.leverancier_id).where(
                Contract.tenant_id == tid, Contract.leverancier_id.isnot(None), _sc(Contract.id)
            )
        )
    ).all():
        if r.id in contract_ids and r.leverancier_id in partij_info:
            edges.append(LandschapsEdge(
                bron_id=r.id, doel_id=r.leverancier_id,
                relatietype="leverancier", label="geleverd door", ring="contracten",
            ))

    # ── Ring — Bedrijfsfuncties (ADR-043 gate 4, G7/G8): plek-projectie, path-expansie ──
    # De proceslaan is HIERMEE VERVANGEN (ADR-043 G1). Read-only VERRIJKING rond de in-beeld
    # componenten: welke bedrijfsfunctie-PLEK draagt welk systeem. Leest UITSLUITEND de gedeelde
    # leesregel — `dekking_overzicht` (wie draagt de plek, MÉT verdringing: een verdrongen grof
    # antwoord staat niet in `componenten` en wordt dus nooit als "gedekt" getekend — de invariant,
    # ADR-049 besluit 5) en `plek_standen` (de vier standen die de gap-cue voeden, omhoog — G8).
    # NOOIT een ruwe functievervulling-query hier (bronscan-test borgt dat).
    # Path-expansie (G7): een functie/voorouder op meerdere plekken verschijnt PER PAD als eigen
    # plek-knoop (deterministische uuid5 van het pad-namenspoor) — de kaart blijft een schone boom
    # (hoogte=diepte). Twee exemplaren van dezelfde plek dragen dezelfde stand (één plek-waarheid).
    # Geen scope_ids-verbreding (functies zijn verrijking, zoals plateau-info), engine onaangeroerd.
    dekking = await functievervulling_service.dekking_overzicht(session, tid)
    if dekking:
        standen = await functievervulling_service.plek_standen(session, tid)
        stand_van = {(p["functie_id"], p["ouder_functie_id"]): p["stand"] for p in standen["plekken"]}
        # De plaatsings-hiërarchie (ADR-044: de boom leeft in aggregation-plaatsingen). Canonieke
        # structuurbron — dezelfde die de leeslaag intern gebruikt; geen tweede definitie.
        paren = await bedrijfsfunctie_service._plaatsings_paren(session, tid)  # (ouder, kind)
        ouders_van: dict[uuid.UUID, list[uuid.UUID]] = {}
        for ouder, kind in paren:
            ouders_van.setdefault(kind, []).append(ouder)

        # Dangling-guard (spiegel van de oude proces-projectie): een plek telt alleen als een
        # IN-BEELD component haar draagt — het antwoord NÁ verdringing (nooit een verdrongen
        # antwoord). Grof dekt elke plek van de functie; fijn alleen zijn eigen plek — beide komen
        # als aparte dekking-entries mee.
        dragers_op_plek: dict[tuple[uuid.UUID, uuid.UUID | None], list[uuid.UUID]] = {}
        touched: set[uuid.UUID] = set()
        for d in dekking:
            in_beeld = [c["component_id"] for c in d["componenten"] if c["component_id"] in comp_node]
            if in_beeld:
                dragers_op_plek[(d["functie_id"], d["ouder_functie_id"])] = in_beeld
                touched.add(d["functie_id"])

        if touched:
            # Naam-resolutie voor alle betrokken functies (verrijking, geen leesregel).
            betrokken = set(touched)
            for kind, ouders in ouders_van.items():
                betrokken.add(kind)
                betrokken.update(ouders)
            naam_van: dict[uuid.UUID, str] = {}
            for r in (await session.execute(
                select(Bedrijfsfunctie.id, Bedrijfsfunctie.naam)
                .where(Bedrijfsfunctie.tenant_id == tid, Bedrijfsfunctie.id.in_(betrokken))
            )).all():
                naam_van[r.id] = r.naam

            # Path-expansie: alle wortel→touched-functie-paden (DAG, cyclus-veilig via `bezocht`).
            # Elke knoop op zo'n pad wordt een plek-knoop in díé context; de context = het pad.
            paden: list[list[uuid.UUID]] = []

            def _paden_naar(functie: uuid.UUID, staart: list[uuid.UUID], bezocht: frozenset) -> None:
                ouders = [o for o in ouders_van.get(functie, []) if o not in bezocht]
                if not ouders:
                    paden.append([functie, *staart])  # wortel (of cyclus-stop) → compleet pad
                    return
                for o in sorted(ouders, key=str):
                    _paden_naar(o, [functie, *staart], bezocht | {functie})

            for tf in sorted(touched, key=str):
                _paden_naar(tf, [], frozenset())

            _NS = uuid.UUID("00000000-0000-0000-0000-0000000000f4")  # vaste namespace voor plek-uuid5

            def _plek_id(prefix) -> uuid.UUID:
                return uuid.uuid5(_NS, ">".join(str(x) for x in prefix))

            geplaatst: set[tuple] = set()  # ontdubbel gedeelde pad-prefixen tussen paden
            for pad in paden:
                for i, functie in enumerate(pad):
                    prefix = tuple(pad[: i + 1])
                    if prefix in geplaatst:
                        continue
                    geplaatst.add(prefix)
                    ouder = pad[i - 1] if i > 0 else None
                    nodes.append(LandschapsNode(
                        id=_plek_id(prefix),
                        naam=naam_van.get(functie, f"functie {str(functie)[:8]}"),
                        element_type="bedrijfsfunctie", laag="business",
                        archimate_element="business_function",
                        functie_id=functie, plek_stand=stand_van.get((functie, ouder)),
                    ))
                    if i > 0:
                        edges.append(LandschapsEdge(
                            bron_id=_plek_id(prefix), doel_id=_plek_id(pad[:i]),
                            relatietype="functie_plaatsing", label="onderdeel van",
                            ring="bedrijfsfuncties",
                        ))
                    # Systeem→plek-edge alleen waar een in-beeld component déze plek draagt (het
                    # antwoord ná verdringing — nooit een verdrongen antwoord; de invariant).
                    for cid in dragers_op_plek.get((functie, ouder), []):
                        edges.append(LandschapsEdge(
                            bron_id=cid, doel_id=_plek_id(prefix),
                            relatietype="functievervulling", label="ondersteunt",
                            ring="bedrijfsfuncties",
                        ))

    return LandschapskaartResponse(nodes=nodes, edges=edges)
