"""Unit-tests — BWB-ontvlechting modellen, enums en seed (ADR-009)."""
import asyncio
from unittest.mock import AsyncMock


def test_modellen_importeerbaar():
    from models import models as m

    for naam in [
        "Applicatie", "Datatype", "Gebruikersgroep", "Koppeling",
        "ChecklistVraag", "Checklistscore", "Blokkade",
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
