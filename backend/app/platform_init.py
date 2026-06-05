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

from services.seed import seed_checklist_vragen  # noqa: E402


async def platform_init(session_factory=None) -> int:
    """Zaait platform-brede referentiedata. Geeft het aantal checklistvragen terug.

    Gebruikt `get_platform_db_session()` (géén RLS-/tenant-context) — NOOIT
    `get_session(tenant_id)`. `session_factory` is injecteerbaar voor tests; in
    productie valt hij terug op de platform-sessie. De `app.core.database`-import
    is bewust lazy: die module instantieert `Settings()` en is daardoor niet
    offline (zonder .env) importeerbaar.
    """
    if session_factory is None:
        from app.core.database import get_platform_db_session

        session_factory = get_platform_db_session

    async with session_factory() as session:
        return await seed_checklist_vragen(session)


def main() -> None:
    aantal = asyncio.run(platform_init())
    print(f"platform_init: {aantal} checklistvragen geborgd (platform-breed)")


if __name__ == "__main__":
    main()
