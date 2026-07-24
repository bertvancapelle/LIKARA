"""Service-laag voor ChecklistVraag — platform-brede referentiedata (read-only).

`checklistvraag` is BEWUST niet tenant-scoped: het heeft geen RLS en geen
`tenant_id` (89 vaste vragen, gedeeld over alle tenants). Daarom géén
`tenant_id`-filter en géén `set_config`-afhankelijkheid; alle tenants zien
dezelfde set. (Wijk hier niet van af door "scoping toe te voegen".)

Sinds ADR-019 levert `lijst_alle` per vraag ook het `antwoordtype` en de
optie-catalogus mee. De opties worden in één query opgehaald (geen N+1) en op
`vraag_code` gegroepeerd; gedeactiveerde opties komen mee (label-resolutie van
historische antwoorden), oplopend op `volgorde`.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import ChecklistCategorie, ChecklistVraag, ChecklistVraagOptie
from services.errors import NietGevonden


async def haal_op(session: AsyncSession, tenant_id, checklistvraag_id) -> ChecklistVraag:
    """Tenant-resolutie van één vraag — de objecthistorie-toegangscheck (ADR-056
    besluit 17: wie de vragenlijst mag lezen, mag de geschiedenis van een vraag
    lezen). RLS scopet (`tenant_id` reist mee voor de uniforme signatuur); onbekend
    of buiten de tenant ⇒ `NietGevonden` (404, no-leak). Óók inactieve vragen zijn
    resolvebaar: een antwoord op een uitgezette vraag blijft historie."""
    vraag = (
        await session.execute(
            select(ChecklistVraag).where(ChecklistVraag.id == checklistvraag_id)
        )
    ).scalar_one_or_none()
    if vraag is None:
        raise NietGevonden("checklistvraag", checklistvraag_id)
    return vraag


async def lijst_alle(session: AsyncSession, componenttype: str | None = None) -> list[dict]:
    """De **actieve** tenant-vragenset (scoring-read) + hun opties.

    ADR-022 W1: `checklistvraag` is tenant-scoped (RLS) → auto-tenant-scoping. Alleen
    `actief=true`-vragen zijn scoorbaar: byte-identiek aan de set die de engine voor
    `aantal_vragen` telt (`herbereken_lifecycle`), zodat de scoringslijst en de telling
    nooit divergeren. Een soft-gedeactiveerde vraag valt uit deze lijst; een reeds
    bestaande score op zo'n vraag blijft als historie in de DB bestaan (W1).

    ADR-022 Fase E (Besluit 3): met `componenttype` gescoped op het type van het
    component dat gescoord wordt — symmetrisch met de per-type engine-telling (een
    `applicatie`-scoring ziet géén vragen van een ander type en omgekeerd)."""
    stmt = select(ChecklistVraag).where(ChecklistVraag.actief.is_(True))
    if componenttype is not None:
        stmt = stmt.where(ChecklistVraag.componenttype == componenttype)
    vragen = list(
        (await session.execute(stmt.order_by(ChecklistVraag.componenttype, ChecklistVraag.code)))
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

    per_vraag: dict = {}
    for o in opties:
        per_vraag.setdefault(o.checklistvraag_id, []).append(o)

    # LI050 (ADR-022 W3): naam/volgorde uit de categorie-entiteit (één query, geen N+1).
    categorieen = {
        c.id: c
        for c in (await session.execute(select(ChecklistCategorie))).scalars().all()
    }

    return [
        {
            "id": v.id,
            "code": v.code,
            "componenttype": v.componenttype,
            "categorie_id": v.categorie_id,
            "categorie_naam": categorieen[v.categorie_id].naam,
            "categorie_volgorde": categorieen[v.categorie_id].volgorde,
            "volgorde": v.volgorde,
            "vraag": v.vraag,
            "prioriteit": v.prioriteit,
            "antwoordtype": v.antwoordtype,
            "opties": per_vraag.get(v.id, []),
        }
        for v in vragen
    ]
