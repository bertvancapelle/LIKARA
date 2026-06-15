"""Service-laag voor de entiteit Contract (ADR-020 Besluit 2/3/4).

Tenant-scoped (RLS + expliciet `tenant_id`-filter); record buiten de tenant ⇒ 404
(OP-6). Puur registratief — geen afgeleide logica, geen engine-koppeling.

Cross-row-invarianten (Besluit 3) leven hier (CD040 dekt alleen de zelf-consistentie
via de DB-CHECK):
  I1 — `mantelcontract_id` moet (binnen de tenant) een `mantelcontract` zijn → 422 `ONGELDIGE_MANTEL`.
  I2 — een `deelcontract` erft de leverancier van zijn mantel (defensief gevalideerd,
       niet stil overschreven) → 422 `LEVERANCIER_MISMATCH`.
  I3 — type/leverancier van een mantel mét deelcontracten wijzigen → 422 `MANTEL_IN_GEBRUIK`.
  I4 — een mantel met deelcontracten of een contract met koppelingen verwijderen → 409 `IN_GEBRUIK`.

Dekking/kostenmodel zijn declaratieve 0..n-tagsets tegen de catalogus (Besluit 6/10).
"""
import uuid
from datetime import date, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    Component,
    ComponentProfiel,
    Contract,
    ContractConfigDimensie,
    ContractDekking,
    ContractKostenmodel,
    ContractType,
    Element,
    ElementType,
    Leverancier,
    Relatie,
)

_ASSOCIATION = "association"
from schemas.contract import ContractCreate, ContractUpdate
from services import contractconfig_catalog as catalog
from services import leverancier_service
from services.errors import NietGevonden, OngeldigeRegistratie, RegistratieConflict
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_ENTITEIT = "contract"
_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100
_STANDAARD_SORT = "created_at"
_STANDAARD_ORDER = "asc"

_SORTEERBARE_KOLOMMEN = {
    "created_at": Contract.created_at,
    "contractnaam": Contract.contractnaam,
    "begindatum": Contract.begindatum,
    "einddatum": Contract.einddatum,
}
_WAARDE_PARSERS = {
    "created_at": datetime.fromisoformat,
    "contractnaam": str,
    "begindatum": date.fromisoformat,
    "einddatum": date.fromisoformat,
}

_TAG_MODEL = {"dekking": ContractDekking, "kostenmodel": ContractKostenmodel}
_TAG_DIMENSIE = {
    "dekking": ContractConfigDimensie.dekking,
    "kostenmodel": ContractConfigDimensie.kostenmodel,
}

_LIKE_ESCAPE = "\\"


def _escape_like(term: str) -> str:
    return term.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2).replace("%", r"\%").replace("_", r"\_")


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


# ── interne helpers ─────────────────────────────────────────────────────────────

async def haal_op(session: AsyncSession, tenant_id, contract_id) -> Contract:
    """Eén contract binnen de tenant; niet gevonden ⇒ `NietGevonden` (404)."""
    tid = _tenant_uuid(tenant_id)
    obj = (
        await session.execute(
            select(Contract).where(Contract.id == contract_id, Contract.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden(_ENTITEIT, contract_id)
    return obj


async def _heeft_deelcontracten(session: AsyncSession, tid: uuid.UUID, contract_id) -> bool:
    bestaat = (
        await session.execute(
            select(Contract.id)
            .where(Contract.tenant_id == tid, Contract.mantelcontract_id == contract_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    return bestaat is not None


async def _heeft_koppelingen(session: AsyncSession, tid: uuid.UUID, contract_id) -> bool:
    # ADR-023: component↔contract is nu een association-relatie (doel=contract). Een contract
    # met component-associaties verdwijnt niet stil (I4 behouden; analoog aan de leverancier-RESTRICT).
    bestaat = (
        await session.execute(
            select(Relatie.id)
            .where(
                Relatie.tenant_id == tid, Relatie.doel_id == contract_id,
                Relatie.relatietype == _ASSOCIATION,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return bestaat is not None


async def _valideer_consistentie(
    session: AsyncSession, tenant_id, *, contracttype: ContractType, mantelcontract_id, leverancier_id
) -> None:
    """I1/I2 + de deelcontract⇔mantel-consistentie (nette 422 vóór de DB-CHECK)."""
    if contracttype == ContractType.deelcontract:
        if mantelcontract_id is None:
            raise OngeldigeRegistratie(
                "ONGELDIGE_MANTEL", "Een deelcontract vereist een mantelcontract."
            )
        mantel = await haal_op(session, tenant_id, mantelcontract_id)  # 404 buiten tenant
        if mantel.contracttype != ContractType.mantelcontract:  # I1
            raise OngeldigeRegistratie(
                "ONGELDIGE_MANTEL", "Het opgegeven mantelcontract is geen mantelcontract."
            )
        if mantel.leverancier_id != leverancier_id:  # I2
            raise OngeldigeRegistratie(
                "LEVERANCIER_MISMATCH",
                "Een deelcontract erft de leverancier van zijn mantel; de opgegeven "
                "leverancier wijkt af.",
            )
    elif mantelcontract_id is not None:
        raise OngeldigeRegistratie(
            "ONGELDIGE_MANTEL", "Alleen een deelcontract mag onder een mantelcontract hangen."
        )


async def _zet_tags(session: AsyncSession, tid: uuid.UUID, contract_id, veld: str, sleutels: list[str]) -> None:
    """Vervang de volledige tagset (declaratief) voor een dimensie."""
    model = _TAG_MODEL[veld]
    await session.execute(
        delete(model).where(model.tenant_id == tid, model.contract_id == contract_id)
    )
    for s in sleutels:
        session.add(model(tenant_id=tid, contract_id=contract_id, optie_sleutel=s))


async def _laad_tag_sleutels(session: AsyncSession, tid: uuid.UUID, contract_id, veld: str) -> list[str]:
    model = _TAG_MODEL[veld]
    rijen = (
        await session.execute(
            select(model.optie_sleutel)
            .where(model.tenant_id == tid, model.contract_id == contract_id)
            .order_by(model.optie_sleutel)
        )
    ).scalars().all()
    return list(rijen)


# ── publieke API ────────────────────────────────────────────────────────────────

async def lees_detail(session: AsyncSession, tenant_id, contract_id) -> dict:
    """Detail (ContractRead): contract + `leverancier_naam` + geresolveerde tagsets."""
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, contract_id)
    lev_naam = (
        await session.execute(
            select(Leverancier.naam).where(
                Leverancier.id == obj.leverancier_id, Leverancier.tenant_id == tid
            )
        )
    ).scalar_one()
    dekking_sleutels = await _laad_tag_sleutels(session, tid, contract_id, "dekking")
    kostenmodel_sleutels = await _laad_tag_sleutels(session, tid, contract_id, "kostenmodel")
    dekking_labels = await catalog.labels(session, ContractConfigDimensie.dekking)
    kostenmodel_labels = await catalog.labels(session, ContractConfigDimensie.kostenmodel)
    return {
        "id": obj.id,
        "leverancier_id": obj.leverancier_id,
        "leverancier_naam": lev_naam,
        "contracttype": obj.contracttype,
        "mantelcontract_id": obj.mantelcontract_id,
        "contractnaam": obj.contractnaam,
        "extern_contract_id": obj.extern_contract_id,
        "leverancier_contract_id": obj.leverancier_contract_id,
        "begindatum": obj.begindatum,
        "einddatum": obj.einddatum,
        "vernieuwingsdatum": obj.vernieuwingsdatum,
        "omschrijving": obj.omschrijving,
        "toelichting": obj.toelichting,
        "dekking": catalog.resolveer(dekking_sleutels, dekking_labels),
        "kostenmodel": catalog.resolveer(kostenmodel_sleutels, kostenmodel_labels),
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


async def lijst(
    session: AsyncSession,
    tenant_id,
    *,
    limit: int = _STANDAARD_LIMIT,
    after: str | None = None,
    sort: str = _STANDAARD_SORT,
    order: str = _STANDAARD_ORDER,
    leverancier_id: uuid.UUID | None = None,
    contracttype: str | None = None,
    dekking: str | None = None,
    kostenmodel: str | None = None,
    zoek: str | None = None,
) -> tuple[list[dict], str | None]:
    """v2n-keyset-lijst (join op `Leverancier` voor de naam). Filters AND-gecombineerd;
    `dekking`/`kostenmodel` filteren via de tagtabellen; `zoek` = ge-escapete ILIKE op
    `contractnaam`. Default = `created_at` asc."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    if sort not in _SORTEERBARE_KOLOMMEN:
        raise ValueError(f"onbekend sorteerveld: {sort}")
    if order not in (_STANDAARD_ORDER, "desc"):
        raise ValueError(f"onbekende sorteerrichting: {order}")
    kolom = _SORTEERBARE_KOLOMMEN[sort]

    stmt = (
        select(
            Contract.id.label("id"),
            Contract.contractnaam.label("contractnaam"),
            Contract.contracttype.label("contracttype"),
            Contract.leverancier_id.label("leverancier_id"),
            Leverancier.naam.label("leverancier_naam"),
            Contract.mantelcontract_id.label("mantelcontract_id"),
            Contract.begindatum.label("begindatum"),
            Contract.einddatum.label("einddatum"),
            Contract.vernieuwingsdatum.label("vernieuwingsdatum"),
            Contract.created_at.label("created_at"),
            Contract.updated_at.label("updated_at"),
        )
        .join(Leverancier, Leverancier.id == Contract.leverancier_id)
        .where(Contract.tenant_id == tid)
    )
    if leverancier_id is not None:
        stmt = stmt.where(Contract.leverancier_id == leverancier_id)
    if contracttype:
        stmt = stmt.where(Contract.contracttype == ContractType(contracttype))
    if zoek:
        stmt = stmt.where(Contract.contractnaam.ilike(f"%{_escape_like(zoek)}%", escape=_LIKE_ESCAPE))
    if dekking:
        stmt = stmt.where(
            Contract.id.in_(
                select(ContractDekking.contract_id).where(
                    ContractDekking.tenant_id == tid, ContractDekking.optie_sleutel == dekking
                )
            )
        )
    if kostenmodel:
        stmt = stmt.where(
            Contract.id.in_(
                select(ContractKostenmodel.contract_id).where(
                    ContractKostenmodel.tenant_id == tid, ContractKostenmodel.optie_sleutel == kostenmodel
                )
            )
        )
    if after:
        c_sort, c_order, c_is_null, c_waarde_str, c_id = decode_sort_cursor_nullable(after)
        if c_sort != sort or c_order != order:
            raise ValueError("cursor past niet bij de actieve sortering")
        c_waarde = None if c_is_null else _WAARDE_PARSERS[sort](c_waarde_str)
        stmt = stmt.where(
            keyset_seek_nulls_last(
                kolom, Contract.id, order=order, is_null=c_is_null, waarde=c_waarde, cursor_id=c_id
            )
        )
    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, Contract.id, order)).limit(limit + 1)

    rijen = (await session.execute(stmt)).all()
    heeft_meer = len(rijen) > limit
    zichtbaar = rijen[:limit]
    items = [
        {
            "id": r.id,
            "contractnaam": r.contractnaam,
            "contracttype": r.contracttype,
            "leverancier_id": r.leverancier_id,
            "leverancier_naam": r.leverancier_naam,
            "mantelcontract_id": r.mantelcontract_id,
            "begindatum": r.begindatum,
            "einddatum": r.einddatum,
            "vernieuwingsdatum": r.vernieuwingsdatum,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        }
        for r in zichtbaar
    ]
    volgende = (
        encode_sort_cursor_nullable(
            sort=sort, order=order, waarde=getattr(zichtbaar[-1], sort), id=zichtbaar[-1].id
        )
        if heeft_meer
        else None
    )
    return items, volgende


async def maak_aan(session: AsyncSession, tenant_id, data: ContractCreate) -> dict:
    tid = _tenant_uuid(tenant_id)
    await leverancier_service.haal_op(session, tenant_id, data.leverancier_id)  # 404 buiten tenant
    await _valideer_consistentie(
        session, tenant_id,
        contracttype=data.contracttype,
        mantelcontract_id=data.mantelcontract_id,
        leverancier_id=data.leverancier_id,
    )
    await catalog.valideer_sleutels(session, ContractConfigDimensie.dekking, data.dekking)
    await catalog.valideer_sleutels(session, ContractConfigDimensie.kostenmodel, data.kostenmodel)

    velden = data.model_dump(exclude={"dekking", "kostenmodel"})
    # ADR-023 B-mig-1: contract is een element-subtype (shared-PK, business-laag).
    elem = Element(tenant_id=tid, element_type=ElementType.contract)
    session.add(elem)
    await session.flush()
    obj = Contract(id=elem.id, tenant_id=tid, **velden)
    session.add(obj)
    await session.flush()  # obj.id
    await _zet_tags(session, tid, obj.id, "dekking", data.dekking)
    await _zet_tags(session, tid, obj.id, "kostenmodel", data.kostenmodel)
    await session.commit()
    return await lees_detail(session, tenant_id, obj.id)


async def werk_bij(session: AsyncSession, tenant_id, contract_id, data: ContractUpdate) -> dict:
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, contract_id)
    velden = data.model_dump(exclude_unset=True)

    nieuw_type = velden.get("contracttype", obj.contracttype)
    nieuw_mantel = velden["mantelcontract_id"] if "mantelcontract_id" in velden else obj.mantelcontract_id
    nieuw_lev = velden.get("leverancier_id", obj.leverancier_id)

    # I3 — mantel met deelcontracten: type-/leverancier-wissel weigeren.
    if obj.contracttype == ContractType.mantelcontract and await _heeft_deelcontracten(session, tid, contract_id):
        if "contracttype" in velden and nieuw_type != ContractType.mantelcontract:
            raise OngeldigeRegistratie(
                "MANTEL_IN_GEBRUIK",
                "Dit mantelcontract heeft deelcontracten; het contracttype kan niet worden gewijzigd.",
            )
        if "leverancier_id" in velden and nieuw_lev != obj.leverancier_id:
            raise OngeldigeRegistratie(
                "MANTEL_IN_GEBRUIK",
                "Dit mantelcontract heeft deelcontracten; de leverancier kan niet worden gewijzigd.",
            )

    if "leverancier_id" in velden and nieuw_lev != obj.leverancier_id:
        await leverancier_service.haal_op(session, tenant_id, nieuw_lev)  # 404 buiten tenant

    if {"contracttype", "mantelcontract_id", "leverancier_id"} & velden.keys():
        if nieuw_mantel is not None and nieuw_mantel == contract_id:
            raise OngeldigeRegistratie(
                "ONGELDIGE_MANTEL", "Een contract kan niet zijn eigen mantelcontract zijn."
            )
        await _valideer_consistentie(
            session, tenant_id,
            contracttype=nieuw_type, mantelcontract_id=nieuw_mantel, leverancier_id=nieuw_lev,
        )

    if "dekking" in velden:
        await catalog.valideer_sleutels(session, ContractConfigDimensie.dekking, velden["dekking"])
    if "kostenmodel" in velden:
        await catalog.valideer_sleutels(session, ContractConfigDimensie.kostenmodel, velden["kostenmodel"])

    for veld, waarde in velden.items():
        if veld in ("dekking", "kostenmodel"):
            continue
        setattr(obj, veld, waarde)
    if "dekking" in velden:
        await _zet_tags(session, tid, contract_id, "dekking", velden["dekking"])
    if "kostenmodel" in velden:
        await _zet_tags(session, tid, contract_id, "kostenmodel", velden["kostenmodel"])

    await session.commit()
    return await lees_detail(session, tenant_id, contract_id)


async def verwijder(session: AsyncSession, tenant_id, contract_id) -> None:
    """Verwijder binnen de tenant. Een mantel met deelcontracten of een contract met
    koppelingen wordt geweigerd (409 `IN_GEBRUIK`, I4). Dekking/kostenmodel-tags
    cascaden mee via de DB."""
    tid = _tenant_uuid(tenant_id)
    obj = await haal_op(session, tenant_id, contract_id)
    if await _heeft_deelcontracten(session, tid, contract_id):
        raise RegistratieConflict(
            "IN_GEBRUIK", "Dit mantelcontract heeft deelcontracten en kan niet worden verwijderd."
        )
    if await _heeft_koppelingen(session, tid, contract_id):
        raise RegistratieConflict(
            "IN_GEBRUIK", "Dit contract is aan applicaties gekoppeld en kan niet worden verwijderd."
        )
    await session.delete(obj)
    await session.commit()


async def deelcontracten(session: AsyncSession, tenant_id, contract_id) -> list[dict]:
    """De deelcontracten onder een mantel, met gelabelde dekking (CD044 §0c).

    Eigen `DeelcontractItem`-vorm, **los van de gedeelde `ContractLijstItem`**: de
    dekking-resolutie blijft begrensd tot deze kleine per-mantel-lijst (de grote
    contractenlijst krijgt géén per-rij-resolutie). Mantel onbekend ⇒ 404.
    """
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, contract_id)
    rijen = (
        await session.execute(
            select(
                Contract.id.label("id"),
                Contract.contractnaam.label("contractnaam"),
                Contract.contracttype.label("contracttype"),
                Contract.begindatum.label("begindatum"),
                Contract.einddatum.label("einddatum"),
                Contract.vernieuwingsdatum.label("vernieuwingsdatum"),
            )
            .where(Contract.tenant_id == tid, Contract.mantelcontract_id == contract_id)
            .order_by(Contract.contractnaam, Contract.id)
        )
    ).all()
    # Dekking-tags voor álle deelcontracten in één query → groeperen → labelresolutie.
    ids = [r.id for r in rijen]
    dekking_per: dict = {}
    if ids:
        tagrijen = (
            await session.execute(
                select(ContractDekking.contract_id, ContractDekking.optie_sleutel)
                .where(ContractDekking.tenant_id == tid, ContractDekking.contract_id.in_(ids))
                .order_by(ContractDekking.optie_sleutel)
            )
        ).all()
        for t in tagrijen:
            dekking_per.setdefault(t.contract_id, []).append(t.optie_sleutel)
    dekking_labels = await catalog.labels(session, ContractConfigDimensie.dekking)
    return [
        {
            "id": r.id,
            "contractnaam": r.contractnaam,
            "contracttype": r.contracttype,
            "begindatum": r.begindatum,
            "einddatum": r.einddatum,
            "vernieuwingsdatum": r.vernieuwingsdatum,
            "dekking": catalog.resolveer(dekking_per.get(r.id, []), dekking_labels),
        }
        for r in rijen
    ]


async def applicaties(session: AsyncSession, tenant_id, contract_id) -> list[dict]:
    """De aan dit contract gekoppelde applicaties (met rol). Contract onbekend ⇒ 404."""
    tid = _tenant_uuid(tenant_id)
    await haal_op(session, tenant_id, contract_id)
    rol_labels = await catalog.labels(session, ContractConfigDimensie.relatie_rol)
    rijen = (
        await session.execute(
            select(
                Relatie.id.label("koppeling_id"),
                Relatie.bron_id.label("applicatie_id"),  # bron = component (shared-PK)
                Component.naam.label("applicatie_naam"),
                # ADR-022 Fase A: lifecycle leeft op het generieke profiel (shared-PK).
                ComponentProfiel.lifecycle_status.label("lifecycle_status"),
                Relatie.kenmerken.label("kenmerken"),
            )
            .join(Component, Component.id == Relatie.bron_id)
            .join(ComponentProfiel, ComponentProfiel.id == Relatie.bron_id)
            .where(
                Relatie.tenant_id == tid, Relatie.doel_id == contract_id,
                Relatie.relatietype == _ASSOCIATION,
            )
            .order_by(Component.naam, Relatie.id)
        )
    ).all()
    return [
        {
            "koppeling_id": r.koppeling_id,
            "applicatie_id": r.applicatie_id,
            "applicatie_naam": r.applicatie_naam,
            "lifecycle_status": r.lifecycle_status,
            "relatie_rol": (r.kenmerken or {}).get("relatie_rol"),
            "relatie_rol_label": catalog.resolveer_een((r.kenmerken or {}).get("relatie_rol"), rol_labels),
        }
        for r in rijen
    ]
