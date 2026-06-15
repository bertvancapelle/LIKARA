"""ADR-023 Fase B-mig-1 — datatype/gebruikersgroep/contract als element-subtypes (offline)."""


def test_subtypes_hebben_composiet_fk_naar_element():
    from models.models import Contract, Datatype, Gebruikersgroep

    for model in (Datatype, Gebruikersgroep, Contract):
        fks = [
            sorted(c.name for c in con.columns)
            for con in model.__table__.constraints
            if con.__class__.__name__ == "ForeignKeyConstraint"
        ]
        assert ["id", "tenant_id"] in fks, model.__name__


def test_element_type_dekt_de_subtypes():
    from models.models import ElementType

    waarden = {e.value for e in ElementType}
    assert {"component", "datatype", "gebruikersgroep", "contract"} <= waarden
