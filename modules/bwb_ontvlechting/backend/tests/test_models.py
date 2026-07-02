"""Unit-tests — BWB-ontvlechting modellen, enums en seed (ADR-009)."""
import asyncio
import pathlib
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock


def test_modellen_importeerbaar():
    from models import models as m

    for naam in [
        # ADR-023: Koppeling vervangen door het `Relatie`-model (flow).
        # LI059 Slice 3: het `Applicatie`-subtype-model is opgeheven (component ÍS de applicatie).
        "Component", "Datatype", "Gebruikersgroep", "Element", "Relatie",
        "ChecklistVraag", "ChecklistVraagOptie", "Checklistscore", "Blokkade",
    ]:
        assert hasattr(m, naam), f"ontbrekend model: {naam}"
    # LI059 Slice 3: er bestaat geen `Applicatie`-model meer.
    assert not hasattr(m, "Applicatie")


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
        "lift_and_shift", "herbouw", "vervangen", "uitfaseren", "gedeeld", "onbekend"
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
    # ADR-022 W1: seed_checklist_vragen is tenant-scoped — tenant_id is verplicht.
    import uuid

    from services.seed import seed_checklist_vragen

    session = AsyncMock()
    aantal = asyncio.run(seed_checklist_vragen(session, uuid.uuid4()))
    assert aantal == 95  # LI058 — 89 applicatie + 6 database
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()


def test_seed_idempotent():
    """Dubbele uitvoering mag geen fout geven (ON CONFLICT DO NOTHING)."""
    # ADR-022 W1: seed_checklist_vragen is tenant-scoped — tenant_id is verplicht.
    import uuid

    from services.seed import seed_checklist_vragen

    tid = uuid.uuid4()
    session = AsyncMock()
    eerste = asyncio.run(seed_checklist_vragen(session, tid))
    tweede = asyncio.run(seed_checklist_vragen(session, tid))
    assert eerste == tweede == 95  # LI058 — 89 applicatie + 6 database


def test_platform_init_zaait_platform_catalogi_via_platform_session(monkeypatch):
    """ADR-022 W1: platform_init zaait op de geïnjecteerde platform-sessie (géén
    RLS-/tenant-context) UITSLUITEND de platform-catalogi — de contractconfig
    (ADR-020) en de componentconfig (ADR-021/012), in die volgorde. De
    checklistvragen + antwoordconfiguratie zijn tenant-data geworden en worden
    NIET meer platform-breed gezaaid. Retourneert het componentcatalogus-aantal (9)."""
    import app.platform_init as pi

    volgorde = []

    async def fake_contract(session):
        volgorde.append("contractconfig")
        return 9

    async def fake_component(session):
        volgorde.append("componentconfig")
        return 9

    monkeypatch.setattr(pi, "seed_contractconfig", fake_contract)
    monkeypatch.setattr(pi, "seed_componentconfig", fake_component)
    # checklistvragen mogen NIET via platform_init lopen onder W1.
    assert not hasattr(pi, "seed_checklist_vragen")

    session = AsyncMock()

    @asynccontextmanager
    async def fake_platform_session():
        yield session

    aantal = asyncio.run(pi.platform_init(session_factory=fake_platform_session))
    assert aantal == 9
    assert volgorde == ["contractconfig", "componentconfig"]


def test_checklistseed_niet_via_platform_init():
    """ADR-022 W1: de checklist-baseline is tenant-data — `seed_checklist_vragen`
    wordt per tenant aangeroepen (`seed_checklist_vragen(session, tenant_id)`) en
    loopt NIET meer via platform_init. Regressie: platform_init refereert geen
    `seed_checklist_vragen`/`seed_antwoordconfig` meer, alleen de platform-catalogi.

    Via AST geverifieerd op code-referenties — docstrings/comments tellen niet mee,
    zodat de W1-toelichting in de bron toegestaan is.
    """
    import ast

    root = pathlib.Path(__file__).resolve().parents[4]
    bron = (root / "backend" / "app" / "platform_init.py").read_text(encoding="utf-8")
    namen = {
        n.id for n in ast.walk(ast.parse(bron)) if isinstance(n, ast.Name)
    }
    assert "seed_contractconfig" in namen
    assert "seed_componentconfig" in namen
    # tenant-data-seeds lopen niet meer via platform_init
    assert "seed_checklist_vragen" not in namen
    assert "seed_antwoordconfig" not in namen
