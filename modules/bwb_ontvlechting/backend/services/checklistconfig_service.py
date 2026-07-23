"""Service-laag — tenant-beheer van de checklist-vragenset + antwoordconfiguratie
(ADR-019 fase 2D; ADR-022 Wijziging W1).

ADR-022 W1: `checklistvraag`/`checklistvraag_optie` zijn **tenant-eigendom** (RLS).
Deze service draait onder `get_tenant_session` (`lk_app`, tenant-RLS-context) — alle
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
    ChecklistCategorie,
    ChecklistVraag,
    ChecklistVraagOptie,
    Component,
    ComponentConfigDimensie,
    ComponentProfiel,
    LifecycleStatus,
)
from schemas.checklistconfig import (
    AntwoordTypeUpdate,
    BetekenisUpdate,
    CategorieCreate,
    CategorieUpdate,
    OptieCreate,
    OptieUpdate,
    VraagCreate,
    VraagUpdate,
)
from services import componentconfig_catalog as catalog
from services import lifecycle_service
from services import vraagbetekenis_catalog
from services.errors import ConfiguratieConflict, NietGevonden, RegistratieConflict


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _vraag_read(
    vraag: ChecklistVraag, opties: list[ChecklistVraagOptie], categorie: ChecklistCategorie
) -> dict:
    return {
        "id": vraag.id,
        "componenttype": vraag.componenttype,
        "code": vraag.code,
        # LI050 (W3): de categorie is een verwijzing; naam/volgorde reizen mee in de read.
        "categorie_id": vraag.categorie_id,
        "categorie_naam": categorie.naam,
        "categorie_volgorde": categorie.volgorde,
        "volgorde": vraag.volgorde,
        "vraag": vraag.vraag,
        "prioriteit": vraag.prioriteit,
        "antwoordtype": vraag.antwoordtype,
        "actief": vraag.actief,
        "betekenis": vraag.betekenis,
        "opties": opties,
    }


async def _haal_categorie(session: AsyncSession, categorie_id) -> ChecklistCategorie:
    """Categorie op `id` binnen de tenant (RLS). Onbekend/ander-tenant ⇒ NietGevonden."""
    cat = (
        await session.execute(
            select(ChecklistCategorie).where(ChecklistCategorie.id == categorie_id)
        )
    ).scalar_one_or_none()
    if cat is None:
        raise NietGevonden("checklist_categorie", categorie_id)
    return cat


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
    categorieen = {
        c.id: c
        for c in (await session.execute(select(ChecklistCategorie))).scalars().all()
    }
    return [
        _vraag_read(v, per_vraag.get(v.id, []), categorieen[v.categorie_id]) for v in vragen
    ]


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


async def backfill_profielen(session: AsyncSession, tenant_id, componenttype: str) -> int:
    """LI058 — activeer scoring voor BESTAANDE componenten van `componenttype`: geef elk component
    dat nog géén `ComponentProfiel` heeft er een (lifecycle `concept`) en herbereken het hele type.
    In-tenant (RLS), idempotent (alleen ontbrekende profielen). Returnt het aantal nieuwe profielen.

    Gebruikt bij de overgang `checklist_dragend` False→True: nieuw aangemaakte componenten krijgen hun
    profiel al bij create; deze backfill dekt de reeds bestaande. Score blijft de enige lifecycle-driver:
    de herberekening leidt de status puur af uit score + open blokkades."""
    tid = _tenant_uuid(tenant_id)
    ontbrekend = list(
        (
            await session.execute(
                select(Component.id)
                .outerjoin(ComponentProfiel, ComponentProfiel.id == Component.id)
                .where(Component.componenttype == componenttype, ComponentProfiel.id.is_(None))
            )
        )
        .scalars()
        .all()
    )
    for component_id in ontbrekend:
        session.add(
            ComponentProfiel(id=component_id, tenant_id=tid, lifecycle_status=LifecycleStatus.concept)
        )
    if ontbrekend:
        await session.flush()
    await herbereken_type(session, tid, componenttype)
    return len(ontbrekend)


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

def volgende_code(bestaande: set[str]) -> str:
    """LI050 (W4) — de eenvoudigste toekenningsregel die niet botst en de demovulling
    ongemoeid laat: neem het grootste gehele getal dat in een bestaande code voorkomt
    (het deel vóór de punt bij "12.4"-vormen, de hele code bij kale getallen) en tel
    één op → een kale, unieke code ("13", "14", …). Puur en DB-vrij testbaar; de
    UNIQUE-constraint blijft de backstop."""
    hoogste = 0
    for code in bestaande:
        kop = code.split(".", 1)[0]
        if kop.isdigit():
            hoogste = max(hoogste, int(kop))
    return str(hoogste + 1)


async def maak_vraag(session: AsyncSession, tenant_id, data: VraagCreate) -> dict:
    """Voeg een tenant-vraag toe. `componenttype` gevalideerd tegen de catalogus;
    `UNIQUE(tenant_id, componenttype, code)`-schending ⇒ `CHECKLISTVRAAG_BESTAAT` (409).
    Herberekent vervolgens in-tenant de lifecycle van bestaande componenten van dat type."""
    tid = _tenant_uuid(tenant_id)
    await catalog.valideer_sleutel(session, ComponentConfigDimensie.componenttype, data.componenttype)
    # LI050: de vraag KIEST een bestaande categorie van hetzelfde componenttype.
    # OP-6-stijl: onbekend óf ander type ⇒ NietGevonden (geen onderscheid lekken).
    categorie = await _haal_categorie(session, data.categorie_id)
    if categorie.componenttype != data.componenttype:
        raise NietGevonden("checklist_categorie", data.categorie_id)

    # LI050 (W4): het systeem kent de code toe — geen invoerveld meer.
    bestaande = set(
        (
            await session.execute(
                select(ChecklistVraag.code).where(
                    ChecklistVraag.componenttype == data.componenttype
                )
            )
        )
        .scalars()
        .all()
    )
    # LI050 (W5): een nieuwe vraag komt ACHTERAAN in haar categorie; de beheerder
    # sleept hem daarna waar hij hoort.
    hoogste_volgorde = (
        await session.execute(
            select(func.coalesce(func.max(ChecklistVraag.volgorde), 0)).where(
                ChecklistVraag.categorie_id == data.categorie_id
            )
        )
    ).scalar_one()
    vraag = ChecklistVraag(
        tenant_id=tid,
        componenttype=data.componenttype,
        code=volgende_code(bestaande),
        categorie_id=data.categorie_id,
        volgorde=hoogste_volgorde + 1,
        vraag=data.vraag,
        prioriteit=data.prioriteit,
        antwoordtype=data.antwoordtype,
        actief=True,
    )
    session.add(vraag)
    try:
        await session.flush()
    except IntegrityError as exc:
        # Backstop (race op de toegekende code) — voor een gebruiker onbereikbaar:
        # er is geen code-invoer meer; alleen twee gelijktijdige toevoegingen raken dit.
        await session.rollback()
        raise RegistratieConflict(
            "CHECKLISTVRAAG_BESTAAT",
            f"Er bestaat al een vraag met code '{vraag.code}' voor type '{data.componenttype}'.",
        ) from exc

    # Fan-out: een extra (actieve) vraag verhoogt aantal_vragen voor dit type.
    await herbereken_type(session, tid, data.componenttype)
    await session.commit()
    await session.refresh(vraag)
    return _vraag_read(vraag, [], categorie)


async def werk_vraag_bij(session: AsyncSession, checklistvraag_id, data: VraagUpdate) -> dict:
    """Bewerk niet-tellende velden (`vraag`/`categorie_id`/`prioriteit`).
    `componenttype`+`code` zijn immutable. Géén fan-out (aantal_vragen ongewijzigd)."""
    vraag = await _haal_vraag(session, checklistvraag_id)
    velden = data.model_dump(exclude_unset=True)
    if "categorie_id" in velden:
        # Herplaatsen mag, maar alleen naar een categorie van hetzelfde componenttype.
        nieuwe = await _haal_categorie(session, velden["categorie_id"])
        if nieuwe.componenttype != vraag.componenttype:
            raise NietGevonden("checklist_categorie", velden["categorie_id"])
    for veld, waarde in velden.items():
        setattr(vraag, veld, waarde)
    await session.commit()
    await session.refresh(vraag)
    return _vraag_read(
        vraag, await _opties_van(session, vraag.id), await _haal_categorie(session, vraag.categorie_id)
    )


# ── LI050 (ADR-022 W3): categorie-beheer — de indeling als eigen entiteit ─────────
# Zelfde rechten-ingang als het vraagbeheer (Entiteit.CHECKLISTVRAAG, routes): de
# categorie bepaalt de indeling van de vragenlijst voor de hele organisatie.


def _categorie_read(cat: ChecklistCategorie, aantal_vragen: int) -> dict:
    return {
        "id": cat.id,
        "componenttype": cat.componenttype,
        "naam": cat.naam,
        "volgorde": cat.volgorde,
        "aantal_vragen": aantal_vragen,
    }


async def _aantal_vragen_in(session: AsyncSession, categorie_id) -> int:
    return (
        await session.execute(
            select(func.count()).select_from(ChecklistVraag).where(
                ChecklistVraag.categorie_id == categorie_id
            )
        )
    ).scalar_one()


async def lijst_categorieen(
    session: AsyncSession, componenttype: str | None = None
) -> list[dict]:
    """Categorieën (tenant, RLS) + aantal vragen per categorie — gesorteerd op
    componenttype, volgorde, naam. Read voor beheer én keuzelijsten."""
    stmt = select(ChecklistCategorie).order_by(
        ChecklistCategorie.componenttype, ChecklistCategorie.volgorde, ChecklistCategorie.naam
    )
    if componenttype:
        stmt = stmt.where(ChecklistCategorie.componenttype == componenttype)
    cats = list((await session.execute(stmt)).scalars().all())
    tellingen = {
        rij.categorie_id: rij.aantal
        for rij in (
            await session.execute(
                select(
                    ChecklistVraag.categorie_id.label("categorie_id"),
                    func.count().label("aantal"),
                ).group_by(ChecklistVraag.categorie_id)
            )
        ).all()
    }
    return [_categorie_read(c, tellingen.get(c.id, 0)) for c in cats]


async def maak_categorie(session: AsyncSession, tenant_id, data: CategorieCreate) -> dict:
    """Nieuwe categorie voor een componenttype. Naam uniek binnen (tenant, type) —
    schema-afgedwongen; de pre-flush IntegrityError wordt een leesbare 409."""
    tid = _tenant_uuid(tenant_id)
    await catalog.valideer_sleutel(session, ComponentConfigDimensie.componenttype, data.componenttype)
    # LI050 (W5): geen volgorde opgegeven → achteraan binnen het type (daarna slepen).
    volgorde = data.volgorde
    if volgorde is None:
        volgorde = (
            await session.execute(
                select(func.coalesce(func.max(ChecklistCategorie.volgorde), 0)).where(
                    ChecklistCategorie.componenttype == data.componenttype
                )
            )
        ).scalar_one() + 1
    cat = ChecklistCategorie(
        tenant_id=tid,
        componenttype=data.componenttype,
        naam=data.naam,
        volgorde=volgorde,
    )
    session.add(cat)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConfiguratieConflict(
            f"Er bestaat al een categorie '{data.naam}' voor dit componenttype."
        ) from exc
    await session.commit()
    await session.refresh(cat)
    return _categorie_read(cat, 0)


async def wijzig_categorie(session: AsyncSession, categorie_id, data: CategorieUpdate) -> dict:
    """Hernoemen en/of volgorde wijzigen — één handeling, niet per vraag (LI050)."""
    cat = await _haal_categorie(session, categorie_id)
    for veld, waarde in data.model_dump(exclude_unset=True).items():
        setattr(cat, veld, waarde)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConfiguratieConflict(
            f"Er bestaat al een categorie '{data.naam}' voor dit componenttype."
        ) from exc
    await session.commit()
    await session.refresh(cat)
    return _categorie_read(cat, await _aantal_vragen_in(session, cat.id))


async def verwijder_categorie(session: AsyncSession, categorie_id) -> None:
    """Verwijderen wordt geweigerd zolang er vragen onder hangen (409 + telling,
    het GEBRUIK_HEEFT_VERFIJNING-precedent); de RESTRICT-FK is de schema-backstop.
    ORM-delete → geaudit (audit-dekking is ORM-dekking)."""
    cat = await _haal_categorie(session, categorie_id)
    aantal = await _aantal_vragen_in(session, cat.id)
    if aantal:
        meervoud = "vraag" if aantal == 1 else "vragen"
        raise RegistratieConflict(
            "CATEGORIE_HEEFT_VRAGEN",
            f"Er hangen nog {aantal} {meervoud} onder deze categorie; verplaats of "
            "verwijder die eerst — een indeling met vragen verdwijnt nooit stil.",
        )
    await session.delete(cat)
    await session.commit()


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
    return _vraag_read(
        vraag, await _opties_van(session, vraag.id), await _haal_categorie(session, vraag.categorie_id)
    )


# ── Antwoordconfiguratie (ADR-019) — nu tenant-facing (lk_app/RLS) ────────────

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
    return _vraag_read(
        vraag, await _opties_van(session, vraag.id), await _haal_categorie(session, vraag.categorie_id)
    )


# ── ADR-023 Fase F (F-3): betekenis-toekenning ────────────────────────────────

async def lijst_betekenissen(session: AsyncSession) -> list[dict]:
    """Actieve betekenissen uit de platform-brede catalogus (keuzeveld). Read-only."""
    return await vraagbetekenis_catalog.actieve_opties(session)


async def zet_betekenis(
    session: AsyncSession, checklistvraag_id, data: BetekenisUpdate
) -> dict:
    """(Her)toekennen of wissen van de betekenis van een vraag. `None` wist; een waarde
    wordt tegen de actieve catalogus gevalideerd (⇒ 422 `ONGELDIGE_OPTIE`). Uniciteit
    `(tenant, componenttype, betekenis)` ⇒ 409 `CONFIGURATIE_CONFLICT`. Géén fan-out:
    betekenis is classificatie en voedt de engine NIET (lifecycle/score onaangeroerd)."""
    vraag = await _haal_vraag(session, checklistvraag_id)
    if data.betekenis is not None:
        await vraagbetekenis_catalog.valideer_sleutel(session, data.betekenis)
    vraag.betekenis = data.betekenis
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConfiguratieConflict(
            "Een andere vraag van dit componenttype draagt deze betekenis al."
        ) from exc
    await session.commit()
    await session.refresh(vraag)
    return _vraag_read(
        vraag, await _opties_van(session, vraag.id), await _haal_categorie(session, vraag.categorie_id)
    )


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
