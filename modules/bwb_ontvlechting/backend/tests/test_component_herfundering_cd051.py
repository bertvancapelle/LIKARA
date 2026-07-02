"""Tests — ADR-021 component-herfundering (CD051).

Offline metadata-asserts (model-structuur, shared-PK-subtypegrens, CHECK/UNIQUE,
FK-ondelete) + de pure seed-functie + migratie-bron. Het live RLS-/grants-/round-trip-
gedrag is in de migratie geborgd en eenmalig empirisch tegen de stack geverifieerd.
"""
import pathlib

from sqlalchemy import CheckConstraint, UniqueConstraint


def test_nieuwe_modellen_importeerbaar_en_oud_vervangen():
    from models import models as m

    # ADR-023: ComponentStructuur + ComponentContract vervangen door getypeerde relaties (Relatie).
    for naam in ["Component", "Element", "Relatie", "ComponentConfigOptie"]:
        assert hasattr(m, naam), f"ontbrekend model: {naam}"
    assert not hasattr(m, "ApplicatieContract")
    assert not hasattr(m, "ComponentStructuur")   # → assignment/aggregation-relatie
    assert not hasattr(m, "ComponentContract")    # → association-relatie


def test_componentconfig_dimensie_enum():
    from models import models as m

    # ADR-023: derde dimensie `archimate_relatie` (gecureerde acht relatietypes).
    assert [e.value for e in m.ComponentConfigDimensie] == [
        "componenttype", "structuurrelatie_type", "archimate_relatie"
    ]


def test_tenant_tabellen_hebben_tenant_id_catalogus_niet():
    from models import models as m

    for model in (m.Component, m.Relatie):
        assert "tenant_id" in model.__table__.columns, model.__name__
    assert "tenant_id" not in m.ComponentConfigOptie.__table__.columns
    assert m.ComponentConfigOptie.__table__.c.id.type.python_type is int


def test_check_en_unieke_constraints():
    from models import models as m

    # ADR-023: de bron≠doel-CHECK + UNIQUE leven nu op `Relatie` (ex-ComponentStructuur).
    checks = {c.name for c in m.Relatie.__table__.constraints if isinstance(c, CheckConstraint)}
    assert "ck_relatie_bron_ne_doel" in checks

    def uniques(model) -> dict[str, tuple]:
        return {
            c.name: tuple(col.name for col in c.columns)
            for c in model.__table__.constraints
            if isinstance(c, UniqueConstraint)
        }

    # ADR-023a — `uq_relatie` is geen all-types-UniqueConstraint meer, maar een PARTIËLE unieke
    # index (WHERE relatietype <> 'flow'): flow mag meervoud, andere typen blijven uniek.
    assert "uq_relatie" not in uniques(m.Relatie)
    uq_idx = {idx.name: idx for idx in m.Relatie.__table__.indexes}["uq_relatie"]
    assert uq_idx.unique is True
    assert tuple(col.name for col in uq_idx.columns) == (
        "tenant_id", "bron_id", "doel_id", "relatietype"
    )
    assert "flow" in str(uq_idx.dialect_options["postgresql"]["where"])
    # ADR-023: ComponentContract → association-relatie (UNIQUE op `Relatie`).
    assert uniques(m.ComponentConfigOptie)["uq_componentconfig_optie"] == (
        "dimensie", "optie_sleutel"
    )


def test_component_is_enige_bron_na_li059():
    from models import models as m

    # LI059 Slice 3: het `Applicatie`-subtype-model bestaat niet meer — een component met
    # componenttype='applicatie' ÍS de applicatie (domeinmodel §9-7).
    assert not hasattr(m, "Applicatie")
    # Identiteit + transitie-attributen leven op het basis-component (LI057).
    for veld in ("naam", "migratiepad", "complexiteit", "prioriteit"):
        assert veld in m.Component.__table__.columns
    # ADR-022 Fase A: de engine-state (lifecycle_status) leeft op het generieke ComponentProfiel
    # (shared-PK: id = PK én FK→component, CASCADE).
    assert "lifecycle_status" in m.ComponentProfiel.__table__.columns
    fk = next(iter(m.ComponentProfiel.__table__.c.id.foreign_keys))
    assert fk.column.table.name == "component"
    assert (fk.ondelete or "").upper() == "CASCADE"


def test_relatie_endpoint_fk_ondelete():
    from models import models as m

    # ADR-023: relatie-endpoints zijn composiet-FK's (tenant+id) → element, CASCADE
    # (Besluit 12/13: een element verwijderen ruimt zijn relaties op).
    od = {fk.parent.name: (fk.ondelete or "").upper() for fk in m.Relatie.__table__.foreign_keys}
    assert od["bron_id"] == "CASCADE"
    assert od["doel_id"] == "CASCADE"


def test_seed_componentconfig_17_opties():
    from services.seed_componentconfig import bouw_componentconfig

    rijen = bouw_componentconfig()
    # ADR-023 + LI060: 8 componenttypen + 2 structuurrelaties + 8 ArchiMate-relatietypes.
    assert len(rijen) == 18
    typen = [r["optie_sleutel"] for r in rijen if r["dimensie"].value == "componenttype"]
    assert len(typen) == 8 and "applicatie" in typen  # systeem-sleutel aanwezig
    rels = {r["optie_sleutel"] for r in rijen if r["dimensie"].value == "structuurrelatie_type"}
    assert rels == {"draait_op", "maakt_deel_uit_van"}
    archi = {r["optie_sleutel"] for r in rijen if r["dimensie"].value == "archimate_relatie"}
    assert archi == {
        "composition", "aggregation", "serving", "assignment", "flow", "realization",
        "association", "access",
    }
    # OK-1/3: elk componenttype draagt zijn ArchiMate-mapping.
    for r in rijen:
        if r["dimensie"].value == "componenttype":
            assert r["archimate_element"] and r["laag"] and r["aspect"]


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
