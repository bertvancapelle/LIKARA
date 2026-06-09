"""Unit-tests — ADR-019 default-antwoordconfiguratie (CD025).

Toetst de pure config-bouw (DB-vrij) en de idempotente seed (DB gemockt).
"""
import asyncio
from unittest.mock import AsyncMock


def test_bouw_config_27_vragen_96_opties():
    from services.seed_antwoordconfig import bouw_antwoordconfig

    types, opties = bouw_antwoordconfig()
    assert len(types) == 27
    assert len(opties) == 96


def test_alle_codes_bestaan_in_vragenset():
    from services.seed import CHECKLIST_VRAGEN
    from services.seed_antwoordconfig import bouw_antwoordconfig

    codes = {v["code"] for v in CHECKLIST_VRAGEN}
    types, opties = bouw_antwoordconfig()
    assert set(types).issubset(codes)
    assert {o["vraag_code"] for o in opties}.issubset(codes)


def test_afgeleide_sets_volgen_de_enums():
    from models.models import HostingModel, NiveauEnum
    from services.seed_antwoordconfig import bouw_antwoordconfig

    _, opties = bouw_antwoordconfig()

    hosting = [o for o in opties if o["vraag_code"] == "2.1"]
    assert [o["optie_sleutel"] for o in hosting] == [e.value for e in HostingModel]
    assert all(o["afgeleid_bron"] == "HostingModel" for o in hosting)

    niveau = [o for o in opties if o["vraag_code"] == "12.1"]
    assert [o["optie_sleutel"] for o in niveau] == [e.value for e in NiveauEnum]
    assert all(o["afgeleid_bron"] == "NiveauEnum" for o in niveau)


def test_sleutels_uniek_per_vraag():
    from services.seed_antwoordconfig import bouw_antwoordconfig

    _, opties = bouw_antwoordconfig()
    per_vraag: dict[str, list[str]] = {}
    for o in opties:
        per_vraag.setdefault(o["vraag_code"], []).append(o["optie_sleutel"])
    for code, sleutels in per_vraag.items():
        assert len(sleutels) == len(set(sleutels)), f"dubbele optie_sleutel in {code}"


def test_getal_vraag_heeft_geen_opties():
    from models.models import AntwoordType
    from services.seed_antwoordconfig import bouw_antwoordconfig

    types, opties = bouw_antwoordconfig()
    assert types["12.4"] == AntwoordType.getal
    assert [o for o in opties if o["vraag_code"] == "12.4"] == []


def test_seed_idempotent_geeft_vaste_aantallen():
    from services.seed_antwoordconfig import seed_antwoordconfig

    session = AsyncMock()
    eerste = asyncio.run(seed_antwoordconfig(session))
    tweede = asyncio.run(seed_antwoordconfig(session))
    assert eerste == tweede == (27, 96)
    session.commit.assert_awaited()
