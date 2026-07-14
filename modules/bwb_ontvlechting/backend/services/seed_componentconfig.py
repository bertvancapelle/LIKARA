"""Seed — default componentcatalogus (ADR-021 Besluit 8, ADR-012 Addendum C; ADR-023).

Platform-brede referentiedata (één tabel `componentconfig_optie`, drie dimensies:
`componenttype` + `structuurrelatie_type` + `archimate_relatie`). Idempotent via
`ON CONFLICT (dimensie, optie_sleutel) DO NOTHING`. Draait UITSLUITEND via
`platform_init` (init-container). `componenttype.applicatie` is een systeem-sleutel.

ADR-023: elk `componenttype` draagt zijn ArchiMate-mapping (`archimate_element`/`laag`/
`aspect`, OK-1/3); de dimensie `archimate_relatie` bevat de gecureerde acht relatietypes
met per-type kenmerk-definities (`kenmerk_definitie`, OK-2). Migratie `0011` zaait dit op
bestaande DB's; deze seed dekt fresh deploys (byte-gelijk).
"""
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.models import ComponentConfigDimensie, ComponentConfigOptie

# (sleutel, label, archimate_element, laag, aspect, checklist_dragend, ondersteunt_werk)
# ADR-022 Fase E / ADR-023 Fase F (F-6): `checklist_dragend` wordt hier EXPLICIET gezet
# (single source = de seed), niet langer de kolom-default laten winnen. LI058 — beoordeelde
# typen: `applicatie` (systeem-sleutel) + `database`; overige typen niet. De seed (expand) en de
# reconcile-migraties (0023 + 0046) zetten dezelfde stand → geen drift.
# ADR-045 — `ondersteunt_werk` (koppelbaar aan de functie-as, gate 2), bewust RUIM:
# óók fileshare/client_software (de G-schijf-werkelijkheid moet vastlegbaar zijn);
# database/server_compute/integratievoorziening ondersteunen een systeem, geen mens.
# Reconcile-migratie 0065 zet dezelfde stand op bestaande DB's (byte-gelijk).
_COMPONENTTYPE: list[tuple[str, str, str, str, str, bool, bool]] = [
    ("applicatie", "Applicatie", "application_component", "application", "active", True, True),
    ("database", "Database", "system_software", "technology", "active", True, False),  # LI058 — beoordeeld type
    # LI060 — `applicatieserver` hernoemd naar `server_compute` (Server / compute), nu beoordeeld;
    # typing (node/technology/active) ongewijzigd. Volgorde-slot behouden (stabiele lijst).
    ("server_compute", "Server / compute", "node", "technology", "active", True, False),
    ("client_software", "Client-software", "system_software", "technology", "active", False, True),
    ("saas_dienst", "SaaS-dienst", "application_component", "application", "active", False, True),
    # LI060 — `middleware` hernoemd naar `integratievoorziening` (Integratie-/koppelvoorziening),
    # nu beoordeeld. Typing → system_software/technology/active: eigen bindweefsel (ESB/broker) dat de
    # organisatie zélf draait → hoort in de technology-band (naast servers/databases/fileshares),
    # niet bij de afgenomen application-diensten.
    ("integratievoorziening", "Integratie-/koppelvoorziening", "system_software", "technology", "active", True, False),
    ("fileshare", "Fileshare", "node", "technology", "active", False, True),
    # LI060 — nieuw beoordeeld type (basisregistratie valt hieronder — geen apart type).
    ("landelijke_voorziening", "Landelijke voorziening", "application_service", "application", "active", True, True),
]
_STRUCTUURRELATIE: list[tuple[str, str]] = [
    ("draait_op", "Draait op"),
    ("maakt_deel_uit_van", "Maakt deel uit van"),
]
# (sleutel, label, kenmerk_definitie) — de gecureerde acht ArchiMate-relatietypes (OK-1/2).
_ARCHIMATE_RELATIE: list[tuple[str, str, dict]] = [
    ("composition", "Composition", {}),
    # ADR-023 Fase E: aggregation draagt de plateau-lidmaatschap-kenmerken. `dispositie` wordt
    # gevalideerd tegen de algemene relatie-kenmerk-vocabulaire-catalogus (NIET ContractConfig);
    # de contractuele bevestiging is `registratie` (vrije registratie, door het systeem niet
    # gevalideerd/vergeleken; de facade vult wie/wanneer server-side).
    ("aggregation", "Aggregation", {
        "dispositie": {"type": "catalogus", "catalogus": "relatiekenmerk", "dimensie": "dispositie"},
        "contractueel_bevestigd": {"type": "registratie"},
        "bevestigd_aantal_gebruikers": {"type": "registratie"},
        "bevestigd_door": {"type": "registratie"},
        "bevestigd_op": {"type": "registratie"},
    }),
    ("serving", "Serving", {}),
    ("assignment", "Assignment", {}),
    ("flow", "Flow", {
        "protocol": {"type": "enum", "enum": "koppelprotocol"},
        "impact_bij_verbreking": {"type": "enum", "enum": "impact_verbreking"},
        # OK-2-verfijning (v3): richting als kenmerk (eenrichting/tweerichting), geen duplicatie.
        "richting": {"type": "enum", "enum": "koppelrichting"},
    }),
    ("realization", "Realization", {}),
    # ADR-023 — `relatie_rol` is een relatie-kenmerk → gevalideerd tegen de algemene
    # relatie-kenmerk-catalogus (consistentie-opruim), niet langer ContractConfig.
    ("association", "Association", {
        "relatie_rol": {"type": "catalogus", "catalogus": "relatiekenmerk", "dimensie": "relatie_rol"},
    }),
    ("access", "Access", {}),
]


def bouw_componentconfig() -> list[dict]:
    """Puur (DB-vrij): geordende lijst optie-rijen (alle drie de dimensies)."""
    # Uniforme sleutelset per rij — een multi-row `pg_insert` eist dat elke rij dezelfde
    # kolommen levert (anders kan SQLAlchemy de default voor ontbrekende kolommen niet
    # renderen). Waarden byte-identiek: `archimate_*` = None waar niet van toepassing,
    # `kenmerk_definitie` = {} waar niet van toepassing (was server-default '{}').
    rijen: list[dict] = []
    for volgorde, (sleutel, label, elem, laag, aspect, dragend, werk) in enumerate(_COMPONENTTYPE):
        rijen.append({
            "dimensie": ComponentConfigDimensie.componenttype,
            "optie_sleutel": sleutel, "label": label, "volgorde": volgorde, "actief": True,
            "archimate_element": elem, "laag": laag, "aspect": aspect,
            "kenmerk_definitie": {}, "checklist_dragend": dragend, "ondersteunt_werk": werk,
        })
    for volgorde, (sleutel, label) in enumerate(_STRUCTUURRELATIE):
        rijen.append({
            "dimensie": ComponentConfigDimensie.structuurrelatie_type,
            "optie_sleutel": sleutel, "label": label, "volgorde": volgorde, "actief": True,
            "archimate_element": None, "laag": None, "aspect": None,
            "kenmerk_definitie": {}, "checklist_dragend": False, "ondersteunt_werk": False,
        })
    for volgorde, (sleutel, label, kenmerken) in enumerate(_ARCHIMATE_RELATIE):
        rijen.append({
            "dimensie": ComponentConfigDimensie.archimate_relatie,
            "optie_sleutel": sleutel, "label": label, "volgorde": volgorde, "actief": True,
            "archimate_element": None, "laag": None, "aspect": None,
            "kenmerk_definitie": kenmerken, "checklist_dragend": False, "ondersteunt_werk": False,
        })
    return rijen


async def seed_componentconfig(session) -> int:
    """Zaai de default-componentcatalogus (idempotent). Geeft het aantal optie-rijen terug
    (vast 18: 8 componenttypen + 2 structuurrelaties + 8 ArchiMate-relatietypes)."""
    rijen = bouw_componentconfig()
    stmt = pg_insert(ComponentConfigOptie).values(rijen).on_conflict_do_nothing(
        index_elements=["dimensie", "optie_sleutel"]
    )
    await session.execute(stmt)
    await session.commit()
    return len(rijen)
