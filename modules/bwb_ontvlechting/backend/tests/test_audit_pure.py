"""ADR-006 Fase C+D — pure audit-helpers (offline, geen DB).

Dekt: derive-classificatie (Besluit 1), diff-opbouw (Besluit 7, create/delete via een
transient ORM-instance), hash-determinisme + hash-keten-verificatie/breukdetectie
(Besluit 6).
"""
import uuid

from app.core.audit import (
    AuditActie,
    _hash_velden_uit_record,
    bereken_record_hash,
    bouw_wijziging,
    classificeer_actie,
    verifieer_keten,
)


# ── Besluit 1 + v3-splitsing: derive-classificatie ───────────────────────────────

def test_classificeer_lifecycle_altijd_derive():
    # component_profiel (lifecycle) is altijd systeem-afgeleid.
    assert classificeer_actie("component_profiel", AuditActie.update) == AuditActie.derive
    assert classificeer_actie("component_profiel", AuditActie.update, True) == AuditActie.derive


def test_classificeer_blokkade_splitst_op_score_driver():
    # Mét score-driver in de transactie → derive (auto-open/heropenen/opgelost).
    assert classificeer_actie("blokkade", AuditActie.create, True) == AuditActie.derive
    assert classificeer_actie("blokkade", AuditActie.update, True) == AuditActie.derive
    # Zónder score-driver → de onderliggende actie (zelfstandige handmatige wijziging).
    assert classificeer_actie("blokkade", AuditActie.update, False) == AuditActie.update
    assert classificeer_actie("blokkade", AuditActie.update) == AuditActie.update


def test_classificeer_overige_passthrough():
    # Overige entiteiten zijn nooit derive, ook niet met een score-driver in de transactie.
    assert classificeer_actie("checklistscore", AuditActie.create, True) == AuditActie.create
    assert classificeer_actie("leverancier", AuditActie.delete) == AuditActie.delete
    assert classificeer_actie("contract", AuditActie.update, True) == AuditActie.update


# ── Besluit 7: diff = {veld: {oud, nieuw}}, alleen betekenisvolle velden ──────────

def test_bouw_wijziging_create_skipt_pk_en_timestamps():
    from models.models import Leverancier

    lev = Leverancier(tenant_id=uuid.uuid4(), naam="GemSoft B.V.", plaats="Amersfoort")
    wijz = bouw_wijziging(lev, AuditActie.create)
    assert wijz["naam"] == {"oud": None, "nieuw": "GemSoft B.V."}
    assert wijz["plaats"] == {"oud": None, "nieuw": "Amersfoort"}
    # id/tenant_id/timestamps + niet-gezette velden komen NIET in de diff.
    for verboden in ("id", "tenant_id", "created_at", "updated_at", "email"):
        assert verboden not in wijz


def test_bouw_wijziging_delete_is_snapshot_oud():
    from models.models import Leverancier

    lev = Leverancier(tenant_id=uuid.uuid4(), naam="CivData")
    wijz = bouw_wijziging(lev, AuditActie.delete)
    assert wijz["naam"] == {"oud": "CivData", "nieuw": None}


# ── Besluit 6: hash-determinisme + keten ─────────────────────────────────────────

def _velden(actor="u-1", entiteit_id="e-1", actie="create"):
    return {
        "tijdstip": "2026-06-14T10:00:00+00:00",
        "actor_sub": actor,
        "actor_email": None,
        "entiteit_type": "leverancier",
        "entiteit_id": entiteit_id,
        "actie": actie,
        "wijziging": {"naam": {"oud": None, "nieuw": "X"}},
        "correlatie_id": "c-1",
    }


def test_hash_deterministisch_en_gevoelig():
    h1 = bereken_record_hash(None, _velden())
    h2 = bereken_record_hash(None, _velden())
    assert h1 == h2 and len(h1) == 64  # sha256 hex
    # Andere vorige_hash ⇒ andere record_hash (ketenbinding).
    assert bereken_record_hash("abc", _velden()) != h1
    # Ander veld ⇒ andere hash.
    assert bereken_record_hash(None, _velden(actor="u-2")) != h1


def _maak_record(prev_hash, *, actor="u-1", entiteit_id=None, actie="create",
                 wijziging=None, correlatie_id=None, tenant_id=None):
    rec = {
        "tijdstip": "2026-06-14T10:00:00+00:00",
        "actor_sub": actor,
        "actor_email": None,
        "entiteit_type": "leverancier",
        "entiteit_id": entiteit_id or str(uuid.uuid4()),
        "actie": actie,
        "wijziging": wijziging if wijziging is not None else {"a": {"oud": None, "nieuw": 1}},
        "correlatie_id": correlatie_id or str(uuid.uuid4()),
        "vorige_hash": prev_hash,
    }
    if tenant_id is not None:
        rec["tenant_id"] = tenant_id
    rec["record_hash"] = bereken_record_hash(prev_hash, _hash_velden_uit_record(rec))
    return rec


def test_verifieer_intacte_keten():
    r0 = _maak_record(None)
    r1 = _maak_record(r0["record_hash"], actie="update")
    r2 = _maak_record(r1["record_hash"], actie="derive")
    ok, idx = verifieer_keten([r0, r1, r2])
    assert ok is True and idx is None


def test_verifieer_detecteert_inhoudsmanipulatie():
    r0 = _maak_record(None)
    r1 = _maak_record(r0["record_hash"])
    r1["actor_sub"] = "indringer"  # record_hash klopt niet meer
    ok, idx = verifieer_keten([r0, r1])
    assert ok is False and idx == 1


def test_verifieer_detecteert_verbroken_schakel():
    r0 = _maak_record(None)
    r1 = _maak_record(r0["record_hash"])
    r1["vorige_hash"] = "losgekoppeld"  # linkage breekt
    ok, idx = verifieer_keten([r0, r1])
    assert ok is False and idx == 1


def test_verifieer_keten_met_tenant_id_veld():
    tid = str(uuid.uuid4())
    r0 = _maak_record(None, tenant_id=tid)
    r1 = _maak_record(r0["record_hash"], tenant_id=tid)
    ok, idx = verifieer_keten([r0, r1])
    assert ok is True and idx is None
