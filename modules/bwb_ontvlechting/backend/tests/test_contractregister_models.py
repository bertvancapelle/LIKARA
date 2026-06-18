"""Unit-tests — ADR-020 datamodel (CD040).

Offline metadata-asserts conform de offline-grens (complidata-tests): constraints,
FK-ondelete, RLS-`tenant_id`-kolom en enums op modelniveau. Het live RLS-/grants-/
round-trip-gedrag wordt structureel in de migratie geborgd (zie
`test_contractregister_migratie`) + eenmalig empirisch tegen de draaiende stack
(V003-precedent) — niet in deze offline suite.
"""
from sqlalchemy import CheckConstraint, UniqueConstraint


def test_nieuwe_modellen_importeerbaar():
    from models import models as m

    for naam in [
        # ADR-024 slice 1: Leverancier vervangen door element-backed Partij + PartijsoortOptie.
        "Partij", "PartijsoortOptie", "Contract", "ContractDekking",
        "ContractKostenmodel", "ContractConfigOptie",
    ]:
        assert hasattr(m, naam), f"ontbrekend model: {naam}"
    # ADR-023: ComponentContract → association-relatie (Relatie).
    assert not hasattr(m, "ComponentContract")


def test_nieuwe_enum_waarden():
    from models import models as m

    assert [e.value for e in m.ContractType] == [
        "mantelcontract", "deelcontract", "los_contract"
    ]
    # ADR-023 consistentie-opruim: relatie_rol verhuisd naar de relatie-kenmerk-catalogus.
    assert [e.value for e in m.ContractConfigDimensie] == ["dekking", "kostenmodel"]
    assert [e.value for e in m.RelatieKenmerkDimensie] == ["dispositie", "relatie_rol"]


def test_tenant_tabellen_hebben_tenant_id():
    from models import models as m

    for model in (m.Partij, m.Contract, m.ContractDekking, m.ContractKostenmodel):
        assert "tenant_id" in model.__table__.columns, f"{model.__name__} mist tenant_id"


def test_catalogus_is_platform_referentiedata():
    """Catalogus: GEEN tenant_id (geen RLS), int-PK — net als checklistvraag(_optie)."""
    from models import models as m

    assert "tenant_id" not in m.ContractConfigOptie.__table__.columns
    assert m.ContractConfigOptie.__table__.c.id.type.python_type is int


def test_contract_check_constraint_aanwezig():
    from models import models as m

    namen = {
        c.name for c in m.Contract.__table__.constraints
        if isinstance(c, CheckConstraint)
    }
    assert "ck_contract_mantel_consistentie" in namen


def test_unieke_constraints():
    from models import models as m

    def uniques(model) -> dict[str, tuple]:
        return {
            c.name: tuple(col.name for col in c.columns)
            for c in model.__table__.constraints
            if isinstance(c, UniqueConstraint)
        }

    assert uniques(m.ContractDekking)["uq_contract_dekking"] == (
        "tenant_id", "contract_id", "optie_sleutel"
    )
    assert uniques(m.ContractKostenmodel)["uq_contract_kostenmodel"] == (
        "tenant_id", "contract_id", "optie_sleutel"
    )
    assert uniques(m.ContractConfigOptie)["uq_contractconfig_optie"] == (
        "dimensie", "optie_sleutel"
    )


def test_fk_ondelete_gedrag():
    from models import models as m

    def ondeletes(model) -> dict[str, str]:
        return {
            fk.parent.name: (fk.ondelete or "").upper()
            for fk in model.__table__.foreign_keys
        }

    contract = ondeletes(m.Contract)
    assert contract["leverancier_id"] == "RESTRICT"     # leverancier met contracten beschermd
    assert contract["mantelcontract_id"] == "RESTRICT"  # mantel met deelcontracten beschermd

    assert ondeletes(m.ContractDekking)["contract_id"] == "CASCADE"
    assert ondeletes(m.ContractKostenmodel)["contract_id"] == "CASCADE"


def test_verplichte_velden_not_null():
    from models import models as m

    assert m.Partij.__table__.c.naam.nullable is False
    assert m.Contract.__table__.c.contractnaam.nullable is False
    assert m.Contract.__table__.c.contracttype.nullable is False
    assert m.Contract.__table__.c.leverancier_id.nullable is False
    assert m.Contract.__table__.c.mantelcontract_id.nullable is True
    # Datums vrij (B4: geen validatie/NOT NULL).
    for col in ("begindatum", "einddatum", "vernieuwingsdatum"):
        assert m.Contract.__table__.c[col].nullable is True
