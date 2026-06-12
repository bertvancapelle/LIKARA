"""Tests — ADR-021 component-herfundering (CD051).

Offline metadata-asserts (model-structuur, shared-PK-subtypegrens, CHECK/UNIQUE,
FK-ondelete) + de pure seed-functie + migratie-bron. Het live RLS-/grants-/round-trip-
gedrag is in de migratie geborgd en eenmalig empirisch tegen de stack geverifieerd.
"""
import pathlib

from sqlalchemy import CheckConstraint, UniqueConstraint


def test_nieuwe_modellen_importeerbaar_en_oud_vervangen():
    from models import models as m

    for naam in ["Component", "ComponentStructuur", "ComponentContract", "ComponentConfigOptie"]:
        assert hasattr(m, naam), f"ontbrekend model: {naam}"
    assert not hasattr(m, "ApplicatieContract")  # vervangen door ComponentContract


def test_componentconfig_dimensie_enum():
    from models import models as m

    assert [e.value for e in m.ComponentConfigDimensie] == ["componenttype", "structuurrelatie_type"]


def test_tenant_tabellen_hebben_tenant_id_catalogus_niet():
    from models import models as m

    for model in (m.Component, m.ComponentStructuur, m.ComponentContract):
        assert "tenant_id" in model.__table__.columns, model.__name__
    assert "tenant_id" not in m.ComponentConfigOptie.__table__.columns
    assert m.ComponentConfigOptie.__table__.c.id.type.python_type is int


def test_check_en_unieke_constraints():
    from models import models as m

    checks = {c.name for c in m.ComponentStructuur.__table__.constraints if isinstance(c, CheckConstraint)}
    assert "ck_component_structuur_self" in checks

    def uniques(model) -> dict[str, tuple]:
        return {
            c.name: tuple(col.name for col in c.columns)
            for c in model.__table__.constraints
            if isinstance(c, UniqueConstraint)
        }

    assert uniques(m.ComponentStructuur)["uq_component_structuur"] == (
        "tenant_id", "component_id", "op_component_id", "relatietype"
    )
    assert uniques(m.ComponentContract)["uq_component_contract"] == (
        "tenant_id", "component_id", "contract_id"
    )
    assert uniques(m.ComponentConfigOptie)["uq_componentconfig_optie"] == (
        "dimensie", "optie_sleutel"
    )


def test_shared_pk_subtypegrens():
    from models import models as m

    # applicatie.id is FK→component, CASCADE (1-op-1, structureel afgedwongen).
    fk = next(iter(m.Applicatie.__table__.c.id.foreign_keys))
    assert fk.column.table.name == "component"
    assert (fk.ondelete or "").upper() == "CASCADE"
    # naam verhuisde naar component; het subtype draagt het engine-apparaat.
    assert "naam" not in m.Applicatie.__table__.columns
    assert "naam" in m.Component.__table__.columns
    # ADR-022 Fase A: lifecycle_status verhuisde naar het generieke ComponentProfiel
    # (shared-PK); op Applicatie is het nu een read-only proxy-property.
    assert "lifecycle_status" not in m.Applicatie.__table__.columns
    assert "lifecycle_status" in m.ComponentProfiel.__table__.columns
    for veld in ("migratiepad", "complexiteit", "prioriteit"):
        assert veld in m.Applicatie.__table__.columns


def test_structuur_fk_ondelete():
    from models import models as m

    od = {fk.parent.name: (fk.ondelete or "").upper() for fk in m.ComponentStructuur.__table__.foreign_keys}
    assert od["component_id"] == "CASCADE"       # afhankelijke verdwijnt mee
    assert od["op_component_id"] == "RESTRICT"   # onderlegger met afhankelijkheden beschermd


def test_seed_componentconfig_9_opties():
    from services.seed_componentconfig import bouw_componentconfig

    rijen = bouw_componentconfig()
    assert len(rijen) == 9
    typen = [r["optie_sleutel"] for r in rijen if r["dimensie"].value == "componenttype"]
    assert len(typen) == 7 and "applicatie" in typen  # systeem-sleutel aanwezig
    rels = {r["optie_sleutel"] for r in rijen if r["dimensie"].value == "structuurrelatie_type"}
    assert rels == {"draait_op", "maakt_deel_uit_van"}


def test_migratie_0006_bron():
    p = (
        pathlib.Path(__file__).resolve().parents[2]
        / "migrations" / "versions" / "0006_component_herfundering.py"
    )
    bron = p.read_text(encoding="utf-8")
    assert '"0005_contractregister"' in bron and "down_revision" in bron
    assert "component_structuur" in bron and "component_contract" in bron
    assert "ENABLE ROW LEVEL SECURITY" in bron
    assert "TRUNCATE applicatie CASCADE" in bron  # pre-prod herfundering, geen datamigratie
