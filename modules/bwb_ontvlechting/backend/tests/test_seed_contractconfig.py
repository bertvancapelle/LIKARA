"""Unit-tests — ADR-020 default-catalogus-seed (CD040).

Pure bouw (DB-vrij) + idempotente seed (DB gemockt), conform het
`seed_antwoordconfig`-precedent. Plus de `platform_init`-wiring.
"""
import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock


def test_bouw_9_opties_drie_dimensies():
    from models.models import ContractConfigDimensie
    from services.seed_contractconfig import bouw_contractconfig

    rijen = bouw_contractconfig()
    assert len(rijen) == 9

    per_dim: dict = {}
    for r in rijen:
        per_dim.setdefault(r["dimensie"], []).append(r["optie_sleutel"])
    assert set(per_dim) == set(ContractConfigDimensie)
    assert all(len(v) == 3 for v in per_dim.values())


def test_paren_uniek_per_dimensie():
    from services.seed_contractconfig import bouw_contractconfig

    rijen = bouw_contractconfig()
    paren = {(r["dimensie"], r["optie_sleutel"]) for r in rijen}
    assert len(paren) == len(rijen)  # geen dubbele (dimensie, sleutel) — UNIQUE-borg


def test_default_sleutels_per_dimensie():
    from models.models import ContractConfigDimensie as D
    from services.seed_contractconfig import bouw_contractconfig

    rijen = bouw_contractconfig()

    def sleutels(dim):
        return [r["optie_sleutel"] for r in rijen if r["dimensie"] == dim]

    assert sleutels(D.dekking) == ["licentie_aanschaf", "onderhoud_support", "hosting"]
    assert sleutels(D.kostenmodel) == ["saas_pxq", "volume", "per_inwoner"]
    assert sleutels(D.relatie_rol) == ["valt_onder", "onderhoud", "hosting"]


def test_alle_actief_en_oplopende_volgorde():
    from models.models import ContractConfigDimensie
    from services.seed_contractconfig import bouw_contractconfig

    rijen = bouw_contractconfig()
    assert all(r["actief"] is True for r in rijen)
    for dim in ContractConfigDimensie:
        volg = [r["volgorde"] for r in rijen if r["dimensie"] == dim]
        assert volg == [0, 1, 2]


def test_seed_idempotent_geeft_9():
    from services.seed_contractconfig import seed_contractconfig

    session = AsyncMock()
    eerste = asyncio.run(seed_contractconfig(session))
    tweede = asyncio.run(seed_contractconfig(session))
    assert eerste == tweede == 9
    session.commit.assert_awaited()


def test_platform_init_zaait_ook_contractconfig(monkeypatch):
    """Wiring (CD040 + ADR-022 W1): platform_init zaait op dezelfde platform-sessie
    de contractconfig-catalogus, gevolgd door de componentconfig-catalogus, in die
    volgorde. De checklistvragen + antwoordconfig zijn onder W1 tenant-data geworden
    en lopen niet meer via platform_init; platform_init retourneert nu het
    componentcatalogus-aantal (9)."""
    import app.platform_init as pi

    geroepen: list[str] = []

    async def fake_contract(session):
        geroepen.append("contractconfig")
        return 9

    async def fake_component(session):
        geroepen.append("componentconfig")
        return 9

    monkeypatch.setattr(pi, "seed_contractconfig", fake_contract)
    monkeypatch.setattr(pi, "seed_componentconfig", fake_component)

    session = AsyncMock()

    @asynccontextmanager
    async def fake_session():
        yield session

    aantal = asyncio.run(pi.platform_init(session_factory=fake_session))
    assert aantal == 9
    assert geroepen == ["contractconfig", "componentconfig"]
