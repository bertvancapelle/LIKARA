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
)
from schemas.checklistscore import ChecklistscoreCreate, ChecklistscoreUpdate
from services import applicatie_service, lifecycle_service
from services.errors import ChecklistscoreConflict, NietGevonden, OngeldigAntwoord
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
    "eigenaar": Checklistscore.eigenaar,
}
_WAARDE_PARSERS = {
    "created_at": datetime.fromisoformat,
    "checklistvraag_id": uuid.UUID,
    "score": ChecklistScore,
    "eigenaar": str,
}

# Scores die een actieve blokkade vereisen (ADR-013 B2).
_BLOKKADE_VEREIST = (ChecklistScore.nee, ChecklistScore.deels)
_BLOKKADE_ACTIEF = (BlokkadeStatus.open, BlokkadeStatus.in_behandeling)


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def enum_opties() -> dict[str, list[str]]:
    """Read-only keuzewaarden voor de score (single source, DB-vrij)."""
    return {"score": [e.value for e in ChecklistScore]}


async def _valideer_checklistvraag_id(session: AsyncSession, checklistvraag_id) -> None:
    """Onbekende `checklistvraag_id` (globale vragenset) ⇒ NietGevonden (404)."""
    bestaat = (
        await session.execute(
            select(ChecklistVraag.id).where(ChecklistVraag.id == checklistvraag_id)
        )
    ).scalar_one_or_none()
    if bestaat is None:
        raise NietGevonden("checklistvraag", checklistvraag_id)


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


async def maak_aan(
    session: AsyncSession, tenant_id, data: ChecklistscoreCreate
) -> Checklistscore:
    tid = _tenant_uuid(tenant_id)
    # Ouder (applicatie-profiel; component_id == applicatie-id, shared-PK) + vraag
    # valideren (beide tenant-/referentie-scoped) → 404.
    await applicatie_service.haal_op(session, tenant_id, data.component_id)
    await _valideer_checklistvraag_id(session, data.checklistvraag_id)

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

    obj = Checklistscore(tenant_id=tid, **data.model_dump())
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
    return obj


async def werk_bij(
    session: AsyncSession, tenant_id, checklistscore_id, data: ChecklistscoreUpdate
) -> Checklistscore:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, checklistscore_id)
    # ADR-019: alleen valideren als antwoord_waarde wérd meegestuurd (los van score).
    if "antwoord_waarde" in data.model_fields_set:
        await _valideer_antwoord_waarde(session, obj.checklistvraag_id, data.antwoord_waarde)
    oude_score = obj.score  # vóór de update — bepaalt de transitie
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(obj, veld, waarde)
    await session.flush()

    await _synchroniseer_blokkade(session, tid, obj, oude_score)
    await lifecycle_service.herbereken_lifecycle(session, tid, obj.component_id)
    await session.commit()
    await session.refresh(obj)
    return obj


async def verwijder(session: AsyncSession, tenant_id, checklistscore_id) -> None:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, checklistscore_id)
    component_id = obj.component_id
    await session.delete(obj)  # 1-op-1 blokkade gaat mee via ON DELETE CASCADE
    await session.flush()
    await lifecycle_service.herbereken_lifecycle(session, tid, component_id)
    await session.commit()
