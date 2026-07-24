"""Service-laag voor de entiteit Checklistscore (ADR-009/013, Model A).

Naast de standaard tenant-bescherming (RLS + expliciete `tenant_id`-filter):
- ouder-`Applicatie` tenant-scoped valideren (→ 404);
- `vraag_code` valideren tegen de globale `ChecklistVraag`-set (→ 404);
- uniciteit (tenant, applicatie, vraag_code) afdwingen (→ 409, met
  `uq_checklistscore_app_vraag` als backstop);
- de invariant score↔blokkade handhaven (auto-blokkade, ADR-013 B2);
- na elke schrijf/verwijder `herbereken_lifecycle` aanroepen (ADR-013 B3).

`applicatie_id`/`vraag_code` zijn immutabel (niet in Update).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    AntwoordType,
    Blokkade,
    BlokkadeStatus,
    ChecklistScore,
    ChecklistVraag,
    ChecklistVraagOptie,
    Checklistscore,
    Component,
    ComponentProfiel,
)
from schemas.checklistscore import ChecklistscoreCreate, ChecklistscoreUpdate
from services import componentconfig_catalog as comp_catalog
from services import lifecycle_service
from services import partij_service
from services.errors import (
    ChecklistscoreConflict,
    NietGevonden,
    OngeldigAntwoord,
    OngeldigeRegistratie,
)
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "checklistscore"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100

# Default-sortering = exact het pre-CD020-gedrag (created_at oplopend).
_STANDAARD_SORT = "created_at"
_STANDAARD_ORDER = "asc"

# Allowlist-kolommen (ADR-017 B2) — single source naast `ChecklistscoreSorteerveld`.
_SORTEERBARE_KOLOMMEN = {
    "created_at": Checklistscore.created_at,
    "checklistvraag_id": Checklistscore.checklistvraag_id,
    "score": Checklistscore.score,
}
_WAARDE_PARSERS = {
    "created_at": datetime.fromisoformat,
    "checklistvraag_id": uuid.UUID,
    "score": ChecklistScore,
}

# Scores die een actieve blokkade vereisen (ADR-013 B2).
_BLOKKADE_VEREIST = (ChecklistScore.nee, ChecklistScore.deels)
_BLOKKADE_ACTIEF = (BlokkadeStatus.open, BlokkadeStatus.in_behandeling)


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _zet_vraag_gewijzigd(obj: Checklistscore, huidige_tekst: str | None) -> None:
    """ADR-056 besluit 4 — "verouderd" is een VERGELIJKING, geen opgeslagen markering:
    de bevroren formulering wijkt af van de huidige vraagtekst. Transient read-veld;
    een onbekende vraag (hoort niet voor te komen) leest als niet-gewijzigd."""
    obj.vraag_gewijzigd = (
        huidige_tekst is not None and obj.vraag_bevroren != huidige_tekst
    )


async def _verrijk(session: AsyncSession, tid: uuid.UUID, obj: Checklistscore) -> Checklistscore:
    """ADR-037 — zet de afgeleide read-velden (`verantwoordelijke_naam`/`-afdeling`) op de rij.
    Read-only join op de partij (leeslaag); raakt de engine niet. Transient attrs — niet gemapt,
    niet persistent — die `ChecklistscoreRead` (from_attributes) uitleest.
    ADR-056: idem voor `vraag_gewijzigd` (vergelijking bevroren ↔ huidige vraagtekst)."""
    info = (
        await partij_service.resolve_verantwoordelijken(session, tid, [obj.verantwoordelijke_id])
    ).get(obj.verantwoordelijke_id)
    obj.verantwoordelijke_naam = info["naam"] if info else None
    obj.verantwoordelijke_afdeling = info["afdeling"] if info else None
    obj.verantwoordelijke_organisatie = info["organisatie"] if info else None
    _zet_vraag_gewijzigd(obj, await _huidige_vraagtekst(session, obj.checklistvraag_id))
    return obj


async def _verrijk_lijst(session: AsyncSession, tid: uuid.UUID, items: list[Checklistscore]) -> None:
    """Batch-variant van `_verrijk` (één partij-query + één vraag-query voor de pagina)."""
    info_map = await partij_service.resolve_verantwoordelijken(
        session, tid, [o.verantwoordelijke_id for o in items]
    )
    tekst_map = {
        vraag_id: tekst
        for vraag_id, tekst in (
            await session.execute(
                select(ChecklistVraag.id, ChecklistVraag.vraag).where(
                    ChecklistVraag.id.in_({o.checklistvraag_id for o in items})
                )
            )
        ).all()
    } if items else {}
    for o in items:
        info = info_map.get(o.verantwoordelijke_id)
        o.verantwoordelijke_naam = info["naam"] if info else None
        o.verantwoordelijke_afdeling = info["afdeling"] if info else None
        o.verantwoordelijke_organisatie = info["organisatie"] if info else None
        _zet_vraag_gewijzigd(o, tekst_map.get(o.checklistvraag_id))


def enum_opties() -> dict[str, list[str]]:
    """Read-only keuzewaarden voor de score (single source, DB-vrij)."""
    return {"score": [e.value for e in ChecklistScore]}


async def _componenttype_van_profiel(session: AsyncSession, tid: uuid.UUID, component_id) -> str:
    """Het componenttype van een **scoorbaar** component (= heeft een `component_profiel`,
    ADR-022 Fase E). Geen profiel binnen de tenant ⇒ `NietGevonden` (niet scoorbaar)."""
    componenttype = (
        await session.execute(
            select(Component.componenttype)
            .join(ComponentProfiel, ComponentProfiel.id == Component.id)
            .where(Component.id == component_id, Component.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if componenttype is None:
        raise NietGevonden("component_profiel", component_id)
    return componenttype


async def _verzeker_checklist_open(session: AsyncSession, componenttype: str) -> None:
    """ADR-027 — read-only-invariant: score-INVOER (maak/werk_bij) mag alleen als het
    componenttype `checklist_dragend` is. Een gesloten type → 422 `CHECKLIST_GESLOTEN`.

    Dit is een **invoer-blokkade**, GEEN engine-mutatie: bestaande scores/lifecycle blijven
    staan en leesbaar; het auto-blokkade-/lifecycle-pad (`_synchroniseer_blokkade`/
    `herbereken_lifecycle`) wordt NIET via dit pad geraakt (die draaien intern, niet als invoer).
    Symmetrisch: type weer `checklist_dragend=true` → invoer weer mogelijk."""
    if not await comp_catalog.is_checklist_dragend(session, componenttype):
        raise OngeldigeRegistratie(
            "CHECKLIST_GESLOTEN",
            "De checklist voor dit componenttype is gesloten voor bewerking.",
        )


async def _verzeker_checklist_open_voor(session: AsyncSession, tid: uuid.UUID, component_id) -> None:
    """werk_bij-variant: leid het componenttype af uit het component en pas de invariant toe."""
    await _verzeker_checklist_open(session, await _componenttype_van_profiel(session, tid, component_id))


async def _valideer_checklistvraag_id(
    session: AsyncSession, checklistvraag_id, componenttype: str
) -> str:
    """Type-bewuste vraagvalidatie (ADR-022 Fase B): een score mag alleen verwijzen
    naar een `checklistvraag` waarvan `componenttype` gelijk is aan dat van het
    betrokken component. Onbekende vraag óf type-mismatch ⇒ `NietGevonden` (404) —
    de vraag is geen geldige checklistvraag voor dít component (geen aparte/nieuwe
    foutcode; OP-6-stijl: geen onderscheid 'bestaat niet' vs 'ander type').

    Geeft de huidige VRAAGTEKST terug (ADR-056 besluit 4): het aanmaak-pad bevriest
    die bij het antwoord — wat er gevraagd werd toen het gegeven werd."""
    tekst = (
        await session.execute(
            select(ChecklistVraag.vraag).where(
                ChecklistVraag.id == checklistvraag_id,
                ChecklistVraag.componenttype == componenttype,
            )
        )
    ).scalar_one_or_none()
    if tekst is None:
        raise NietGevonden("checklistvraag", checklistvraag_id)
    return tekst


async def _huidige_vraagtekst(session: AsyncSession, checklistvraag_id) -> str | None:
    """De huidige formulering van de vraag (RLS-scoped) — voor het herbevriezen bij
    opnieuw antwoorden (ADR-056 besluit 8)."""
    return (
        await session.execute(
            select(ChecklistVraag.vraag).where(ChecklistVraag.id == checklistvraag_id)
        )
    ).scalar_one_or_none()


def _is_blokkerend(score) -> bool:
    """Score die een blokkade rechtvaardigt (`nee`/`deels`)."""
    return score in _BLOKKADE_VEREIST


async def _valideer_antwoord_waarde(
    session: AsyncSession, checklistvraag_id, antwoord_waarde
) -> None:
    """Semantische validatie van `antwoord_waarde` tegen de vraagconfiguratie (ADR-019).

    Onafhankelijk van het score-pad — raakt blokkade/lifecycle NIET. De structurele
    vorm (envelope/typen) is al door Pydantic gevalideerd; hier de betekenis: past
    het type bij de vraag, en is de gekozen optiesleutel een ACTIEVE optie van die
    vraag. Ongeldig ⇒ `OngeldigAntwoord` (HTTP 422-envelope).
    """
    if antwoord_waarde is None:
        return
    vraag = (
        await session.execute(select(ChecklistVraag).where(ChecklistVraag.id == checklistvraag_id))
    ).scalar_one_or_none()
    if vraag is None:
        return  # checklistvraag_id-bestaan wordt elders afgedwongen (maak_aan)

    if vraag.antwoordtype == AntwoordType.geen:
        raise OngeldigAntwoord("Deze vraag heeft geen gestructureerd antwoordveld.")
    if vraag.antwoordtype == AntwoordType.getal:
        if "getal" not in antwoord_waarde:
            raise OngeldigAntwoord("Voor deze vraag wordt een getal verwacht.")
        return  # bereik (>= 1) al door de schema-validatie afgedwongen

    actieve = {
        sleutel
        for (sleutel,) in (
            await session.execute(
                select(ChecklistVraagOptie.optie_sleutel).where(
                    ChecklistVraagOptie.checklistvraag_id == checklistvraag_id,
                    ChecklistVraagOptie.actief.is_(True),
                )
            )
        ).all()
    }
    if vraag.antwoordtype == AntwoordType.enkelvoudige_keuze:
        if "optie" not in antwoord_waarde:
            raise OngeldigAntwoord("Voor deze vraag wordt één optie verwacht.")
        if antwoord_waarde["optie"] not in actieve:
            raise OngeldigAntwoord("De gekozen optie is onbekend of niet (meer) actief.")
    else:  # meerkeuze
        if "opties" not in antwoord_waarde:
            raise OngeldigAntwoord("Voor deze vraag wordt een lijst opties verwacht.")
        if not set(antwoord_waarde["opties"]) <= actieve:
            raise OngeldigAntwoord("Eén of meer gekozen opties zijn onbekend of niet (meer) actief.")


async def _synchroniseer_blokkade(
    session: AsyncSession, tid: uuid.UUID, score_obj, oude_score
) -> None:
    """Handhaaf de invariant score↔blokkade op basis van de TRANSITIE (ADR-013 B2).

    De auto-logica reageert uitsluitend op een score die de blokkerende grens
    kruist — nooit op een ongewijzigde of binnen-blokkerende score. Daardoor is
    "score `nee` + blokkade `opgelost`" een geldige, stabiele eindtoestand
    (geremedieerd → `migratieklaar`); een latere bewerking heropent niets.

    - `oude_score=None` ⇒ aanmaken: blokkerende score → nieuwe blokkade `open`.
    - regressie `ja`/`nvt` → `nee`/`deels`: geen actieve blokkade ⇒ maak `open`;
      alleen een `opgelost` exemplaar ⇒ heropen (`open`, `opgelost_op=null`).
    - correctie `nee`/`deels` → `ja`/`nvt`: actieve blokkade ⇒ auto-`opgelost`.
    - score ongewijzigd of binnen-blokkerend (`nee↔deels`, `ja↔nvt`): NIETS
      (handmatige blokkade-status, incl. `opgelost`, blijft ongemoeid).
    """
    nieuw_blokkerend = _is_blokkerend(score_obj.score)
    oud_blokkerend = _is_blokkerend(oude_score) if oude_score is not None else False

    # Geen kruising van de blokkerende grens ⇒ blokkade volledig ongemoeid.
    if oude_score is not None and nieuw_blokkerend == oud_blokkerend:
        return

    blok = (
        await session.execute(
            select(Blokkade).where(Blokkade.checklistscore_id == score_obj.id)
        )
    ).scalar_one_or_none()

    if nieuw_blokkerend and not oud_blokkerend:
        # Aanmaken met blokkerende score, of regressie ja/nvt → nee/deels.
        if blok is None:
            session.add(
                Blokkade(
                    tenant_id=tid,
                    checklistscore_id=score_obj.id,
                    component_id=score_obj.component_id,
                    status=BlokkadeStatus.open,
                )
            )
        elif blok.status == BlokkadeStatus.opgelost:
            blok.status = BlokkadeStatus.open
            blok.opgelost_op = None
        # open/in_behandeling → ongemoeid
    elif oud_blokkerend and not nieuw_blokkerend:
        # Score-correctie nee/deels → ja/nvt: actieve blokkade auto-oplossen.
        if blok is not None and blok.status in _BLOKKADE_ACTIEF:
            blok.status = BlokkadeStatus.opgelost
            blok.opgelost_op = datetime.now(timezone.utc)

    await session.flush()


async def lijst(
    session: AsyncSession,
    tenant_id,
    *,
    limit: int = _STANDAARD_LIMIT,
    after: str | None = None,
    component_id: uuid.UUID | None = None,
    sort: str = _STANDAARD_SORT,
    order: str = _STANDAARD_ORDER,
) -> tuple[list[Checklistscore], str | None]:
    """Server-side sorteerbare keyset-lijst binnen de tenant (ADR-017 + CD020).

    Default (geen `sort`/`order`) = exact het pre-CD020-gedrag (`created_at`
    oplopend). Uniform NULLS-LAST-pad (CD016); `Checklistscore.id` = tiebreaker.
    Cursor die niet bij `sort`/`order` past ⇒ `ValueError` (route ⇒ 400).
    """
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    if sort not in _SORTEERBARE_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    kolom = _SORTEERBARE_KOLOMMEN[sort]

    stmt = select(Checklistscore).where(Checklistscore.tenant_id == tid)
    if component_id is not None:
        stmt = stmt.where(Checklistscore.component_id == component_id)
    if after:
        c_sort, c_order, c_is_null, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_is_null else _WAARDE_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(
                kolom, Checklistscore.id, order=order, is_null=c_is_null,
                waarde=c_waarde, cursor_id=c_id,
            )
        )
    stmt = stmt.order_by(
        *keyset_order_by_nulls_last(kolom, Checklistscore.id, order)
    ).limit(limit + 1)

    rijen = list((await session.execute(stmt)).scalars().all())
    heeft_meer = len(rijen) > limit
    items = rijen[:limit]
    volgende = (
        encode_sort_cursor_nullable(
            sort=sort, order=order, waarde=getattr(items[-1], kolom.key), id=items[-1].id
        )
        if heeft_meer
        else None
    )
    await _verrijk_lijst(session, tid, items)  # ADR-037: afgeleide verantwoordelijke-velden
    return items, volgende


async def haal_op(session: AsyncSession, tenant_id, checklistscore_id) -> Checklistscore:
    tid = _tenant_uuid(tenant_id)
    stmt = select(Checklistscore).where(
        Checklistscore.id == checklistscore_id,
        Checklistscore.tenant_id == tid,
    )
    obj = (await session.execute(stmt)).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, checklistscore_id)
    return obj


async def lees_detail(session: AsyncSession, tenant_id, checklistscore_id) -> Checklistscore:
    """Read-pad voor de route: haal_op + afgeleide verantwoordelijke-velden (ADR-037)."""
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, checklistscore_id)
    return await _verrijk(session, tid, obj)


async def maak_aan(
    session: AsyncSession, tenant_id, data: ChecklistscoreCreate
) -> Checklistscore:
    tid = _tenant_uuid(tenant_id)
    # ADR-022 Fase E: het score-anker is het generieke `component_profiel` van een
    # checklist-dragend component (niet langer `applicatie`-gebonden). Bestaat er geen
    # profiel ⇒ niet scoorbaar (404). Het componenttype komt van de component en stuurt
    # de type-bewuste vraagvalidatie (Fase B): de vraag moet bij dat type horen.
    componenttype = await _componenttype_van_profiel(session, tid, data.component_id)
    await _verzeker_checklist_open(session, componenttype)
    vraagtekst = await _valideer_checklistvraag_id(session, data.checklistvraag_id, componenttype)

    # Uniciteit up-front (tenant, component, checklistvraag) → 409.
    bestaat = (
        await session.execute(
            select(Checklistscore.id).where(
                Checklistscore.tenant_id == tid,
                Checklistscore.component_id == data.component_id,
                Checklistscore.checklistvraag_id == data.checklistvraag_id,
            )
        )
    ).scalar_one_or_none()
    if bestaat is not None:
        raise ChecklistscoreConflict()

    # ADR-019: antwoord_waarde semantisch valideren (los van score/engine).
    await _valideer_antwoord_waarde(session, data.checklistvraag_id, data.antwoord_waarde)
    # ADR-037: verantwoordelijke aard-valideren (afdeling/persoon) — registratief, raakt de engine niet.
    if data.verantwoordelijke_id is not None:
        await partij_service.valideer_verantwoordelijke(session, tid, data.verantwoordelijke_id)

    # ADR-056 besluit 4 — bevries wat er gevraagd werd toen dit antwoord gegeven werd.
    obj = Checklistscore(tenant_id=tid, vraag_bevroren=vraagtekst, **data.model_dump())
    session.add(obj)
    try:
        await session.flush()  # id toekennen + unieke index als backstop
    except IntegrityError as exc:
        await session.rollback()
        raise ChecklistscoreConflict() from exc

    await _synchroniseer_blokkade(session, tid, obj, oude_score=None)
    await lifecycle_service.herbereken_lifecycle(session, tid, obj.component_id)
    await session.commit()
    await session.refresh(obj)
    return await _verrijk(session, tid, obj)


async def werk_bij(
    session: AsyncSession, tenant_id, checklistscore_id, data: ChecklistscoreUpdate
) -> Checklistscore:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, checklistscore_id)
    # ADR-027 — read-only-invariant: ook het bijwerken van een score is invoer en wordt
    # geblokkeerd als het componenttype niet (meer) checklist-dragend is.
    await _verzeker_checklist_open_voor(session, tid, obj.component_id)
    # ADR-019: alleen valideren als antwoord_waarde wérd meegestuurd (los van score).
    if "antwoord_waarde" in data.model_fields_set:
        await _valideer_antwoord_waarde(session, obj.checklistvraag_id, data.antwoord_waarde)
    # ADR-037: verantwoordelijke aard-valideren als hij (niet-leeg) wérd meegestuurd.
    if "verantwoordelijke_id" in data.model_fields_set and data.verantwoordelijke_id is not None:
        await partij_service.valideer_verantwoordelijke(session, tid, data.verantwoordelijke_id)
    oude_score = obj.score  # vóór de update — bepaalt de transitie
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(obj, veld, waarde)
    # ADR-056 — élke bewerking van het antwoord is "aanraken" en dooft de stille
    # notitie (besluit 6: het antwoord is van het team). Draagt de bewerking de
    # AFHANDELING (`score`), dan is dat "opnieuw antwoorden" (besluit 8): de
    # formulering wordt op de huidige tekst herbevroren en het verouderd-sein dooft
    # (de vergelijking wordt weer gelijk). Een bewerking zónder score laat de
    # bevroren tekst staan — alleen opnieuw antwoorden dooft het sein.
    obj.vraag_verduidelijkt_op = None
    if "score" in data.model_fields_set:
        tekst = await _huidige_vraagtekst(session, obj.checklistvraag_id)
        if tekst is not None:
            obj.vraag_bevroren = tekst
    await session.flush()

    await _synchroniseer_blokkade(session, tid, obj, oude_score)
    await lifecycle_service.herbereken_lifecycle(session, tid, obj.component_id)
    await session.commit()
    await session.refresh(obj)
    return await _verrijk(session, tid, obj)


async def verwijder(session: AsyncSession, tenant_id, checklistscore_id) -> None:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, checklistscore_id)
    component_id = obj.component_id
    await session.delete(obj)  # 1-op-1 blokkade gaat mee via ON DELETE CASCADE
    await session.flush()
    await lifecycle_service.herbereken_lifecycle(session, tid, component_id)
    await session.commit()
