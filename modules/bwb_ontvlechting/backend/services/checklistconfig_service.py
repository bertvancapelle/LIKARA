"""Service-laag — platform-beheer van de checklist-antwoordconfiguratie
(ADR-019 fase 2D, ADR-012 Addendum A).

Draait op `get_platform_session` (cd_platform) — platform-brede referentiedata,
géén tenant-/RLS-context. Raakt `score`/lifecycle/blokkade NIET.

Integriteitsregels:
- **Antwoordtype wisselen is alleen toegestaan vanuit `geen`.** Een reeds-getypeerde
  vraag van type laten wisselen zou opgeslagen tenant-`antwoord_waarde` kunnen
  verwezen; die data leeft in de tenant-tabel `checklistscore`, die cd_platform per
  ADR-012 NIET mag lezen — dus controleren-en-blokkeren-op-gebruik kan niet over de
  domeingrens. We blokkeren daarom conservatief elke wissel van een reeds
  geconfigureerde vraag. `geen → type` is bewijsbaar veilig: een `geen`-vraag kan
  per 2B-validatie geen `antwoord_waarde` hebben.
- **Afgeleide optiesets** (`afgeleid_bron`, 2.1←HostingModel / 12.1←NiveauEnum) zijn
  structureel read-only: alleen het label is aanpasbaar; toevoegen/soft-deactiveren/
  volgorde wijzigen ⇒ `ConfiguratieConflict` (409).
- **Soft-deactivate, nooit hard delete**; `optie_sleutel` is stabiel.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import AntwoordType, ChecklistVraag, ChecklistVraagOptie
from schemas.checklistconfig import AntwoordTypeUpdate, OptieCreate, OptieUpdate
from services.errors import ConfiguratieConflict, NietGevonden


async def lijst_config(session: AsyncSession) -> list[dict]:
    """Alle vragen + antwoordtype + ALLE opties (incl. inactieve), beheer-read."""
    vragen = list(
        (await session.execute(select(ChecklistVraag).order_by(ChecklistVraag.code)))
        .scalars()
        .all()
    )
    opties = list(
        (
            await session.execute(
                select(ChecklistVraagOptie).order_by(
                    ChecklistVraagOptie.vraag_code, ChecklistVraagOptie.volgorde
                )
            )
        )
        .scalars()
        .all()
    )
    per_code: dict[str, list[ChecklistVraagOptie]] = {}
    for o in opties:
        per_code.setdefault(o.vraag_code, []).append(o)
    return [
        {
            "code": v.code,
            "vraag": v.vraag,
            "antwoordtype": v.antwoordtype,
            "opties": per_code.get(v.code, []),
        }
        for v in vragen
    ]


async def _haal_vraag(session: AsyncSession, vraag_code: str) -> ChecklistVraag:
    vraag = (
        await session.execute(select(ChecklistVraag).where(ChecklistVraag.code == vraag_code))
    ).scalar_one_or_none()
    if vraag is None:
        raise NietGevonden("checklistvraag", vraag_code)
    return vraag


async def _haal_optie(session: AsyncSession, optie_id: uuid.UUID) -> ChecklistVraagOptie:
    optie = (
        await session.execute(
            select(ChecklistVraagOptie).where(ChecklistVraagOptie.id == optie_id)
        )
    ).scalar_one_or_none()
    if optie is None:
        raise NietGevonden("checklistvraag_optie", optie_id)
    return optie


async def _is_afgeleide_set(session: AsyncSession, vraag_code: str) -> bool:
    """True als de optieset van deze vraag uit een model-enum is afgeleid."""
    bestaat = (
        await session.execute(
            select(ChecklistVraagOptie.id)
            .where(
                ChecklistVraagOptie.vraag_code == vraag_code,
                ChecklistVraagOptie.afgeleid_bron.is_not(None),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    return bestaat is not None


async def zet_antwoordtype(
    session: AsyncSession, vraag_code: str, data: AntwoordTypeUpdate
) -> dict:
    """Zet het antwoordtype. Alleen vanuit `geen` (orphan-bescherming).

    Geeft de vraag + zijn opties terug in het config-formaat (zoals `lijst_config`).
    """
    vraag = await _haal_vraag(session, vraag_code)
    if data.antwoordtype != vraag.antwoordtype and vraag.antwoordtype != AntwoordType.geen:
        raise ConfiguratieConflict(
            "Een reeds geconfigureerde vraag kan niet van antwoordtype wisselen; "
            "bestaande antwoorden zouden verweesd kunnen raken."
        )
    vraag.antwoordtype = data.antwoordtype
    await session.commit()
    opties = list(
        (
            await session.execute(
                select(ChecklistVraagOptie)
                .where(ChecklistVraagOptie.vraag_code == vraag_code)
                .order_by(ChecklistVraagOptie.volgorde)
            )
        )
        .scalars()
        .all()
    )
    return {
        "code": vraag.code,
        "vraag": vraag.vraag,
        "antwoordtype": data.antwoordtype,
        "opties": opties,
    }


async def voeg_optie_toe(
    session: AsyncSession, vraag_code: str, data: OptieCreate
) -> ChecklistVraagOptie:
    """Voeg een optie toe (niet-afgeleide vraag; unieke stabiele sleutel)."""
    await _haal_vraag(session, vraag_code)
    if await _is_afgeleide_set(session, vraag_code):
        raise ConfiguratieConflict("Aan een afgeleide optieset kan geen optie worden toegevoegd.")

    bestaat = (
        await session.execute(
            select(ChecklistVraagOptie.id).where(
                ChecklistVraagOptie.vraag_code == vraag_code,
                ChecklistVraagOptie.optie_sleutel == data.optie_sleutel,
            )
        )
    ).scalar_one_or_none()
    if bestaat is not None:
        raise ConfiguratieConflict("Een optie met deze sleutel bestaat al voor deze vraag.")

    optie = ChecklistVraagOptie(
        vraag_code=vraag_code,
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
