"""Service — Signalering registratiegaten (ADR-035, Slice 1). Puur read-only afgeleid.

Drie KRITIEKE component-signalen:
- ``component_zonder_eigenaar``          — ``component.eigenaar_organisatie_id IS NULL``
- ``component_zonder_verantwoordelijke`` — geen ``roltoewijzing`` met ``object_id == component``
- ``biv_classificatie_onvolledig``      — ≥1 van ``biv_{beschikbaarheid,integriteit,vertrouwelijkheid}`` IS NULL (ADR-028)

Engine-invariant (machine-geborgd via de offline import-afwezigheidstest): bewust GEEN import van
``lifecycle_service`` / ``herbereken_lifecycle`` / ``bepaal_lifecycle`` / ``ComponentProfiel`` /
``Blokkade`` / ``Checklistscore``. ``lifecycle_status`` (woont op de engine-tabel
``component_profiel``) wordt engine-veilig gelezen via een lichtgewicht ``table()/column()``-handle
i.p.v. de ORM-klasse (zoals de Landschapskaart). Geen mutatie — uitsluitend SELECT; RLS scoopt op
de tenant (dubbele bescherming met de expliciete ``tenant_id``-filter).
"""
import uuid

from sqlalchemy import and_, column, exists, func, literal, or_, select, table
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    ChecklistVraag,
    Component,
    Contract,
    Gebruikersgroep,
    Organisatiegebruik,
    Partij,
    Relatie,
    Roltoewijzing,
)

# Lichtgewicht handle op de engine-tabel (shared-PK: component_profiel.id == component.id) — leest
# lifecycle_status zonder ComponentProfiel te importeren, zodat de engine-borging groen blijft.
_profiel = table("component_profiel", column("id"), column("tenant_id"), column("lifecycle_status"))

# ADR-037 — lichtgewicht handle op `checklistscore` (géén Checklistscore-ORM, zelfde reden als
# `_profiel`): leest het gescoorde antwoord + de verantwoordelijke-FK voor het aandacht-signaal.
_checklistscore = table(
    "checklistscore",
    column("id"), column("tenant_id"), column("component_id"),
    column("checklistvraag_id"), column("score"), column("verantwoordelijke_id"),
)

_SIG_EIGENAAR = "component_zonder_eigenaar"
_SIG_VERANTWOORDELIJKE = "component_zonder_verantwoordelijke"
# ADR-028 slice 4 — kritiek: BIV pas compleet als B, I én V staan (één-of-meer-leeg = signaal).
_SIG_BIV = "biv_classificatie_onvolledig"
# Slice 2 — aandacht-signalen.
_SIG_GG = "component_zonder_gebruikersgroep"
_SIG_ISOLATIE = "component_geisoleerd"
_SIG_CONTRACT = "contract_zonder_component"
# ADR-038 — `gebruikersgroep_zonder_organisatie` is verwijderd: een groep hoort nu altijd bij een
# organisatie (schema NOT NULL), dus dit signaal kan nooit meer vuren.
_SIG_OBJ_ROL = "object_zonder_roltoewijzing"
# ADR-036 stap C — grof gebruiksfeit zónder afdeling-verfijning eronder ("detaillering ontbreekt").
_SIG_GEBRUIK_GEEN_VERFIJNING = "gebruiksfeit_zonder_verfijning"
# ADR-037 — gescoord antwoord zonder verantwoordelijke (aandacht). Bewust ONDERSCHEIDEN van
# `component_zonder_verantwoordelijke` (beheerrol op een component) — andere sleutel, andere entiteit.
_SIG_ANTW_VERANTW = "antwoord_zonder_verantwoordelijke"
_KRITIEK = "kritiek"
_AANDACHT = "aandacht"

# Gebruikersgroep heeft geen `naam`-kolom → label = de afdeling-partij-naam (ADR-036a; via een
# per-query join op `afdeling_id`), anders een generieke fallback. `_gg_label(afd)` bouwt de
# coalesce voor de meegegeven afdeling-partij-alias.
def _gg_label(afd):
    return func.coalesce(afd.naam, literal("(gebruikersgroep)"))


def _geen_roltoewijzing(id_col, tid: uuid.UUID):
    """~EXISTS roltoewijzing met object_id == id_col (binnen de tenant)."""
    return ~exists(
        select(Roltoewijzing.id).where(
            Roltoewijzing.tenant_id == tid, Roltoewijzing.object_id == id_col
        )
    )


def _aitem(r, signaal: str, entiteit_type: str | None = None) -> dict:
    """Aandacht-item: {id, naam[, entiteit_type], signaal, niveau}."""
    d = {"id": r.id, "naam": r.naam, "signaal": signaal, "niveau": _AANDACHT}
    if entiteit_type is not None:
        d["entiteit_type"] = entiteit_type
    return d


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _lc(val) -> str | None:
    if val is None:
        return None
    return val.value if hasattr(val, "value") else str(val)


def _basis_select(tid: uuid.UUID):
    """Component + lifecycle_status (LEFT JOIN op de profiel-handle), tenant-gescoopt, op naam."""
    return (
        select(Component.id, Component.naam, _profiel.c.lifecycle_status)
        .outerjoin(_profiel, and_(_profiel.c.id == Component.id, _profiel.c.tenant_id == tid))
        .where(Component.tenant_id == tid)
        .order_by(Component.naam.asc(), Component.id.asc())
    )


def _item(r, signaal: str) -> dict:
    return {
        "id": r.id, "naam": r.naam, "lifecycle_status": _lc(r.lifecycle_status),
        "signaal": signaal, "niveau": _KRITIEK,
    }


async def component_zonder_eigenaar(session: AsyncSession, tenant_id) -> list[dict]:
    """Componenten zonder ``eigenaar_organisatie_id`` (IS NULL). Inclusief kale types. Read-only."""
    tid = _tenant_uuid(tenant_id)
    stmt = _basis_select(tid).where(Component.eigenaar_organisatie_id.is_(None))
    rijen = (await session.execute(stmt)).all()
    return [_item(r, _SIG_EIGENAAR) for r in rijen]


async def component_zonder_verantwoordelijke(session: AsyncSession, tenant_id) -> list[dict]:
    """Componenten zonder enige roltoewijzing (geen verantwoordelijke partij). Read-only."""
    tid = _tenant_uuid(tenant_id)
    geen_rol = ~exists(
        select(Roltoewijzing.id).where(
            Roltoewijzing.tenant_id == tid, Roltoewijzing.object_id == Component.id,
        )
    )
    stmt = _basis_select(tid).where(geen_rol)
    rijen = (await session.execute(stmt)).all()
    return [_item(r, _SIG_VERANTWOORDELIJKE) for r in rijen]


def _biv_onvolledig():
    """Predikaat: minstens één BIV-aspect leeg → classificatie onvolledig (ADR-028)."""
    return or_(
        Component.biv_beschikbaarheid.is_(None),
        Component.biv_integriteit.is_(None),
        Component.biv_vertrouwelijkheid.is_(None),
    )


async def component_biv_onvolledig(session: AsyncSession, tenant_id) -> list[dict]:
    """Componenten met een onvolledige BIV-classificatie (≥1 aspect leeg). Read-only.

    Een component telt pas als geclassificeerd wanneer beschikbaarheid, integriteit én
    vertrouwelijkheid gevuld zijn. Puur registratief — raakt de engine niet."""
    tid = _tenant_uuid(tenant_id)
    stmt = _basis_select(tid).where(_biv_onvolledig())
    rijen = (await session.execute(stmt)).all()
    return [_item(r, _SIG_BIV) for r in rijen]


async def badge_voor_component(session: AsyncSession, tenant_id, component_id: uuid.UUID) -> dict:
    """Badge-info voor één component (Slice 1: de twee kritieke component-signalen). Read-only.

    Terug: ``{signalen: list[str], kritiek: int, aandacht: int}``. Een component buiten de tenant
    (of onbestaand) levert een lege badge (geen lek)."""
    tid = _tenant_uuid(tenant_id)
    bestaat = (
        await session.execute(
            select(Component.id).where(Component.tenant_id == tid, Component.id == component_id)
        )
    ).first() is not None
    if not bestaat:
        return {"signalen": [], "kritiek": 0, "aandacht": 0}

    geen_eigenaar = (
        await session.execute(
            select(Component.id).where(
                Component.tenant_id == tid,
                Component.id == component_id,
                Component.eigenaar_organisatie_id.is_(None),
            )
        )
    ).first() is not None
    geen_rol = (
        await session.execute(
            select(Roltoewijzing.id).where(
                Roltoewijzing.tenant_id == tid, Roltoewijzing.object_id == component_id,
            )
        )
    ).first() is None
    geen_gg = (
        await session.execute(
            select(Relatie.id).where(
                Relatie.tenant_id == tid, Relatie.relatietype == "serving",
                Relatie.doel_id == component_id,
            )
        )
    ).first() is None
    geisoleerd = (
        await session.execute(
            select(Relatie.id).where(
                Relatie.tenant_id == tid, Relatie.relatietype == "flow",
                or_(Relatie.bron_id == component_id, Relatie.doel_id == component_id),
            )
        )
    ).first() is None
    biv_onvolledig = (
        await session.execute(
            select(Component.id).where(
                Component.tenant_id == tid,
                Component.id == component_id,
                _biv_onvolledig(),
            )
        )
    ).first() is not None

    kritiek: list[str] = []
    aandacht: list[str] = []
    if geen_eigenaar:
        kritiek.append(_SIG_EIGENAAR)
    if geen_rol:
        kritiek.append(_SIG_VERANTWOORDELIJKE)
    if biv_onvolledig:
        kritiek.append(_SIG_BIV)
    if geen_gg:
        aandacht.append(_SIG_GG)
    if geisoleerd:
        aandacht.append(_SIG_ISOLATIE)
    if geen_rol:  # een component zonder roltoewijzing telt óók als 'object zonder roltoewijzing' (ADR-035)
        aandacht.append(_SIG_OBJ_ROL)
    return {"signalen": kritiek + aandacht, "kritiek": len(kritiek), "aandacht": len(aandacht)}


# ── Slice 2 — aandacht-signalen (alle puur SELECT) ───────────────────────────────────────────────
async def component_zonder_gebruikersgroep(session: AsyncSession, tenant_id) -> list[dict]:
    """Componenten zonder serving-relatie van een gebruikersgroep (doel=component)."""
    tid = _tenant_uuid(tenant_id)
    geen_serving = ~exists(
        select(Relatie.id).where(
            Relatie.tenant_id == tid, Relatie.relatietype == "serving", Relatie.doel_id == Component.id
        )
    )
    stmt = (
        select(Component.id, Component.naam)
        .where(Component.tenant_id == tid, geen_serving)
        .order_by(Component.naam.asc(), Component.id.asc())
    )
    return [_aitem(r, _SIG_GG) for r in (await session.execute(stmt)).all()]


async def component_geisoleerd(session: AsyncSession, tenant_id) -> list[dict]:
    """Componenten zonder enige flow-relatie (als bron óf doel)."""
    tid = _tenant_uuid(tenant_id)
    geen_flow = ~exists(
        select(Relatie.id).where(
            Relatie.tenant_id == tid, Relatie.relatietype == "flow",
            or_(Relatie.bron_id == Component.id, Relatie.doel_id == Component.id),
        )
    )
    stmt = (
        select(Component.id, Component.naam)
        .where(Component.tenant_id == tid, geen_flow)
        .order_by(Component.naam.asc(), Component.id.asc())
    )
    return [_aitem(r, _SIG_ISOLATIE) for r in (await session.execute(stmt)).all()]


async def contract_zonder_component(session: AsyncSession, tenant_id) -> list[dict]:
    """Contracten zonder association-relatie van een component (doel=contract)."""
    tid = _tenant_uuid(tenant_id)
    geen_assoc = ~exists(
        select(Relatie.id).where(
            Relatie.tenant_id == tid, Relatie.relatietype == "association", Relatie.doel_id == Contract.id
        )
    )
    stmt = (
        select(Contract.id, Contract.contractnaam.label("naam"))
        .where(Contract.tenant_id == tid, geen_assoc)
        .order_by(Contract.contractnaam.asc(), Contract.id.asc())
    )
    return [_aitem(r, _SIG_CONTRACT) for r in (await session.execute(stmt)).all()]


async def object_zonder_roltoewijzing(session: AsyncSession, tenant_id) -> list[dict]:
    """Componenten, contracten én gebruikersgroepen zonder enige roltoewijzing (object_id)."""
    tid = _tenant_uuid(tenant_id)
    out: list[dict] = []
    comp = (await session.execute(
        select(Component.id, Component.naam)
        .where(Component.tenant_id == tid, _geen_roltoewijzing(Component.id, tid))
        .order_by(Component.naam.asc(), Component.id.asc())
    )).all()
    out += [_aitem(r, _SIG_OBJ_ROL, "component") for r in comp]
    contr = (await session.execute(
        select(Contract.id, Contract.contractnaam.label("naam"))
        .where(Contract.tenant_id == tid, _geen_roltoewijzing(Contract.id, tid))
        .order_by(Contract.contractnaam.asc(), Contract.id.asc())
    )).all()
    out += [_aitem(r, _SIG_OBJ_ROL, "contract") for r in contr]
    afd = aliased(Partij)
    gg = (await session.execute(
        select(Gebruikersgroep.id, _gg_label(afd).label("naam"))
        .outerjoin(afd, and_(afd.id == Gebruikersgroep.afdeling_id, afd.tenant_id == tid))
        .where(Gebruikersgroep.tenant_id == tid, _geen_roltoewijzing(Gebruikersgroep.id, tid))
        .order_by(_gg_label(afd).asc(), Gebruikersgroep.id.asc())
    )).all()
    out += [_aitem(r, _SIG_OBJ_ROL, "gebruikersgroep") for r in gg]
    return out


async def gebruiksfeit_zonder_verfijning(session: AsyncSession, tenant_id) -> list[dict]:
    """Grove gebruiksfeiten (organisatie gebruikt applicatie) zónder énige afdeling-verfijning
    eronder — "gebruik bekend, detaillering ontbreekt" (ADR-036 stap C). Dooft zodra één
    afdeling-mét-die-organisatie eronder hangt (een gebruikersgroep met `gebruik_id` naar dit feit).

    Aantal-onbekend telt hier bewust NIET mee (een afdeling waarvan alleen het ledental ontbreekt is
    géén ontbrekende detaillering — voorkomt ruis). Label = "applicatie — organisatie"; de badge linkt
    naar de applicatie (`applicatie_id`). Puur read-only, engine onaangeroerd."""
    tid = _tenant_uuid(tenant_id)
    geen_verfijning = ~exists(
        select(Gebruikersgroep.id).where(
            Gebruikersgroep.tenant_id == tid, Gebruikersgroep.gebruik_id == Organisatiegebruik.id
        )
    )
    stmt = (
        select(
            Organisatiegebruik.id,
            Organisatiegebruik.applicatie_id.label("applicatie_id"),
            Component.naam.label("app_naam"),
            Partij.naam.label("org_naam"),
        )
        .join(Component, and_(Component.id == Organisatiegebruik.applicatie_id, Component.tenant_id == tid))
        .join(Partij, and_(Partij.id == Organisatiegebruik.organisatie_id, Partij.tenant_id == tid))
        .where(Organisatiegebruik.tenant_id == tid, geen_verfijning)
        .order_by(Component.naam.asc(), Partij.naam.asc(), Organisatiegebruik.id.asc())
    )
    return [
        {
            "id": r.id, "applicatie_id": r.applicatie_id,
            "naam": f"{r.app_naam} — {r.org_naam}",
            "signaal": _SIG_GEBRUIK_GEEN_VERFIJNING, "niveau": _AANDACHT,
        }
        for r in (await session.execute(stmt)).all()
    ]


async def antwoord_zonder_verantwoordelijke(session: AsyncSession, tenant_id) -> list[dict]:
    """Gescoorde checklistantwoorden (``score IS NOT NULL``) zónder ``verantwoordelijke_id`` — de
    bron staat er nog niet bij (ADR-037). Lege placeholder-rijen (geen score) vuren bewust NIET.

    Engine-veilig: leest ``checklistscore`` via de ``table()``-handle (géén Checklistscore-ORM),
    zoals ``lifecycle_status`` via ``_profiel``. Label = "component — vraag_code"; het item draagt
    ``component_id`` voor de doorklik naar de checklist-context. Puur read-only."""
    tid = _tenant_uuid(tenant_id)
    cs = _checklistscore
    stmt = (
        select(
            cs.c.id,
            cs.c.component_id.label("component_id"),
            Component.naam.label("comp_naam"),
            ChecklistVraag.code.label("vraag_code"),
        )
        .join(Component, and_(Component.id == cs.c.component_id, Component.tenant_id == tid))
        .join(ChecklistVraag, and_(ChecklistVraag.id == cs.c.checklistvraag_id, ChecklistVraag.tenant_id == tid))
        .where(cs.c.tenant_id == tid, cs.c.score.isnot(None), cs.c.verantwoordelijke_id.is_(None))
        .order_by(Component.naam.asc(), ChecklistVraag.code.asc(), cs.c.id.asc())
    )
    return [
        {
            "id": r.id, "component_id": r.component_id,
            "naam": f"{r.comp_naam} — {r.vraag_code}",
            "signaal": _SIG_ANTW_VERANTW, "niveau": _AANDACHT,
        }
        for r in (await session.execute(stmt)).all()
    ]


async def registratiegaten(session: AsyncSession, tenant_id) -> dict:
    """Alle actieve signaaltypen, gegroepeerd per ernst (kritiek/aandacht). Read-only."""
    return {
        "kritiek": {
            _SIG_EIGENAAR: await component_zonder_eigenaar(session, tenant_id),
            _SIG_VERANTWOORDELIJKE: await component_zonder_verantwoordelijke(session, tenant_id),
            _SIG_BIV: await component_biv_onvolledig(session, tenant_id),
        },
        "aandacht": {
            _SIG_GG: await component_zonder_gebruikersgroep(session, tenant_id),
            _SIG_ISOLATIE: await component_geisoleerd(session, tenant_id),
            _SIG_CONTRACT: await contract_zonder_component(session, tenant_id),
            _SIG_GEBRUIK_GEEN_VERFIJNING: await gebruiksfeit_zonder_verfijning(session, tenant_id),
            _SIG_OBJ_ROL: await object_zonder_roltoewijzing(session, tenant_id),
            _SIG_ANTW_VERANTW: await antwoord_zonder_verantwoordelijke(session, tenant_id),
        },
    }
