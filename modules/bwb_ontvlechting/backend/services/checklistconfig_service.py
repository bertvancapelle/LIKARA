"""Service-laag — tenant-beheer van de checklist-vragenset + antwoordconfiguratie
(ADR-019 fase 2D; ADR-022 Wijziging W1).

ADR-022 W1: `checklistvraag`/`checklistvraag_optie` zijn **tenant-eigendom** (RLS).
Deze service draait onder `get_tenant_session` (`cd_app`, tenant-RLS-context) — alle
SELECT/UPDATE/DELETE auto-scopen op de tenant; INSERTs zetten `tenant_id` expliciet
(RLS-`WITH CHECK`). Vragen worden geadresseerd op hun surrogate-`id` (`code` is alleen
uniek binnen `(tenant_id, componenttype)`).

Integriteitsregels (ongewijzigd):
- **Antwoordtype wisselen** alleen vanuit `geen` (orphan-bescherming).
- **Afgeleide optiesets** (`afgeleid_bron`) zijn structureel read-only (alleen label).
- **Soft-deactivate** opties én vragen; nooit hard delete in dit blok.

ADR-022 W1 nieuw: vraag-CRUD (toevoegen/bewerken/(de)activeren). Een mutatie die
`aantal_vragen` van een type wijzigt (toevoegen/(de)activeren) herberekent **in-tenant,
atomair** de lifecycle van alle componenten van dat type (`herbereken_type`).
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    AntwoordType,
    ChecklistVraag,
    ChecklistVraagOptie,
    Component,
    ComponentConfigDimensie,
    ComponentProfiel,
)
from schemas.checklistconfig import (
    AntwoordTypeUpdate,
    OptieCreate,
    OptieUpdate,
    VraagCreate,
    VraagUpdate,
)
from services import componentconfig_catalog as catalog
from services import lifecycle_service
from services.errors import ConfiguratieConflict, NietGevonden, RegistratieConflict


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _vraag_read(vraag: ChecklistVraag, opties: list[ChecklistVraagOptie]) -> dict:
    return {
        "id": vraag.id,
        "componenttype": vraag.componenttype,
        "code": vraag.code,
        "categorie_nr": vraag.categorie_nr,
        "categorie_naam": vraag.categorie_naam,
        "vraag": vraag.vraag,
        "prioriteit": vraag.prioriteit,
        "antwoordtype": vraag.antwoordtype,
        "actief": vraag.actief,
        "opties": opties,
    }


async def lijst_config(session: AsyncSession) -> list[dict]:
    """Alle (tenant-eigen) vragen + antwoordtype + ALLE opties (incl. inactieve)."""
    vragen = list(
        (
            await session.execute(
                select(ChecklistVraag).order_by(
                    ChecklistVraag.componenttype, ChecklistVraag.code
                )
            )
        )
        .scalars()
        .all()
    )
    opties = list(
        (
            await session.execute(
                select(ChecklistVraagOptie).order_by(
                    ChecklistVraagOptie.checklistvraag_id, ChecklistVraagOptie.volgorde
                )
            )
        )
        .scalars()
        .all()
    )
    per_vraag: dict[uuid.UUID, list[ChecklistVraagOptie]] = {}
    for o in opties:
        per_vraag.setdefault(o.checklistvraag_id, []).append(o)
    return [_vraag_read(v, per_vraag.get(v.id, [])) for v in vragen]


async def _haal_vraag(session: AsyncSession, checklistvraag_id) -> ChecklistVraag:
    """Vraag op `id` binnen de tenant (RLS). Onbekend/ander-tenant ⇒ NietGevonden."""
    vraag = (
        await session.execute(
            select(ChecklistVraag).where(ChecklistVraag.id == checklistvraag_id)
        )
    ).scalar_one_or_none()
    if vraag is None:
        raise NietGevonden("checklistvraag", checklistvraag_id)
    return vraag


async def _opties_van(session: AsyncSession, checklistvraag_id) -> list[ChecklistVraagOptie]:
    return list(
        (
            await session.execute(
                select(ChecklistVraagOptie)
                .where(ChecklistVraagOptie.checklistvraag_id == checklistvraag_id)
                .order_by(ChecklistVraagOptie.volgorde)
            )
        )
        .scalars()
        .all()
    )


async def _haal_optie(session: AsyncSession, optie_id: uuid.UUID) -> ChecklistVraagOptie:
    optie = (
        await session.execute(
            select(ChecklistVraagOptie).where(ChecklistVraagOptie.id == optie_id)
        )
    ).scalar_one_or_none()
    if optie is None:
        raise NietGevonden("checklistvraag_optie", optie_id)
    return optie


async def _is_afgeleide_set(session: AsyncSession, checklistvraag_id: uuid.UUID) -> bool:
    """True als de optieset van deze vraag uit een model-enum is afgeleid."""
    bestaat = (
        await session.execute(
            select(ChecklistVraagOptie.id)
            .where(
                ChecklistVraagOptie.checklistvraag_id == checklistvraag_id,
                ChecklistVraagOptie.afgeleid_bron.is_not(None),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return bestaat is not None


# ── ADR-022 W1: in-tenant fan-out ─────────────────────────────────────────────

async def herbereken_type(session: AsyncSession, tenant_id, componenttype: str) -> int:
    """Herbereken de lifecycle van álle eigen componenten van `componenttype`
    (in-tenant, RLS), in dezelfde transactie als de aanroepende vraag-mutatie —
    atomair, geen stale-venster. Geeft het aantal herberekende componenten terug."""
    tid = _tenant_uuid(tenant_id)
    ids = list(
        (
            await session.execute(
                select(ComponentProfiel.id)
                .join(Component, Component.id == ComponentProfiel.id)
                .where(Component.componenttype == componenttype)
            )
        )
        .scalars()
        .all()
    )
    for component_id in ids:
        await lifecycle_service.herbereken_lifecycle(session, tid, component_id)
    return len(ids)


async def impact_telling(session: AsyncSession, componenttype: str) -> int:
    """Read-only "raakt N componenten" — aantal eigen componenten van dit type (RLS)."""
    return (
        await session.execute(
            select(func.count()).select_from(Component).where(
                Component.componenttype == componenttype
            )
        )
    ).scalar_one()


# ── ADR-022 W1: vraag-CRUD ────────────────────────────────────────────────────

async def maak_vraag(session: AsyncSession, tenant_id, data: VraagCreate) -> dict:
    """Voeg een tenant-vraag toe. `componenttype` gevalideerd tegen de catalogus;
    `UNIQUE(tenant_id, componenttype, code)`-schending ⇒ `CHECKLISTVRAAG_BESTAAT` (409).
    Herberekent vervolgens in-tenant de lifecycle van bestaande componenten van dat type."""
    tid = _tenant_uuid(tenant_id)
    await catalog.valideer_sleutel(session, ComponentConfigDimensie.componenttype, data.componenttype)

    vraag = ChecklistVraag(
        tenant_id=tid,
        componenttype=data.componenttype,
        code=data.code,
        categorie_nr=data.categorie_nr,
        categorie_naam=data.categorie_naam,
        vraag=data.vraag,
        prioriteit=data.prioriteit,
        antwoordtype=data.antwoordtype,
        actief=True,
    )
    session.add(vraag)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise RegistratieConflict(
            "CHECKLISTVRAAG_BESTAAT",
            f"Er bestaat al een vraag met code '{data.code}' voor type '{data.componenttype}'.",
        ) from exc

    # Fan-out: een extra (actieve) vraag verhoogt aantal_vragen voor dit type.
    await herbereken_type(session, tid, data.componenttype)
    await session.commit()
    await session.refresh(vraag)
    return _vraag_read(vraag, [])


async def werk_vraag_bij(session: AsyncSession, checklistvraag_id, data: VraagUpdate) -> dict:
    """Bewerk niet-tellende velden (`vraag`/`categorie_nr`/`categorie_naam`/`prioriteit`).
    `componenttype`+`code` zijn immutable. Géén fan-out (aantal_vragen ongewijzigd)."""
    vraag = await _haal_vraag(session, checklistvraag_id)
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(vraag, veld, waarde)
    await session.commit()
    await session.refresh(vraag)
    return _vraag_read(vraag, await _opties_van(session, vraag.id))


async def zet_actief(session: AsyncSession, tenant_id, checklistvraag_id, actief: bool) -> dict:
    """(De)activeer een vraag (soft-deactivatie). Wijzigt de actieve set ⇒ fan-out."""
    tid = _tenant_uuid(tenant_id)
    vraag = await _haal_vraag(session, checklistvraag_id)
    if vraag.actief != actief:
        vraag.actief = actief
        await session.flush()
        await herbereken_type(session, tid, vraag.componenttype)
    await session.commit()
    await session.refresh(vraag)
    return _vraag_read(vraag, await _opties_van(session, vraag.id))


# ── Antwoordconfiguratie (ADR-019) — nu tenant-facing (cd_app/RLS) ────────────

async def zet_antwoordtype(
    session: AsyncSession, checklistvraag_id, data: AntwoordTypeUpdate
) -> dict:
    """Zet het antwoordtype. Alleen vanuit `geen` (orphan-bescherming)."""
    vraag = await _haal_vraag(session, checklistvraag_id)
    if data.antwoordtype != vraag.antwoordtype and vraag.antwoordtype != AntwoordType.geen:
        raise ConfiguratieConflict(
            "Een reeds geconfigureerde vraag kan niet van antwoordtype wisselen; "
            "bestaande antwoorden zouden verweesd kunnen raken."
        )
    vraag.antwoordtype = data.antwoordtype
    await session.commit()
    await session.refresh(vraag)
    return _vraag_read(vraag, await _opties_van(session, vraag.id))


async def voeg_optie_toe(
    session: AsyncSession, tenant_id, checklistvraag_id, data: OptieCreate
) -> ChecklistVraagOptie:
    """Voeg een optie toe (niet-afgeleide vraag; unieke stabiele sleutel)."""
    tid = _tenant_uuid(tenant_id)
    vraag = await _haal_vraag(session, checklistvraag_id)
    if await _is_afgeleide_set(session, vraag.id):
        raise ConfiguratieConflict("Aan een afgeleide optieset kan geen optie worden toegevoegd.")

    bestaat = (
        await session.execute(
            select(ChecklistVraagOptie.id).where(
                ChecklistVraagOptie.checklistvraag_id == vraag.id,
                ChecklistVraagOptie.optie_sleutel == data.optie_sleutel,
            )
        )
    ).scalar_one_or_none()
    if bestaat is not None:
        raise ConfiguratieConflict("Een optie met deze sleutel bestaat al voor deze vraag.")

    optie = ChecklistVraagOptie(
        tenant_id=tid,
        checklistvraag_id=vraag.id,
        optie_sleutel=data.optie_sleutel,
        label=data.label,
        volgorde=data.volgorde,
        actief=True,
        afgeleid_bron=None,
    )
    session.add(optie)
    await session.commit()
    await session.refresh(optie)
    return optie


async def wijzig_optie(
    session: AsyncSession, optie_id: uuid.UUID, data: OptieUpdate
) -> ChecklistVraagOptie:
    """Wijzig label en/of volgorde. Bij een afgeleide optie alleen het label."""
    optie = await _haal_optie(session, optie_id)
    if optie.afgeleid_bron is not None and data.volgorde is not None:
        raise ConfiguratieConflict(
            "Bij een afgeleide optie is alleen het label aanpasbaar, niet de volgorde."
        )
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(optie, veld, waarde)
    await session.commit()
    await session.refresh(optie)
    return optie


async def deactiveer_optie(
    session: AsyncSession, optie_id: uuid.UUID
) -> ChecklistVraagOptie:
    """Soft-deactiveer een optie (`actief=false`). Afgeleide opties mogen niet."""
    optie = await _haal_optie(session, optie_id)
    if optie.afgeleid_bron is not None:
        raise ConfiguratieConflict("Een afgeleide optie kan niet worden gedeactiveerd.")
    optie.actief = False
    await session.commit()
    await session.refresh(optie)
    return optie
