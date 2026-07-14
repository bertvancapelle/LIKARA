"""Service-laag — functievervulling: "component X ondersteunt bedrijfsfunctie Y" (ADR-049, gate 2a).

Het procesvervulling-recept, mét één verschil: de as is KAAL (géén applicatiefunctie/werkwoord).
Het anker is het ADRES van de plek (ADR-049 besluit 2): `functie_id` + `ouder_functie_id`
(NULL = grof "geldt overal", gevuld = fijn "déze plek") — GEEN verwijzing naar `relatie.id`.

Validatie vooraf (fail-secure, 404 no-leak buiten de tenant):
- component-kant = een bestaand `component`-element ⇒ anders 422 `ONGELDIG_COMPONENT`;
- het componenttype ondersteunt werk (ADR-045; de picker spiegelt exact deze regel) ⇒ anders
  422 `COMPONENT_ONDERSTEUNT_GEEN_WERK`;
- functie-kant = een bestaande bedrijfsfunctie ⇒ anders 422 `ONGELDIGE_FUNCTIE` (404 bij onbekend);
- de functie is niet vervallen ⇒ anders 422 `VERVALLEN_NIET_KOPPELBAAR` (zichtbaar ≠ koppelbaar);
- bij een fijne koppeling: de PLEK bestaat (aggregation-relatie ouder→functie) ⇒ anders 422
  `ONBEKENDE_PLEK`; de ouder is een bedrijfsfunctie;
- dubbel (grof of fijn) ⇒ 409 `KOPPELING_BESTAAT` (pre-check; de partiële UNIQUE is de DB-backstop).

DE LEESREGEL "fijn verdringt grof" leeft ÉÉN keer, in `dekking_overzicht` — een LEESLAAG, nooit
opgeslagen (ADR-049 besluit 1/5). Consumenten (boom nu, componentdetail/kaart/gap later) lezen
die uitkomst; ze rekenen niet zelf. Puur registratief — géén engine-import (score blijft de enige
lifecycle-driver; ADR-049-invariant).
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.models import (
    Bedrijfsfunctie,
    Component,
    ComponentConfigDimensie,
    ComponentConfigOptie,
    Element,
    ElementType,
    Functievervulling,
    Relatie,
)
from app.core.tenant_context import huidige_actor
from services import actor_resolutie
from services import componentconfig_catalog as cc_catalog
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict

_ENTITEIT = "functievervulling"
_AGGREGATION = "aggregation"  # de plaatsing: bron = ouder, doel = kind (ADR-044)


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def _element_type(session: AsyncSession, tid: uuid.UUID, element_id) -> str | None:
    rij = (
        await session.execute(
            select(Element.element_type).where(Element.tenant_id == tid, Element.id == element_id)
        )
    ).scalar_one_or_none()
    return getattr(rij, "value", rij) if rij is not None else None


async def _plek_bestaat(session: AsyncSession, tid: uuid.UUID, ouder_id, functie_id) -> bool:
    """Bestaat de plek? = een aggregation-relatie (bron = ouder, doel = functie)."""
    rij = (
        await session.execute(
            select(Relatie.id).where(
                Relatie.tenant_id == tid,
                Relatie.relatietype == _AGGREGATION,
                Relatie.bron_id == ouder_id,
                Relatie.doel_id == functie_id,
            )
        )
    ).scalar_one_or_none()
    return rij is not None


async def _aggregatie_paren(session: AsyncSession, tid: uuid.UUID) -> list[tuple]:
    """Alle plaatsingen als (ouder, kind)-paren — aggregation-relaties waarvan BEIDE endpoints
    bedrijfsfuncties zijn (harde scoping; plateau-lidmaatschap gebruikt hetzelfde relatietype
    met andere endpoints en blijft buiten beeld). Structurele leeshulp voor de leesregel —
    NIET de leesregel zelf (die zit in `dekking_overzicht`)."""
    ouder_bf = aliased(Bedrijfsfunctie)
    kind_bf = aliased(Bedrijfsfunctie)
    rijen = (
        await session.execute(
            select(Relatie.bron_id, Relatie.doel_id)
            .join(ouder_bf, (ouder_bf.id == Relatie.bron_id) & (ouder_bf.tenant_id == tid))
            .join(kind_bf, (kind_bf.id == Relatie.doel_id) & (kind_bf.tenant_id == tid))
            .where(Relatie.tenant_id == tid, Relatie.relatietype == _AGGREGATION)
        )
    ).all()
    return [(r.bron_id, r.doel_id) for r in rijen]


async def maak_aan(
    session: AsyncSession, tenant_id, component_id, functie_id,
    ouder_functie_id=None, toelichting: str | None = None,
) -> dict:
    tid = _tenant_uuid(tenant_id)
    # Component-kant: een bestaand component-element…
    if await _element_type(session, tid, component_id) != ElementType.component.value:
        raise OngeldigeRegistratie(
            "ONGELDIG_COMPONENT", "De component-kant moet een bestaand component zijn."
        )
    # …van een type dat WERK ondersteunt (ADR-045; de picker spiegelt exact deze regel — join
    # op de catalogus-eigenschap, nooit op een hardcoded typelijst).
    if not await _component_ondersteunt_werk(session, tid, component_id):
        raise OngeldigeRegistratie(
            "COMPONENT_ONDERSTEUNT_GEEN_WERK",
            "Dit type component ondersteunt geen werk en kan niet aan een functie gekoppeld worden.",
        )
    # Functie-kant: een bestaande bedrijfsfunctie, niet vervallen.
    et = await _element_type(session, tid, functie_id)
    if et is None:
        raise NietGevonden(_ENTITEIT, functie_id)
    if et != ElementType.bedrijfsfunctie.value:
        raise OngeldigeRegistratie(
            "ONGELDIGE_FUNCTIE", "De functie-kant moet een bestaande bedrijfsfunctie zijn."
        )
    functie = (
        await session.execute(
            select(Bedrijfsfunctie).where(
                Bedrijfsfunctie.id == functie_id, Bedrijfsfunctie.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if functie is None:
        raise NietGevonden(_ENTITEIT, functie_id)
    if functie.vervallen:
        raise OngeldigeRegistratie(
            "VERVALLEN_NIET_KOPPELBAAR",
            "Deze functie bestaat niet meer in het referentiemodel en is niet koppelbaar.",
        )
    # Fijne koppeling: de PLEK moet bestaan (ADR-049 — verfijnen kan alleen op een plek die er is).
    if ouder_functie_id is not None:
        if await _element_type(session, tid, ouder_functie_id) != ElementType.bedrijfsfunctie.value:
            raise OngeldigeRegistratie(
                "ONGELDIGE_FUNCTIE", "De ouder van een plek moet een bedrijfsfunctie zijn."
            )
        if not await _plek_bestaat(session, tid, ouder_functie_id, functie_id):
            raise OngeldigeRegistratie(
                "ONBEKENDE_PLEK",
                "Deze functie staat niet onder die functie; verfijnen kan alleen op een bestaande plek.",
            )
    # Dubbel (grof óf fijn) ⇒ 409 (pre-check; de partiële UNIQUE is de DB-backstop).
    dubbel_filter = [
        Functievervulling.tenant_id == tid,
        Functievervulling.component_id == component_id,
        Functievervulling.functie_id == functie_id,
    ]
    dubbel_filter.append(
        Functievervulling.ouder_functie_id.is_(None) if ouder_functie_id is None
        else Functievervulling.ouder_functie_id == ouder_functie_id
    )
    if (await session.execute(select(Functievervulling.id).where(*dubbel_filter))).scalar_one_or_none():
        raise RegistratieConflict(
            "KOPPELING_BESTAAT", "Dit component is hier al aan deze functie gekoppeld."
        )
    actor_sub, actor_email = huidige_actor()
    obj = Functievervulling(
        tenant_id=tid, component_id=component_id, functie_id=functie_id,
        ouder_functie_id=ouder_functie_id, toelichting=toelichting,
        verklaard_door_sub=actor_sub, verklaard_door=actor_email,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return await _lees_een(session, obj)


async def _component_ondersteunt_werk(session: AsyncSession, tid: uuid.UUID, component_id) -> bool:
    """True als het componenttype `ondersteunt_werk = true` draagt — via de catalogus-join
    (ADR-045 besluit 5), nooit tegen een hardcoded typelijst."""
    rij = (
        await session.execute(
            select(ComponentConfigOptie.ondersteunt_werk)
            .join(Component, Component.componenttype == ComponentConfigOptie.optie_sleutel)
            .where(
                Component.id == component_id, Component.tenant_id == tid,
                ComponentConfigOptie.dimensie == ComponentConfigDimensie.componenttype,
            )
        )
    ).scalar_one_or_none()
    return bool(rij)


async def _haal_op(session: AsyncSession, tid: uuid.UUID, vervulling_id) -> Functievervulling:
    obj = (
        await session.execute(
            select(Functievervulling).where(
                Functievervulling.id == vervulling_id, Functievervulling.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, vervulling_id)  # 404 no-leak kruis-tenant
    return obj


async def verwijder(session: AsyncSession, tenant_id, vervulling_id) -> None:
    """Verwijder één koppeling. Een fijne koppeling weghalen laat het grove antwoord op die
    plek automatisch wéér leesbaar worden (de leesregel valt terug op grof) — er is nooit iets
    weggeschreven (ADR-049 besluit 1)."""
    tid = _tenant_uuid(tenant_id)
    obj = await _haal_op(session, tid, vervulling_id)
    await session.delete(obj)
    await session.commit()


async def _lees_een(session: AsyncSession, obj: Functievervulling) -> dict:
    tid = obj.tenant_id
    type_labels = await cc_catalog.labels(session, ComponentConfigDimensie.componenttype)
    comp = (
        await session.execute(
            select(Component.naam, Component.componenttype).where(
                Component.id == obj.component_id, Component.tenant_id == tid
            )
        )
    ).one_or_none()
    naam = await actor_resolutie.resolveer_naam(
        session, tid, sub=obj.verklaard_door_sub, email=obj.verklaard_door
    )
    return {
        "vervulling_id": obj.id,
        "component_id": obj.component_id,
        "component_naam": comp.naam if comp else None,
        "componenttype": comp.componenttype if comp else None,
        "componenttype_label": cc_catalog.resolveer_een(comp.componenttype, type_labels) if comp else None,
        "toelichting": obj.toelichting,
        "functie_id": obj.functie_id,
        "ouder_functie_id": obj.ouder_functie_id,
        "herkomst": "fijn" if obj.ouder_functie_id is not None else "grof",
        "verklaard_door_naam": naam,
    }


async def dekking_overzicht(session: AsyncSession, tenant_id) -> list[dict]:
    """DE LEESREGEL (ADR-049 besluit 1/5), één vindplaats: "welke componenten dragen déze plek".

    Per plek (functie + ouder-functie): draagt de plek een eigen (fijn) antwoord, dan wint dat
    en verdwijnt het grove uit beeld; anders is het grove antwoord van de functie leesbaar. De
    verdringing wordt NIET opgeslagen — dit is een pure afleiding. Geeft alleen plekken mét
    dekking terug (plekken zonder koppeling staan er niet in). Read-only; twee queries totaal."""
    tid = _tenant_uuid(tenant_id)
    type_labels = await cc_catalog.labels(session, ComponentConfigDimensie.componenttype)
    rijen = (
        await session.execute(
            select(
                Functievervulling.id,
                Functievervulling.component_id,
                Functievervulling.functie_id,
                Functievervulling.ouder_functie_id,
                Functievervulling.toelichting,
                Component.naam.label("component_naam"),
                Component.componenttype.label("componenttype"),
            )
            .join(Component, (Component.id == Functievervulling.component_id) & (Component.tenant_id == tid))
            .where(Functievervulling.tenant_id == tid)
            .order_by(Component.naam, Functievervulling.id)
        )
    ).all()
    if not rijen:
        return []

    def _entry(r) -> dict:
        return {
            "vervulling_id": r.id,
            "component_id": r.component_id,
            "component_naam": r.component_naam,
            "componenttype": r.componenttype,
            "componenttype_label": cc_catalog.resolveer_een(r.componenttype, type_labels),
            "toelichting": r.toelichting,
        }

    grof_per_functie: dict = {}          # functie_id -> [entry]
    fijn_per_plek: dict = {}             # (functie_id, ouder_id) -> [entry]
    for r in rijen:
        if r.ouder_functie_id is None:
            grof_per_functie.setdefault(r.functie_id, []).append(_entry(r))
        else:
            fijn_per_plek.setdefault((r.functie_id, r.ouder_functie_id), []).append(_entry(r))

    # Alle plekken enumereren: aggregation-paren (kind onder ouder) + wortels (functie zonder
    # ouder). Een grove koppeling dekt élke plek van haar functie; een fijne alleen haar eigen plek.
    paren = await _aggregatie_paren(session, tid)
    kinderen_met_ouder: set = set()
    plekken: set = set()
    for ouder, kind in paren:
        plekken.add((kind, ouder))
        kinderen_met_ouder.add(kind)
    betrokken_functies = set(grof_per_functie) | {f for (f, _o) in fijn_per_plek}
    for f in betrokken_functies:
        if f not in kinderen_met_ouder:
            plekken.add((f, None))  # wortelplek

    # Reikwijdte per functie — uit DEZELFDE afleiding, nooit opgeslagen: N = alle plekken van
    # de functie, K = daarvan verfijnd (alleen plekken die nog bestaan tellen mee). Dit voedt
    # zowel het getelde grof-label ("geldt nog op M van de N plekken") ALS de verdringing —
    # één bron, geen tweede telling (de "3-van-19"-les LI040).
    totaal_plekken_per_functie: dict = {}
    for f, _o in plekken:
        totaal_plekken_per_functie[f] = totaal_plekken_per_functie.get(f, 0) + 1
    verfijnd_per_functie: dict = {}
    for (f, o) in fijn_per_plek:
        if (f, o) in plekken:  # een verfijning op een verdwenen plek telt niet mee (2b-terrein)
            verfijnd_per_functie[f] = verfijnd_per_functie.get(f, 0) + 1

    uit: list[dict] = []
    for functie_id, ouder_id in plekken:
        fijn = fijn_per_plek.get((functie_id, ouder_id))
        if fijn:
            # Het grove antwoord van deze functie wordt hier verdrongen — maar het bestaat nog
            # (ADR-049 besluit 1). Read-only meegeleverd, zónder eigen actie (de actie woont bij
            # de herkomst, niet op deze plek). Een grof systeem dat hier ÓÓK expliciet als
            # verfijning staat is NIET verdrongen maar bevestigd → laat het uit `verdrongen`
            # (anders zou de rij zichzelf tegenspreken: hetzelfde systeem als antwoord én als
            # weggedrukt). Blijft er niets over, dan is `verdrongen` leeg en verdwijnt de regel.
            bevestigd = {f["component_id"] for f in fijn}
            verdrongen = [g for g in grof_per_functie.get(functie_id, []) if g["component_id"] not in bevestigd]
            uit.append({
                "functie_id": functie_id, "ouder_functie_id": ouder_id,
                "herkomst": "fijn", "componenten": fijn,
                "verdrongen": verdrongen,
                "grof_totaal_plekken": None, "grof_geldt_op": None,
            })
        elif functie_id in grof_per_functie:
            n = totaal_plekken_per_functie.get(functie_id, 1)
            k = verfijnd_per_functie.get(functie_id, 0)
            uit.append({
                "functie_id": functie_id, "ouder_functie_id": ouder_id,
                "herkomst": "grof", "componenten": grof_per_functie[functie_id],
                "verdrongen": [],
                "grof_totaal_plekken": n, "grof_geldt_op": n - k,
            })
    return uit
