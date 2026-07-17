"""ADR-006 — audit-trail: capture-hook + hash-keten (append-only wijzigingsspoor).

Eén centrale SQLAlchemy `before_flush`/`after_flush`-event op de gedeelde `Session`
(naast de `after_begin`-tenant-hook in `app.core.database`) vertaalt
`session.new/dirty/deleted` naar auditrecords (Besluit 2). Geen per-service-aanpassing.

- **Actor + correlatie** komen uit de request-scoped ContextVar (`app.core.tenant_context`,
  Besluit 3). Driver + afgeleide gevolgen delen één `correlatie_id`.
- **Routering** (Besluit 4): een RLS-sessie (`session.info['rls']`) → `audit_log`
  (tenant-scoped, `entiteit_id` uuid); elke andere sessie → `platform_audit_log`
  (`entiteit_id` als string).
- **`derive`** (Besluit 1): mutaties op de systeem-afgeleide entiteiten `component_profiel`
  (lifecycle) en `blokkade` krijgen actie `derive`; al het overige create/update/delete.
- **Hash-keten** (Besluit 6): `record_hash = sha256(vorige_hash ‖ betekenisdragende velden)`,
  keten per tenant (`audit_log`) resp. één keten (`platform_audit_log`). De keten is
  *detecterend* (verifieer_keten), niet *voorkomend* — conform Besluit 6.
- **Onwijzigbaarheid**: de tabellen zelf zitten NOOIT in de capture (geen ORM-flush; via
  core-INSERT) en worden niet geauditeerd.

Pure helpers (`bouw_wijziging`, `bereken_record_hash`, `verifieer_keten`, classificatie)
zijn DB-vrij en offline getest; de event-wrappers doen alleen I/O.
"""
import hashlib
import json
import uuid
from datetime import date, datetime, timezone
from enum import Enum

import sqlalchemy as sa
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from app.core.tenant_context import (
    huidige_actor,
    huidige_correlatie_id,
    huidige_tenant_id,
)


class AuditActie(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"
    derive = "derive"


# Gedeeld sa.Enum-typeobject (de migratie beheert de DDL: `auditactie_enum`).
auditactie_enum = sa.Enum(AuditActie, name="auditactie_enum")

# ── Welke entiteiten zijn compliance-relevant? (ADR-006 §2 mutatie-oppervlakken) ──
# Eén centrale bron. Tenant-entiteiten → audit_log; platform-entiteiten →
# platform_audit_log. De audit-tabellen zelf staan hier NIET in (worden via core-INSERT
# geschreven, nooit via ORM-flush) → ze auditeren zichzelf niet.
AUDIT_TENANT_ENTITEITEN: frozenset[str] = frozenset({
    # LI059 facade-purge: `applicatie` verwijderd — de subtabel is weg (0047) en applicatie-
    # componenten worden als `component` geauditeerd.
    "element", "component", "component_profiel", "datatype",
    "gebruikersgroep", "relatie", "checklistscore", "blokkade", "checklistvraag",
    "checklistvraag_optie", "partij", "contract", "contract_dekking",
    "contract_kostenmodel",
    # ADR-030 — per-band contractdekking (audit-gat gedicht in LI035: mutaties op de
    # band-dekking landden niet in de trail terwijl de contract-brede tags dat wél deden).
    "contract_band_dekking",
    # ADR-024 slice 2b — rol-toewijzing (partij vervult rol op component/contract).
    "roltoewijzing",
    # ADR-036 — grof gebruiksfeit (organisatie gebruikt applicatie).
    "organisatiegebruik",
    # ADR-023 Fase E — migratielaag. Het plateau-/gap-lidmaatschap loopt via `relatie`
    # (aggregation/association) → al gedekt door het bestaande relatie-spoor.
    "plateau", "work_package", "deliverable", "gap",
    # ADR-042 — procesregister (nestbare procesboom) + koppelregel component→proces.
    "proces", "procesvervulling",
    # ADR-049 gate 2a — koppelregel component→bedrijfsfunctie (kaal; grof/fijn per plek).
    "functievervulling",
    # ADR-043 gate 1a — bedrijfsfunctie-as + ingelezen referentiemodel-instantie.
    "bedrijfsfunctie", "referentiemodel",
    # ADR-027 — niet-scorende component-klaarverklaring (klaar→open→klaar mét reden,
    # per-veld-diffs in de append-only audit-trail; geen aparte historie-tabel).
    "component_klaarverklaring",
    # ADR-052 slice 1 — tenant-norm harde feiten (governance-config; per-feit verplicht-vlag).
    "component_norm",
    # ADR-029 — koppeling Keycloak-login ↔ persoon-partij (registratiefeit bij gebruiker-aanmaak).
    "gebruiker_persoon",
    # ADR-033 slice 2 — opgeslagen Impact-verkenner-views; ook de junctie, zodat selectie-
    # wijzigingen (component toevoegen/verwijderen) naspeurbaar zijn.
    "impact_view", "impact_view_component",
})
AUDIT_PLATFORM_ENTITEITEN: frozenset[str] = frozenset({
    "tenant", "componentconfig_optie", "contractconfig_optie",
    # ADR-023 Fase E — relatie-kenmerk-vocabulaire-catalogus (platform-breed beheer).
    "relatiekenmerk_optie",
    # ADR-028 — componentclassificatie-catalogi (platform-breed beheer).
    "componentrol_optie", "biv_schaal_optie",
    # ADR-042 — applicatiefunctie-catalogus (platform-breed beheer).
    "applicatiefunctie_optie",
    # ADR-043 — referentiemodel-aanbod (platform-gecureerd).
    "referentiemodel_optie",
})

# Altijd systeem-afgeleid (Besluit 1): lifecycle leeft alleen als afgeleide → `derive`.
_ALTIJD_DERIVE: frozenset[str] = frozenset({"component_profiel"})

# Score-driver-vlag (transactie-scoped, op `session.info`): blokkade-classificatie (v3)
# splitst op herkomst — een blokkade-mutatie samen met een score-driver in dezelfde
# transactie is `derive` (auto-open/heropenen/opgelost, ADR-016); een zelfstandige
# handmatige blokkade-wijziging (open↔in_behandeling) zónder score-driver is `update`.
_SCORE_DRIVER_FLAG = "_lk_audit_score_driver"
_PENDING_KEY = "_lk_audit_pending"

_ACTOR_ONBEKEND = "system:onbekend"


# ── Pure helpers (DB-vrij, offline testbaar) ─────────────────────────────────────

def _json_safe(waarde):
    """Maak een kolomwaarde JSON-serialiseerbaar en deterministisch."""
    if waarde is None or isinstance(waarde, (str, int, float, bool)):
        return waarde
    if isinstance(waarde, Enum):
        return waarde.value
    if isinstance(waarde, (uuid.UUID,)):
        return str(waarde)
    if isinstance(waarde, (datetime, date)):
        return waarde.isoformat()
    if isinstance(waarde, dict):
        return {k: _json_safe(v) for k, v in waarde.items()}
    if isinstance(waarde, (list, tuple)):
        return [_json_safe(v) for v in waarde]
    return str(waarde)


def classificeer_actie(
    tablename: str, basis_actie: AuditActie, score_driver_aanwezig: bool = False
) -> AuditActie:
    """Classificeer de actie (Besluit 1 + v3-splitsing). Pure functie.

    - `component_profiel` (lifecycle): altijd `derive` (bestaat alleen als afgeleide);
    - `blokkade`: `derive` mét een score-driver in dezelfde transactie (systeem-afgeleid:
      auto-open/heropenen/opgelost), anders de onderliggende create/update/delete
      (zelfstandige handmatige wijziging — een directe mensehandeling);
    - overige entiteiten: de onderliggende create/update/delete.
    """
    if tablename in _ALTIJD_DERIVE:
        return AuditActie.derive
    if tablename == "blokkade":
        return AuditActie.derive if score_driver_aanwezig else basis_actie
    return basis_actie


def bouw_wijziging(obj, basis_actie: AuditActie) -> dict:
    """`{veld: {oud, nieuw}}` — alleen betekenisvol veranderde velden (Besluit 7).

    - create: nieuwe (niet-None) waarden, `oud=None`; PK/timestamps overgeslagen;
    - update/derive: uitsluitend gewijzigde velden, uit `attrs[*].history`;
    - delete: snapshot van de niet-None waarden, `nieuw=None`.

    MOET in `before_flush` worden aangeroepen (de attribuut-history is daarna leeg).
    """
    state = sa.inspect(obj)
    wijziging: dict = {}
    for attr in state.mapper.column_attrs:
        key = attr.key
        if key in ("id", "tenant_id", "created_at", "updated_at"):
            continue  # surrogaat-PK/tenant-anker/timestamps = geen inhoudelijke wijziging
        if basis_actie == AuditActie.create:
            val = getattr(obj, key)
            if val is not None:
                wijziging[key] = {"oud": None, "nieuw": _json_safe(val)}
        elif basis_actie == AuditActie.delete:
            val = getattr(obj, key)
            if val is not None:
                wijziging[key] = {"oud": _json_safe(val), "nieuw": None}
        else:  # update
            hist = state.attrs[key].history
            if hist.has_changes():
                oud = hist.deleted[0] if hist.deleted else None
                nieuw = hist.added[0] if hist.added else None
                wijziging[key] = {"oud": _json_safe(oud), "nieuw": _json_safe(nieuw)}
    return wijziging


def _canon(velden: dict) -> str:
    """Deterministische canonieke serialisatie van de betekenisdragende velden."""
    return json.dumps(velden, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def bereken_record_hash(vorige_hash: str | None, velden: dict) -> str:
    """`record_hash = sha256(vorige_hash ‖ canon(betekenisdragende velden))` (Besluit 6).

    `velden` bevat exact de gehashte velden (zonder `id`/`record_hash`): tijdstip,
    actor_sub, actor_email, entiteit_type, entiteit_id, actie, wijziging, correlatie_id
    en — voor `audit_log` — tenant_id. SHA-256 (NCSC); hex-digest.
    """
    payload = (vorige_hash or "") + "|" + _canon(velden)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verifieer_keten(records: list[dict]) -> tuple[bool, int | None]:
    """Valideer een chronologisch geordende keten (Besluit 6).

    Per record: (a) `record_hash` herberekend uit de velden + `vorige_hash` klopt;
    (b) `vorige_hash` == `record_hash` van de voorganger (eerste: None). Retourneert
    `(True, None)` bij een intacte keten, anders `(False, index_van_breuk)`.

    Elk record is een dict met minimaal de gehashte velden + `record_hash`/`vorige_hash`
    (de lees-API levert deze 1-op-1 uit de kolommen).
    """
    vorige_record_hash: str | None = None
    for i, rec in enumerate(records):
        if rec.get("vorige_hash") != vorige_record_hash:
            return False, i
        velden = _hash_velden_uit_record(rec)
        verwacht = bereken_record_hash(rec.get("vorige_hash"), velden)
        if verwacht != rec.get("record_hash"):
            return False, i
        vorige_record_hash = rec.get("record_hash")
    return True, None


def _hash_velden_uit_record(rec: dict) -> dict:
    """Extraheer de gehashte velden uit een opgeslagen record (insert én verify
    gebruiken exact dezelfde sleutelset/serialisatie)."""
    velden = {
        "tijdstip": _json_safe(rec["tijdstip"]),
        "actor_sub": rec["actor_sub"],
        "actor_email": rec.get("actor_email"),
        "entiteit_type": rec["entiteit_type"],
        "entiteit_id": _json_safe(rec["entiteit_id"]),
        "actie": _json_safe(rec["actie"]),
        "wijziging": rec.get("wijziging"),
        "correlatie_id": _json_safe(rec["correlatie_id"]),
    }
    if "tenant_id" in rec and rec["tenant_id"] is not None:
        velden["tenant_id"] = _json_safe(rec["tenant_id"])
    return velden


# ── Capture-hook (event-wrappers, I/O) ───────────────────────────────────────────

def _basis_actie(obj, soort: str) -> AuditActie:
    if soort == "new":
        return AuditActie.create
    if soort == "deleted":
        return AuditActie.delete
    return AuditActie.update


@event.listens_for(Session, "before_flush")
def _lk_audit_before_flush(session, flush_context, instances):
    """Vang de mutaties + bouw de diffs zolang de attribuut-history nog leeft.

    Stash een lijst pending-entries op `session.info`; `after_flush` finaliseert
    (entiteit_id van net-aangemaakte rijen is dan pas bekend) en schrijft weg.
    """
    pending = []

    # v3: onthoud transactie-breed of er een score-driver in deze transactie zit
    # (de score wordt vóór de afgeleide blokkade geflusht; de vlag overleeft de
    # tussenliggende flushes en wordt bij commit/rollback gereset).
    gewijzigd = (
        list(session.new)
        + list(session.deleted)
        + [o for o in session.dirty if session.is_modified(o, include_collections=False)]
    )
    if any(getattr(o, "__tablename__", None) == "checklistscore" for o in gewijzigd):
        session.info[_SCORE_DRIVER_FLAG] = True
    score_driver = bool(session.info.get(_SCORE_DRIVER_FLAG))

    def _verwerk(obj, soort):
        tablename = getattr(obj, "__tablename__", None)
        if tablename is None:
            return
        is_tenant = tablename in AUDIT_TENANT_ENTITEITEN
        is_platform = tablename in AUDIT_PLATFORM_ENTITEITEN
        if not (is_tenant or is_platform):
            return
        basis = _basis_actie(obj, soort)
        actie = classificeer_actie(tablename, basis, score_driver)
        wijziging = bouw_wijziging(obj, basis)
        if basis == AuditActie.update and not wijziging:
            return  # geen inhoudelijke wijziging (bv. alleen timestamp) → niet loggen
        # entiteit_id: bij delete/update nu vastleggen (na flush is het object weg/expired);
        # bij create pas in after_flush (server-default-PK wordt dan toegekend).
        captured_id = None if basis == AuditActie.create else getattr(obj, "id", None)
        pending.append({
            "obj": obj,
            "tablename": tablename,
            "is_tenant": is_tenant,
            "actie": actie,
            "wijziging": wijziging,
            "captured_id": captured_id,
        })

    for obj in session.new:
        _verwerk(obj, "new")
    for obj in session.deleted:
        _verwerk(obj, "deleted")
    for obj in session.dirty:
        if session.is_modified(obj, include_collections=False):
            _verwerk(obj, "dirty")

    if pending:
        session.info.setdefault(_PENDING_KEY, []).extend(pending)


@event.listens_for(Session, "after_flush")
def _lk_audit_after_flush(session, flush_context):
    """Schrijf de in `before_flush` verzamelde auditrecords weg via core-INSERT
    (geen ORM-flush ⇒ geen recursie). Hash-keten per doel-tabel."""
    pending = session.info.pop(_PENDING_KEY, None)
    if not pending:
        return

    actor_sub, actor_email = huidige_actor()
    actor_sub = actor_sub or _ACTOR_ONBEKEND
    correlatie_id = huidige_correlatie_id() or str(uuid.uuid4())
    tenant_id = huidige_tenant_id()
    conn = session.connection()

    # Verzamel per doel-tabel zodat we de keten-staart één keer per tabel ophalen.
    tenant_entries = [p for p in pending if p["is_tenant"]]
    platform_entries = [p for p in pending if not p["is_tenant"]]

    if tenant_entries:
        _schrijf_keten(
            conn, tabel="audit_log", entries=tenant_entries, tenant_id=tenant_id,
            actor_sub=actor_sub, actor_email=actor_email, correlatie_id=correlatie_id,
            entiteit_id_is_uuid=True,
        )
    if platform_entries:
        _schrijf_keten(
            conn, tabel="platform_audit_log", entries=platform_entries, tenant_id=None,
            actor_sub=actor_sub, actor_email=actor_email, correlatie_id=correlatie_id,
            entiteit_id_is_uuid=False,
        )


def schrijf_expliciet_record(conn, *, tenant_id, actor_sub, actor_email, correlatie_id,
                             entiteit_type, entiteit_id, wijziging, actie=AuditActie.update):
    """Schrijf ÉÉN expliciet tenant-auditrecord (sync Core-connection) voor een mutatie die
    NIET via een ORM-flush loopt — bv. een Keycloak-only gebruikersbeheer-actie. Hergebruikt
    de keten-lock/staart/insert, zodat het record byte-identiek in de hash-keten landt en de
    lees-/verify-API het 1-op-1 oppikt."""
    entry = {"obj": None, "tablename": entiteit_type, "actie": actie,
             "wijziging": wijziging or None, "captured_id": str(entiteit_id)}
    _schrijf_keten(
        conn, tabel="audit_log", entries=[entry], tenant_id=tenant_id,
        actor_sub=actor_sub or _ACTOR_ONBEKEND, actor_email=actor_email,
        correlatie_id=correlatie_id or str(uuid.uuid4()), entiteit_id_is_uuid=True,
    )


async def registreer_gebruikersactie(session, *, koppel_id, wijziging) -> None:
    """Expliciete audit voor een Keycloak-only gebruikersbeheer-actie (ADR-029 Fase 2b).

    `entiteit_type='gebruiker_persoon'`, `entiteit_id`=de koppelrij-id, `actie=update`; de
    `wijziging` beschrijft de actie ({veld:{oud,nieuw}}). Actor/correlatie/tenant uit de
    request-context (zoals de flush-capture). Bij wachtwoord-reset bevat `wijziging` NOOIT het
    wachtwoord — alleen het feit. Schrijft binnen de lopende transactie; de caller commit."""
    actor_sub, actor_email = huidige_actor()
    correlatie_id = huidige_correlatie_id()
    tenant_id = huidige_tenant_id()
    await session.run_sync(lambda s: schrijf_expliciet_record(
        s.connection(), tenant_id=tenant_id, actor_sub=actor_sub, actor_email=actor_email,
        correlatie_id=correlatie_id, entiteit_type="gebruiker_persoon",
        entiteit_id=koppel_id, wijziging=wijziging,
    ))


@event.listens_for(Session, "after_commit")
def _lk_audit_after_commit(session):
    """Transactie-einde: reset de score-driver-vlag (v3) en eventuele restpending,
    zodat een volgende transactie op dezelfde (pool-)sessie schoon begint."""
    session.info.pop(_SCORE_DRIVER_FLAG, None)
    session.info.pop(_PENDING_KEY, None)


@event.listens_for(Session, "after_rollback")
def _lk_audit_after_rollback(session):
    session.info.pop(_SCORE_DRIVER_FLAG, None)
    session.info.pop(_PENDING_KEY, None)


# Vaste namespace voor de audit-append advisory locks (ADR-006 → 6006). Serialiseert
# uitsluitend het audit-append-pad; botst niet met andere advisory locks (die zijn er niet).
_AUDIT_LOCK_NS = 6006


def _neem_append_lock(conn, tenant_id: str | None) -> None:
    """Serialiseer de keten-append per tenant (v4, Besluit 6).

    Een transactie-gebonden advisory lock op `(ns, hashtext(tenant_id|'platform'))`:
    twee gelijktijdige schrijvers binnen dezelfde tenant kunnen niet op dezelfde
    voorganger ankeren → een fork is **structureel onmogelijk**. De lock wordt vóór het
    lezen van de staart genomen en automatisch vrijgegeven bij commit/rollback;
    re-acquisitie binnen dezelfde transactie (meerdere flushes) is een no-op. De
    platform-keten gebruikt één vaste globale sleutel (`'platform'`).
    """
    sleutel = tenant_id if tenant_id is not None else "platform"
    conn.execute(
        text("SELECT pg_advisory_xact_lock(:ns, hashtext(:k))"),
        {"ns": _AUDIT_LOCK_NS, "k": sleutel},
    )


def _staart_hash(conn, tabel: str, tenant_id: str | None) -> str | None:
    """De `record_hash` van het laatste record in de keten (de staart waaraan we
    aanhaken): het record waarnaar geen enkel `vorige_hash` verwijst. Per tenant
    (audit_log; RLS scoopt al, de filter is defense-in-depth) resp. globaal."""
    tenant_filter = "a.tenant_id = :tid AND " if tenant_id is not None else ""
    sub_filter = "b.tenant_id = :tid AND " if tenant_id is not None else ""
    sql = text(
        f"SELECT a.record_hash FROM {tabel} a "
        f"WHERE {tenant_filter}NOT EXISTS ("
        f"  SELECT 1 FROM {tabel} b WHERE {sub_filter}b.vorige_hash = a.record_hash"
        f") ORDER BY a.tijdstip DESC LIMIT 1"
    )
    params = {"tid": tenant_id} if tenant_id is not None else {}
    return conn.execute(sql, params).scalar()


def _schrijf_keten(conn, *, tabel, entries, tenant_id, actor_sub, actor_email,
                   correlatie_id, entiteit_id_is_uuid):
    # v4: neem de append-lock VÓÓR het lezen van de staart, zodat lezen-ketenen-insert
    # geserialiseerd is binnen de tenant (resp. de globale platform-keten).
    _neem_append_lock(conn, tenant_id)
    vorige_hash = _staart_hash(conn, tabel, tenant_id)
    for p in entries:
        ent_id = p["captured_id"] if p["captured_id"] is not None else getattr(p["obj"], "id")
        ent_id_str = str(ent_id)
        tijdstip = datetime.now(timezone.utc)
        velden = {
            "tijdstip": tijdstip.isoformat(),
            "actor_sub": actor_sub,
            "actor_email": actor_email,
            "entiteit_type": p["tablename"],
            "entiteit_id": ent_id_str,
            "actie": p["actie"].value,
            "wijziging": p["wijziging"] or None,
            "correlatie_id": correlatie_id,
        }
        if tenant_id is not None:
            velden["tenant_id"] = tenant_id
        record_hash = bereken_record_hash(vorige_hash, velden)
        _insert_record(
            conn, tabel=tabel, tenant_id=tenant_id, tijdstip=tijdstip,
            actor_sub=actor_sub, actor_email=actor_email, entiteit_type=p["tablename"],
            entiteit_id=ent_id_str, entiteit_id_is_uuid=entiteit_id_is_uuid,
            actie=p["actie"].value, wijziging=p["wijziging"] or None,
            correlatie_id=correlatie_id, record_hash=record_hash, vorige_hash=vorige_hash,
        )
        vorige_hash = record_hash


def _insert_record(conn, *, tabel, tenant_id, tijdstip, actor_sub, actor_email,
                   entiteit_type, entiteit_id, entiteit_id_is_uuid, actie, wijziging,
                   correlatie_id, record_hash, vorige_hash):
    ent_cast = "CAST(:entiteit_id AS uuid)" if entiteit_id_is_uuid else ":entiteit_id"
    tenant_col = "tenant_id, " if tenant_id is not None else ""
    tenant_val = "CAST(:tenant_id AS uuid), " if tenant_id is not None else ""
    sql = text(
        f"INSERT INTO {tabel} ("
        f"  {tenant_col}tijdstip, actor_sub, actor_email, entiteit_type, entiteit_id,"
        f"  actie, wijziging, correlatie_id, record_hash, vorige_hash"
        f") VALUES ("
        f"  {tenant_val}:tijdstip, :actor_sub, :actor_email, :entiteit_type, {ent_cast},"
        f"  CAST(:actie AS auditactie_enum), CAST(:wijziging AS jsonb),"
        f"  CAST(:correlatie_id AS uuid), :record_hash, :vorige_hash"
        f")"
    )
    params = {
        "tijdstip": tijdstip, "actor_sub": actor_sub, "actor_email": actor_email,
        "entiteit_type": entiteit_type, "entiteit_id": entiteit_id, "actie": actie,
        "wijziging": json.dumps(wijziging) if wijziging is not None else None,
        "correlatie_id": correlatie_id, "record_hash": record_hash,
        "vorige_hash": vorige_hash,
    }
    if tenant_id is not None:
        params["tenant_id"] = tenant_id
    conn.execute(sql, params)
