"""Actor-naam-resolutie (ADR-029 Fase 3b) — gedeeld door klaarverklaring, plateau (en later audit).

Resolveert een actor naar een leesbare naam via de gebruiker-persoon-koppeling (ADR-029):
`gebruiker_persoon.keycloak_sub == actor_sub` (tenant-scoped) → `Partij(persoon).naam`. Geen
koppeling (beheerder/ongekoppeld) of historische rij (geen sub) → de bewaarde e-mail als fallback.
Nooit een lege weergave waar een waarde bestaat.

ENGINE-INVARIANT: read-only naam-lookup; importeert GEEN lifecycle/score-symbolen
(`lifecycle_service`/`herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade`/
`Checklistscore`).
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import GebruikerPersoon, Partij


def _tid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def pak_sub_email(bevestigd_door) -> tuple[str | None, str | None]:
    """Normaliseer een opgeslagen actor-waarde naar (sub, email).

    Nieuwe vorm = dict `{"sub": ..., "email": ...}`; historische vorm = kale e-mailstring
    (dan sub=None, email=de string). `None` → (None, None)."""
    if isinstance(bevestigd_door, dict):
        return bevestigd_door.get("sub"), bevestigd_door.get("email")
    if isinstance(bevestigd_door, str):
        return None, bevestigd_door
    return None, None


async def resolveer_namen(session: AsyncSession, tenant_id, subs: set[str]) -> dict[str, str]:
    """Batch: map van `keycloak_sub` → `persoon.naam` voor de gekoppelde subs (tenant-scoped).
    Subs zonder koppeling staan niet in de map."""
    schone = {s for s in subs if s}
    if not schone:
        return {}
    rijen = (
        await session.execute(
            select(GebruikerPersoon.keycloak_sub, Partij.naam)
            .join(Partij, Partij.id == GebruikerPersoon.persoon_id)
            .where(GebruikerPersoon.tenant_id == _tid(tenant_id), GebruikerPersoon.keycloak_sub.in_(schone))
        )
    ).all()
    return {sub: naam for sub, naam in rijen}


async def resolveer_naam(session: AsyncSession, tenant_id, *, sub: str | None, email: str | None) -> str | None:
    """Naam van één actor: koppeling op `sub` → `persoon.naam`; anders de e-mail-fallback."""
    if sub:
        naam_map = await resolveer_namen(session, tenant_id, {sub})
        if sub in naam_map:
            return naam_map[sub]
    return email


_LIKE_ESCAPE = "\\"


def _escape_like(term: str) -> str:
    return term.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2).replace("%", r"\%").replace("_", r"\_")


async def subs_voor_naam(session: AsyncSession, tenant_id, fragment: str) -> set[str]:
    """Omgekeerde lookup voor het audit-naam-filter: alle `keycloak_sub`'s van gekoppelde
    personen wier naam het (ge-escapete) fragment bevat (tenant-scoped, case-insensitive).
    Lege/whitespace-fragment of geen match → lege set (caller toont dan een lege lijst)."""
    frag = (fragment or "").strip()
    if not frag:
        return set()
    rijen = (
        await session.execute(
            select(GebruikerPersoon.keycloak_sub)
            .join(Partij, Partij.id == GebruikerPersoon.persoon_id)
            .where(
                GebruikerPersoon.tenant_id == _tid(tenant_id),
                Partij.naam.ilike(f"%{_escape_like(frag)}%", escape=_LIKE_ESCAPE),
            )
        )
    ).scalars().all()
    return set(rijen)


async def gekoppelde_subs(session: AsyncSession, tenant_id) -> set[str]:
    """Alle `keycloak_sub`'s in deze tenant die AAN een persoon gekoppeld zijn — ongeacht naam.

    Nodig om het audit-zoekveld dezelfde regel te laten volgen als de kolom "Wie": die toont
    `naam or e-mail`. Een rij mét koppeling toont dus de NAAM, en dan mag een treffer op het
    e-mailadres niet meetellen — anders vindt de consultant een regel op iets wat er niet staat.
    Dat is dezelfde soort fout als het defect dat hier gerepareerd wordt, alleen omgekeerd."""
    rijen = (
        await session.execute(
            select(GebruikerPersoon.keycloak_sub).where(
                GebruikerPersoon.tenant_id == _tid(tenant_id),
            )
        )
    ).scalars().all()
    return set(rijen)
