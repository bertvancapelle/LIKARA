"""Tests — Fase B slice 2a (LI022): context-routes naar componenten.

Endpoint 1: `contract_service.componenten` levert ALLE aan een contract gekoppelde componenten,
incl. kale/profielloze (de regressie die `applicaties` via de ComponentProfiel-INNER-join miste).
Endpoint 2: `gebruikersgroep_service.contexten` (distinct (organisatie, afdeling)-picker, doorzoekbaar)
+ `componenten_voor_context` (nullable-veilige exacte context → component-ids).

Borging (dubbel): offline import-/bron-afwezigheid (de read-functies raken de engine niet — endpoint 1
ná de fix juist géén ComponentProfiel meer) + een live no-mutation-test (de endpoints creëren/muteren
geen component_profiel). Live-tests zijn self-contained (eigen WT-fixtures, opruimen in `finally`).
"""
import ast
import asyncio
import inspect
import textwrap
import uuid
from datetime import date

import pytest


def _code_zonder_docstring(fn) -> str:
    """De functie-bron zonder docstring (V010-les: een platte tekstscan struikelt anders over een
    docstring die een symbool ter uitleg noemt)."""
    node = ast.parse(textwrap.dedent(inspect.getsource(fn))).body[0]
    if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
        node.body = node.body[1:]
    return ast.unparse(node)

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"

_ENGINE_SYMBOLEN = (
    "lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
    "ComponentProfiel", "Blokkade", "Checklistscore",
)
_MUTATIE_VERBEN = ("session.add", ".commit(", ".flush(", "delete(")


# ── Offline engine-borging ───────────────────────────────────────────────────────

def test_gebruikersgroep_service_importeert_geen_engine():
    """De gebruiker-context-functies leven in gebruikersgroep_service — dat raakt de engine niet."""
    from services import gebruikersgroep_service as m
    for naam in _ENGINE_SYMBOLEN:
        assert not hasattr(m, naam), f"gebruikersgroep_service mag {naam} niet importeren"


def test_contract_componenten_bronscan_engine_vrij():
    """Endpoint 1 moet ná de fix juist GÉÉN ComponentProfiel/engine meer aanraken (function-bronscan;
    de module zelf importeert ComponentProfiel nog voor `applicaties`)."""
    from services import contract_service
    src = _code_zonder_docstring(contract_service.componenten)
    for naam in _ENGINE_SYMBOLEN:
        assert naam not in src, f"contract_service.componenten mag {naam} niet raken"
    for verb in _MUTATIE_VERBEN:
        assert verb not in src, f"contract_service.componenten is read-only (geen {verb})"


def test_gebruiker_context_functies_read_only_bronscan():
    """Beide gebruiker-context-functies zijn read-only (geen mutatie-verben in de bron)."""
    from services import gebruikersgroep_service as m
    for fn in (m.contexten, m.componenten_voor_context):
        src = _code_zonder_docstring(fn)
        for naam in _ENGINE_SYMBOLEN:
            assert naam not in src, f"{fn.__name__} mag {naam} niet raken"
        for verb in _MUTATIE_VERBEN:
            assert verb not in src, f"{fn.__name__} is read-only (geen {verb})"


# ── Live-integratie (lk_app) ─────────────────────────────────────────────────────

import app.core.database  # noqa: E402,F401 — registreert de tenant-context-hook
from app.core.tenant_context import reset_tenant_context, zet_tenant_context  # noqa: E402


def _db_bereikbaar() -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    async def _check():
        eng = create_async_engine(_LK_APP_URL)
        try:
            async with eng.connect() as c:
                await c.execute(text("SELECT 1"))
            return True
        finally:
            await eng.dispose()
    try:
        return asyncio.run(_check())
    except Exception:
        return False


integratie = pytest.mark.skipif(not _db_bereikbaar(), reason="lk_app-DB niet bereikbaar (offline)")


async def _sessie_run(fn):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    eng = create_async_engine(_LK_APP_URL)
    smf = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    tok = zet_tenant_context(_TID)
    try:
        async with smf() as s:
            s.sync_session.info["rls"] = True
            return await fn(s)
    finally:
        reset_tenant_context(tok)
        await eng.dispose()


async def _ruim(s, ids):
    """Opruimen via het element-supertype (cascade subtype + relaties/profiel). Geordend zodat een
    contract VÓÓR zijn leverancier verdwijnt (contract.leverancier_id is ON DELETE RESTRICT)."""
    from sqlalchemy import text
    for eid in ids:
        if eid is not None:
            await s.execute(text("DELETE FROM element WHERE id = :i"), {"i": str(eid)})
            await s.commit()


def _app_create(naam):
    from schemas.component import ComponentCreate
    return ComponentCreate(componenttype="applicatie", naam=naam, hostingmodel="saas", migratiepad="onbekend",
                            complexiteit="midden", prioriteit="midden")


@integratie
def test_contract_componenten_bevat_ook_kale_component():
    """Endpoint 1 (regressie): een contract met zowel een applicatie als een KALE (profielloze)
    component → `componenten` levert BEIDE; `applicaties` (ComponentProfiel-INNER-join) levert
    alléén de applicatie. Self-contained WT-fixtures."""
    from schemas.component import ComponentCreate
    from schemas.component_contract import ComponentContractCreate
    from schemas.contract import ContractCreate
    from schemas.partij import PartijCreate
    from models.models import PartijAard
    from services import (
        component_service, component_contract_service, contract_service, partij_service,
    )

    sfx = uuid.uuid4().hex[:8]

    async def _flow(s):
        lev_id = app_id = kaal_id = contract_id = None
        try:
            lev = await partij_service.maak_aan(s, _TID, PartijCreate(aard=PartijAard.externe_partij, naam=f"WT-S2a-Lev-{sfx}"))
            lev_id = lev.id
            app = await component_service.maak_aan(s, _TID, _app_create(f"WT-S2a-App-{sfx}"))
            app_id = app["id"]
            kaal = await component_service_maak(s, ComponentCreate(naam=f"WT-S2a-DB-{sfx}", componenttype="fileshare"))
            kaal_id = kaal["id"]
            con = await contract_service.maak_aan(s, _TID, ContractCreate(
                leverancier_id=lev_id, contracttype="los_contract", contractnaam=f"WT-S2a-Con-{sfx}",
                begindatum=date(2024, 1, 1), einddatum=date(2027, 12, 31), dekking=[], kostenmodel=[]))
            contract_id = con["id"]
            for cid in (app_id, kaal_id):
                await component_contract_service.maak_aan(
                    s, _TID, ComponentContractCreate(component_id=cid, contract_id=contract_id, relatie_rol="valt_onder"))

            comp_rows = await contract_service.componenten(s, _TID, contract_id)
            app_rows = await contract_service.applicaties(s, _TID, contract_id)
            return (
                {r["component_id"] for r in comp_rows},
                {r["applicatie_id"] for r in app_rows},
                app_id, kaal_id,
            )
        finally:
            await _ruim(s, [app_id, kaal_id, contract_id, lev_id])

    comp_ids, app_ids, app_id, kaal_id = asyncio.run(_sessie_run(_flow))
    # Endpoint 1 (nieuw): BEIDE componenten — de kale component is de regressie-asserter.
    assert {app_id, kaal_id} <= comp_ids
    # /applicaties: alléén de profiel-dragende applicatie (kale component valt weg).
    assert app_id in app_ids
    assert kaal_id not in app_ids


async def component_service_maak(s, body):
    from services import component_service as svc
    return await svc.maak_aan(s, _TID, body)


@integratie
def test_gebruiker_contexten_en_componenten():
    """Endpoint 2a/2b: distinct contexten (incl. lege-organisatie-casus) + de juiste component-ids per
    context. Self-contained: een org-context (org gezet) + een org-loze context (de "Burgers"-casus)."""
    from schemas.gebruikersgroep import GebruikersgroepCreate
    from schemas.partij import PartijCreate
    from models.models import PartijAard
    from services import component_service, gebruikersgroep_service as gg, partij_service

    sfx = uuid.uuid4().hex[:8]
    afd_org = f"WT-S2a-Afd-{sfx}"

    async def _flow(s):
        org_id = a_org = a_burg = g1 = g2 = afd_id = None
        try:
            org = await partij_service.maak_aan(s, _TID, PartijCreate(aard=PartijAard.organisatie, naam=f"WT-S2a-Org-{sfx}"))
            org_id = org.id
            # ADR-036a — afdeling = een echte organisatie_eenheid-partij binnen de organisatie.
            afd = await partij_service.maak_aan(s, _TID, PartijCreate(
                aard=PartijAard.organisatie_eenheid, naam=afd_org, organisatie_id=org_id))
            afd_id = afd.id
            a_org = (await component_service.maak_aan(s, _TID, _app_create(f"WT-S2a-AppOrg-{sfx}")))["id"]
            a_burg = (await component_service.maak_aan(s, _TID, _app_create(f"WT-S2a-AppBurg-{sfx}")))["id"]
            g1 = (await gg.maak_aan(s, _TID, GebruikersgroepCreate(
                applicatie_id=a_org, organisatie_id=org_id, afdeling_id=afd_id, aantal_gebruikers=10)))["id"]
            # Org-loze groep (burgers): geen organisatie ⇒ geen afdeling (ADR-036a).
            g2 = (await gg.maak_aan(s, _TID, GebruikersgroepCreate(
                applicatie_id=a_burg, organisatie_id=None, afdeling_id=None, aantal_gebruikers=20)))["id"]

            # 2a — zoek op de afdeling-naam → precies de org-context (distinct via de afdeling-partij).
            ctx = await gg.contexten(s, _TID, zoek=afd_org)
            mijn = {(c["organisatie_id"], c["afdeling"]): c for c in ctx}
            # 2b — componenten per context (nullable-veilig; afdeling_id-referentie).
            comp_org = await gg.componenten_voor_context(s, _TID, organisatie_id=org_id, afdeling_id=afd_id)
            comp_burg = await gg.componenten_voor_context(s, _TID, organisatie_id=None, afdeling_id=None)
            return (mijn, comp_org, comp_burg, org_id, afd_org, a_org, a_burg)
        finally:
            # RESTRICT-volgorde: groepen → afdeling → apps/organisatie.
            await _ruim(s, [g1, g2, afd_id, a_org, a_burg, org_id])

    mijn, comp_org, comp_burg, org_id, afd_org, a_org, a_burg = asyncio.run(_sessie_run(_flow))

    # 2a — de org-context is aanwezig, distinct via de afdeling-partij, met geresolveerde namen.
    assert (org_id, afd_org) in mijn
    assert mijn[(org_id, afd_org)]["aantal_componenten"] == 1
    assert mijn[(org_id, afd_org)]["organisatie_naam"] == f"WT-S2a-Org-{sfx}"
    # 2b — exact de juiste component voor de org-context; de burger-component is bereikbaar via de
    # organisatie-loze context (— / —), die met andere org-loze groepen deelt (dus 'bevat', geen '==').
    assert {r["component_id"] for r in comp_org} == {a_org}
    assert a_burg in {r["component_id"] for r in comp_burg}


@integratie
def test_endpoints_muteren_geen_component_profiel():
    """Live no-mutation: het aanroepen van de drie read-endpoints creëert/muteert geen
    component_profiel (telling vóór == ná). Gebruikt de bestaande seed-data, geen fixtures."""
    from sqlalchemy import text
    from services import contract_service, gebruikersgroep_service as gg

    async def _flow(s):
        async def _telling():
            return (await s.execute(text("SELECT count(*) FROM component_profiel"))).scalar_one()

        voor = await _telling()
        # Een bestaand contract uit de seed (eerste alfabetisch) + alle contexten aanroepen.
        con_id = (await s.execute(text("SELECT id FROM contract ORDER BY contractnaam LIMIT 1"))).scalar()
        if con_id is not None:
            await contract_service.componenten(s, _TID, con_id)
        ctx = await gg.contexten(s, _TID)
        for c in ctx[:3]:
            await gg.componenten_voor_context(s, _TID, organisatie_id=c["organisatie_id"], afdeling_id=c["afdeling_id"])
        na = await _telling()
        return voor, na, len(ctx)

    voor, na, n_ctx = asyncio.run(_sessie_run(_flow))
    assert na == voor, "read-endpoints mogen geen component_profiel aanmaken/muteren"
    assert n_ctx >= 1  # de seed levert ten minste één gebruikercontext
