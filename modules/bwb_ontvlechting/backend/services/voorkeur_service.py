"""Service-laag — persoonlijke gebruikersvoorkeuren (ADR-041 slice 1).

Een generieke key/value-laag: per gebruiker (Keycloak-`sub`) precies één rij per `voorkeur_sleutel`,
met een klein JSON-blob als waarde. Tenant-scoped (RLS + expliciet `tenant_id`-filter). Bovenop RLS
leeft hier de **eigen-scope**: de `sub` komt ALTIJD server-side uit de auth-context (`huidige_actor()`),
nooit uit de payload — een gebruiker leest/schrijft/verwijdert uitsluitend zijn EIGEN voorkeuren. Ook
platform-/tenant-beheerders bewerken langs deze weg geen andermans voorkeuren (voorkeuren zijn
persoonlijk).

Puur registratie/weergave — RAAKT DE ENGINE NOOIT: importeert géén `lifecycle_service`/
`herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade`/`Checklistscore` en raakt geen
lifecycle-/score-/blokkade-state. Dit is een SCHRIJVENDE service; de borging is "raakt de engine niet",
niet "schrijft niets" (hij schrijft uitsluitend naar de eigen `gebruiker_voorkeur`-tabel).
"""
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import huidige_actor
from models.models import GebruikerVoorkeur
from services.errors import OngeldigeRegistratie


# Bekende voorkeur-sleutels (de laag blijft generiek; deze constante houdt de sleutel greppable).
GEBRUIKTE_COMPONENTTYPEN = "gebruikte_componenttypen"  # ADR-041 slice 2


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _huidige_sub() -> str | None:
    """De stabiele Keycloak-sub van de huidige request (server-side; nooit client-aanleverbaar)."""
    sub, _email = huidige_actor()
    return sub


async def haal_waarde(session: AsyncSession, tenant_id, sleutel: str):
    """De waarde-blob van de voorkeur `sleutel` van de HUIDIGE gebruiker, of None (geen voorkeur).

    Voor consumenten (bv. het schrijf-slot van `organisatiegebruik`, slice 2) die een persoonlijke
    voorkeur willen toepassen. Read-only; eigen-scope (`sub` uit de auth-context)."""
    tid = _tenant_uuid(tenant_id)
    sub = _huidige_sub()
    if not sub:
        return None
    obj = await _haal_eigen(session, tid, sub, sleutel)
    return obj.waarde if obj is not None else None


async def lijst_eigen(session: AsyncSession, tenant_id) -> list[GebruikerVoorkeur]:
    """Alle voorkeuren van de HUIDIGE gebruiker (nooit die van een ander)."""
    tid = _tenant_uuid(tenant_id)
    sub = _huidige_sub()
    if not sub:
        return []
    return list(
        (
            await session.execute(
                select(GebruikerVoorkeur)
                .where(GebruikerVoorkeur.tenant_id == tid, GebruikerVoorkeur.sub == sub)
                .order_by(GebruikerVoorkeur.voorkeur_sleutel)
            )
        )
        .scalars()
        .all()
    )


async def _haal_eigen(session: AsyncSession, tid: uuid.UUID, sub: str, sleutel: str) -> GebruikerVoorkeur | None:
    return (
        await session.execute(
            select(GebruikerVoorkeur).where(
                GebruikerVoorkeur.tenant_id == tid,
                GebruikerVoorkeur.sub == sub,
                GebruikerVoorkeur.voorkeur_sleutel == sleutel,
            )
        )
    ).scalar_one_or_none()


async def upsert(session: AsyncSession, tenant_id, sleutel: str, waarde) -> GebruikerVoorkeur:
    """Zet (aanmaken of vervangen) de voorkeur `sleutel` van de huidige gebruiker op `waarde`."""
    tid = _tenant_uuid(tenant_id)
    sub = _huidige_sub()
    if not sub:  # defensief: een geauthenticeerde request draagt altijd een sub
        raise OngeldigeRegistratie("GEEN_ACTOR", "Geen gebruiker-context beschikbaar voor deze voorkeur.")
    obj = await _haal_eigen(session, tid, sub, sleutel)
    if obj is None:
        obj = GebruikerVoorkeur(tenant_id=tid, sub=sub, voorkeur_sleutel=sleutel, waarde=waarde)
        session.add(obj)
    else:
        obj.waarde = waarde
    await session.commit()
    await session.refresh(obj)
    return obj


async def verwijder(session: AsyncSession, tenant_id, sleutel: str) -> None:
    """Herroep de voorkeur `sleutel` van de huidige gebruiker (idempotent — geen fout als hij ontbreekt)."""
    tid = _tenant_uuid(tenant_id)
    sub = _huidige_sub()
    if not sub:
        return
    await session.execute(
        delete(GebruikerVoorkeur).where(
            GebruikerVoorkeur.tenant_id == tid,
            GebruikerVoorkeur.sub == sub,
            GebruikerVoorkeur.voorkeur_sleutel == sleutel,
        )
    )
    await session.commit()
