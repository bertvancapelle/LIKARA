"""Service-laag — Bedrijfsfunctie (ADR-043 gate 1a; ADR-044 gate 1a-bis).

Bedrijfsfunctie is een element-subtype (shared-PK). **ADR-044: de boom leeft in
PLAATSINGEN** — `aggregation`-relaties (bron = ouder/geheel, doel = kind/deel) in het
unified relatiemodel, via deze dunne facade (plateau-spiegel: `Relatie` direct bouwen).
Eén functie kan op meerdere plekken staan; `UNIQUE(tenant, bron, doel, relatietype)` op
`relatie` borgt precies één plaatsing per (ouder, functie)-paar. Alle plekken zijn
gelijkwaardig: geen thuisplek, geen rangorde.

Regels (besluiten LI039 + ADR-044):

- **Endpoint-typeborging zit HIER** (de generieke relatie-facade valideert geen
  elementtypen): bron én doel moeten bestaande bedrijfsfuncties zijn ⇒ 422
  `ONGELDIGE_PLAATSING` bij een bestaand element van een ander type, 404 (no-leak) bij
  onbekend.
- **Modelinhoud is niet bewerkbaar** (naam/definitie: `werk_bij`) en haar **plaatsingen
  komen uit de bron** — het gebruikers-pad weigert plaatsings-mutaties op modelinhoud met
  422 `MODELINHOUD_BESCHERMD`; het seed-/import-pad (gate 1b) passeert dat slot legitiem
  via de keyword-only `via_import`.
- **Vervallen = niet koppelbaar**: geen nieuwe plaatsing ónder een vervallen functie
  (gebruikers-pad) → 422 `VERVALLEN_NIET_KOPPELBAAR`.
- **Cycluspreventie servicelaag** (visited-BFS omhoog over álle ouders — de graaf kent
  meerdere ouders) → 422 `CYCLISCHE_HIERARCHIE`. Geen DB-trigger.
- **Verwijderen**: alleen een eigen functie zonder kinderen ("kind" = er bestaat een
  plaatsing waarin deze functie de OUDER is) → anders 409 `HEEFT_DEELFUNCTIES`; een
  model-functie verwijder je nooit (die vervalt) → 422. Dubbele plaatsing → 409
  `PLAATSING_BESTAAT` (pre-check; de UNIQUE is de DB-backstop).

Plaatsingen worden ORM-matig aangemaakt/verwijderd (audit-capture ziet alleen
ORM-mutaties; relaties zijn via het `relatie`-spoor geaudit). Niets hier raakt
lifecycle/score/blokkade — bewust géén engine-import (score blijft de enige
lifecycle-driver; ADR-043/044-invariant).
"""
import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from models.models import Bedrijfsfunctie, Element, ElementType, Referentiemodel, Relatie
from schemas.bedrijfsfunctie import BedrijfsfunctieCreate, BedrijfsfunctieUpdate
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "bedrijfsfunctie"
_AGGREGATION = "aggregation"  # het bestaande relatietype; bron = ouder, doel = kind
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100
_STANDAARD_SORT = "created_at"
_STANDAARD_ORDER = "asc"
_LIKE_ESCAPE = "\\"

# ADR-017 — sorteer-allowlist (rauwe kolomnaam komt NOOIT in ORDER BY); v2n-keyset.
_SORTEERBARE_KOLOMMEN = {
    "created_at": Bedrijfsfunctie.created_at,
    "naam": Bedrijfsfunctie.naam,
}
_WAARDE_PARSERS = {
    "created_at": datetime.fromisoformat,
    "naam": str,
}


def _escape_like(term: str) -> str:
    return term.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2).replace("%", r"\%").replace("_", r"\_")


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def haal_op(session: AsyncSession, tenant_id, functie_id) -> Bedrijfsfunctie:
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Bedrijfsfunctie).where(
                Bedrijfsfunctie.id == functie_id, Bedrijfsfunctie.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, functie_id)
    return obj


async def _element_type(session: AsyncSession, tid: uuid.UUID, element_id) -> str | None:
    rij = (
        await session.execute(
            select(Element.element_type).where(Element.tenant_id == tid, Element.id == element_id)
        )
    ).scalar_one_or_none()
    return getattr(rij, "value", rij) if rij is not None else None


async def _vereis_bedrijfsfunctie(session: AsyncSession, tid: uuid.UUID, element_id, rol: str) -> None:
    """Endpoint-typeborging (ADR-044 1.1): 404 no-leak bij onbekend; 422
    `ONGELDIGE_PLAATSING` bij een bestaand element van een ander type."""
    et = await _element_type(session, tid, element_id)
    if et is None:
        raise NietGevonden(_ENTITEIT, element_id)
    if et != ElementType.bedrijfsfunctie.value:
        raise OngeldigeRegistratie(
            "ONGELDIGE_PLAATSING",
            f"De {rol} van een plaatsing moet een bedrijfsfunctie zijn.",
        )


# ── Plaatsingen (de boom) — leeshulpen ────────────────────────────────────────────

async def _plaatsings_paren(session: AsyncSession, tid: uuid.UUID) -> list[tuple[uuid.UUID, uuid.UUID]]:
    """Alle plaatsingen van de tenant als (ouder, kind)-paren: aggregation-relaties
    waarvan BEIDE endpoints bedrijfsfuncties zijn (harde scoping — plateau-lidmaatschap
    gebruikt hetzelfde relatietype met andere endpoints en blijft zo buiten beeld)."""
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


def _ouders_map(paren: list[tuple[uuid.UUID, uuid.UUID]]) -> dict:
    m: dict = {}
    for ouder, kind in paren:
        m.setdefault(kind, []).append(ouder)
    for lijst in m.values():
        lijst.sort(key=str)  # deterministisch; geen rangorde-betekenis
    return m


def _kinderen_map(paren: list[tuple[uuid.UUID, uuid.UUID]]) -> dict:
    m: dict = {}
    for ouder, kind in paren:
        m.setdefault(ouder, []).append(kind)
    return m


async def _plaatsing_rij(session: AsyncSession, tid: uuid.UUID, ouder_id, functie_id) -> Relatie | None:
    return (
        await session.execute(
            select(Relatie).where(
                Relatie.tenant_id == tid,
                Relatie.relatietype == _AGGREGATION,
                Relatie.bron_id == ouder_id,
                Relatie.doel_id == functie_id,
            )
        )
    ).scalar_one_or_none()


async def _zou_kring_maken(session: AsyncSession, tid: uuid.UUID, functie_id, nieuw_ouder_id) -> bool:
    """True als functie→ouder een kring zou sluiten: klim vanaf de voorgestelde ouder
    omhoog over ÁLLE diens ouders (BFS + visited-set — de graaf kent meervoudige
    ouders); raken we de functie, dan is zij een (transitieve) voorouder → kring."""
    paren = await _plaatsings_paren(session, tid)
    ouders = _ouders_map(paren)
    visited: set = set()
    frontier = [nieuw_ouder_id]
    while frontier:
        volgende = []
        for huidige in frontier:
            if huidige == functie_id:
                return True
            if huidige in visited:
                continue
            visited.add(huidige)
            volgende.extend(ouders.get(huidige, []))
        frontier = volgende
    return False


# ── Read-vorm ─────────────────────────────────────────────────────────────────────

async def _model_labels(session: AsyncSession, tid: uuid.UUID) -> dict:
    """Eén label-map per lijst/read (geen N+1): referentiemodel-id → (naam, versie)."""
    rijen = (
        await session.execute(
            select(Referentiemodel.id, Referentiemodel.naam, Referentiemodel.versie)
            .where(Referentiemodel.tenant_id == tid)
        )
    ).all()
    return {r.id: (r.naam, r.versie) for r in rijen}


def _lees(obj: Bedrijfsfunctie, model_labels: dict | None = None,
          ouder_ids: list | None = None) -> dict:
    naam_versie = (model_labels or {}).get(obj.bron_model_id)
    return {
        "id": obj.id,
        "naam": obj.naam,
        "definitie": obj.definitie,
        "ouder_ids": ouder_ids or [],
        "bron_model_id": obj.bron_model_id,
        "bron_sleutel": obj.bron_sleutel,
        "bron_model_naam": naam_versie[0] if naam_versie else None,
        "bron_model_versie": naam_versie[1] if naam_versie else None,
        "vervallen": obj.vervallen,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


def _is_modelinhoud(obj: Bedrijfsfunctie) -> bool:
    return obj.bron_sleutel is not None


async def _lees_met_ouders(session: AsyncSession, tid: uuid.UUID, obj: Bedrijfsfunctie) -> dict:
    paren = await _plaatsings_paren(session, tid)
    return _lees(obj, await _model_labels(session, tid), _ouders_map(paren).get(obj.id, []))


# ── CRUD ─────────────────────────────────────────────────────────────────────────

async def maak_aan(
    session: AsyncSession, tenant_id, data: BedrijfsfunctieCreate, *,
    bron_model_id=None, bron_sleutel: str | None = None,
) -> dict:
    """Het gebruikers-pad (route) maakt uitsluitend EIGEN functies (bron leeg). De
    keyword-only herkomst-parameters zijn het seed-/import-pad (gate 1b). Een optionele
    `ouder_id` in de Create = aanmaken mét eerste plaatsing in één handeling
    ("+ Deelfunctie"); de plaatsing loopt door dezelfde `plaats`-validaties."""
    tid = _tenant_uuid(tenant_id)
    if data.ouder_id is not None:
        # Vooraf valideren (type/vervallen) zodat er geen half-aangemaakte functie
        # achterblijft; kring is onmogelijk (de functie bestaat nog niet).
        await _vereis_bedrijfsfunctie(session, tid, data.ouder_id, "ouder")
        ouder = await haal_op(session, tid, data.ouder_id)
        if ouder.vervallen and bron_sleutel is None:
            raise OngeldigeRegistratie(
                "VERVALLEN_NIET_KOPPELBAAR",
                "Deze functie bestaat niet meer in het referentiemodel; "
                "er kan niets nieuws onder gehangen worden.",
            )
    elem = Element(tenant_id=tid, element_type=ElementType.bedrijfsfunctie)
    session.add(elem)
    await session.flush()
    obj = Bedrijfsfunctie(
        id=elem.id, tenant_id=tid, naam=data.naam, definitie=data.definitie,
        bron_model_id=bron_model_id, bron_sleutel=bron_sleutel,
    )
    session.add(obj)
    if data.ouder_id is not None:
        session.add(Relatie(
            tenant_id=tid, bron_id=data.ouder_id, doel_id=elem.id,
            relatietype=_AGGREGATION, kenmerken={},
        ))
    await session.commit()
    await session.refresh(obj)
    return await _lees_met_ouders(session, tid, obj)


async def lees_detail(session: AsyncSession, tenant_id, functie_id) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, functie_id)
    return await _lees_met_ouders(session, tid, obj)


async def werk_bij(
    session: AsyncSession, tenant_id, functie_id, data: BedrijfsfunctieUpdate
) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, functie_id)
    velden = data.model_dump(exclude_unset=True)
    # ADR-043 kern (besluit 5): modelinhoud lees je — je wijzigt hem niet. Naam en
    # definitie komen van de bron; élke wijziging op een bron-dragende functie wordt
    # geweigerd (de UI spiegelt dit, maar de service is de handhaver).
    if velden and _is_modelinhoud(obj):
        raise OngeldigeRegistratie(
            "MODELINHOUD_BESCHERMD",
            "Deze functie komt uit het referentiemodel; naam en definitie "
            "worden door het model bepaald en zijn hier niet te wijzigen.",
        )
    for veld, waarde in velden.items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return await _lees_met_ouders(session, tid, obj)


async def verwijder(session: AsyncSession, tenant_id, functie_id) -> None:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, functie_id)  # 404 kruis-tenant
    # Een model-functie verwijder je nooit — die vervalt bij een herinlees (gate 1b).
    if _is_modelinhoud(obj):
        raise OngeldigeRegistratie(
            "MODELINHOUD_BESCHERMD",
            "Deze functie komt uit het referentiemodel en kan niet verwijderd worden; "
            "verdwijnt ze uit het model, dan wordt ze als vervallen gemarkeerd.",
        )
    # "Zonder kinderen" = er bestaat geen plaatsing waarin deze functie de OUDER is
    # (ADR-044 1.2). Pre-check ⇒ 409; de element-cascade zou anders stil de
    # plaatsings-rijen wegvagen terwijl de kinderen wees achterblijven als wortels.
    kind_bf = aliased(Bedrijfsfunctie)
    heeft_kind = (
        await session.execute(
            select(Relatie.id)
            .join(kind_bf, (kind_bf.id == Relatie.doel_id) & (kind_bf.tenant_id == tid))
            .where(
                Relatie.tenant_id == tid,
                Relatie.relatietype == _AGGREGATION,
                Relatie.bron_id == functie_id,
            ).limit(1)
        )
    ).scalar_one_or_none()
    if heeft_kind is not None:
        raise RegistratieConflict(
            "HEEFT_DEELFUNCTIES",
            "Deze functie heeft deelfuncties; verplaats of verwijder die eerst.",
        )
    # Verwijder via het element-supertype (cascade element → subtype → eigen
    # plaatsings-rijen als kind, via de relatie-endpoint-FK's).
    await session.execute(delete(Element).where(Element.tenant_id == tid, Element.id == functie_id))
    await session.commit()


# ── Plaatsingen (ADR-044) — muteren ──────────────────────────────────────────────

async def plaats(
    session: AsyncSession, tenant_id, functie_id, ouder_id, *, via_import: bool = False,
) -> dict:
    """Voeg één plaatsing toe: hang `functie_id` (kind) onder `ouder_id`. Meerdere
    ouders = meerdere plaatsingen, alle gelijkwaardig. `via_import=True` is het
    seed-/import-pad (gate 1b): modelinhoud-plaatsingen komen uit de bron en passeren
    het gebruikers-slot legitiem."""
    tid = _tenant_uuid(tenant_id)
    await _vereis_bedrijfsfunctie(session, tid, functie_id, "functie")
    await _vereis_bedrijfsfunctie(session, tid, ouder_id, "ouder")
    if ouder_id == functie_id:
        raise OngeldigeRegistratie(
            "CYCLISCHE_HIERARCHIE", "Een bedrijfsfunctie kan niet onder zichzelf hangen."
        )
    obj = await haal_op(session, tid, functie_id)
    if not via_import:
        # De plaatsingen van een modelfunctie komen uit de bron (ADR-044 1.2).
        if _is_modelinhoud(obj):
            raise OngeldigeRegistratie(
                "MODELINHOUD_BESCHERMD",
                "Deze functie komt uit het referentiemodel; haar plek in de boom "
                "wordt door het model bepaald.",
            )
        ouder = await haal_op(session, tid, ouder_id)
        if ouder.vervallen:
            raise OngeldigeRegistratie(
                "VERVALLEN_NIET_KOPPELBAAR",
                "Deze functie bestaat niet meer in het referentiemodel; "
                "er kan niets nieuws onder gehangen worden.",
            )
    if await _zou_kring_maken(session, tid, functie_id, ouder_id):
        raise OngeldigeRegistratie(
            "CYCLISCHE_HIERARCHIE",
            "Deze ouder-functie is (via haar plaatsingen) een deelfunctie van deze "
            "functie — dat zou een kring maken.",
        )
    if await _plaatsing_rij(session, tid, ouder_id, functie_id) is not None:
        raise RegistratieConflict(
            "PLAATSING_BESTAAT", "Deze functie staat al onder deze ouder."
        )
    session.add(Relatie(
        tenant_id=tid, bron_id=ouder_id, doel_id=functie_id,
        relatietype=_AGGREGATION, kenmerken={},
    ))
    await session.commit()
    await session.refresh(obj)
    return await _lees_met_ouders(session, tid, obj)


async def verwijder_plaatsing(
    session: AsyncSession, tenant_id, functie_id, ouder_id, *, via_import: bool = False,
) -> dict:
    """Haal één plaatsing weg (de functie zelf blijft bestaan; zonder plaatsingen wordt
    ze een wortel — dat is legitiem). Gebruikers-pad alleen op eigen functies."""
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tid, functie_id)
    if not via_import and _is_modelinhoud(obj):
        raise OngeldigeRegistratie(
            "MODELINHOUD_BESCHERMD",
            "Deze functie komt uit het referentiemodel; haar plek in de boom "
            "wordt door het model bepaald.",
        )
    rij = await _plaatsing_rij(session, tid, ouder_id, functie_id)
    if rij is None:
        raise NietGevonden("plaatsing", ouder_id)
    await session.delete(rij)  # ORM-delete → audit via het relatie-spoor
    await session.commit()
    await session.refresh(obj)
    return await _lees_met_ouders(session, tid, obj)


# ── Lijst + subboom ──────────────────────────────────────────────────────────────

async def lijst(
    session: AsyncSession, tenant_id, *,
    limit: int = _STANDAARD_LIMIT, after: str | None = None,
    sort: str = _STANDAARD_SORT, order: str = _STANDAARD_ORDER,
    zoek: str | None = None,
) -> tuple[list[dict], str | None]:
    """v2n-keyset-lijst binnen de tenant (ADR-017; default = created_at oplopend).
    `zoek` = ge-escapete ILIKE op `naam`. Elke rij draagt haar `ouder_ids` (alle
    plaatsingen — één relatie-query per pagina, geen N+1). Onbekend sort/order of
    cursor-mismatch ⇒ ValueError (route: 422 via de enum resp. 400 ONGELDIGE_CURSOR)."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    if sort not in _SORTEERBARE_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    kolom = _SORTEERBARE_KOLOMMEN[sort]

    stmt = select(Bedrijfsfunctie).where(Bedrijfsfunctie.tenant_id == tid)
    if zoek:
        stmt = stmt.where(
            Bedrijfsfunctie.naam.ilike(f"%{_escape_like(zoek)}%", escape=_LIKE_ESCAPE)
        )
    if after:
        c_sort, c_order, c_is_null, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_is_null else _WAARDE_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(
                kolom, Bedrijfsfunctie.id, order=order,
                is_null=c_is_null, waarde=c_waarde, cursor_id=c_id,
            )
        )
    stmt = stmt.order_by(
        *keyset_order_by_nulls_last(kolom, Bedrijfsfunctie.id, order)
    ).limit(limit + 1)

    rijen = list((await session.execute(stmt)).scalars().all())
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    volgende = (
        encode_sort_cursor_nullable(sort=sort, order=order, waarde=getattr(items[-1], sort), id=items[-1].id)
        if heeft_meer else None
    )
    labels = await _model_labels(session, tid)
    ouders = _ouders_map(await _plaatsings_paren(session, tid))
    return [_lees(o, labels, ouders.get(o.id, [])) for o in items], volgende


async def subboom(session: AsyncSession, tenant_id, functie_id) -> list[dict]:
    """Read-traversal van de subboom (alle deelfuncties, alle niveaus) vanaf één
    functie, over de plaatsingen. BFS met visited-set (cyclus-veilig; elke functie één
    keer, op haar KORTSTE afstand — `ouder_id` in het item is de traversal-ouder).
    Read-only — geen schrijfpaden, geen engine-koppeling."""
    tid = _tenant_uuid(tenant_id)
    wortel = await haal_op(session, tenant_id, functie_id)  # 404 kruis-tenant
    paren = await _plaatsings_paren(session, tid)
    kinderen = _kinderen_map(paren)
    per_id = {
        o.id: o for o in (
            await session.execute(
                select(Bedrijfsfunctie).where(Bedrijfsfunctie.tenant_id == tid)
            )
        ).scalars().all()
    }
    geraakt: list[dict] = []
    visited = {functie_id}
    frontier = [(functie_id, [wortel.naam])]
    niveau = 0
    while frontier:
        niveau += 1
        volgende = []
        for ouder_id, pad in sorted(frontier, key=lambda x: str(x[0])):
            for kind_id in sorted(kinderen.get(ouder_id, []), key=lambda k: (per_id[k].naam if k in per_id else "", str(k))):
                if kind_id in visited or kind_id not in per_id:
                    continue
                visited.add(kind_id)
                k = per_id[kind_id]
                kind_pad = pad + [k.naam]
                geraakt.append({
                    "id": k.id, "naam": k.naam, "ouder_id": ouder_id,
                    "vervallen": k.vervallen, "niveau": niveau, "pad": kind_pad,
                })
                volgende.append((kind_id, kind_pad))
        frontier = volgende
    return geraakt
