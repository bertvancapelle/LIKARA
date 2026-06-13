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

from models.models import ChecklistVraag, ChecklistVraagOptie


async def lijst_alle(session: AsyncSession) -> list[dict]:
    """De **actieve** tenant-vragenset (scoring-read) + hun opties.

    ADR-022 W1: `checklistvraag` is tenant-scoped (RLS) → auto-tenant-scoping. Alleen
    `actief=true`-vragen zijn scoorbaar: dit is byte-identiek aan de set die de engine
    voor `aantal_vragen` telt (`herbereken_lifecycle`), zodat de scoringslijst en de
    telling nooit divergeren. Een soft-gedeactiveerde vraag valt uit deze lijst; een
    reeds bestaande score op zo'n vraag blijft als historie in de DB bestaan (W1) maar
    verschijnt niet meer als scoorbaar item."""
    vragen = list(
        (
            await session.execute(
                select(ChecklistVraag)
                .where(ChecklistVraag.actief.is_(True))
                .order_by(ChecklistVraag.componenttype, ChecklistVraag.code)
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

    per_vraag: dict = {}
    for o in opties:
        per_vraag.setdefault(o.checklistvraag_id, []).append(o)

    return [
        {
            "id": v.id,
            "code": v.code,
            "componenttype": v.componenttype,
            "categorie_nr": v.categorie_nr,
            "categorie_naam": v.categorie_naam,
            "vraag": v.vraag,
            "prioriteit": v.prioriteit,
            "antwoordtype": v.antwoordtype,
            "opties": per_vraag.get(v.id, []),
        }
        for v in vragen
    ]
