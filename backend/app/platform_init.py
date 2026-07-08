"""Platform-initialisatie — platform-brede referentiedata zaaien.

Draai dit ÉÉN keer per platform, direct ná `alembic upgrade head`:

    cd backend && python3 -m app.platform_init

De 89 checklistvragen (ADR-009) zijn platform-brede referentiedata die door
álle tenants gedeeld worden — ze horen NIET bij tenant-onboarding. Het zaaien
gebeurt zonder RLS-/tenant-context via `get_platform_db_session()` en is
idempotent (INSERT ... ON CONFLICT (code) DO NOTHING), dus herhaalde uitvoering
is veilig.

`CHECKLIST_VRAGEN` blijft de enige bron — hier hergebruikt, niet gedupliceerd.
"""
import asyncio
import pathlib
import sys

# Module-backend op sys.path zodat de seed-bron herbruikt kan worden bij een
# losse CLI-aanroep (`python -m app.platform_init`). In de testomgeving zorgt
# conftest.py al voor dit pad.
_MOD_BACKEND = (
    pathlib.Path(__file__).resolve().parents[2]
    / "modules"
    / "bwb_ontvlechting"
    / "backend"
)
if str(_MOD_BACKEND) not in sys.path:
    sys.path.insert(0, str(_MOD_BACKEND))

from services.seed_applicatiefunctie import seed_applicatiefunctie  # noqa: E402
from services.seed_bivschaal import seed_bivschaal  # noqa: E402
from services.seed_componentconfig import seed_componentconfig  # noqa: E402
from services.seed_componentrol import seed_componentrol  # noqa: E402
from services.seed_contractconfig import seed_contractconfig  # noqa: E402
from services.seed_partijsoort import seed_partijsoort  # noqa: E402
from services.seed_relatiekenmerk import seed_relatiekenmerk  # noqa: E402
from services.seed_vraagbetekenis import seed_vraagbetekenis  # noqa: E402


async def platform_init(session_factory=None) -> int:
    """Zaait **platform-brede** referentiedata. Geeft het aantal componentcatalogus-
    opties terug.

    Stappen op dezelfde platform-sessie: (1) de ADR-020-contractconfig-catalogus,
    (2) de ADR-023-relatiekenmerk-catalogus (o.a. dispositie), (3) de ADR-023-Fase-F
    vraagbetekenis-catalogus (technische_plaatsing), (4) de partijsoort-catalogus,
    (5) de ADR-021/012-componentconfig-catalogus, en (6/7) de ADR-028-componentclassificatie-
    catalogi (componentrol + BIV-schaal). Alle platform-breed (geen tenant/RLS), idempotent.

    ADR-022 W1: de checklistvragen + antwoordconfiguratie zijn **tenant-data** geworden
    en worden NIET meer platform-breed gezaaid — ze worden per tenant gekopieerd uit de
    baseline (`seed_checklist_vragen`/`seed_antwoordconfig`, via onboarding/`dev_seed`).
    Gebruikt `get_platform_db_session()` (géén RLS-/tenant-context). De
    `app.core.database`-import is bewust lazy (offline-importeerbaarheid).
    """
    if session_factory is None:
        from app.core.database import get_platform_db_session

        session_factory = get_platform_db_session

    # ADR-006: vaste systeem-actor voor het platform-audit-spoor van de catalogus-seed.
    from app.core.tenant_context import reset_audit_context, zet_audit_context

    audit_tokens = zet_audit_context("system:platform_init")
    try:
        async with session_factory() as session:
            await seed_contractconfig(session)
            await seed_relatiekenmerk(session)
            await seed_vraagbetekenis(session)
            await seed_partijsoort(session)
            aantal = await seed_componentconfig(session)
            # ADR-028 — componentclassificatie-catalogi (na de componentcatalogus).
            await seed_componentrol(session)
            await seed_bivschaal(session)
            # ADR-042 — applicatiefunctie-catalogus (het wát-veld op de koppelregel).
            await seed_applicatiefunctie(session)
            return aantal
    finally:
        reset_audit_context(audit_tokens)


def main() -> None:
    aantal = asyncio.run(platform_init())
    print(f"platform_init: {aantal} componentcatalogus-opties geborgd (platform-breed)")


if __name__ == "__main__":
    main()
