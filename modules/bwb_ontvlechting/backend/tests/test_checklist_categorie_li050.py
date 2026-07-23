"""Tests — checklist-categorie als eigen entiteit (ADR-022 W3 / LI050).

Borging conform de opdracht:
1. het SCHEMA weigert twee gelijknamige categorieën binnen één componenttype
   (offline: structurele constraint-assert; live: dubbele insert → IntegrityError);
2. verwijderen met vragen eronder wordt GEWEIGERD, met het aantal in de melding;
3. een dubbele naam bij aanmaken → leesbare 409 (ConfiguratieConflict);
4. de doorklik-data: de blokkade-read levert `categorie_id` van de vraag zelf —
   de rechten-guard-test staat in `backend/tests/test_rbac.py` (vraagbeheer-app).
"""
import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

_TID = "11111111-1111-1111-1111-111111111111"
_LK_APP_URL = "postgresql+asyncpg://lk_app:changeme_dev@localhost:5432/likara"
_LK_ADMIN_URL = "postgresql+asyncpg://lk_admin:changeme_dev@localhost:5432/likara"


def _db_bereikbaar() -> bool:
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


# ── 1. Schema: uniciteit + RESTRICT — structureel (offline) ──────────────────────


def test_schema_uniciteit_en_restrict_structureel():
    from models.models import ChecklistCategorie, ChecklistVraag

    uniques = {
        tuple(c.columns.keys()): c.name
        for c in ChecklistCategorie.__table__.constraints
        if hasattr(c, "columns") and c.__class__.__name__ == "UniqueConstraint"
    }
    # Twee gelijknamige categorieën binnen één componenttype kunnen structureel niet.
    assert ("tenant_id", "componenttype", "naam") in uniques
    # Composiet-FK-target (tenant-consistentie).
    assert ("tenant_id", "id") in uniques

    fks = {
        fk.name: fk
        for fk in ChecklistVraag.__table__.constraints
        if fk.__class__.__name__ == "ForeignKeyConstraint"
    }
    fk = fks["fk_checklistvraag_categorie"]
    # RESTRICT: een categorie met vragen kan structureel niet verdwijnen.
    assert fk.ondelete == "RESTRICT"
    # De gedenormaliseerde kolommen zijn écht weg.
    assert "categorie_nr" not in ChecklistVraag.__table__.columns
    assert "categorie_naam" not in ChecklistVraag.__table__.columns
    assert "categorie_id" in ChecklistVraag.__table__.columns


# ── 2. Verwijderen met vragen eronder → 409 met telling ──────────────────────────


def _result(obj):
    r = MagicMock()
    r.scalar_one_or_none.return_value = obj
    return r


def _count(n):
    r = MagicMock()
    r.scalar_one.return_value = n
    return r


_CAT = SimpleNamespace(id=uuid.uuid4(), componenttype="applicatie", naam="Testcat", volgorde=1)


def test_verwijderen_met_vragen_geweigerd_met_telling():
    from services import checklistconfig_service as svc
    from services.errors import RegistratieConflict

    session = AsyncMock()
    session.execute.side_effect = [_result(_CAT), _count(7)]
    with pytest.raises(RegistratieConflict) as ei:
        asyncio.run(svc.verwijder_categorie(session, _CAT.id))
    assert ei.value.code == "CATEGORIE_HEEFT_VRAGEN"
    # Het aantal staat ín de melding — de gebruiker leest wat hem tegenhoudt.
    assert "7 vragen" in ei.value.bericht
    session.delete.assert_not_called()


def test_verwijderen_zonder_vragen_verwijdert_orm():
    """Lege categorie → ORM-delete (audit-dekking is ORM-dekking) + commit."""
    from services import checklistconfig_service as svc

    session = AsyncMock()
    session.execute.side_effect = [_result(_CAT), _count(0)]
    asyncio.run(svc.verwijder_categorie(session, _CAT.id))
    session.delete.assert_called_once_with(_CAT)
    session.commit.assert_awaited_once()


def test_verwijderen_enkelvoud_in_melding():
    from services import checklistconfig_service as svc
    from services.errors import RegistratieConflict

    session = AsyncMock()
    session.execute.side_effect = [_result(_CAT), _count(1)]
    with pytest.raises(RegistratieConflict) as ei:
        asyncio.run(svc.verwijder_categorie(session, _CAT.id))
    assert "1 vraag " in ei.value.bericht


# ── 3. Dubbele naam bij aanmaken → leesbare 409 ─────────────────────────────────


def test_maak_categorie_dubbele_naam_409():
    from sqlalchemy.exc import IntegrityError

    from schemas.checklistconfig import CategorieCreate
    from services import checklistconfig_service as svc
    from services.errors import ConfiguratieConflict

    session = AsyncMock()
    session.flush.side_effect = IntegrityError("uq_checklist_categorie_naam", None, Exception())

    async def _run():
        # catalogusvalidatie van het componenttype wordt hier niet geoefend (eigen tests);
        # monkeypatch-vrij: valideer via een sleutel die de catalogus-mock accepteert.
        from services import componentconfig_catalog as catalog

        origineel = catalog.valideer_sleutel

        async def _ok(*_a, **_k):
            return None

        catalog.valideer_sleutel = _ok
        try:
            await svc.maak_categorie(
                session, _TID, CategorieCreate(componenttype="applicatie", naam="Dubbel", volgorde=1)
            )
        finally:
            catalog.valideer_sleutel = origineel

    with pytest.raises(ConfiguratieConflict) as ei:
        asyncio.run(_run())
    assert "Dubbel" in ei.value.bericht


# ── 4. Live: het schema zelf weigert de dubbele naam (skip-if-offline) ──────────


@integratie
def test_schema_weigert_dubbele_naam_live():
    """Twee gelijknamige categorieën binnen één componenttype: de DB weigert met de
    benoemde constraint — óók buiten de applicatielaag om (lk_admin-insert)."""
    import asyncpg

    naam = f"WT-cat-{uuid.uuid4().hex[:8]}"

    async def _flow():
        eng = create_async_engine(_LK_ADMIN_URL)
        try:
            async with eng.begin() as c:
                await c.execute(
                    text(
                        "INSERT INTO checklist_categorie (tenant_id, componenttype, naam, volgorde) "
                        "VALUES (:t, 'applicatie', :n, 999)"
                    ),
                    {"t": _TID, "n": naam},
                )
            geweigerd = False
            try:
                async with eng.begin() as c:
                    await c.execute(
                        text(
                            "INSERT INTO checklist_categorie (tenant_id, componenttype, naam, volgorde) "
                            "VALUES (:t, 'applicatie', :n, 998)"
                        ),
                        {"t": _TID, "n": naam},
                    )
            except Exception as exc:  # IntegrityError-wrap verschilt per driver-laag
                geweigerd = True
                assert "uq_checklist_categorie_naam" in str(exc)
            assert geweigerd, "dubbele categorienaam werd NIET door het schema geweigerd"
        finally:
            async with eng.begin() as c:
                await c.execute(
                    text("DELETE FROM checklist_categorie WHERE naam = :n"), {"n": naam}
                )
            await eng.dispose()

    asyncio.run(_flow())


# ── 4b. LI050 (W4): de toegekende code botst nooit met een bestaande ────────────


def test_volgende_code_botst_niet_met_demovulling():
    """De toekenningsregel: grootste gehele getal in bestaande codes ("12.4" → 12,
    kale "13" → 13) + 1. Puur en DB-vrij; de UNIQUE-constraint blijft de backstop."""
    from services.checklistconfig_service import volgende_code

    # De demovulling-vorm: "1.1" … "12.4" → volgende is "13" (geen botsing mogelijk).
    demovulling = {f"{n}.{m}" for n in range(1, 13) for m in range(1, 5)}
    assert volgende_code(demovulling) == "13"
    # Doortellen over eerder toegekende kale codes heen.
    assert volgende_code(demovulling | {"13"}) == "14"
    # Lege set (nieuw type) → "1"; niet-numerieke restanten worden genegeerd.
    assert volgende_code(set()) == "1"
    assert volgende_code({"X9", "1.1"}) == "2"
    # De uitkomst zit nooit al in de set (bots-borging over een brede greep).
    for bestaande in (demovulling, {"1"}, {"99.9", "100"}, set()):
        assert volgende_code(bestaande) not in bestaande


# ── 5. Doorklik-data: blokkade-read draagt de categorie van de vraag zelf ───────


def test_blokkade_read_schemas_dragen_categorie_id():
    """De doorklik naar het checklist-tabblad leidt de categorie uit de blokkade-read
    af (`categorie_id`), nooit meer uit de code-prefix — beide read-schemas dragen het
    veld (de frontend-kant wordt in BlokkadeSectie.test.js bewezen mét code≠volgorde)."""
    from schemas.blokkade import BlokkadeLijstItem, BlokkadeOverzichtItem

    assert "categorie_id" in BlokkadeLijstItem.model_fields
    assert "categorie_id" in BlokkadeOverzichtItem.model_fields
