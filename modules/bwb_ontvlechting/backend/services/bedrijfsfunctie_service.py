"""Service-laag — Bedrijfsfunctie (ADR-043 gate 1a).

Bedrijfsfunctie is een element-subtype (shared-PK), nestbaar via `ouder_id` (composiet
self-FK) — het proces-recept 1-op-1, plus de ADR-043-regels (besluiten LI039):

- **Modelinhoud is niet bewerkbaar** (besluit 5, ADR-043 kern): draagt een functie een
  bronsleutel, dan zijn naam/definitie/ouder read-only → 422 `MODELINHOUD_BESCHERMD`.
  Een EIGEN functie (geen bronsleutel) is volledig bewerkbaar. Verwijderen van een
  model-functie kan nooit (die vervalt bij een herinlees, gate 1b) → 422.
- **Vervallen = zichtbaar, niet meer koppelbaar** (besluit 6): een nieuwe functie kan
  niet ónder een vervallen functie hangen en een eigen functie kan er niet naartoe
  verplaatst worden → 422 `VERVALLEN_NIET_KOPPELBAAR` (verder bouwen op een verdwenen
  fundament mag niet stil gebeuren). Bestaande kinderen blijven staan.
- **Cycluspreventie**: visited-set-traversal langs de ouder-keten (proces-recept),
  geen DB-trigger → 422 `CYCLISCHE_HIERARCHIE`.
- **Verwijdergedrag**: een eigen functie met directe deelfuncties → 409
  `HEEFT_DEELFUNCTIES` (pre-check; de self-FK `ON DELETE RESTRICT` is de DB-backstop).

Het gebruikers-pad (`maak_aan` via de route) maakt uitsluitend eigen functies; de
seed/import (gate 1b) zet herkomst via de keyword-only `bron_model_id`/`bron_sleutel`.
De lijst is server-side sorteerbaar (ADR-017, v2n-keyset) + `zoek`-ILIKE.

Niets hier raakt lifecycle/score/blokkade — er is bewust géén engine-import (score
blijft de enige lifecycle-driver; ADR-043-invariant).
"""
import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Bedrijfsfunctie, Element, ElementType, Referentiemodel
from schemas.bedrijfsfunctie import BedrijfsfunctieCreate, BedrijfsfunctieUpdate
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "bedrijfsfunctie"
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


async def _model_labels(session: AsyncSession, tid: uuid.UUID) -> dict:
    """Eén label-map per lijst/read (geen N+1): referentiemodel-id → (naam, versie).
    De ingelezen-modellen-set per tenant is klein (één rij per model)."""
    rijen = (
        await session.execute(
            select(Referentiemodel.id, Referentiemodel.naam, Referentiemodel.versie)
            .where(Referentiemodel.tenant_id == tid)
        )
    ).all()
    return {r.id: (r.naam, r.versie) for r in rijen}


def _lees(obj: Bedrijfsfunctie, model_labels: dict | None = None) -> dict:
    naam_versie = (model_labels or {}).get(obj.bron_model_id)
    return {
        "id": obj.id,
        "naam": obj.naam,
        "definitie": obj.definitie,
        "ouder_id": obj.ouder_id,
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


async def _zou_kring_maken(
    session: AsyncSession, tid: uuid.UUID, functie_id, nieuw_ouder_id
) -> bool:
    """True als `functie_id` met ouder `nieuw_ouder_id` een kring zou vormen: loop de
    ouder-keten vanaf de voorgestelde ouder omhoog; raken we `functie_id`, dan is die
    een (transitieve) voorouder van de ouder → kring. Visited-set = cyclus-veilig."""
    huidige = nieuw_ouder_id
    visited: set = set()
    while huidige is not None:
        if huidige == functie_id:
            return True
        if huidige in visited:
            break  # vangnet tegen een (niet zou mogen bestaan) bestaande kring
        visited.add(huidige)
        huidige = (
            await session.execute(
                select(Bedrijfsfunctie.ouder_id).where(
                    Bedrijfsfunctie.tenant_id == tid, Bedrijfsfunctie.id == huidige
                )
            )
        ).scalar_one_or_none()
    return False


async def _valideer_ouder(session: AsyncSession, tid: uuid.UUID, functie_id, ouder_id) -> None:
    """Ouder bestaat binnen de tenant (404 no-leak); niet vervallen (besluit LI039-6:
    verder bouwen op een verdwenen fundament mag niet stil); geen self-parent; geen kring."""
    if ouder_id is None:
        return
    if ouder_id == functie_id:
        raise OngeldigeRegistratie(
            "CYCLISCHE_HIERARCHIE", "Een bedrijfsfunctie kan niet onder zichzelf hangen."
        )
    ouder = await haal_op(session, tid, ouder_id)  # 404 als de ouder niet (in tenant) bestaat
    if ouder.vervallen:
        raise OngeldigeRegistratie(
            "VERVALLEN_NIET_KOPPELBAAR",
            "Deze functie bestaat niet meer in het referentiemodel; "
            "er kan niets nieuws onder gehangen worden.",
        )
    if functie_id is not None and await _zou_kring_maken(session, tid, functie_id, ouder_id):
        raise OngeldigeRegistratie(
            "CYCLISCHE_HIERARCHIE",
            "Deze ouder-functie is een deelfunctie van deze functie — dat zou een kring maken.",
        )


async def maak_aan(
    session: AsyncSession, tenant_id, data: BedrijfsfunctieCreate, *,
    bron_model_id=None, bron_sleutel: str | None = None,
) -> dict:
    """Het gebruikers-pad (route) maakt uitsluitend EIGEN functies (bron leeg). De
    keyword-only herkomst-parameters zijn het seed-/import-pad (gate 1b): beide samen
    gezet = modelinhoud (de DB-CHECK `ck_bedrijfsfunctie_bron_paar` is de backstop)."""
    tid = _tenant_uuid(tenant_id)
    # Een nieuwe functie kan nog niemands voorouder zijn → alleen ouder-bestaan +
    # vervallen-check (functie_id=None ⇒ geen kring-check nodig).
    await _valideer_ouder(session, tid, None, data.ouder_id)
    elem = Element(tenant_id=tid, element_type=ElementType.bedrijfsfunctie)
    session.add(elem)
    await session.flush()
    obj = Bedrijfsfunctie(
        id=elem.id, tenant_id=tid, naam=data.naam, definitie=data.definitie,
        ouder_id=data.ouder_id, bron_model_id=bron_model_id, bron_sleutel=bron_sleutel,
    )
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return _lees(obj, await _model_labels(session, tid))


async def lees_detail(session: AsyncSession, tenant_id, functie_id) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, functie_id)
    return _lees(obj, await _model_labels(session, tid))


async def werk_bij(
    session: AsyncSession, tenant_id, functie_id, data: BedrijfsfunctieUpdate
) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, functie_id)
    velden = data.model_dump(exclude_unset=True)
    # ADR-043 kern (besluit 5): modelinhoud lees je — je wijzigt hem niet. Naam,
    # definitie én plek komen van de bron; élke wijziging op een bron-dragende functie
    # wordt geweigerd (de UI spiegelt dit, maar de service is de handhaver).
    if velden and _is_modelinhoud(obj):
        raise OngeldigeRegistratie(
            "MODELINHOUD_BESCHERMD",
            "Deze functie komt uit het referentiemodel; naam, definitie en plek "
            "worden door het model bepaald en zijn hier niet te wijzigen.",
        )
    if "ouder_id" in velden:
        # Verplaatsen = één veldwijziging; server-side cycluspreventie + vervallen-guard.
        await _valideer_ouder(session, tid, obj.id, velden["ouder_id"])
    for veld, waarde in velden.items():
        setattr(obj, veld, waarde)
    await session.commit()
    await session.refresh(obj)
    return _lees(obj, await _model_labels(session, tid))


async def verwijder(session: AsyncSession, tenant_id, functie_id) -> None:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, functie_id)  # 404 kruis-tenant
    # Een model-functie verwijder je nooit — die vervalt bij een herinlees (gate 1b);
    # hard verwijderen zou via CASCADE eigen registratie meesleuren (besluit LI039-6).
    if _is_modelinhoud(obj):
        raise OngeldigeRegistratie(
            "MODELINHOUD_BESCHERMD",
            "Deze functie komt uit het referentiemodel en kan niet verwijderd worden; "
            "verdwijnt ze uit het model, dan wordt ze als vervallen gemarkeerd.",
        )
    # Verwijdergedrag: een functie met directe deelfuncties wordt niet (stilzwijgend)
    # met haar subboom weggevaagd. Pre-check ⇒ 409; de self-FK RESTRICT is de DB-backstop.
    heeft_kind = (
        await session.execute(
            select(Bedrijfsfunctie.id).where(
                Bedrijfsfunctie.tenant_id == tid, Bedrijfsfunctie.ouder_id == functie_id
            ).limit(1)
        )
    ).scalar_one_or_none()
    if heeft_kind is not None:
        raise RegistratieConflict(
            "HEEFT_DEELFUNCTIES",
            "Deze functie heeft deelfuncties; verplaats of verwijder die eerst.",
        )
    # Verwijder via het element-supertype (cascade element → bedrijfsfunctie-subtype).
    await session.execute(delete(Element).where(Element.tenant_id == tid, Element.id == functie_id))
    await session.commit()


async def lijst(
    session: AsyncSession, tenant_id, *,
    limit: int = _STANDAARD_LIMIT, after: str | None = None,
    sort: str = _STANDAARD_SORT, order: str = _STANDAARD_ORDER,
    zoek: str | None = None, ouder_id=None,
) -> tuple[list[dict], str | None]:
    """v2n-keyset-lijst binnen de tenant (ADR-017; default = created_at oplopend).
    `zoek` = ge-escapete ILIKE op `naam`; `ouder_id` filtert op directe deelfuncties.
    Onbekend sort/order of cursor-mismatch ⇒ ValueError (route: 422 via de enum resp.
    400 ONGELDIGE_CURSOR)."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    if sort not in _SORTEERBARE_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    kolom = _SORTEERBARE_KOLOMMEN[sort]

    stmt = select(Bedrijfsfunctie).where(Bedrijfsfunctie.tenant_id == tid)
    if ouder_id is not None:
        stmt = stmt.where(Bedrijfsfunctie.ouder_id == ouder_id)
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
    return [_lees(o, labels) for o in items], volgende


async def subboom(session: AsyncSession, tenant_id, functie_id) -> list[dict]:
    """Read-traversal van de subboom (alle deelfuncties, alle niveaus) vanaf één functie.
    Iteratieve BFS per niveau met visited-set (cyclus-veilig; kortste afstand `niveau` +
    pad). Read-only — geen schrijfpaden, geen engine-koppeling. Leesbasis voor het
    functieboom-scherm (blok 2) en later de gap-cue (gate 3)."""
    tid = _tenant_uuid(tenant_id)
    wortel = await haal_op(session, tenant_id, functie_id)  # 404 kruis-tenant
    geraakt: list[dict] = []
    visited = {functie_id}
    frontier = [(functie_id, [wortel.naam])]
    niveau = 0
    while frontier:
        niveau += 1
        ouder_pad = {n: pad for (n, pad) in frontier}
        rijen = (
            await session.execute(
                select(Bedrijfsfunctie)
                .where(
                    Bedrijfsfunctie.tenant_id == tid,
                    Bedrijfsfunctie.ouder_id.in_(list(ouder_pad.keys())),
                )
                .order_by(Bedrijfsfunctie.naam, Bedrijfsfunctie.id)
            )
        ).scalars().all()
        volgende = []
        for r in rijen:
            if r.id in visited:
                continue
            visited.add(r.id)
            pad = ouder_pad[r.ouder_id] + [r.naam]
            geraakt.append({
                "id": r.id, "naam": r.naam, "ouder_id": r.ouder_id,
                "vervallen": r.vervallen, "niveau": niveau, "pad": pad,
            })
            volgende.append((r.id, pad))
        frontier = volgende
    return geraakt
