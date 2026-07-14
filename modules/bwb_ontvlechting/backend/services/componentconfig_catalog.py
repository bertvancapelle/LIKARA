"""Catalogus-lookup/-validatie voor de componentcatalogus (ADR-021 Besluit 8).

Spiegel van `contractconfig_catalog` voor `componentconfig_optie` (dimensies
`componenttype` + `structuurrelatie_type`). De tenant-sessie (`lk_app`) mag de
platform-brede catalogus LEZEN (SELECT-grant, CD051). Valideren tegen de **actieve**
opties van de **juiste dimensie**; uitlezen resolvet ook gedeactiveerde sleutels.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import ComponentConfigDimensie, ComponentConfigOptie
from services.errors import OngeldigeRegistratie


async def _opties(session: AsyncSession, dimensie: ComponentConfigDimensie, *, alleen_actief: bool):
    stmt = select(
        ComponentConfigOptie.optie_sleutel,
        ComponentConfigOptie.label,
        ComponentConfigOptie.actief,
    ).where(ComponentConfigOptie.dimensie == dimensie)
    if alleen_actief:
        stmt = stmt.where(ComponentConfigOptie.actief.is_(True))
    return list((await session.execute(stmt)).all())


async def actieve_sleutels(session: AsyncSession, dimensie: ComponentConfigDimensie) -> set[str]:
    return {r.optie_sleutel for r in await _opties(session, dimensie, alleen_actief=True)}


async def is_checklist_dragend(session: AsyncSession, componenttype: str) -> bool:
    """ADR-022 Fase E (Besluit 1): de catalogus-vlag is de ENIGE bron voor
    "krijgt dit type een component_profiel + engine". Onbekend type ⇒ False."""
    return bool(
        (
            await session.execute(
                select(ComponentConfigOptie.checklist_dragend).where(
                    ComponentConfigOptie.dimensie == ComponentConfigDimensie.componenttype,
                    ComponentConfigOptie.optie_sleutel == componenttype,
                )
            )
        ).scalar_one_or_none()
    )


async def labels(
    session: AsyncSession, dimensie: ComponentConfigDimensie
) -> dict[str, tuple[str, bool]]:
    """`{optie_sleutel: (label, actief)}` voor ALLE opties (incl. inactieve)."""
    return {r.optie_sleutel: (r.label, r.actief) for r in await _opties(session, dimensie, alleen_actief=False)}


async def valideer_sleutel(
    session: AsyncSession, dimensie: ComponentConfigDimensie, sleutel: str
) -> None:
    """Weiger een onbekende/inactieve/verkeerd-gedimensioneerde sleutel ⇒ 422 `ONGELDIGE_OPTIE`."""
    if sleutel in await actieve_sleutels(session, dimensie):
        return
    raise OngeldigeRegistratie(
        "ONGELDIGE_OPTIE",
        f"Onbekende of inactieve optie '{sleutel}' voor dimensie '{dimensie.value}'.",
    )


async def archimate_typing(session: AsyncSession) -> dict[str, dict[str, str | None]]:
    """ADR-023 Fase C — per `componenttype` de ArchiMate-typing (element/laag/aspect)
    uit de catalogus. ALLE opties (incl. inactieve) zodat historische component-rijen
    resolvebaar blijven. Read-only projectie (geen schemawijziging); voedt het
    laag-label + laag-filter van de componentlijst."""
    rijen = (
        await session.execute(
            select(
                ComponentConfigOptie.optie_sleutel,
                ComponentConfigOptie.archimate_element,
                ComponentConfigOptie.laag,
                ComponentConfigOptie.aspect,
            ).where(ComponentConfigOptie.dimensie == ComponentConfigDimensie.componenttype)
        )
    ).all()
    return {
        r.optie_sleutel: {
            "archimate_element": r.archimate_element,
            "laag": r.laag,
            "aspect": r.aspect,
        }
        for r in rijen
    }


async def kenmerk_definitie(session: AsyncSession, relatietype: str) -> dict:
    """ADR-023 OK-2 — de kenmerk-property-definities van een ArchiMate-relatietype
    (dim `archimate_relatie`). Onbekend type ⇒ leeg (geen toegestane kenmerken)."""
    return (
        await session.execute(
            select(ComponentConfigOptie.kenmerk_definitie).where(
                ComponentConfigOptie.dimensie == ComponentConfigDimensie.archimate_relatie,
                ComponentConfigOptie.optie_sleutel == relatietype,
            )
        )
    ).scalar_one_or_none() or {}


def resolveer_een(sleutel: str, label_map: dict[str, tuple[str, bool]]) -> str:
    """Resolveer één sleutel naar zijn label (fallback: de sleutel zelf)."""
    return label_map.get(sleutel, (sleutel, False))[0]


async def actieve_opties_per_dimensie(session: AsyncSession) -> dict[str, list[dict]]:
    """Actieve opties per dimensie voor formuliergebruik (CD052 §5).

    `{componenttype:[{optie_sleutel,label}…], structuurrelatie_type:[…]}`, per dimensie
    gesorteerd op `volgorde`. Alleen-actief."""
    rijen = (
        await session.execute(
            select(
                ComponentConfigOptie.dimensie,
                ComponentConfigOptie.optie_sleutel,
                ComponentConfigOptie.label,
                ComponentConfigOptie.volgorde,
                ComponentConfigOptie.checklist_dragend,
                ComponentConfigOptie.ondersteunt_werk,
                ComponentConfigOptie.archimate_element,
                ComponentConfigOptie.laag,
            )
            .where(ComponentConfigOptie.actief.is_(True))
            .order_by(
                ComponentConfigOptie.dimensie,
                ComponentConfigOptie.volgorde,
                ComponentConfigOptie.id,
            )
        )
    ).all()
    uit: dict[str, list[dict]] = {d.value: [] for d in ComponentConfigDimensie}
    for r in rijen:
        dim = r.dimensie.value if hasattr(r.dimensie, "value") else str(r.dimensie)
        # ADR-022 Fase E: `checklist_dragend` meeleveren (alleen zinvol voor componenttype).
        # ADR-045: `ondersteunt_werk` idem — het tenant-read-pad voor de catalogus-vlag
        # (voedt het lijstfilter nu en de koppel-picker in gate 2).
        # ADR-023 Fase C: ArchiMate-laag/-element meeleveren (read-only typing-projectie; voor
        # het laag-filter + laag-label in de componentlijst). Null voor andere dimensies.
        uit[dim].append(
            {
                "optie_sleutel": r.optie_sleutel, "label": r.label,
                "checklist_dragend": r.checklist_dragend,
                "ondersteunt_werk": r.ondersteunt_werk,
                "archimate_element": r.archimate_element, "laag": r.laag,
            }
        )
    return uit
