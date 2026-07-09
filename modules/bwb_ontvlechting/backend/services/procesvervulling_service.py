"""Service-laag — procesvervulling: "component X vervult applicatiefunctie Y in proces Z"
(ADR-042 slice 3, het roltoewijzing-recept).

Tenant-scoped (RLS + expliciete `tenant_id`-filter). Validatie vooraf (fail-secure,
404 no-leak buiten de tenant):
- component-kant = een bestaand `component`-element — élk componenttype, component-breed
  (ADR-042 besluit 3) ⇒ anders 422 `ONGELDIG_COMPONENT`;
- proces-kant = een bestaand `proces`-element ⇒ anders 422 `ONGELDIG_PROCES`;
- `applicatiefunctie` = actieve catalogus-optie ⇒ anders 422 `ONGELDIGE_APPLICATIEFUNCTIE`;
- dubbel tripel ⇒ 409 `VERVULLING_BESTAAT` (pre-check; de UNIQUE is de DB-backstop).

Leesbaar in beide richtingen (per proces de componenten, per component de processen) met
naam-verrijking via joins + één label-map per lijst (geen N+1). Puur registratief — geen
engine-import (score blijft de enige lifecycle-driver; ADR-042-invariant).

Slice 5 (roll-up-inzicht) voegt twee PURE LEESPADEN toe — geen opslag, geen mutatie:
- `rollup_voor_proces`: de koppelregels uit de volledige subboom van een proces
  (cyclus-veilig via `proces_service.subboom`), per regel mét herkomst-proces + pad;
- `processen_voor_organisatie`: welke processen steunen op de componenten van een
  organisatie (eigendom + geregistreerd gebruik samengenomen, dedupe per proces) —
  een AFGELEID beeld, er wordt niets geregistreerd.
"""
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.models import (
    Component,
    ComponentConfigDimensie,
    Element,
    ElementType,
    Organisatiegebruik,
    Partij,
    Proces,
    Procesvervulling,
)
from services import applicatiefunctie_catalog as af_catalog
from services import componentconfig_catalog as cc_catalog
from services import proces_service
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict

_ENTITEIT = "procesvervulling"


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def _element_type(session: AsyncSession, tid: uuid.UUID, element_id) -> str | None:
    rij = (
        await session.execute(
            select(Element.element_type).where(Element.tenant_id == tid, Element.id == element_id)
        )
    ).scalar_one_or_none()
    return getattr(rij, "value", rij) if rij is not None else None


async def actieve_functies(session: AsyncSession) -> list[dict]:
    """Actieve applicatiefunctie-opties voor het keuze-dropdown."""
    return await af_catalog.actieve_opties(session)


async def maak_aan(
    session: AsyncSession, tenant_id, component_id, proces_id, applicatiefunctie: str,
    toelichting: str | None = None,
) -> dict:
    tid = _tenant_uuid(tenant_id)
    # Component-kant: een bestaand component-element — élk componenttype (component-breed).
    if await _element_type(session, tid, component_id) != ElementType.component.value:
        raise OngeldigeRegistratie(
            "ONGELDIG_COMPONENT", "De component-kant moet een bestaand component zijn."
        )
    # Proces-kant: een bestaand proces-element.
    if await _element_type(session, tid, proces_id) != ElementType.proces.value:
        raise OngeldigeRegistratie(
            "ONGELDIG_PROCES", "De proces-kant moet een bestaand proces zijn."
        )
    await af_catalog.valideer_functie(session, applicatiefunctie)
    # Dubbel tripel ⇒ 409 (pre-check; de UNIQUE-constraint is de DB-backstop).
    bestaat = (
        await session.execute(
            select(Procesvervulling.id).where(
                Procesvervulling.tenant_id == tid,
                Procesvervulling.component_id == component_id,
                Procesvervulling.proces_id == proces_id,
                Procesvervulling.applicatiefunctie == applicatiefunctie,
            )
        )
    ).scalar_one_or_none()
    if bestaat is not None:
        raise RegistratieConflict(
            "VERVULLING_BESTAAT",
            "Dit component vervult deze applicatiefunctie al in dit proces.",
        )
    obj = Procesvervulling(
        tenant_id=tid, component_id=component_id, proces_id=proces_id,
        applicatiefunctie=applicatiefunctie, toelichting=toelichting,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return await _lees_een(session, obj)


async def _haal_op(session: AsyncSession, tid: uuid.UUID, vervulling_id) -> Procesvervulling:
    obj = (
        await session.execute(
            select(Procesvervulling).where(
                Procesvervulling.id == vervulling_id, Procesvervulling.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, vervulling_id)  # 404 no-leak kruis-tenant
    return obj


async def werk_bij(session: AsyncSession, tenant_id, vervulling_id, data) -> dict:
    """Wijzig de KENMERK-velden van een koppelregel (applicatiefunctie + toelichting);
    component/proces zijn de ankers van het feit en blijven onwijzigbaar (schema weert
    ze al). Gewone ORM-update (setattr + commit) → de centrale audit logt automatisch
    per-veld oud→nieuw. Zelfde validaties als bij aanmaken: onbekende/inactieve functie
    ⇒ 422; wijziging naar een al bestaand tripel ⇒ 409 `VERVULLING_BESTAAT`."""
    tid = _tenant_uuid(tenant_id)
    obj = await _haal_op(session, tid, vervulling_id)
    velden = data.model_dump(exclude_unset=True)
    nieuwe_functie = velden.get("applicatiefunctie")
    if nieuwe_functie is not None and nieuwe_functie != obj.applicatiefunctie:
        await af_catalog.valideer_functie(session, nieuwe_functie)
        # Het gewijzigde tripel mag niet al bestaan (pre-check; de UNIQUE is de backstop).
        bestaat = (
            await session.execute(
                select(Procesvervulling.id).where(
                    Procesvervulling.tenant_id == tid,
                    Procesvervulling.component_id == obj.component_id,
                    Procesvervulling.proces_id == obj.proces_id,
                    Procesvervulling.applicatiefunctie == nieuwe_functie,
                    Procesvervulling.id != obj.id,
                )
            )
        ).scalar_one_or_none()
        if bestaat is not None:
            raise RegistratieConflict(
                "VERVULLING_BESTAAT",
                "Dit component vervult deze applicatiefunctie al in dit proces.",
            )
    for veld, waarde in velden.items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return await _lees_een(session, obj)


async def verwijder(session: AsyncSession, tenant_id, vervulling_id) -> None:
    tid = _tenant_uuid(tenant_id)
    obj = await _haal_op(session, tid, vervulling_id)
    await session.delete(obj)
    await session.commit()


async def _lees_een(session: AsyncSession, obj: Procesvervulling) -> dict:
    """Volledige read van één regel (na aanmaak): beide zijden verrijkt."""
    tid = obj.tenant_id
    af_labels = await af_catalog.labels(session)
    comp = (
        await session.execute(
            select(Component.naam, Component.componenttype).where(
                Component.id == obj.component_id, Component.tenant_id == tid
            )
        )
    ).one_or_none()
    type_labels = await cc_catalog.labels(session, ComponentConfigDimensie.componenttype)
    ouder = aliased(Proces)
    pr = (
        await session.execute(
            select(Proces.naam, ouder.naam.label("ouder_naam"))
            .outerjoin(ouder, (ouder.id == Proces.ouder_id) & (ouder.tenant_id == tid))
            .where(Proces.id == obj.proces_id, Proces.tenant_id == tid)
        )
    ).one_or_none()
    return {
        "vervulling_id": obj.id,
        "applicatiefunctie": obj.applicatiefunctie,
        "applicatiefunctie_label": af_catalog.resolveer_een(obj.applicatiefunctie, af_labels),
        "toelichting": obj.toelichting,
        "component_id": obj.component_id,
        "component_naam": comp.naam if comp else None,
        "componenttype": comp.componenttype if comp else None,
        "componenttype_label": cc_catalog.resolveer_een(comp.componenttype, type_labels) if comp else None,
        "proces_id": obj.proces_id,
        "proces_naam": pr.naam if pr else None,
        "proces_ouder_naam": pr.ouder_naam if pr else None,
    }


async def lijst_voor_proces(session: AsyncSession, tenant_id, proces_id) -> list[dict]:
    """"Componenten in dit proces": de koppelregels van één proces, verrijkt met
    component-naam + type(-label) + functie-label; gesorteerd op component-naam dan
    functie. Onbekend proces binnen de tenant ⇒ 404 (no-leak)."""
    tid = _tenant_uuid(tenant_id)
    if await _element_type(session, tid, proces_id) != ElementType.proces.value:
        raise NietGevonden("proces", proces_id)
    af_labels = await af_catalog.labels(session)
    type_labels = await cc_catalog.labels(session, ComponentConfigDimensie.componenttype)
    rijen = (
        await session.execute(
            select(
                Procesvervulling.id,
                Procesvervulling.applicatiefunctie,
                Procesvervulling.toelichting,
                Procesvervulling.component_id,
                Component.naam.label("component_naam"),
                Component.componenttype.label("componenttype"),
            )
            .join(
                Component,
                (Component.id == Procesvervulling.component_id) & (Component.tenant_id == tid),
            )
            .where(Procesvervulling.tenant_id == tid, Procesvervulling.proces_id == proces_id)
            .order_by(Component.naam, Procesvervulling.applicatiefunctie, Procesvervulling.id)
        )
    ).all()
    return [
        {
            "vervulling_id": r.id,
            "applicatiefunctie": r.applicatiefunctie,
            "applicatiefunctie_label": af_catalog.resolveer_een(r.applicatiefunctie, af_labels),
            "toelichting": r.toelichting,
            "component_id": r.component_id,
            "component_naam": r.component_naam,
            "componenttype": r.componenttype,
            "componenttype_label": cc_catalog.resolveer_een(r.componenttype, type_labels),
        }
        for r in rijen
    ]


async def lijst_voor_component(session: AsyncSession, tenant_id, component_id) -> list[dict]:
    """"Vervult een rol in": de koppelregels van één component, verrijkt met proces-naam
    + procescontext (ouder-naam) + functie-label; gesorteerd op proces-naam dan functie.
    Onbekend component binnen de tenant ⇒ 404 (no-leak)."""
    tid = _tenant_uuid(tenant_id)
    if await _element_type(session, tid, component_id) != ElementType.component.value:
        raise NietGevonden("component", component_id)
    af_labels = await af_catalog.labels(session)
    ouder = aliased(Proces)
    rijen = (
        await session.execute(
            select(
                Procesvervulling.id,
                Procesvervulling.applicatiefunctie,
                Procesvervulling.toelichting,
                Procesvervulling.proces_id,
                Proces.naam.label("proces_naam"),
                ouder.naam.label("proces_ouder_naam"),
            )
            .join(Proces, (Proces.id == Procesvervulling.proces_id) & (Proces.tenant_id == tid))
            .outerjoin(ouder, (ouder.id == Proces.ouder_id) & (ouder.tenant_id == tid))
            .where(Procesvervulling.tenant_id == tid, Procesvervulling.component_id == component_id)
            .order_by(Proces.naam, Procesvervulling.applicatiefunctie, Procesvervulling.id)
        )
    ).all()
    return [
        {
            "vervulling_id": r.id,
            "applicatiefunctie": r.applicatiefunctie,
            "applicatiefunctie_label": af_catalog.resolveer_een(r.applicatiefunctie, af_labels),
            "toelichting": r.toelichting,
            "proces_id": r.proces_id,
            "proces_naam": r.proces_naam,
            "proces_ouder_naam": r.proces_ouder_naam,
        }
        for r in rijen
    ]


# ── Slice 5 — roll-up-inzicht (pure leespaden; geen opslag, geen mutatie) ────────


async def rollup_voor_proces(session: AsyncSession, tenant_id, proces_id) -> list[dict]:
    """Doorgerolde koppelregels: alle regels uit de VOLLEDIGE subboom van dit proces
    (alle deelprocessen, alle niveaus) — de eigen regels van het proces zelf zitten er
    bewust NIET in (die toont de bestaande directe lijst). Cyclus-veilig via
    `proces_service.subboom` (visited-set); één vervulling-query over alle subboom-ids +
    join op component (geen N+1). Per regel de herkomst: proces-naam + `proces_pad`
    (namen vanaf het directe deelproces t/m het herkomst-proces — de wortel zelf niet).
    Onbekend proces binnen de tenant ⇒ 404 (no-leak). Read-only."""
    tid = _tenant_uuid(tenant_id)
    # 404 no-leak + cyclus-veilige traversal in één beweging (subboom valideert de wortel).
    boom = await proces_service.subboom(session, tid, proces_id)
    if not boom:
        return []
    # pad[0] = de wortel (dit proces zelf) — herkomst-context is het pad dáárna.
    pad_per_proces = {n["id"]: n["pad"][1:] for n in boom}
    naam_per_proces = {n["id"]: n["naam"] for n in boom}
    # Tak-bepaling: het DIRECTE deelproces waaronder de herkomst valt — de stabiele
    # groepeersleutel voor het samengevoegde "Onderliggende processen"-blok (namen in
    # het pad kunnen botsen, ids niet). Subboom levert BFS-volgorde: ouders vóór
    # kinderen, dus één lineaire doorloop volstaat.
    tak_per_proces: dict = {}
    for n in boom:
        tak_per_proces[n["id"]] = n["id"] if n["ouder_id"] == proces_id else tak_per_proces.get(n["ouder_id"])
    af_labels = await af_catalog.labels(session)
    type_labels = await cc_catalog.labels(session, ComponentConfigDimensie.componenttype)
    rijen = (
        await session.execute(
            select(
                Procesvervulling.id,
                Procesvervulling.applicatiefunctie,
                Procesvervulling.toelichting,
                Procesvervulling.component_id,
                Procesvervulling.proces_id,
                Component.naam.label("component_naam"),
                Component.componenttype.label("componenttype"),
            )
            .join(
                Component,
                (Component.id == Procesvervulling.component_id) & (Component.tenant_id == tid),
            )
            .where(
                Procesvervulling.tenant_id == tid,
                Procesvervulling.proces_id.in_(list(pad_per_proces.keys())),
            )
            .order_by(Component.naam, Procesvervulling.applicatiefunctie, Procesvervulling.id)
        )
    ).all()
    return [
        {
            "vervulling_id": r.id,
            "applicatiefunctie": r.applicatiefunctie,
            "applicatiefunctie_label": af_catalog.resolveer_een(r.applicatiefunctie, af_labels),
            "toelichting": r.toelichting,
            "component_id": r.component_id,
            "component_naam": r.component_naam,
            "componenttype": r.componenttype,
            "componenttype_label": cc_catalog.resolveer_een(r.componenttype, type_labels),
            "proces_id": r.proces_id,
            "proces_naam": naam_per_proces.get(r.proces_id),
            "proces_pad": pad_per_proces.get(r.proces_id, []),
            "tak_id": tak_per_proces.get(r.proces_id),
        }
        for r in rijen
    ]


async def processen_voor_organisatie(session: AsyncSession, tenant_id, organisatie_id) -> list[dict]:
    """Afgeleid beeld: welke processen steunen op de componenten van deze organisatie.
    Brug = eigendom (`component.eigenaar_organisatie_id`) ÉN geregistreerd gebruik
    (`organisatiegebruik`) samengenomen; per proces telt één component één keer (dedupe —
    ook bij eigendom+gebruik tegelijk, of meerdere functies in hetzelfde proces).
    Onbekende partij binnen de tenant ⇒ 404 (no-leak). Read-only — hier wordt niets
    geregistreerd; twee queries totaal (partij-check + één join-query, geen N+1)."""
    tid = _tenant_uuid(tenant_id)
    partij = (
        await session.execute(
            select(Partij.id).where(Partij.tenant_id == tid, Partij.id == organisatie_id)
        )
    ).scalar_one_or_none()
    if partij is None:
        raise NietGevonden("partij", organisatie_id)
    # Brug-componenten als subquery: eigendom OF gebruik (dedupe volgt uit de groepering).
    gebruik_sq = select(Organisatiegebruik.applicatie_id).where(
        Organisatiegebruik.tenant_id == tid,
        Organisatiegebruik.organisatie_id == organisatie_id,
    )
    ouder = aliased(Proces)
    rijen = (
        await session.execute(
            select(
                Procesvervulling.proces_id,
                Procesvervulling.component_id,
                Proces.naam.label("proces_naam"),
                ouder.naam.label("proces_ouder_naam"),
                Component.naam.label("component_naam"),
                Component.componenttype.label("componenttype"),
            )
            .join(
                Component,
                (Component.id == Procesvervulling.component_id) & (Component.tenant_id == tid),
            )
            .join(Proces, (Proces.id == Procesvervulling.proces_id) & (Proces.tenant_id == tid))
            .outerjoin(ouder, (ouder.id == Proces.ouder_id) & (ouder.tenant_id == tid))
            .where(
                Procesvervulling.tenant_id == tid,
                or_(
                    Component.eigenaar_organisatie_id == organisatie_id,
                    Component.id.in_(gebruik_sq),
                ),
            )
            .order_by(Proces.naam, Proces.id, Component.naam, Component.id)
        )
    ).all()
    type_labels = await cc_catalog.labels(session, ComponentConfigDimensie.componenttype)
    processen: dict = {}
    for r in rijen:
        p = processen.setdefault(
            r.proces_id,
            {
                "proces_id": r.proces_id,
                "proces_naam": r.proces_naam,
                "proces_ouder_naam": r.proces_ouder_naam,
                "componenten": [],
                "_gezien": set(),
            },
        )
        if r.component_id in p["_gezien"]:
            continue  # dedupe: één component telt één keer per proces
        p["_gezien"].add(r.component_id)
        p["componenten"].append(
            {
                "component_id": r.component_id,
                "component_naam": r.component_naam,
                "componenttype": r.componenttype,
                "componenttype_label": cc_catalog.resolveer_een(r.componenttype, type_labels),
            }
        )
    resultaat = []
    for p in processen.values():
        p.pop("_gezien")
        p["component_aantal"] = len(p["componenten"])
        resultaat.append(p)
    return resultaat
