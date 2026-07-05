"""Service-laag — gebruikersbeheer (ADR-029 Fase 2).

LIKARA is de primaire ingang voor gebruikers: aanmaken maakt in één reeks een persoon-partij
(ADR-024) + een Keycloak-account (Admin API) + de koppelrij `gebruiker_persoon`. De koppeling
`keycloak_sub <-> persoon_id` ontstaat bij aanmaak.

ENGINE-INVARIANT: dit raakt de score-/lifecycle-engine NIET. Importeert bewust géén
`lifecycle_service`/`herbereken_lifecycle`/`bepaal_lifecycle`/`ComponentProfiel`/`Blokkade`/
`Checklistscore`. Puur registratief + provisioning.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import keycloak
from app.core.audit import registreer_gebruikersactie
from app.core.tenant_context import huidige_actor
from models.models import GebruikerPersoon, Partij, PartijAard
from schemas.gebruiker import GebruikerPersoonRead
from services import partij_service
from services.errors import (
    KeycloakNietBeschikbaar,
    NietGevonden,
    OngeldigeRegistratie,
    RegistratieConflict,
)
from services.pagination import (
    decode_sort_cursor_nullable,
    encode_sort_cursor_nullable,
    keyset_order_by_nulls_last,
    keyset_seek_nulls_last,
)

_LIMIET = 25
_MAX_LIMIET = 100


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _lees(
    rij: GebruikerPersoon, persoon: Partij, *, org_naam: str | None = None, afd_naam: str | None = None
) -> GebruikerPersoonRead:
    return GebruikerPersoonRead(
        id=rij.id, keycloak_sub=rij.keycloak_sub, persoon_id=rij.persoon_id,
        naam=persoon.naam, email=persoon.email, aangemaakt_op=rij.aangemaakt_op,
        organisatie_id=persoon.organisatie_id, organisatie_naam=org_naam,
        afdeling_id=persoon.afdeling_id, afdeling=afd_naam,
    )


async def _namen(session: AsyncSession, tid: uuid.UUID, ids) -> dict:
    """Resolve partij-namen voor een set ids (organisatie/afdeling), tenant-scoped. Read-only."""
    unieke = {i for i in ids if i}
    if not unieke:
        return {}
    rijen = (
        await session.execute(
            select(Partij.id, Partij.naam).where(Partij.id.in_(unieke), Partij.tenant_id == tid)
        )
    ).all()
    return {r.id: r.naam for r in rijen}


async def maak_gebruiker(
    session: AsyncSession, tenant_id, *, naam: str, email: str,
    afdeling_id: uuid.UUID | None, functietitel: str | None, rol: str,
) -> tuple[GebruikerPersoonRead, str]:
    """Maak een gebruiker aan (persoon + Keycloak-account + koppelrij).

    Retourneert (read-object, tijdelijk_wachtwoord) — het wachtwoord is uitsluitend voor de
    eenmalige 201-respons. Flow met transactionele veiligheid:
      1. email niet al gekoppeld binnen de tenant → anders 422 EMAIL_AL_IN_GEBRUIK.
      2. persoon-partij aanmaken (flush, géén commit) via partij_service.
      3. Keycloak-account aanmaken; faalt dit → rollback (niets in KC of create faalde) → 503.
      4. koppelrij gebruiker_persoon aanmaken (sub uit stap 3).
      5. commit; faalt dit → best-effort KC-account deactiveren (orphan-cleanup) → 503.
    """
    tid = _tenant_uuid(tenant_id)

    # 1. Email mag nog niet aan een gekoppelde gebruiker hangen (join koppelrij <-> persoon).
    bestaat = (
        await session.execute(
            select(GebruikerPersoon.id)
            .join(Partij, Partij.id == GebruikerPersoon.persoon_id)
            .where(GebruikerPersoon.tenant_id == tid, Partij.email == email)
        )
    ).scalar_one_or_none()
    if bestaat is not None:
        raise OngeldigeRegistratie("EMAIL_AL_IN_GEBRUIK", "Er bestaat al een gebruiker met dit e-mailadres.")

    # 2. Persoon-partij aanmaken (flush, geen commit).
    persoon = await partij_service.maak_persoon_flush(
        session, tid, naam=naam, email=email, afdeling_id=afdeling_id, functietitel=functietitel,
    )

    # 3. Keycloak-account aanmaken; bij fout: rollback (geen orphan — create faalde of niets gemaakt).
    wachtwoord = keycloak.genereer_tijdelijk_wachtwoord()
    try:
        sub = await keycloak.maak_keycloak_gebruiker(email=email, naam=naam, tijdelijk_wachtwoord=wachtwoord, rol=rol)
    except keycloak.KeycloakProvisioningFout as exc:
        await session.rollback()
        raise KeycloakNietBeschikbaar(f"Aanmaken Keycloak-account mislukt: {exc.bericht}") from exc

    # 4. Koppelrij.
    koppel = GebruikerPersoon(tenant_id=tid, keycloak_sub=sub, persoon_id=persoon.id)
    session.add(koppel)

    # 5. Commit; faalt dit dan bestaat het KC-account al → best-effort deactiveren (orphan-cleanup).
    try:
        await session.commit()
    except Exception as exc:
        await session.rollback()
        await keycloak.deactiveer_keycloak_gebruiker(sub)
        raise KeycloakNietBeschikbaar("Opslaan van de gebruiker mislukt; het account is gedeactiveerd.") from exc

    await session.refresh(koppel)
    await session.refresh(persoon)
    return _lees(koppel, persoon), wachtwoord


# ── ADR-029 Fase 2b — beheeracties op een bestaande gebruiker ────────────────────────

def _huidige_sub() -> str | None:
    return huidige_actor()[0]


async def _haal_koppel(session: AsyncSession, tid: uuid.UUID, gebruiker_id) -> GebruikerPersoon:
    """De koppelrij binnen de tenant; niet gevonden ⇒ 404 (geen lek)."""
    obj = (
        await session.execute(
            select(GebruikerPersoon).where(
                GebruikerPersoon.id == gebruiker_id, GebruikerPersoon.tenant_id == tid
            )
        )
    ).scalar_one_or_none()
    if obj is None:
        raise NietGevonden("gebruiker", gebruiker_id)
    return obj


async def _tel_actieve_beheerders_behalve(session: AsyncSession, tid: uuid.UUID, *, behalve_sub: str) -> int:
    """Tel de ACTIEVE beheerders onder de tenant-gebruikers, exclusief `behalve_sub`.

    Rollen leven in Keycloak (niet in de DB) en `/roles/{rol}/users` is geblokkeerd voor het
    provisioning-account → tel via de toegestane per-gebruiker rol-mappings-read over de
    `gebruiker_persoon`-set. Alleen ingeschakelde beheerders tellen (een uitgeschakelde
    beheerder beschermt niet tegen lockout). Loopt alleen op het guard-pad (zelden)."""
    subs = (
        await session.execute(
            select(GebruikerPersoon.keycloak_sub).where(
                GebruikerPersoon.tenant_id == tid, GebruikerPersoon.keycloak_sub != behalve_sub
            )
        )
    ).scalars().all()
    aantal = 0
    for sub in subs:
        info = await keycloak.lees_keycloak_gebruiker(sub)
        if info and info.get("enabled") and "beheerder" in info.get("rollen", []):
            aantal += 1
    return aantal


async def reset_wachtwoord(session: AsyncSession, tenant_id, gebruiker_id) -> str:
    """Genereer een nieuw eenmalig wachtwoord (verplicht wijzigen bij eerste login) en geef het
    één keer terug. Het wachtwoord wordt NOOIT opgeslagen/gelogd; de audit legt alleen het feit vast."""
    tid = _tenant_uuid(tenant_id)
    koppel = await _haal_koppel(session, tid, gebruiker_id)
    wachtwoord = keycloak.genereer_tijdelijk_wachtwoord()
    try:
        await keycloak.reset_keycloak_wachtwoord(koppel.keycloak_sub, wachtwoord)
    except keycloak.KeycloakProvisioningFout as exc:
        raise KeycloakNietBeschikbaar(f"Wachtwoord opnieuw instellen mislukt: {exc.bericht}") from exc
    await registreer_gebruikersactie(
        session, koppel_id=koppel.id, wijziging={"wachtwoord": {"oud": None, "nieuw": "opnieuw ingesteld"}}
    )
    await session.commit()
    return wachtwoord


async def wijzig_rol(session: AsyncSession, tenant_id, gebruiker_id, nieuwe_rol: str) -> None:
    """Vervang de huidige tenant-rol door `nieuwe_rol`. Guards: niet jezelf de beheerrol
    ontnemen; niet de laatste (actieve) beheerder de-rollen."""
    tid = _tenant_uuid(tenant_id)
    koppel = await _haal_koppel(session, tid, gebruiker_id)
    info = await keycloak.lees_keycloak_gebruiker(koppel.keycloak_sub)
    huidige_rol = next((r for r in (info or {}).get("rollen", []) if r in keycloak.TENANT_ROLLEN), None)
    if nieuwe_rol == huidige_rol:
        return  # niets te doen
    if huidige_rol == "beheerder" and nieuwe_rol != "beheerder":
        if koppel.keycloak_sub == _huidige_sub():
            raise RegistratieConflict("EIGEN_BEHEERROL", "Je kunt jezelf niet de beheerrol ontnemen.")
        if await _tel_actieve_beheerders_behalve(session, tid, behalve_sub=koppel.keycloak_sub) == 0:
            raise RegistratieConflict("LAATSTE_BEHEERDER", "Dit is de laatste beheerder; wijs eerst een andere beheerder aan.")
    try:
        await keycloak.wijzig_keycloak_rol(koppel.keycloak_sub, nieuwe_rol)
    except keycloak.KeycloakProvisioningFout as exc:
        raise KeycloakNietBeschikbaar(f"Rol wijzigen mislukt: {exc.bericht}") from exc
    await registreer_gebruikersactie(
        session, koppel_id=koppel.id, wijziging={"rol": {"oud": huidige_rol, "nieuw": nieuwe_rol}}
    )
    await session.commit()


async def zet_actief(session: AsyncSession, tenant_id, gebruiker_id, actief: bool) -> None:
    """Account in-/uitschakelen (nooit verwijderen). Bij uitschakelen: guards (niet je eigen
    account, niet de laatste beheerder) + de lopende sessie direct afkappen (Keycloak-logout)."""
    tid = _tenant_uuid(tenant_id)
    koppel = await _haal_koppel(session, tid, gebruiker_id)
    if not actief:
        if koppel.keycloak_sub == _huidige_sub():
            raise RegistratieConflict("EIGEN_ACCOUNT", "Je kunt je eigen account niet uitschakelen.")
        info = await keycloak.lees_keycloak_gebruiker(koppel.keycloak_sub)
        if info and "beheerder" in info.get("rollen", []):
            if await _tel_actieve_beheerders_behalve(session, tid, behalve_sub=koppel.keycloak_sub) == 0:
                raise RegistratieConflict("LAATSTE_BEHEERDER", "Dit is de laatste beheerder; je kunt 'm niet uitschakelen.")
    try:
        await keycloak.zet_keycloak_enabled(koppel.keycloak_sub, actief)
        if not actief:
            await keycloak.logout_keycloak_gebruiker(koppel.keycloak_sub)
    except keycloak.KeycloakProvisioningFout as exc:
        raise KeycloakNietBeschikbaar(f"Account-status wijzigen mislukt: {exc.bericht}") from exc
    await registreer_gebruikersactie(
        session, koppel_id=koppel.id, wijziging={"enabled": {"oud": (not actief), "nieuw": actief}}
    )
    await session.commit()


async def corrigeer_gegevens(
    session: AsyncSession, tenant_id, gebruiker_id, *, naam: str, email: str,
    afdeling_id: uuid.UUID | None = None,
) -> GebruikerPersoonRead:
    """Corrigeer naam/e-mail (+ optioneel afdeling/organisatie) op de persoon-partij (bron van
    waarheid, ORM → auto-audit) én naam/e-mail op het Keycloak-account. Email blijft uniek binnen
    de tenant. Afdeling wijzigen (LI032): de organisatie volgt uit de afdeling, samen gevalideerd
    (`_valideer_lidmaatschap`); alles in één transactie zodat de audit één diff capture't."""
    tid = _tenant_uuid(tenant_id)
    koppel = await _haal_koppel(session, tid, gebruiker_id)
    persoon = (
        await session.execute(
            select(Partij).where(Partij.id == koppel.persoon_id, Partij.tenant_id == tid)
        )
    ).scalar_one_or_none()
    if persoon is None:
        raise NietGevonden("gebruiker", gebruiker_id)
    botst = (
        await session.execute(
            select(GebruikerPersoon.id)
            .join(Partij, Partij.id == GebruikerPersoon.persoon_id)
            .where(GebruikerPersoon.tenant_id == tid, Partij.email == email, GebruikerPersoon.id != koppel.id)
        )
    ).scalar_one_or_none()
    if botst is not None:
        raise OngeldigeRegistratie("EMAIL_AL_IN_GEBRUIK", "Er bestaat al een gebruiker met dit e-mailadres.")
    # LI032 — bewaar de oude naam/e-mail: het account (Keycloak) wordt ALLEEN aangeroepen als een
    # daarvan echt wijzigt. Een afdeling-/organisatie-only wissel is puur interne registratie en
    # raakt het account niet (geen 503, interne wijziging gaat niet verloren bij een account-storing).
    account_wijzigt = naam != persoon.naam or email != persoon.email
    persoon.naam = naam
    persoon.email = email
    # LI032 — afdeling (en daarmee organisatie) wijzigen. Alleen als er een andere afdeling komt.
    if afdeling_id is not None and afdeling_id != persoon.afdeling_id:
        afdeling = (
            await session.execute(
                select(Partij).where(Partij.id == afdeling_id, Partij.tenant_id == tid)
            )
        ).scalar_one_or_none()
        if afdeling is None or afdeling.aard != PartijAard.organisatie_eenheid:
            raise OngeldigeRegistratie("ONGELDIGE_AFDELING", "De afdeling moet een bestaande afdeling zijn.")
        nieuwe_org = afdeling.organisatie_id
        if nieuwe_org != persoon.organisatie_id:
            # Aanspreekpunt-blokkade: verplaats geen persoon die nog aanspreekpunt is van een partij
            # die hij achterlaat — dat zou een stille inconsistentie geven. Weiger met uitleg.
            blokkeerders = (
                await session.execute(
                    select(Partij.naam).where(
                        Partij.contactpersoon_id == persoon.id, Partij.tenant_id == tid
                    )
                )
            ).scalars().all()
            if blokkeerders:
                raise RegistratieConflict(
                    "AANSPREEKPUNT_BLOKKEERT_VERPLAATSING",
                    f"Deze persoon is nog aanspreekpunt van {', '.join(blokkeerders)}; "
                    "maak dat eerst los voordat je hem naar een andere organisatie verplaatst.",
                )
        # Samen gezet en tegen elkaar gevalideerd (afdeling = organisatie_eenheid binnen de organisatie).
        await partij_service._valideer_lidmaatschap(session, tid, PartijAard.persoon, nieuwe_org, afdeling_id)
        persoon.organisatie_id = nieuwe_org
        persoon.afdeling_id = afdeling_id
    # Account (Keycloak) alleen synchroniseren als naam/e-mail echt wijzigt; anders overslaan zodat
    # een afdeling-/organisatie-only wissel niet op een onnodige account-aanroep kan struikelen.
    if account_wijzigt:
        try:
            await keycloak.werk_keycloak_gegevens_bij(koppel.keycloak_sub, naam=naam, email=email)
        except keycloak.KeycloakProvisioningFout as exc:
            await session.rollback()
            raise KeycloakNietBeschikbaar(f"Gegevens corrigeren mislukt: {exc.bericht}") from exc
    await session.commit()  # partij naam/email/org/afdeling-diff → ORM-audit (entiteit_type=partij)
    await session.refresh(koppel)
    await session.refresh(persoon)
    namen = await _namen(session, tid, {persoon.organisatie_id, persoon.afdeling_id})
    return _lees(
        koppel, persoon,
        org_naam=namen.get(persoon.organisatie_id), afd_naam=namen.get(persoon.afdeling_id),
    )


async def lijst_gebruikers(
    session: AsyncSession, tenant_id, *, limit: int = _LIMIET, after: str | None = None, verrijk: bool = True,
) -> tuple[list[GebruikerPersoonRead], str | None]:
    """Gekoppelde gebruikers (join koppelrij <-> persoon), gesorteerd op naam; v2n-keyset.

    `verrijk` (default True): vul per gebruiker de huidige rol + enabled-status uit Keycloak
    (best-effort, None bij onbereikbaar). Bewust N+1 over een begrensde tenant-set —
    `/roles/{rol}/users` is geblokkeerd, dus een echte batch is niet beschikbaar."""
    tid = _tenant_uuid(tenant_id)
    limit = max(1, min(limit, _MAX_LIMIET))
    kolom = Partij.naam

    stmt = (
        select(GebruikerPersoon, Partij.naam, Partij.email, Partij.organisatie_id, Partij.afdeling_id)
        .join(Partij, Partij.id == GebruikerPersoon.persoon_id)
        .where(GebruikerPersoon.tenant_id == tid)
    )
    if after:
        c_sort, c_order, c_isnull, c_waarde, c_id = decode_sort_cursor_nullable(after)
        if c_sort != "naam" or c_order != "asc":
            raise ValueError("cursor past niet bij de sortering")
        stmt = stmt.where(
            keyset_seek_nulls_last(
                kolom, GebruikerPersoon.id, order="asc", is_null=c_isnull, waarde=c_waarde, cursor_id=c_id
            )
        )
    stmt = stmt.order_by(*keyset_order_by_nulls_last(kolom, GebruikerPersoon.id, "asc")).limit(limit + 1)

    rijen = (await session.execute(stmt)).all()
    meer = len(rijen) > limit
    rijen = rijen[:limit]
    # LI032 — batch-resolve de organisatie-/afdeling-namen (één query; geen N+1).
    namen = await _namen(session, tid, {r[3] for r in rijen} | {r[4] for r in rijen})
    items = [
        GebruikerPersoonRead(
            id=gp.id, keycloak_sub=gp.keycloak_sub, persoon_id=gp.persoon_id,
            naam=naam, email=email, aangemaakt_op=gp.aangemaakt_op,
            organisatie_id=org_id, organisatie_naam=namen.get(org_id),
            afdeling_id=afd_id, afdeling=namen.get(afd_id),
        )
        for gp, naam, email, org_id, afd_id in rijen
    ]
    if verrijk:
        for it in items:
            info = await keycloak.lees_keycloak_gebruiker(it.keycloak_sub)
            if info:
                it.enabled = info.get("enabled")
                it.rol = next((r for r in info.get("rollen", []) if r in keycloak.TENANT_ROLLEN), None)
    volgende = None
    if meer and items:
        laatste_gp, laatste_naam, *_ = rijen[-1]
        volgende = encode_sort_cursor_nullable(sort="naam", order="asc", waarde=laatste_naam, id=str(laatste_gp.id))
    return items, volgende
