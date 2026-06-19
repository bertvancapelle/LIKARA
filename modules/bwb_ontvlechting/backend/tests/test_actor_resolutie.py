"""Tests — actor-naam-resolutie helper (ADR-029 Fase 3b). Offline: vorm-normalisatie + engine-borging."""


def test_pak_sub_email_vormen():
    from services.actor_resolutie import pak_sub_email

    # Nieuwe vorm: dict {sub, email}.
    assert pak_sub_email({"sub": "kc-1", "email": "a@b.nl"}) == ("kc-1", "a@b.nl")
    # Historische vorm: kale e-mailstring → (None, email).
    assert pak_sub_email("oud@org.nl") == (None, "oud@org.nl")
    # Leeg.
    assert pak_sub_email(None) == (None, None)
    # Dict zonder sub (defensief).
    assert pak_sub_email({"email": "x@y.nl"}) == (None, "x@y.nl")


def test_actor_resolutie_raakt_engine_niet():
    import services.actor_resolutie as s

    for naam in ("lifecycle_service", "herbereken_lifecycle", "bepaal_lifecycle",
                 "ComponentProfiel", "Blokkade", "Checklistscore"):
        assert not hasattr(s, naam), f"actor_resolutie mag de engine niet importeren: {naam!r}"
