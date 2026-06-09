"""Unit-tests — BWB-ontvlechting modellen, enums en seed (ADR-009)."""
import asyncio
import pathlib
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock


def test_modellen_importeerbaar():
    from models import models as m

    for naam in [
        "Applicatie", "Datatype", "Gebruikersgroep", "Koppeling",
        "ChecklistVraag", "ChecklistVraagOptie", "Checklistscore", "Blokkade",
    ]:
        assert hasattr(m, naam), f"ontbrekend model: {naam}"


def test_enum_waarden():
    from models import models as m

    assert [e.value for e in m.HostingModel] == [
        "on_premise", "private_cloud", "saas", "iaas", "paas", "hybride", "onbekend"
    ]
    assert [e.value for e in m.LifecycleStatus] == [
        "concept", "in_inventarisatie", "checklist_compleet", "geblokkeerd", "migratieklaar"
    ]
    assert [e.value for e in m.NiveauEnum] == ["laag", "midden", "hoog"]
    assert [e.value for e in m.Migratiepad] == [
        "lift_and_shift", "herbouw", "vervangen", "uitfaseren", "tijdelijk_gedeeld", "onbekend"
    ]
    assert [e.value for e in m.DatatypeCategorie] == [
        "gestructureerd_db", "documenten", "email", "spatial", "binair", "combinatie"
    ]
    assert [e.value for e in m.Koppelrichting] == ["eenrichting", "tweerichting"]
    assert [e.value for e in m.Koppelprotocol] == [
        "api", "bestandsuitwisseling", "database_link", "middleware", "overig"
    ]
    assert [e.value for e in m.ImpactVerbreking] == ["laag", "midden", "hoog", "kritiek"]
    assert [e.value for e in m.ChecklistScore] == ["ja", "deels", "nee", "nvt"]
    assert [e.value for e in m.BlokkadeStatus] == ["open", "in_behandeling", "opgelost"]
    assert [e.value for e in m.ChecklistPrioriteit] == ["hoog", "midden", "laag"]
    assert [e.value for e in m.AntwoordType] == [
        "geen", "enkelvoudige_keuze", "meerkeuze", "getal"
    ]


def test_seed_codes_uniek_en_89():
    from services.seed import CHECKLIST_VRAGEN

    codes = [v["code"] for v in CHECKLIST_VRAGEN]
    assert len(codes) == 89
    assert len(set(codes)) == 89


def test_seed_geeft_89_terug():
    from services.seed import seed_checklist_vragen

    session = AsyncMock()
    aantal = asyncio.run(seed_checklist_vragen(session))
    assert aantal == 89
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()


def test_seed_idempotent():
    """Dubbele uitvoering mag geen fout geven (ON CONFLICT DO NOTHING)."""
    from services.seed import seed_checklist_vragen

    session = AsyncMock()
    eerste = asyncio.run(seed_checklist_vragen(session))
    tweede = asyncio.run(seed_checklist_vragen(session))
    assert eerste == tweede == 89


def test_platform_init_zaait_beide_seeds_via_platform_session(monkeypatch):
    """platform_init zaait op de geïnjecteerde platform-sessie (géén RLS-/tenant-
    context) BEIDE referentiesets: de 89 checklistvragen én de ADR-019-
    antwoordconfiguratie, in die volgorde. Retourneert het vragen-aantal (89)."""
    import app.platform_init as pi

    volgorde = []

    async def fake_vragen(session):
        volgorde.append("vragen")
        return 89

    async def fake_config(session):
        volgorde.append("config")
        return (27, 96)

    monkeypatch.setattr(pi, "seed_checklist_vragen", fake_vragen)
    monkeypatch.setattr(pi, "seed_antwoordconfig", fake_config)

    session = AsyncMock()

    @asynccontextmanager
    async def fake_platform_session():
        yield session

    aantal = asyncio.run(pi.platform_init(session_factory=fake_platform_session))
    assert aantal == 89
    assert volgorde == ["vragen", "config"]  # beide gezaaid, vragen eerst


def test_seed_niet_via_tenant_pad():
    """Regressie tegen terugval naar tenant-seed: de ChecklistVraag-seed loopt
    uitsluitend via platform-init (`get_platform_db_session`), nooit via een
    tenant-/RLS-sessie (`get_session`).

    Via AST geverifieerd op code-referenties — docstrings/comments tellen niet
    mee, zodat de toelichting `get_session(tenant_id)` in de bron toegestaan is.
    """
    import ast

    root = pathlib.Path(__file__).resolve().parents[4]
    bron = (root / "backend" / "app" / "platform_init.py").read_text(encoding="utf-8")
    namen = {
        n.id for n in ast.walk(ast.parse(bron)) if isinstance(n, ast.Name)
    }
    assert "seed_checklist_vragen" in namen
    assert "get_platform_db_session" in namen
    assert "get_session" not in namen  # tenant-/RLS-sessie wordt niet gebruikt
