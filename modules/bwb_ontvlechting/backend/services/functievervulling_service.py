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
    FunctievervullingOordeel,
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
    ouder_functie_id=None, toelichting: str | None = None, oordeel: str | None = None,
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
    # ADR-051 — een koppeling en een "geen systeem"-bevinding zijn tegengestelde antwoorden op
    # dezelfde plek: ze mogen daar niet naast elkaar staan.
    await _weiger_tegengesteld(session, tid, functie_id, ouder_functie_id, wil_geen_systeem=False)
    oordeel = _valideer_oordeel(oordeel)
    actor_sub, actor_email = huidige_actor()
    obj = Functievervulling(
        tenant_id=tid, component_id=component_id, functie_id=functie_id,
        ouder_functie_id=ouder_functie_id, toelichting=toelichting, oordeel=oordeel,
        verklaard_door_sub=actor_sub, verklaard_door=actor_email,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return await _lees_een(session, obj)


def _valideer_oordeel(oordeel: str | None) -> FunctievervullingOordeel | None:
    """ADR-051 besluit 3/4 — oordeel is optioneel (leeg = nog niet beoordeeld) en uit een gesloten
    set (naar_behoren / noodoplossing); onbekend ⇒ 422."""
    if oordeel is None:
        return None
    try:
        return FunctievervullingOordeel(oordeel)
    except ValueError as e:
        raise OngeldigeRegistratie("ONGELDIG_OORDEEL", "Onbekend oordeel.") from e


async def _weiger_tegengesteld(session, tid, functie_id, ouder_functie_id, *, wil_geen_systeem: bool) -> None:
    """Op één plek staat óf een koppeling óf de bevinding "geen systeem" — nooit beide (ADR-051
    besluit 2, plek-niveau; de XOR-CHECK borgt het rij-niveau). Zoekt de tegengestelde soort op
    exact dezelfde plek (zelfde functie + zelfde adres) en weigert met 409."""
    stmt = select(Functievervulling.id).where(
        Functievervulling.tenant_id == tid,
        Functievervulling.functie_id == functie_id,
        Functievervulling.ouder_functie_id.is_(None) if ouder_functie_id is None
        else Functievervulling.ouder_functie_id == ouder_functie_id,
        # wil ik een koppeling zetten? dan botst een bestaande geen-systeem, en omgekeerd.
        Functievervulling.geen_systeem.is_(not wil_geen_systeem),
    )
    if (await session.execute(stmt)).scalar_one_or_none():
        if wil_geen_systeem:
            raise RegistratieConflict(
                "PLEK_HEEFT_KOPPELING",
                "Hier is al een systeem gekoppeld; haal dat eerst weg voordat je 'geen systeem' vastlegt.",
            )
        raise RegistratieConflict(
            "PLEK_IS_GEEN_SYSTEEM",
            "Hier is vastgesteld dat geen systeem draait; haal die bevinding eerst weg voordat je koppelt.",
        )


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


async def _vereis_koppelbare_functie(session, tid, functie_id, ouder_functie_id) -> None:
    """Gedeelde plek-validatie: functie is een bestaande, niet-vervallen bedrijfsfunctie; bij een
    fijne plek bestaat het adres (aggregation ouder→functie) en is de ouder ook een bedrijfsfunctie."""
    et = await _element_type(session, tid, functie_id)
    if et is None:
        raise NietGevonden(_ENTITEIT, functie_id)
    if et != ElementType.bedrijfsfunctie.value:
        raise OngeldigeRegistratie("ONGELDIGE_FUNCTIE", "De functie-kant moet een bestaande bedrijfsfunctie zijn.")
    functie = (
        await session.execute(
            select(Bedrijfsfunctie).where(Bedrijfsfunctie.id == functie_id, Bedrijfsfunctie.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if functie is None:
        raise NietGevonden(_ENTITEIT, functie_id)
    if functie.vervallen:
        raise OngeldigeRegistratie(
            "VERVALLEN_NIET_KOPPELBAAR",
            "Deze functie bestaat niet meer in het referentiemodel en is niet koppelbaar.",
        )
    if ouder_functie_id is not None:
        if await _element_type(session, tid, ouder_functie_id) != ElementType.bedrijfsfunctie.value:
            raise OngeldigeRegistratie("ONGELDIGE_FUNCTIE", "De ouder van een plek moet een bedrijfsfunctie zijn.")
        if not await _plek_bestaat(session, tid, ouder_functie_id, functie_id):
            raise OngeldigeRegistratie(
                "ONBEKENDE_PLEK",
                "Deze functie staat niet onder die functie; verfijnen kan alleen op een bestaande plek.",
            )


async def registreer_geen_systeem(
    session: AsyncSession, tenant_id, functie_id, ouder_functie_id=None, toelichting: str | None = None,
) -> dict:
    """ADR-051 besluit 2 — leg vast: "hier draait geen systeem — vastgesteld". Een BEVINDING, strikt
    onderscheiden van "nooit naar gekeken" (ADR-044 besluit 3). Draagt géén component (XOR-CHECK)."""
    tid = _tenant_uuid(tenant_id)
    await _vereis_koppelbare_functie(session, tid, functie_id, ouder_functie_id)
    dubbel = select(Functievervulling.id).where(
        Functievervulling.tenant_id == tid, Functievervulling.functie_id == functie_id,
        Functievervulling.geen_systeem.is_(True),
        Functievervulling.ouder_functie_id.is_(None) if ouder_functie_id is None
        else Functievervulling.ouder_functie_id == ouder_functie_id,
    )
    if (await session.execute(dubbel)).scalar_one_or_none():
        raise RegistratieConflict("BEVINDING_BESTAAT", "Hier is al vastgesteld dat geen systeem draait.")
    await _weiger_tegengesteld(session, tid, functie_id, ouder_functie_id, wil_geen_systeem=True)
    actor_sub, actor_email = huidige_actor()
    obj = Functievervulling(
        tenant_id=tid, component_id=None, functie_id=functie_id, ouder_functie_id=ouder_functie_id,
        geen_systeem=True, toelichting=toelichting, verklaard_door_sub=actor_sub, verklaard_door=actor_email,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return await _lees_een(session, obj)


async def zet_oordeel(session: AsyncSession, tenant_id, vervulling_id, oordeel: str | None) -> dict:
    """ADR-051 besluit 3/4 — zet of wis het oordeel op een component-koppeling (registratie-feit →
    WIJZIGEN). Op een "geen systeem"-bevinding is een oordeel betekenisloos ⇒ 422."""
    tid = _tenant_uuid(tenant_id)
    obj = await _haal_op(session, tid, vervulling_id)
    if obj.geen_systeem:
        raise OngeldigeRegistratie(
            "OORDEEL_OP_BEVINDING", "Een 'geen systeem'-bevinding krijgt geen oordeel."
        )
    obj.oordeel = _valideer_oordeel(oordeel)
    await session.commit()
    await session.refresh(obj)
    return await _lees_een(session, obj)


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
        # ADR-051 — de herkomst zegt óók of dit een bevinding ("geen systeem") is; het oordeel
        # (naar_behoren/noodoplossing/None) hoort bij een component-koppeling.
        "herkomst": "geen_systeem" if obj.geen_systeem else ("fijn" if obj.ouder_functie_id is not None else "grof"),
        "geen_systeem": obj.geen_systeem,
        "oordeel": obj.oordeel.value if obj.oordeel is not None else None,
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
    # LEFT join: de geen-systeem-bevindingen (component_id NULL) komen óók mee.
    rijen = (
        await session.execute(
            select(
                Functievervulling.id,
                Functievervulling.component_id,
                Functievervulling.functie_id,
                Functievervulling.ouder_functie_id,
                Functievervulling.toelichting,
                Functievervulling.geen_systeem,
                Functievervulling.oordeel,
                Component.naam.label("component_naam"),
                Component.componenttype.label("componenttype"),
            )
            .outerjoin(Component, (Component.id == Functievervulling.component_id) & (Component.tenant_id == tid))
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
            "oordeel": r.oordeel.value if r.oordeel is not None else None,
        }

    grof_per_functie: dict = {}          # functie_id -> [entry]      (component-koppelingen)
    fijn_per_plek: dict = {}             # (functie_id, ouder) -> [entry]
    geen_grof: dict = {}                 # functie_id -> bevinding_id  (geen systeem, grof)
    geen_fijn: dict = {}                 # (functie_id, ouder) -> bevinding_id
    for r in rijen:
        if r.geen_systeem:
            if r.ouder_functie_id is None:
                geen_grof[r.functie_id] = r.id
            else:
                geen_fijn[(r.functie_id, r.ouder_functie_id)] = r.id
        elif r.ouder_functie_id is None:
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
    betrokken_functies = (
        set(grof_per_functie) | {f for (f, _o) in fijn_per_plek}
        | set(geen_grof) | {f for (f, _o) in geen_fijn}
    )
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
    for plek in set(fijn_per_plek) | set(geen_fijn):
        f, o = plek
        if plek in plekken:  # een verfijning (component óf "geen systeem") op een bestaande plek
            verfijnd_per_functie[f] = verfijnd_per_functie.get(f, 0) + 1

    def _geen_entry(functie_id, ouder_id, bevinding_id) -> dict:
        # "Hier draait niets — vastgesteld": een bevinding, geen componenten, geen teller.
        return {
            "functie_id": functie_id, "ouder_functie_id": ouder_id,
            "herkomst": "geen_systeem", "componenten": [], "verdrongen": [],
            "bevinding_id": bevinding_id, "grof_totaal_plekken": None, "grof_geldt_op": None,
        }

    uit: list[dict] = []
    for functie_id, ouder_id in plekken:
        # ADR-051 — een fijn antwoord (component óf "geen systeem") verdringt het grove op die plek.
        if (functie_id, ouder_id) in geen_fijn:
            uit.append(_geen_entry(functie_id, ouder_id, geen_fijn[(functie_id, ouder_id)]))
            continue
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
                "verdrongen": verdrongen, "bevinding_id": None,
                "grof_totaal_plekken": None, "grof_geldt_op": None,
            })
        elif functie_id in geen_grof:
            uit.append(_geen_entry(functie_id, ouder_id, geen_grof[functie_id]))
        elif functie_id in grof_per_functie:
            n = totaal_plekken_per_functie.get(functie_id, 1)
            k = verfijnd_per_functie.get(functie_id, 0)
            uit.append({
                "functie_id": functie_id, "ouder_functie_id": ouder_id,
                "herkomst": "grof", "componenten": grof_per_functie[functie_id],
                "verdrongen": [], "bevinding_id": None,
                "grof_totaal_plekken": n, "grof_geldt_op": n - k,
            })
    return uit


async def _functie_namen(session: AsyncSession, tid: uuid.UUID, ids) -> dict:
    """Resolveer functie-namen voor een set ids (naam is een leeslaag-verrijking, GEEN
    her-afleiding van de leesregel). Onbekende/None ids vallen weg."""
    schone = {i for i in ids if i is not None}
    if not schone:
        return {}
    rijen = (
        await session.execute(
            select(Bedrijfsfunctie.id, Bedrijfsfunctie.naam).where(
                Bedrijfsfunctie.tenant_id == tid, Bedrijfsfunctie.id.in_(schone)
            )
        )
    ).all()
    return {r.id: r.naam for r in rijen}


async def overzicht_voor_component(session: AsyncSession, tenant_id, component_id) -> list[dict]:
    """De richting component → plekken (ADR-043 gate 4 besluit G2/G9): "waarvoor dient dit systeem".

    ⚠ INVARIANT (ADR-043 §Gate 4 / ADR-049 besluit 5): deze functie leest UITSLUITEND de gedeelde
    leesregel `dekking_overzicht` en indexeert die her op dit component — NOOIT een verse rauwe
    `where component_id`-query op `functievervulling`. Zou ze dat wél doen, dan miste ze de
    verdringing en toonde ze "geldt overal" terwijl een plek allang verdrongen is (de tweede-
    waarheid-val). De structurele borging staat in `test_functievervulling_component_gate4.py`
    (bronscan: deze functie leest de leesregel en bevat géén eigen rauwe koppelregel-query).

    Component-kant onbekend binnen de tenant ⇒ 404 (no-leak). Read-only; nooit opgeslagen.

    Levert één regel per koppeling van dit component:
    - **grof** (geldt overal): één regel per functie, met `grof_totaal_plekken`/`grof_geldt_op`
      (de reikwijdte-telling uit de leesregel) en `verdrongen_op` (op hoeveel plekken een fijner
      antwoord dit grove hier verbergt — het blijft bestaan, ADR-049 besluit 1);
    - **fijn** (één plek): één regel per plek, met de plek-context (`ouder_naam`).
    """
    tid = _tenant_uuid(tenant_id)
    if await _element_type(session, tid, component_id) != ElementType.component.value:
        raise NietGevonden("component", component_id)
    dekking = await dekking_overzicht(session, tid)
    cid = str(component_id)

    def _is_dit(c) -> bool:
        return str(c["component_id"]) == cid

    grof: dict = {}   # functie_id -> regel (grove koppeling van dit component)
    fijn: list = []   # fijne koppelingen (per plek)
    for d in dekking:
        for c in d["componenten"]:
            if not _is_dit(c):
                continue
            if d["herkomst"] == "grof":
                # De grove plek draagt de GEZAGHEBBENDE reikwijdte-telling; die zet hij ongeacht
                # de volgorde (een verdrongen-plek kan de entry eerder hebben aangemaakt).
                e = grof.setdefault(d["functie_id"], {"verdrongen_op": 0})
                e["vervulling_id"] = c["vervulling_id"]
                e["oordeel"] = c["oordeel"]
                e["grof_totaal_plekken"] = d["grof_totaal_plekken"]
                e["grof_geldt_op"] = d["grof_geldt_op"]
            elif d["herkomst"] == "fijn":
                fijn.append({
                    "vervulling_id": c["vervulling_id"], "oordeel": c["oordeel"],
                    "functie_id": d["functie_id"], "ouder_functie_id": d["ouder_functie_id"],
                })
        # Dit component als VERDRONGEN grof antwoord op een fijne plek (het bestaat nog, ADR-049).
        # Fallback-telling (None) alleen als de grove plek zelf niet meer verschijnt (overal verdrongen).
        for c in d.get("verdrongen", []):
            if not _is_dit(c):
                continue
            e = grof.setdefault(d["functie_id"], {
                "vervulling_id": c["vervulling_id"], "oordeel": c["oordeel"],
                "grof_totaal_plekken": None, "grof_geldt_op": None, "verdrongen_op": 0,
            })
            e["verdrongen_op"] += 1

    namen = await _functie_namen(
        session, tid,
        set(grof) | {f["functie_id"] for f in fijn} | {f["ouder_functie_id"] for f in fijn},
    )
    uit: list = []
    for fid, e in grof.items():
        uit.append({
            "vervulling_id": e["vervulling_id"], "herkomst": "grof",
            "functie_id": fid, "functie_naam": namen.get(fid),
            "ouder_functie_id": None, "ouder_naam": None, "oordeel": e["oordeel"],
            "grof_totaal_plekken": e["grof_totaal_plekken"], "grof_geldt_op": e["grof_geldt_op"],
            "verdrongen_op": e["verdrongen_op"],
        })
    for f in fijn:
        uit.append({
            "vervulling_id": f["vervulling_id"], "herkomst": "fijn",
            "functie_id": f["functie_id"], "functie_naam": namen.get(f["functie_id"]),
            "ouder_functie_id": f["ouder_functie_id"], "ouder_naam": namen.get(f["ouder_functie_id"]),
            "oordeel": f["oordeel"], "grof_totaal_plekken": None, "grof_geldt_op": None,
            "verdrongen_op": 0,
        })
    uit.sort(key=lambda k: ((k["functie_naam"] or "").lower(), (k["ouder_naam"] or "").lower(), str(k["vervulling_id"])))
    return uit


async def plek_standen(session: AsyncSession, tenant_id) -> dict:
    """ADR-051 besluit 1/5 — de VIER standen per plek, uit dezelfde afleiding als `dekking_overzicht`
    (één bron, twee vensters). Read-only, nooit opgeslagen.

    Per plek (functie + ouder): draagt de plek zelf een antwoord (via de leesregel), dan is de stand
    'hier' (component) of 'niets' (bevinding). Zo niet, en draagt een BOVENLIGGENDE functie een
    component-koppeling, dan 'via_boven' (de omhoog-cue — een derde stand tussen gat en groen). Anders
    'gat'. ⚠ Dit kijkt OMHOOG (hangt er iets bóven mij?), niet omlaag zoals de proces-gap-cue.

    Geeft: `{plekken: [{functie_id, ouder_functie_id, stand, via_functie_id?}], tellers: {...}}` —
    de boom-cue leest `plekken`, de centrale signalering leest dezelfde lijst + `tellers`."""
    tid = _tenant_uuid(tenant_id)
    dekking = await dekking_overzicht(session, tid)
    per_plek = {(d["functie_id"], d["ouder_functie_id"]): d for d in dekking}
    # Een functie "draagt een koppeling" als er ergens een component aan hangt (grof of fijn).
    functies_met_koppeling = {
        d["functie_id"] for d in dekking if d["herkomst"] in ("grof", "fijn")
    }

    paren = await _aggregatie_paren(session, tid)
    ouders_van: dict = {}
    kinderen_met_ouder: set = set()
    alle_functies: set = set()
    for ouder, kind in paren:
        ouders_van.setdefault(kind, []).append(ouder)
        kinderen_met_ouder.add(kind)
        alle_functies.add(ouder)
        alle_functies.add(kind)

    def _dichtstbijzijnde_dragers(start_ouder):
        """BFS OMHOOG langs het pad van DÉZE plek — vanaf de `ouder_functie_id` van de plaatsing,
        NIET vanaf alle ouders van de functie (ADR-044 besluit 4: de plek is de teleenheid; elke
        plaatsing haar eigen antwoord). Geeft `(aantal, enige)` van de dragende voorouders op de
        DICHTSTBIJZIJNDE afstand: bij precies één een functie-id, bij meerdere op gelijke afstand
        `enige=None` + het aantal — nooit een willekeurige keuze (de UUID-tiebreak-fout). Een
        wortelplek (`ouder=None`) heeft niets boven zich. DAG-veilig via `bezocht`."""
        if start_ouder is None:
            return (0, None)
        bezocht: set = set()
        niveau = {start_ouder}
        while niveau:
            dragers = sorted(niveau & functies_met_koppeling, key=str)
            if dragers:
                return (len(dragers), dragers[0] if len(dragers) == 1 else None)
            bezocht |= niveau
            niveau = {o for f in niveau for o in ouders_van.get(f, [])} - bezocht
        return (0, None)

    # Alle plekken: aggregation-paren + wortels (functie zonder ouder).
    plekken: set = {(kind, ouder) for ouder, kind in paren}
    for f in alle_functies:
        if f not in kinderen_met_ouder:
            plekken.add((f, None))

    tellers = {"gat": 0, "via_boven": 0, "hier": 0, "niets": 0, "zonder_oordeel": 0}
    uit: list[dict] = []
    for functie_id, ouder_id in plekken:
        d = per_plek.get((functie_id, ouder_id))
        via, via_aantal = None, 0
        if d and d["herkomst"] == "geen_systeem":
            stand = "niets"
        elif d:  # 'grof' of 'fijn' → een component draagt deze plek
            stand = "hier"
            if any(c.get("oordeel") is None for c in d["componenten"]):
                tellers["zonder_oordeel"] += 1
        else:
            via_aantal, via = _dichtstbijzijnde_dragers(ouder_id)
            stand = "via_boven" if via_aantal > 0 else "gat"
        tellers[stand] += 1
        uit.append({
            "functie_id": functie_id, "ouder_functie_id": ouder_id,
            "stand": stand, "via_functie_id": via, "via_aantal": via_aantal,
        })
    return {"plekken": uit, "tellers": tellers}
