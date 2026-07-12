"""DEV-ONLY testdata-seed — BWB-ontvlechting (V005, LK-Testdata-seed).

╔══════════════════════════════════════════════════════════════════════════╗
║  DIT IS GEEN PRODUCTIE-SEED.                                              ║
║  - NIET aanroepen vanuit `app.platform_init` of de init-container.        ║
║  - Vult UITSLUITEND de dev-tenant met een realistisch applicatielandschap ║
║    zodat de V005-schermen gevulde data tonen.                             ║
║  - Loopt volledig via de bestaande SERVICE-LAAG (dezelfde paden als de    ║
║    UI/API): applicatie aanmaken → start-inventarisatie → checklistscores  ║
║    zetten. Lifecycle en blokkades worden NOOIT hard gezet — ze worden     ║
║    afgeleid (ADR-013/016). `in_behandeling` via een handmatige transitie; ║
║    `opgelost` via de legitieme auto-resolutie (score nee/deels → ja).     ║
║  - Idempotent: een applicatie die al bestaat (op naam, binnen de tenant)  ║
║    wordt volledig overgeslagen → een tweede run wijzigt de tellingen niet.║
╚══════════════════════════════════════════════════════════════════════════╝

Draaien (binnen de draaiende stack, als lk_app onder RLS):

    docker compose exec lk-api python3 dev_seed_testdata.py

`TIEL`/gemeentenamen komen in deze seed NERGENS voor (de 89 checklistvragen zelf
zijn bestaande platform-referentiedata en vallen buiten deze seed).
"""
import asyncio
import pathlib
import sys
from datetime import date

# --- sys.path: portable in de container (/app + /modules) én lokaal -----------
_HERE = pathlib.Path(__file__).resolve().parent  # backend/  (in container: /app)
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))  # levert `app.*` (o.a. app.models.base)
for _cand in (
    pathlib.Path("/modules/bwb_ontvlechting/backend"),
    _HERE.parent / "modules" / "bwb_ontvlechting" / "backend",
):
    if _cand.exists():
        sys.path.insert(0, str(_cand))  # levert top-level `models`, `services`, `schemas`
        break

from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.core.database import get_worker_session  # noqa: E402
from models.models import (  # noqa: E402
    AntwoordType,
    Blokkade,
    BlokkadeStatus,
    ChecklistScore,
    ChecklistVraag,
    ChecklistVraagOptie,
    Checklistscore,
    Component,
    Contract,
    Element,
    ElementType,
    GebruikerPersoon,
    Gebruikersgroep,
    HostingModel,
    Organisatiegebruik,
    Partij,
    PartijAard,
    PartijScope,
    Relatie,
)
from schemas.component import ComponentCreate  # noqa: E402
from schemas.component_contract import ComponentContractCreate  # noqa: E402
from schemas.blokkade import BlokkadeUpdate  # noqa: E402
from schemas.checklistscore import ChecklistscoreCreate, ChecklistscoreUpdate  # noqa: E402
from schemas.contract import ContractCreate  # noqa: E402
from schemas.relatie import RelatieCreate  # noqa: E402
from schemas.partij import PartijCreate, PartijUpdate  # noqa: E402
from schemas.gebruikersgroep import GebruikersgroepCreate  # noqa: E402
from services import (  # noqa: E402
    component_contract_service,
    component_service,
    blokkade_service,
    checklistscore_service,
    contract_service,
    gebruikersgroep_service,
    organisatiegebruik_service,
    partij_service,
    bedrijfsfunctie_service,
    proces_service,
    procesvervulling_service,
    relatie_service,
    roltoewijzing_service,
)
from services.errors import RegistratieConflict  # noqa: E402
from services.seed import CHECKLIST_VRAGEN, seed_checklist_vragen  # noqa: E402
from services.seed_antwoordconfig import seed_antwoordconfig  # noqa: E402

# Bestaande dev-tenant (hoofdopdracht §2) — geen nieuwe tenant.
DEV_TENANT = "11111111-1111-1111-1111-111111111111"

# Vaste code-volgorde van de 89 vragen (deterministisch scoren).
CODES = [v["code"] for v in CHECKLIST_VRAGEN]

# ADR-022 Fase A: checklistscores ankeren op component_id + checklistvraag_id (UUID).
# Deze maps (code ↔ checklistvraag.id, binnen het applicatie-type) worden in main()
# eenmalig uit de DB geladen; de seed blijft per `code` redeneren.
_CODE_TO_ID: dict[str, object] = {}
_ID_TO_CODE: dict[object, str] = {}

# Neutrale, deterministische defaults voor de NOT NULL-velden die de opdracht
# niet noemt (aanvulling A §2). Raken geen acceptatiepunt.
APP_DEFAULTS = {"migratiepad": "onbekend", "complexiteit": "midden", "prioriteit": "midden"}
KOP_DEFAULTS = {"richting": "eenrichting", "impact_bij_verbreking": "midden"}

# --- Aanvulling B: bevinding/eigenaar/actie op een subset gescoorde rijen --------
# Functierol-pool voor `eigenaar` (deterministisch op app-index, GEEN persoonsnaam).
ROL_POOL = [
    "Applicatiebeheerder", "Functioneel beheerder", "Migratiecoördinator",
    "Informatiemanager", "Gegevensbeheerder",
]
# Apps waarvan ALLE blokkade-rijen alle drie de velden krijgen (A: 2+3+4 = 9 rijen).
BLOKKADE_VELDEN_APPS = frozenset({1, 6, 10})

# Standalone, TIEL-vrije onderbouwingen per vraagcode (de vraagteksten zelf bevatten
# 'Tiel' — die echoën we nooit). Onbekende code → generieke deterministische fallback.
BEVINDING_PER_CODE = {
    "1.1": "Naam en functioneel domein van de applicatie zijn vastgelegd.",
    "1.2": "Het functionele domein is bepaald en gedocumenteerd.",
    "1.3": "Het juridisch eigenaarschap van de applicatie vergt nadere afstemming.",
    "1.4": "Het eigenaarschap van de data is nog niet eenduidig belegd.",
    "1.5": "De applicatie wordt door meerdere organisatieonderdelen gebruikt.",
    "1.6": "Een verwerkersovereenkomst is aanwezig en actueel.",
    "2.1": "Het hostingmodel is vastgesteld en gedocumenteerd.",
}
ACTIE_PER_CODE = {
    "1.1": "Registratie in de CMDB controleren en vastleggen.",
    "1.2": "Domeinindeling bevestigen met de proceseigenaar.",
    "1.3": "Eigenaarschap juridisch laten bevestigen en vastleggen.",
    "1.4": "Data-eigenaarschap afstemmen en formeel beleggen.",
}


# --- 12 applicaties (hoofdopdracht §Data + aanvulling A §1) --------------------
# scored = aantal te scoren vragen; blokkeer = aantal eerste codes met nee/deels.
# post   = legitieme nabewerkingen om in_behandeling/opgelost af te leiden.
#   {"op": "in_behandeling", "pos": i}  → handmatige transitie open→in_behandeling
#   {"op": "oplossen",       "pos": i}  → score CODES[i] nee/deels → ja (auto-opgelost)
APPS = [
    {"naam": "Zaaksysteem", "org": "Informatievoorziening", "host": "saas",
     "beschrijving": "Centraal zaakgericht werken; integratiehub (StUF-ZKN).",
     "scored": 89, "blokkeer": 2, "post": []},
    {"naam": "Gegevensmakelaar", "org": "Informatievoorziening", "host": "on_premise",
     "beschrijving": "Broker/servicebus voor StUF/Digikoppeling-berichten.",
     "scored": 55, "blokkeer": 0, "post": []},
    {"naam": "DMS", "org": "DIV", "host": "saas",
     "beschrijving": "Documentmanagement, gekoppeld aan het zaaksysteem.",
     "scored": 89, "blokkeer": 0, "post": []},
    {"naam": "Burgerzaken", "org": "Publiekszaken", "host": "on_premise",
     "beschrijving": "Burgerzaken-/BRP-frontoffice-applicatie.",
     "scored": 40, "blokkeer": 0, "post": []},
    {"naam": "BRP-bevraging", "org": "Publiekszaken", "host": "on_premise",
     "beschrijving": "Bevraging basisregistratie personen via de broker.",
     "scored": 70, "blokkeer": 0, "post": []},
    {"naam": "Belastingsysteem", "org": "Financiën", "host": "private_cloud",
     "beschrijving": "Heffing/inning, gekoppeld aan WOZ/financieel.",
     "scored": 89, "blokkeer": 3,
     "post": [{"op": "in_behandeling", "pos": 1}, {"op": "oplossen", "pos": 2}]},
    {"naam": "Financieel", "org": "Financiën", "host": "private_cloud",
     "beschrijving": "Grootboek/financiële administratie.",
     "scored": 89, "blokkeer": 0, "post": []},
    {"naam": "Sociaal-domein-suite", "org": "Sociaal Domein", "host": "saas",
     "beschrijving": "Suite voor het sociaal domein (Wmo/Jeugd/Participatie).",
     "scored": 89, "blokkeer": 1, "post": [{"op": "oplossen", "pos": 0}]},
    {"naam": "GIS-viewer", "org": "Ruimte", "host": "on_premise",
     "beschrijving": "Kaartviewer; leest periodieke export, geen live koppeling.",
     "scored": 89, "blokkeer": 0, "post": []},
    {"naam": "Subsidiemodel", "org": "Subsidies", "host": "on_premise",
     "beschrijving": "Lokaal rekenmodel (schaduw-IT), niet geïntegreerd.",
     "scored": 89, "blokkeer": 4, "post": []},
    {"naam": "HR-systeem", "org": "P&O", "host": "saas",
     "beschrijving": "Personeels-/salarissysteem, (nog) niet gekoppeld.",
     "scored": 25, "blokkeer": 0, "post": []},
    {"naam": "e-Depot", "org": "DIV", "host": "private_cloud",
     "beschrijving": "Te-/in te richten archiefvoorziening.",
     "scored": 0, "blokkeer": 0, "post": []},
]

# --- 10 koppelingen (bron-index → doel-index, 1-based zoals de opdracht) -------
# protocol: middleware voor de broker-/StUF-links 1→2, 2→5, 2→6, 2→8; api elders.
KOPPELINGEN = [
    (1, 2, "StUF-berichtenverkeer", "middleware"),
    (1, 3, "documentkoppeling", "api"),
    (1, 4, "zaak-/persoonskoppeling", "api"),
    (1, 7, "financiële boekingen", "api"),
    (1, 8, "zaakkoppeling", "api"),
    (2, 5, "StUF-BG", "middleware"),
    (2, 6, "gegevenslevering", "middleware"),
    (2, 8, "gegevenslevering", "middleware"),
    (4, 5, "persoonsbevraging", "api"),
    (6, 7, "debiteuren/boekingen", "api"),
]


# === Aanvulling D — contractlandschap (ADR-020) ===============================
# Door Bert vastgesteld landschap (CD046). Deterministisch + idempotent; loopt via
# de service-laag zodat de invarianten (I1/I2, catalogus-validatie, uniciteit) gelden.
# Géén 'TIEL' in namen (fictieve, plausibele NL-gegevens; geen echte bedrijven).
# Legacy/ongebruikt (`_seed_aanvulling_d` wordt niet door main() aangeroepen — het leidende
# scenario is `_seed_bvowb_scenario`). Bewust ZONDER `contactpersoon`-veld: dat vrije-tekstveld
# bestaat na ADR-039 niet meer op PartijCreate (het aanspreekpunt is `contactpersoon_id`, gezet in
# het canonieke scenario). Zo blijft deze dict een geldige PartijCreate mocht de functie ooit lopen.
LEVERANCIERS_D = [
    {"naam": "GemSoft B.V.", "straat_huisnummer": "Softwareplein 12", "postcode": "3811 AB",
     "plaats": "Amersfoort",
     "telefoon": "033-1234567", "mobiel": "06-12345678", "email": "contact@gemsoft.test"},
    {"naam": "CivData Solutions", "straat_huisnummer": "Dataweg 8", "postcode": "3542 AD",
     "plaats": "Utrecht",
     "telefoon": "030-7654321", "mobiel": "06-87654321", "email": "info@civdata.test"},
    # Minimaal: alleen plaats + email.
    {"naam": "InfraHost Nederland", "plaats": "Rotterdam", "email": "support@infrahost.test"},
    # Minimaal: alleen telefoon.
    {"naam": "GeoWorks B.V.", "telefoon": "020-5556677"},
]

# Mantel (#1) staat vóór de deelcontracten (#2/#3): de lijstvolgorde borgt dat de
# mantel-id beschikbaar is wanneer een deelcontract eraan refereert.
CONTRACTEN_D = [
    {"contractnaam": "GemSoft Raamovereenkomst 2024-2028", "leverancier": "GemSoft B.V.",
     "type": "mantelcontract", "mantel": None,
     "dekking": ["licentie_aanschaf", "onderhoud_support"], "kostenmodel": [],
     "begindatum": date(2024, 1, 1), "einddatum": date(2028, 12, 31),
     "vernieuwingsdatum": date(2027, 10, 1),
     "extern_contract_id": "RAAM-2024-001", "leverancier_contract_id": "GS-2024-RAAM"},
    {"contractnaam": "Deel Burgerzaken-suite", "leverancier": "GemSoft B.V.",
     "type": "deelcontract", "mantel": "GemSoft Raamovereenkomst 2024-2028",
     "dekking": ["licentie_aanschaf", "onderhoud_support"], "kostenmodel": ["per_inwoner"],
     "begindatum": date(2024, 3, 1), "einddatum": date(2028, 12, 31),
     "leverancier_contract_id": "GS-BZ-2024"},  # extern-ID bewust leeg
    {"contractnaam": "Deel Financiën", "leverancier": "GemSoft B.V.",
     "type": "deelcontract", "mantel": "GemSoft Raamovereenkomst 2024-2028",
     "dekking": ["licentie_aanschaf", "onderhoud_support"], "kostenmodel": ["saas_pxq"],
     "begindatum": date(2024, 4, 1), "einddatum": date(2028, 12, 31)},  # beide ID's leeg
    {"contractnaam": "CivData SaaS-overeenkomst", "leverancier": "CivData Solutions",
     "type": "los_contract", "mantel": None,
     "dekking": ["licentie_aanschaf", "hosting"], "kostenmodel": ["saas_pxq"],
     "begindatum": date(2023, 1, 1), "einddatum": date(2026, 12, 31),
     "vernieuwingsdatum": date(2026, 7, 1), "extern_contract_id": "CIV-SAAS-2023"},
    {"contractnaam": "CivData Onderhoudscontract", "leverancier": "CivData Solutions",
     "type": "los_contract", "mantel": None,
     "dekking": ["onderhoud_support"], "kostenmodel": [],
     "begindatum": date(2023, 6, 1), "einddatum": date(2026, 6, 1),
     "toelichting": "Onderhoud op de bestaande implementatie; jaarlijkse evaluatie."},
    {"contractnaam": "InfraHost Hostingdiensten", "leverancier": "InfraHost Nederland",
     "type": "los_contract", "mantel": None,
     "dekking": ["hosting"], "kostenmodel": ["volume"],
     "begindatum": date(2024, 1, 1), "einddatum": date(2027, 12, 31)},
    {"contractnaam": "GeoWorks Licentieovereenkomst", "leverancier": "GeoWorks B.V.",
     "type": "los_contract", "mantel": None,
     "dekking": ["licentie_aanschaf"], "kostenmodel": ["volume"],
     "begindatum": date(2025, 1, 1),  # einddatum bewust leeg
     "omschrijving": "Licentie voor de geo-/kaartfunctionaliteit."},
]

# Koppelingen: (app-index 1-based in APPS) → contractnaam, relatie_rol.
# Belastingsysteem (6) is de multi-contract-app: valt_onder #3 + onderhoud #5 + hosting #6.
# Zonder enige koppeling (bewust): Zaaksysteem (1), HR-systeem (11), e-Depot (12).
KOPPELINGEN_D = [
    (4, "Deel Burgerzaken-suite", "valt_onder"),        # Burgerzaken
    (5, "Deel Burgerzaken-suite", "valt_onder"),        # BRP-bevraging
    (6, "Deel Financiën", "valt_onder"),                # Belastingsysteem
    (7, "Deel Financiën", "valt_onder"),                # Financieel
    (3, "CivData SaaS-overeenkomst", "valt_onder"),     # DMS (saas)
    (8, "CivData SaaS-overeenkomst", "valt_onder"),     # Sociaal-domein-suite (saas)
    (6, "CivData Onderhoudscontract", "onderhoud"),     # Belastingsysteem (multi)
    (6, "InfraHost Hostingdiensten", "hosting"),        # Belastingsysteem (multi)
    (2, "InfraHost Hostingdiensten", "hosting"),        # Gegevensmakelaar (on-premise)
    (10, "InfraHost Hostingdiensten", "hosting"),       # Subsidiemodel (on-premise)
    (9, "GeoWorks Licentieovereenkomst", "valt_onder"), # GIS-viewer (geo/spatial)
]


def _score_voor(index: int, blokkeer: int) -> str:
    """Deterministische score per scored-positie (codevolgorde oplopend).

    - eerste `blokkeer` posities: afwisselend nee/deels (blokkerend);
    - overige: ~20% nvt (elke 5e), rest ja.
    """
    if index < blokkeer:
        return "nee" if index % 2 == 0 else "deels"
    return "nvt" if index % 5 == 4 else "ja"


async def _seed_applicatie(session, app: dict, bestaande: dict) -> "uuid_like":
    """Maak één applicatie + scores + afgeleide blokkades. Idempotent op naam."""
    naam = app["naam"]
    if naam in bestaande:
        print(f"  = {naam}: bestaat al — overgeslagen")
        return bestaande[naam]

    obj = await component_service.maak_aan(
        session, DEV_TENANT,
        ComponentCreate(
            componenttype="applicatie",
            naam=naam, beschrijving=app["beschrijving"], hostingmodel=app["host"],
            # ADR-024 B6-b: eigenaar-organisatie is nu een optionele partij-verwijzing
            # (`eigenaar_organisatie_id`); de vrije-tekst-velden `eigenaar_naam`/`leverancier`
            # zijn met migratie 0034 verwijderd en niet langer invoervelden (extra='forbid').
            **APP_DEFAULTS,
        ),
    )
    app_id = obj["id"]

    # e-Depot blijft `concept`: niet starten, niet scoren.
    if app["scored"] == 0 and not app["post"]:
        print(f"  + {naam}: aangemaakt (concept, 0/89)")
        return app_id

    # Verlaat de `concept`-vloer via de legitieme handmatige start (ADR-013):
    # herbereken vanuit `concept` blijft anders `concept`.
    await component_service.start_beoordeling(session, DEV_TENANT, app_id)

    for i in range(app["scored"]):
        await checklistscore_service.maak_aan(
            session, DEV_TENANT,
            ChecklistscoreCreate(
                component_id=app_id, checklistvraag_id=_CODE_TO_ID[CODES[i]],
                score=_score_voor(i, app["blokkeer"]),
            ),
        )

    # Nabewerkingen — uitsluitend via de legitieme paden.
    for stap in app["post"]:
        code = CODES[stap["pos"]]
        score_obj = (
            await session.execute(
                select(Checklistscore).where(
                    Checklistscore.component_id == app_id,
                    Checklistscore.checklistvraag_id == _CODE_TO_ID[code],
                )
            )
        ).scalar_one()
        if stap["op"] == "in_behandeling":
            # Handmatige transitie open → in_behandeling (blokkade_service).
            blok = (
                await session.execute(
                    select(Blokkade).where(Blokkade.checklistscore_id == score_obj.id)
                )
            ).scalar_one()
            await blokkade_service.werk_bij(
                session, DEV_TENANT, blok.id,
                BlokkadeUpdate(status=BlokkadeStatus.in_behandeling),
            )
        elif stap["op"] == "oplossen":
            # Legitieme auto-resolutie: score nee/deels → ja ⇒ blokkade auto-opgelost.
            await checklistscore_service.werk_bij(
                session, DEV_TENANT, score_obj.id,
                ChecklistscoreUpdate(score=ChecklistScore.ja),
            )

    print(f"  + {naam}: aangemaakt ({app['scored']}/89, {app['blokkeer']} blokkerend)")
    return app_id


async def _seed_koppelingen(session, app_ids: dict) -> None:
    """Maak de 10 koppelingen als **flow-relaties** (ADR-023 cutover). Idempotent op (bron, doel)."""
    bestaande = {
        (r.bron_id, r.doel_id)
        for r in (
            await session.execute(select(Relatie).where(Relatie.relatietype == "flow"))
        ).scalars().all()
    }
    for bron_idx, doel_idx, omschrijving, protocol in KOPPELINGEN:
        bron_id = app_ids[bron_idx]
        doel_id = app_ids[doel_idx]
        if (bron_id, doel_id) in bestaande:
            print(f"  = flow {bron_idx}→{doel_idx}: bestaat al — overgeslagen")
            continue
        # ADR-023a — naam verplicht voor flow: beschrijvende naam op basis van de
        # bron-/doel-applicatienamen (paren in deze seed zijn uniek → geen volgnummer nodig).
        naam = f"{APPS[bron_idx - 1]['naam']} → {APPS[doel_idx - 1]['naam']}"
        await relatie_service.maak_aan(
            session, DEV_TENANT,
            RelatieCreate(
                bron_id=bron_id, doel_id=doel_id, relatietype="flow", naam=naam,
                kenmerken={"protocol": protocol, "richting": KOP_DEFAULTS["richting"],
                           "impact_bij_verbreking": KOP_DEFAULTS["impact_bij_verbreking"]},
                omschrijving=omschrijving,
            ),
        )
        print(f"  + flow {bron_idx}→{doel_idx}: {omschrijving}")


def _code_key(code: str):
    """Numerieke sleutel voor codevolgorde ('1.10' > '1.2')."""
    return tuple(int(deel) for deel in code.split("."))


async def _vul_velden(session, score_obj, eigenaar: str, *, met_actie: bool) -> bool:
    """PATCH bevinding(+actie)+eigenaar op één score-rij. Idempotent: al gevuld → skip.

    Stuurt NOOIT `score` mee → `_synchroniseer_blokkade`/`herbereken_lifecycle`
    blijven no-op (FASE 1-bewijs); lifecycle/blokkades wijzigen niet.
    """
    if score_obj.bevinding:  # reeds gevuld (tweede run) → niets doen
        return False
    code = _ID_TO_CODE[score_obj.checklistvraag_id]
    # ADR-037 — het vrije-tekstveld `eigenaar` verviel; de verantwoordelijke wordt als partij-FK
    # gezet (zie `_seed_bvowb_scenario`, verantwoordelijke-stap). Deze helper is legacy/ongebruikt
    # (geen caller) en vult enkel nog bevinding/actie.
    velden = {
        "bevinding": BEVINDING_PER_CODE.get(
            code, f"De bevinding voor checklistvraag {code} is vastgelegd."
        ),
    }
    if met_actie:
        velden["actie"] = ACTIE_PER_CODE.get(code, "Vervolgactie afstemmen en vastleggen.")
    await checklistscore_service.werk_bij(
        session, DEV_TENANT, score_obj.id, ChecklistscoreUpdate(**velden)
    )
    return True


async def _seed_velden(session, app_nr: int, app_id) -> int:
    """Vul bevinding/eigenaar/actie op de subset gescoorde rijen van één app.

    A (apps 1/6/10): alle blokkade-rijen → bevinding+eigenaar+actie.
    B (elke app met scores): eerste 3 niet-geblokkeerde gescoorde rijen (codevolgorde)
       → bevinding+eigenaar. Apps zonder scores (e-Depot) worden niet aangeraakt.
    """
    eigenaar = ROL_POOL[(app_nr - 1) % len(ROL_POOL)]
    scores = (
        await session.execute(
            select(Checklistscore).where(Checklistscore.component_id == app_id)
        )
    ).scalars().all()
    if not scores:
        return 0

    blok_score_ids = {
        sid for (sid,) in (
            await session.execute(
                select(Blokkade.checklistscore_id).where(Blokkade.component_id == app_id)
            )
        ).all()
    }
    op_code = sorted(scores, key=lambda s: _code_key(_ID_TO_CODE[s.checklistvraag_id]))
    blok_rijen = [s for s in op_code if s.id in blok_score_ids]
    nonblok_rijen = [s for s in op_code if s.id not in blok_score_ids]

    gevuld = 0
    if app_nr in BLOKKADE_VELDEN_APPS:
        for s in blok_rijen:
            if await _vul_velden(session, s, eigenaar, met_actie=True):
                gevuld += 1
    for s in nonblok_rijen[:3]:
        if await _vul_velden(session, s, eigenaar, met_actie=False):
            gevuld += 1
    return gevuld


async def _laad_catalogus(session) -> tuple[dict, dict]:
    """(code → antwoordtype voor getypeerde vragen, code → [actieve optie_sleutels])."""
    typed = {
        code: at
        for (code, at) in (
            await session.execute(
                select(ChecklistVraag.code, ChecklistVraag.antwoordtype).where(
                    ChecklistVraag.antwoordtype != AntwoordType.geen
                )
            )
        ).all()
    }
    opties_per_code: dict[str, list[str]] = {}
    for vraag_id, sleutel in (
        await session.execute(
            select(ChecklistVraagOptie.checklistvraag_id, ChecklistVraagOptie.optie_sleutel)
            .where(ChecklistVraagOptie.actief.is_(True))
            .order_by(ChecklistVraagOptie.checklistvraag_id, ChecklistVraagOptie.volgorde)
        )
    ).all():
        opties_per_code.setdefault(_ID_TO_CODE[vraag_id], []).append(sleutel)
    return typed, opties_per_code


def _kies_antwoord(antwoordtype, code: str, app_nr: int, host: str, opties: list[str]):
    """Deterministische, gevarieerde antwoord_waarde-envelope (of None)."""
    if antwoordtype == AntwoordType.getal:
        return {"getal": app_nr}  # 1..12 — onderling verschillend
    if not opties:
        return None
    if antwoordtype == AntwoordType.enkelvoudige_keuze:
        # 2.1 ← werkelijke hostingmodel van de app (sleutel = enum-waarde = host).
        if code == "2.1" and host in opties:
            return {"optie": host}
        return {"optie": opties[app_nr % len(opties)]}
    # meerkeuze: eerste optie, plus bij even app-index de tweede.
    keuze = [opties[0]]
    if app_nr % 2 == 0 and len(opties) > 1:
        keuze.append(opties[1])
    return {"opties": keuze}


async def _seed_antwoord_waarden(
    session, app_nr: int, host: str, app_id, typed: dict, opties_per_code: dict
) -> int:
    """Vul antwoord_waarde op bestaande gescoorde rijen van getypeerde vragen.

    Via `checklistscore_service.werk_bij` (zónder `score`) zodat de 2B-validatie
    meeloopt en de engine no-op blijft. Idempotent: reeds-gevulde rijen worden
    overgeslagen.
    """
    scores = (
        await session.execute(
            select(Checklistscore).where(Checklistscore.component_id == app_id)
        )
    ).scalars().all()

    gevuld = 0
    for s in scores:
        code = _ID_TO_CODE[s.checklistvraag_id]
        if code not in typed or s.antwoord_waarde:
            continue
        waarde = _kies_antwoord(
            typed[code], code, app_nr, host, opties_per_code.get(code, [])
        )
        if waarde is None:
            continue
        await checklistscore_service.werk_bij(
            session, DEV_TENANT, s.id, ChecklistscoreUpdate(antwoord_waarde=waarde)
        )
        gevuld += 1
    return gevuld


async def _seed_aanvulling_d(session, app_ids: dict) -> dict:
    """Aanvulling D — leveranciers/contracten/koppelingen via de service-laag.

    Idempotent: leveranciers op naam, contracten op contractnaam, koppelingen op
    (applicatie_id, contract_id). Tweede run wijzigt niets. De service-laag handhaaft
    I1/I2 (mantel/leverancier-erving), catalogus-validatie en uniciteit.
    """
    # --- Externe partijen (element-backed, idempotent op naam) ---
    lev_ids = {
        r.naam: r.id
        for r in (
            await session.execute(select(Partij).where(Partij.aard == PartijAard.externe_partij))
        ).scalars().all()
    }
    for lev in LEVERANCIERS_D:
        if lev["naam"] in lev_ids:
            print(f"  = externe partij {lev['naam']}: bestaat al — overgeslagen")
            continue
        obj = await partij_service.maak_aan(
            session, DEV_TENANT, PartijCreate(aard=PartijAard.externe_partij, **lev)
        )
        lev_ids[lev["naam"]] = obj.id
        print(f"  + externe partij {lev['naam']}")

    # ADR-024 slice 2a/2a-bis: voorbeeld-partijen met "hoort bij"-samenhang (idempotent op naam).
    # Organisatie (top) → afdeling onder de organisatie → persoon onder org + afdeling.
    partij_ids = {r.naam: r.id for r in (await session.execute(select(Partij))).scalars().all()}

    async def _zorg_partij(aard, naam, **velden):
        if naam in partij_ids:
            print(f"  = partij {naam} ({aard.value}): bestaat al — overgeslagen")
            return partij_ids[naam]
        obj = await partij_service.maak_aan(session, DEV_TENANT, PartijCreate(aard=aard, naam=naam, **velden))
        partij_ids[naam] = obj.id
        print(f"  + partij {naam} ({aard.value})")
        return obj.id

    org_id = await _zorg_partij(
        PartijAard.organisatie, "Gemeente Veldendam", omschrijving="Eigen organisatie"
    )
    afd_id = await _zorg_partij(
        PartijAard.organisatie_eenheid, "Afdeling Informatievoorziening",
        organisatie_id=org_id, omschrijving="Interne afdeling I&A",
    )
    await _zorg_partij(
        PartijAard.persoon, "J. de Vries",
        organisatie_id=org_id, afdeling_id=afd_id,
        email="j.devries@gemeente.test", telefoon="06-12345678",
        omschrijving="Functioneel beheerder",
    )

    # --- Contracten (idempotent op contractnaam; mantel vóór deel) ---
    con_ids = {
        r.contractnaam: r.id for r in (await session.execute(select(Contract))).scalars().all()
    }
    for c in CONTRACTEN_D:
        if c["contractnaam"] in con_ids:
            print(f"  = contract {c['contractnaam']}: bestaat al — overgeslagen")
            continue
        body = ContractCreate(
            leverancier_id=lev_ids[c["leverancier"]],
            contracttype=c["type"],
            contractnaam=c["contractnaam"],
            mantelcontract_id=con_ids[c["mantel"]] if c.get("mantel") else None,
            extern_contract_id=c.get("extern_contract_id"),
            leverancier_contract_id=c.get("leverancier_contract_id"),
            begindatum=c.get("begindatum"),
            einddatum=c.get("einddatum"),
            vernieuwingsdatum=c.get("vernieuwingsdatum"),
            omschrijving=c.get("omschrijving"),
            toelichting=c.get("toelichting"),
            dekking=c.get("dekking", []),
            kostenmodel=c.get("kostenmodel", []),
        )
        res = await contract_service.maak_aan(session, DEV_TENANT, body)
        con_ids[c["contractnaam"]] = res["id"]
        print(f"  + contract {c['contractnaam']} ({c['type']})")

    # --- Koppelingen (idempotent op (applicatie_id, contract_id)) ---
    bestaande_kop = {
        (r.bron_id, r.doel_id)  # ADR-023: component↔contract = association-relatie
        for r in (
            await session.execute(select(Relatie).where(Relatie.relatietype == "association"))
        ).scalars().all()
    }
    for app_idx, contractnaam, rol in KOPPELINGEN_D:
        app_id = app_ids[app_idx]
        contract_id = con_ids[contractnaam]
        if (app_id, contract_id) in bestaande_kop:
            print(f"  = koppeling app{app_idx}→{contractnaam}: bestaat al — overgeslagen")
            continue
        await component_contract_service.maak_aan(
            session, DEV_TENANT,
            ComponentContractCreate(component_id=app_id, contract_id=contract_id, relatie_rol=rol),
        )
        print(f"  + koppeling app{app_idx}→{contractnaam} ({rol})")

    return {"leveranciers": len(lev_ids), "contracten": len(con_ids)}


async def _seed_technische_laag(session, app_ids: dict) -> dict:
    """Aanvulling E (ADR-021 B5) — technische laag: een gedeelde database-component
    onder Belastingsysteem + Financieel + structuurrelaties (+ GIS→fileshare), zodat
    gedeelde infrastructuur en de impactanalyse demonstreerbaar zijn. Kale componenten
    (geen subtype). Idempotent op component-naam resp. (component, op_component, type)."""
    import uuid as _uuid

    tid = _uuid.UUID(DEV_TENANT)
    comps = {c.naam: c.id for c in (await session.execute(select(Component))).scalars().all()}

    async def _ensure(naam, type_, host, org):
        if naam in comps:
            return comps[naam]
        # ADR-023: element-identiteit eerst (shared-PK), daarna de component.
        elem = Element(tenant_id=tid, element_type=ElementType.component)
        session.add(elem)
        await session.flush()
        # ADR-024 B6-b: `eigenaar_organisatie` (vrije tekst) is vervangen door de optionele
        # `eigenaar_organisatie_id`-FK; kale componenten laten we hier zonder eigenaar.
        c = Component(id=elem.id, tenant_id=tid, naam=naam, componenttype=type_, hostingmodel=host)
        session.add(c)
        await session.flush()
        comps[naam] = c.id
        print(f"  + component {naam} ({type_})")
        return c.id

    db_id = await _ensure("Oracle FIN-DB", "database", HostingModel.on_premise, "Financiën")
    fs_id = await _ensure("Geo-fileshare", "fileshare", HostingModel.on_premise, "Ruimte")

    # ADR-023: draait_op → assignment-relatie, oriëntatie host→gehoste (bron=host/op, doel=gehoste/comp).
    bestaand = {
        (r.bron_id, r.doel_id)
        for r in (
            await session.execute(select(Relatie).where(Relatie.relatietype == "assignment"))
        ).scalars().all()
    }
    relaties = [
        (db_id, app_ids[6]),   # Oracle FIN-DB → Belastingsysteem (draait op, gedeeld)
        (db_id, app_ids[7]),   # Oracle FIN-DB → Financieel
        (fs_id, app_ids[9]),   # Geo-fileshare → GIS-viewer
    ]
    for host_id, gehoste_id in relaties:
        if (host_id, gehoste_id) in bestaand:
            continue
        await relatie_service.maak_aan(
            session, DEV_TENANT,
            RelatieCreate(bron_id=host_id, doel_id=gehoste_id, relatietype="assignment"),
        )
        print(f"  + assignment: {host_id} → {gehoste_id}")
    return {"componenten_extra": 2, "structuurrelaties": len(relaties)}


async def _seed_tweede_type(session) -> dict:
    """ADR-022 Fase E — een TWEEDE checklist-dragend type (`client_software`) end-to-end.

    NB (ADR-023 Fase F / F-6): bewust `client_software` als demo-type — het enige niet-
    applicatie-type dat de live-gedragstests niet als profielloze infra vastpinnen. De
    dev-seed markeert het zélf checklist-dragend (duurzaam na reseed); `applicatieserver`
    en `database` blijven `false` (de structurele eindstand).

    1. markeer het type platform-breed checklist-dragend (catalogus, als lk_platform);
    2. enkele tenant-eigen vragen voor dat type;
    3. twee componenten van het type (krijgen een generiek profiel, start `concept`);
    4. één component gestart (`in_inventarisatie`) + volledig gescoord → `migratieklaar`;
       de tweede blijft op `concept` (demonstreert de "Start beoordeling"-knop).
    Idempotent op vraag-code resp. component-naam."""
    from app.core.database import platform_session_factory
    from sqlalchemy import text as _text

    from schemas.checklistconfig import VraagCreate
    from schemas.checklistscore import ChecklistscoreCreate
    from schemas.component import ComponentCreate
    from services import checklistconfig_service as cc
    from services import component_service as comp
    from services import lifecycle_service

    TYPE = "client_software"
    # 1. Catalogus-vlag (platform; lk_platform mag componentconfig_optie UPDATEn).
    async with platform_session_factory() as ps:
        await ps.execute(
            _text(
                "UPDATE componentconfig_optie SET checklist_dragend = true "
                "WHERE dimensie = 'componenttype' AND optie_sleutel = :t"
            ),
            {"t": TYPE},
        )
        await ps.commit()

    # 2. Tenant-vragen voor het type (idempotent op code).
    bestaande_codes = {
        c for (c,) in (
            await session.execute(
                select(ChecklistVraag.code).where(ChecklistVraag.componenttype == TYPE)
            )
        ).all()
    }
    CS_VRAGEN = [
        ("CS.1", "Is de client-software-versie nog ondersteund (geen end-of-life)?"),
        ("CS.2", "Wordt de client-software centraal uitgerold en gepatcht?"),
        ("CS.3", "Zijn er licentie-afspraken vastgelegd voor de client-software?"),
    ]
    for code, vraag in CS_VRAGEN:
        if code in bestaande_codes:
            continue
        await cc.maak_vraag(
            session, DEV_TENANT,
            VraagCreate(componenttype=TYPE, code=code, vraag=vraag, categorie_nr=1, categorie_naam="Client-software"),
        )
    code_to_id = {
        c: i for (c, i) in (
            await session.execute(
                select(ChecklistVraag.code, ChecklistVraag.id).where(ChecklistVraag.componenttype == TYPE)
            )
        ).all()
    }

    # 3. Twee componenten (idempotent op naam) — krijgen een generiek profiel.
    bestaande_namen = {
        c.naam for c in (
            await session.execute(select(Component).where(Component.componenttype == TYPE))
        ).scalars().all()
    }
    srv_gestart = None
    for naam, start in (("Client-software PRD-01", True), ("Client-software ACC-02", False)):
        if naam in bestaande_namen:
            continue
        c = await comp.maak_aan(
            session, DEV_TENANT,
            ComponentCreate(naam=naam, componenttype=TYPE, hostingmodel=HostingModel.on_premise),
        )
        if start:
            srv_gestart = c["id"]
            # 4. Start beoordeling (concept → in_inventarisatie) + volledig scoren → migratieklaar.
            await lifecycle_service.start_beoordeling(session, DEV_TENANT, c["id"])
            await session.commit()
            for code in ("CS.1", "CS.2", "CS.3"):
                await checklistscore_service.maak_aan(
                    session, DEV_TENANT,
                    ChecklistscoreCreate(component_id=c["id"], checklistvraag_id=code_to_id[code], score="ja"),
                )
            print(f"  + {naam}: gestart + 3/3 gescoord (→ migratieklaar)")
        else:
            print(f"  + {naam}: aangemaakt (concept — demonstreert Start beoordeling)")
    return {"type": TYPE, "vragen": len(code_to_id), "gestart_component": srv_gestart}


# === ADR-025 — Landschapskaart-demodata ======================================
# Gevarieerd, samenhangend mini-landschap zodat de Landschapskaart (ego + impact) in
# beide modi gevuld is. Lifecycle wordt NOOIT hard gezet — de engine leidt hem af uit
# de checklistscores (zoals een gebruiker). Idempotent: bestaat-al → overslaan / stil.
LK_SERVERS = [("App-server Noord", "applicatieserver"), ("Databasecluster Prod", "database")]

# plan: 'alles' → migratieklaar · 'helft'/'drie' → in_inventarisatie · 'blokkade' → geblokkeerd ·
#       'geen' → concept (lifecycle-vloer). 'Zaaksysteem' bestaat al uit de basisseed (migratieklaar)
#       → create+score worden dan overgeslagen (idempotent), de relaties hangen we er wél aan.
LK_APPS = [
    # 'Klantportaal' i.p.v. 'Zaaksysteem': de basis-seed kent al een 'Zaaksysteem' (met 2 blokkades →
    # geblokkeerd). Een eigen, niet-botsende naam levert de bedoelde migratieklaar-headline zónder de
    # engine of de bredere demo te raken.
    {"naam": "Klantportaal", "host": "saas", "plan": "alles"},
    {"naam": "Documentbeheer", "host": "saas", "plan": "helft"},
    {"naam": "HRM-portaal", "host": "on_premise", "plan": "blokkade"},
    {"naam": "Financieel systeem", "host": "private_cloud", "plan": "drie"},
    {"naam": "Burgerzaken-suite", "host": "on_premise", "plan": "geen"},
    {"naam": "Rapportage-tool", "host": "saas", "plan": "geen"},
]
LK_CONTRACTEN = [
    ("Licentiecontract Klantportaal", "SaaS-leverancier NL"),
    ("Onderhoudscontract Infra", "TechSupplier BV"),
]
LK_FLOW = [
    ("Klantportaal", "Documentbeheer"), ("Klantportaal", "HRM-portaal"),
    ("Financieel systeem", "Klantportaal"), ("Burgerzaken-suite", "Klantportaal"),
    ("Burgerzaken-suite", "Financieel systeem"), ("Rapportage-tool", "Financieel systeem"),
    ("Rapportage-tool", "HRM-portaal"),
]
LK_ASSIGNMENT = [
    ("App-server Noord", "Klantportaal"), ("App-server Noord", "Documentbeheer"),
    ("Databasecluster Prod", "Klantportaal"), ("Databasecluster Prod", "Financieel systeem"),
    ("Databasecluster Prod", "HRM-portaal"),
]
LK_ASSOCIATION = [
    ("Klantportaal", "Licentiecontract Klantportaal"), ("Documentbeheer", "Licentiecontract Klantportaal"),
    ("App-server Noord", "Onderhoudscontract Infra"), ("Databasecluster Prod", "Onderhoudscontract Infra"),
]
LK_ROLLEN = [
    ("Afdeling Informatisering", "functioneel_beheer", "Klantportaal"),
    ("Afdeling Informatisering", "functioneel_beheer", "Documentbeheer"),
    ("TechSupplier BV", "technisch_beheer", "Klantportaal"),
    ("TechSupplier BV", "technisch_beheer", "HRM-portaal"),
    ("P. van Dijk", "product_owner", "Klantportaal"),
    ("P. van Dijk", "eigenaar", "Burgerzaken-suite"),
    ("SaaS-leverancier NL", "technisch_beheer", "Financieel systeem"),
    # ADR-024 — nieuwe rollen, voor de doorklik vanuit de VerantwoordelijkheidSectie.
    ("P. van Dijk", "account_manager", "Zaaksysteem"),
    ("J. de Vries", "service_delivery_manager", "Klantportaal"),
]


def _lk_scores(plan: str, n: int) -> list[str]:
    """Score-reeks (codevolgorde) per plan; engine leidt de lifecycle eruit af."""
    if plan == "alles":
        return ["ja"] * n
    if plan == "helft":
        return ["ja"] * -(-n // 2)            # ceil(n/2) scores → rest ongescoord
    if plan == "drie":
        return ["ja"] * min(3, n)
    if plan == "blokkade":
        return (["nee"] + ["ja"] * (n - 1)) if n else []  # één nee → open blokkade
    return []                                  # 'geen' → concept


async def seed_landschapskaart_demo(session, tenant_id) -> dict:
    """ADR-025 — demolandschap voor de Landschapskaart. Idempotent + engine-geleid."""
    naam_naar_id: dict[str, object] = {}

    # --- Servers (kale componenten) + applicaties (engine-geleide lifecycle) ---
    comps = {c.naam: c.id for c in (await session.execute(select(Component))).scalars().all()}
    for naam, type_ in LK_SERVERS:
        if naam in comps:
            naam_naar_id[naam] = comps[naam]
            print(f"  = component {naam}: bestaat al — overgeslagen")
            continue
        c = await component_service.maak_aan(
            session, tenant_id, ComponentCreate(naam=naam, componenttype=type_, hostingmodel="on_premise"))
        naam_naar_id[naam] = c["id"]
        print(f"  + component {naam} ({type_})")

    bestaande_apps = {r.naam: r.id for r in (await session.execute(
        select(Component).where(Component.componenttype == "applicatie"))).scalars().all()}
    n_vragen = len(CODES)
    for app in LK_APPS:
        naam = app["naam"]
        if naam in bestaande_apps:
            naam_naar_id[naam] = bestaande_apps[naam]
            print(f"  = applicatie {naam}: bestaat al — overgeslagen (scores ongewijzigd)")
            continue
        obj = await component_service.maak_aan(
            session, tenant_id,
            ComponentCreate(componenttype="applicatie", naam=naam, beschrijving=f"Demo-applicatie {naam}", hostingmodel=app["host"], **APP_DEFAULTS))
        naam_naar_id[naam] = obj["id"]
        scores = _lk_scores(app["plan"], n_vragen)
        if scores:
            # Verlaat de concept-vloer via de legitieme start; daarna scoren (engine herberekent).
            await component_service.start_beoordeling(session, tenant_id, obj["id"])
            for i, score in enumerate(scores):
                await checklistscore_service.maak_aan(
                    session, tenant_id,
                    ChecklistscoreCreate(component_id=obj["id"], checklistvraag_id=_CODE_TO_ID[CODES[i]], score=score))
        print(f"  + applicatie {naam} (plan={app['plan']}, {len(scores)}/{n_vragen} gescoord)")

    # --- Partijen (organisatie → afdeling → persoon + twee externe partijen) ---
    partij_ids = {r.naam: r.id for r in (await session.execute(select(Partij))).scalars().all()}

    async def _zorg_partij(aard, naam, **velden):
        if naam in partij_ids:
            naam_naar_id[naam] = partij_ids[naam]
            print(f"  = partij {naam}: bestaat al — overgeslagen")
            return partij_ids[naam]
        obj = await partij_service.maak_aan(session, tenant_id, PartijCreate(aard=aard, naam=naam, **velden))
        partij_ids[naam] = obj.id
        naam_naar_id[naam] = obj.id
        print(f"  + partij {naam} ({aard.value})")
        return obj.id

    org_id = await _zorg_partij(PartijAard.organisatie, "Gemeente BWB", omschrijving="Demo-organisatie")
    afd_id = await _zorg_partij(PartijAard.organisatie_eenheid, "Afdeling Informatisering", organisatie_id=org_id)
    # ADR-024 (Optie 1) — personen met contactgegevens (functietitel is persoon-only).
    await _zorg_partij(
        PartijAard.persoon, "P. van Dijk", organisatie_id=org_id, afdeling_id=afd_id,
        email="p.vandijk@bwb.test", telefoon="06-12345678", functietitel="Informatiemanager")
    await _zorg_partij(
        PartijAard.persoon, "J. de Vries", organisatie_id=org_id, afdeling_id=afd_id,
        email="j.devries@bwb.test", telefoon="06-87654321", functietitel="Product Owner")
    await _zorg_partij(PartijAard.externe_partij, "TechSupplier BV")
    await _zorg_partij(PartijAard.externe_partij, "SaaS-leverancier NL")
    # Zaaksysteem (basis-seed) resolvbaar maken voor een roltoewijzing (staat niet in LK_APPS).
    if "Zaaksysteem" in bestaande_apps:
        naam_naar_id["Zaaksysteem"] = bestaande_apps["Zaaksysteem"]

    # --- Contracten (leverancier = externe partij) ---
    con_ids = {r.contractnaam: r.id for r in (await session.execute(select(Contract))).scalars().all()}
    for contractnaam, leverancier in LK_CONTRACTEN:
        if contractnaam in con_ids:
            naam_naar_id[contractnaam] = con_ids[contractnaam]
            print(f"  = contract {contractnaam}: bestaat al — overgeslagen")
            continue
        res = await contract_service.maak_aan(
            session, tenant_id,
            ContractCreate(leverancier_id=partij_ids[leverancier], contracttype="los_contract",
                           contractnaam=contractnaam, dekking=[], kostenmodel=[]))
        con_ids[contractnaam] = res["id"]
        naam_naar_id[contractnaam] = res["id"]
        print(f"  + contract {contractnaam}")

    # --- Relaties: flow + assignment (idempotent op (bron, doel) per type) ---
    async def _bestaande(relatietype):
        return {(r.bron_id, r.doel_id) for r in (
            await session.execute(select(Relatie).where(Relatie.relatietype == relatietype))).scalars().all()}

    flow_set = await _bestaande("flow")
    for bron, doel in LK_FLOW:
        b, d = naam_naar_id[bron], naam_naar_id[doel]
        if (b, d) in flow_set:
            continue
        await relatie_service.maak_aan(session, tenant_id, RelatieCreate(
            bron_id=b, doel_id=d, relatietype="flow", naam=f"{bron} → {doel}",
            kenmerken={"richting": KOP_DEFAULTS["richting"], "impact_bij_verbreking": KOP_DEFAULTS["impact_bij_verbreking"]},
            omschrijving="koppeling"))
        print(f"  + flow {bron}→{doel}")

    assign_set = await _bestaande("assignment")
    for host, gehoste in LK_ASSIGNMENT:
        b, d = naam_naar_id[host], naam_naar_id[gehoste]
        if (b, d) in assign_set:
            continue
        await relatie_service.maak_aan(session, tenant_id, RelatieCreate(
            bron_id=b, doel_id=d, relatietype="assignment", omschrijving="draait op"))
        print(f"  + assignment {host}→{gehoste}")

    # --- Contract-associaties (component↔contract) idempotent op (component, contract) ---
    assoc_set = await _bestaande("association")
    for comp_naam, contractnaam in LK_ASSOCIATION:
        b, d = naam_naar_id[comp_naam], naam_naar_id[contractnaam]
        if (b, d) in assoc_set:
            continue
        await component_contract_service.maak_aan(session, tenant_id, ComponentContractCreate(
            component_id=b, contract_id=d, relatie_rol="valt_onder"))
        print(f"  + association {comp_naam}↔{contractnaam}")

    # --- Roltoewijzingen (beheerorganisatie) — stil bij dubbel (409) ---
    for partij, rol, object_naam in LK_ROLLEN:
        try:
            await roltoewijzing_service.maak_aan(
                session, tenant_id, naam_naar_id[partij], naam_naar_id[object_naam], rol)
            print(f"  + roltoewijzing {partij} · {rol} · {object_naam}")
        except RegistratieConflict:
            print(f"  = roltoewijzing {partij} · {rol} · {object_naam}: bestaat al — overgeslagen")

    # --- Verificatie: engine-bepaalde lifecycle per demo-applicatie ---
    print("Seed landschapskaart — lifecycle-statussen:")
    lifecycles = {}
    for app in LK_APPS:
        detail = await component_service.lees_detail(session, tenant_id, naam_naar_id[app["naam"]])
        status = getattr(detail.get("lifecycle_status"), "value", detail.get("lifecycle_status"))
        lifecycles[app["naam"]] = status
        print(f"  {app['naam']+':':<22}{status}")
    return lifecycles


async def _seed_bvowb_scenario(session, tenant_id) -> dict:
    """BvoWB shared-services scenario (de ENIGE dev-scenario-seed): één dienstenprovider die
    een gedeeld ICT-landschap beheert voor 3 gemeenten, met leveranciers, ketenpartners, DVO's
    en een volledig rollenmodel. Volgorde: organisaties → leveranciers → afdelingen → personen →
    applicaties (+scoring) → contracten → component↔contract → flows → roltoewijzingen →
    gebruikersgroepen. Alles idempotent (skip op naam). Afgestemde keuzes:
    - DVO-leverancier = BvoWB (aard=organisatie) — toegestaan als contract-leverancier.
    - `soort`: alleen 'leverancier'/'ketenpartner' bestaan in de catalogus; 'dienstenprovider'/
      'samenwerkende gemeente' → None.
    - flow-richting naar_doel/naar_bron → eenrichting · bidirectioneel → tweerichting;
      protocol REST/SOAP → api · StUF → middleware.
    - ADR-038 — een groep hoort altijd bij een organisatie; burger-doelgroepen zijn externe
      organisaties (aard=organisatie + scope=extern) met segment-afdelingen eronder.
    - flow naar een ketenpartner-partij (Belastingdienst) wordt NIET aangemaakt — flows lopen
      tussen componenten, niet naar een partij."""
    from datetime import date

    tid = tenant_id
    telling = {k: 0 for k in (
        "organisaties", "leveranciers", "ketenpartners", "burgers", "afdelingen", "personen",
        "applicaties", "contracten", "associaties", "flows", "roltoewijzingen",
        "scores", "organisatiegebruik", "gebruikersgroepen",
        "processen", "procesvervullingen",
        "referentiemodellen", "bedrijfsfuncties",
    )}

    partij_id = {r.naam: r.id for r in (await session.execute(select(Partij))).scalars().all()}
    app_id = {r.naam: r.id for r in (await session.execute(
        select(Component).where(Component.componenttype == "applicatie"))).scalars().all()}
    contract_id = {r.contractnaam: r.id for r in (await session.execute(select(Contract))).scalars().all()}

    async def _partij(aard, naam, cat, **velden):
        if naam in partij_id:
            return partij_id[naam]
        obj = await partij_service.maak_aan(session, tid, PartijCreate(aard=aard, naam=naam, **velden))
        partij_id[naam] = obj.id
        telling[cat] += 1
        return obj.id

    # ── 1. Organisaties (aard=organisatie): dienstenprovider + gemeenten ──
    # ADR-038 — intern/extern expliciet: BvoWB is de eigen organisatie (intern); de deelnemende
    # gemeenten staan erbuiten (extern).
    organisaties = [
        ("BvoWB", None, "Markt 1", "4001 AA", "Tiel", "0344-678900", "info@bvowb.test", PartijScope.intern),
        # Tweede eigen (interne) organisatie: maakt de organisatie-keuze op het gebruiker-scherm
        # écht een keuze (meer dan één interne organisatie) en verplaatsen tussen organisaties testbaar.
        ("RID Rivierenland", None, "Stationsweg 20", "4001 CE", "Tiel", "0344-678940", "info@rid-rivierenland.test", PartijScope.intern),
        ("Gemeente Tiel", None, "Achterweg 2", "4001 BB", "Tiel", "0344-678910", "info@gemeentetiel.test", PartijScope.extern),
        ("Gemeente Culemborg", None, "Herenstraat 3", "4101 CC", "Culemborg", "0345-678920", "info@culemborg.test", PartijScope.extern),
        ("Gemeente West Betuwe", None, "Dorpsstraat 4", "4021 DD", "West Betuwe", "0344-678930", "info@westbetuwe.test", PartijScope.extern),
    ]
    for naam, soort, straat, pc, plaats, tel, mail, scope in organisaties:
        await _partij(PartijAard.organisatie, naam, "organisaties", soort=soort, scope=scope,
                      straat_huisnummer=straat, postcode=pc, plaats=plaats, telefoon=tel, email=mail)
    bvowb_id = partij_id["BvoWB"]

    # ── 1b. Ketenpartners (aard=externe_partij, soort=ketenpartner) — externe samenwerkingspartijen ──
    ketenpartners = [
        ("Provincie Gelderland", "Markt 11", "6811 CG", "Arnhem", "026-3599111", "info@gelderland.test"),
        ("RVIG", "Turfmarkt 147", "2511 DP", "Den Haag", "070-3614614", "info@rvig.test"),
        ("RDW", "Europaweg 205", "9723 AS", "Groningen", "0900-0739", "info@rdw.test"),
        ("Belastingdienst", "Parnassusweg 5", "1077 DC", "Amsterdam", "0800-0543", "info@belastingdienst.test"),
    ]
    for naam, straat, pc, plaats, tel, mail in ketenpartners:
        await _partij(PartijAard.externe_partij, naam, "ketenpartners", soort="ketenpartner",
                      straat_huisnummer=straat, postcode=pc, plaats=plaats, telefoon=tel, email=mail)

    # ── 2. Leveranciers (aard=externe_partij, soort=leverancier) ──
    leveranciers = [
        ("GemSoft B.V.", "Softwareweg 12", "3821 BB", "Amersfoort", "033-4567890", "info@gemsoft.test"),
        ("CivData Solutions", "Dataplein 5", "2521 CC", "Den Haag", "070-3456789", "contact@civdata.test"),
        ("GeoWorks B.V.", "Geostraat 8", "1234 DD", "Amsterdam", "020-5678901", "info@geoworks.test"),
        ("DataBridge B.V.", "Databrug 3", "6827 HH", "Arnhem", "026-4567890", "hello@databridge.test"),
        ("FinSys N.V.", "Financiënweg 99", "3011 FF", "Rotterdam", "010-3456789", "info@finsys.test"),
        ("SocioSuite GmbH", "Sozialstraße 7", "6221 GG", "Maastricht", "043-3456789", "info@sociosuite.test"),
        ("BurgX B.V.", "Burgemeesterslaan 44", "5611 EE", "Eindhoven", "040-2345678", "support@burgx.test"),
        ("PermitPro B.V.", "Vergunningenweg 8", "5223 AA", "'s-Hertogenbosch", "073-6789012", "info@permitpro.test"),
        ("HRWorks B.V.", "Personeelsplein 22", "3511 AB", "Utrecht", "030-2345678", "info@hrworks.test"),
        ("OmgevingsSoft B.V.", "Omgevingslaan 15", "6811 JK", "Arnhem", "026-5678901", "info@omgevingssoft.test"),
    ]
    for naam, straat, pc, plaats, tel, mail in leveranciers:
        await _partij(PartijAard.externe_partij, naam, "leveranciers", soort="leverancier",
                      straat_huisnummer=straat, postcode=pc, plaats=plaats, telefoon=tel, email=mail)

    # ── 3. Burger-doelgroepen: zie stap 13b (ADR-038 — externe organisaties met afdelingen). ──

    # ── 4. Afdelingen BvoWB (onder BvoWB) ──
    afdelingen = [
        ("Beheer & Exploitatie", "Markt 1", "4001 AA", "Tiel", "0344-678901", "beheer@bvowb.test"),
        ("Informatievoorziening", "Markt 1", "4001 AA", "Tiel", "0344-678902", "iv@bvowb.test"),
        ("Klantbeheer & Relatiebeheer", "Markt 1", "4001 AA", "Tiel", "0344-678903", "klantbeheer@bvowb.test"),
    ]
    for naam, straat, pc, plaats, tel, mail in afdelingen:
        await _partij(PartijAard.organisatie_eenheid, naam, "afdelingen", organisatie_id=bvowb_id,
                      straat_huisnummer=straat, postcode=pc, plaats=plaats, telefoon=tel, email=mail)

    # ── 4b. Afdelingen RID Rivierenland (tweede interne organisatie) ──
    rid_id = partij_id["RID Rivierenland"]
    rid_afdelingen = [
        ("Servicedesk", "Stationsweg 20", "4001 CE", "Tiel", "0344-678941", "servicedesk@rid-rivierenland.test"),
        ("Projecten & Advies", "Stationsweg 20", "4001 CE", "Tiel", "0344-678942", "projecten@rid-rivierenland.test"),
    ]
    for naam, straat, pc, plaats, tel, mail in rid_afdelingen:
        await _partij(PartijAard.organisatie_eenheid, naam, "afdelingen", organisatie_id=rid_id,
                      straat_huisnummer=straat, postcode=pc, plaats=plaats, telefoon=tel, email=mail)

    # ── 5. BvoWB-medewerkers (org=BvoWB, afdeling=…) ──
    bvowb_medewerkers = [
        ("P. van Dijk", "Beheer & Exploitatie", "06-23456789", "p.vandijk@bvowb.test"),
        ("T. Klaassen", "Beheer & Exploitatie", "06-34567890", "t.klaassen@bvowb.test"),
        ("J. de Vries", "Informatievoorziening", "06-12345678", "j.devries@bvowb.test"),
        ("S. de Boer", "Informatievoorziening", "06-45678901", "s.deboer@bvowb.test"),
        ("R. Visser", "Klantbeheer & Relatiebeheer", "06-56789012", "r.visser@bvowb.test"),
        ("M. Bakker", "Klantbeheer & Relatiebeheer", "06-67890123", "m.bakker@bvowb.test"),
    ]
    for naam, afd, tel, mail in bvowb_medewerkers:
        await _partij(PartijAard.persoon, naam, "personen", organisatie_id=bvowb_id,
                      afdeling_id=partij_id[afd], telefoon=tel, email=mail)

    # ── 6. Gemeente-contactpersonen (org=gemeente) ──
    gemeente_personen = [
        ("A. Janssen", "Gemeente Tiel", "06-11223344", "a.janssen@gemeentetiel.test"),
        ("W. de Groot", "Gemeente Tiel", "06-22334455", "w.degroot@gemeentetiel.test"),
        ("B. van Essen", "Gemeente Culemborg", "06-33445566", "b.vanessen@culemborg.test"),
        ("C. Lievaart", "Gemeente Culemborg", "06-44556677", "c.lievaart@culemborg.test"),
        ("D. Lammers", "Gemeente West Betuwe", "06-55667788", "d.lammers@westbetuwe.test"),
        ("E. van Dijk", "Gemeente West Betuwe", "06-66778899", "e.vandijk@westbetuwe.test"),
    ]
    for naam, org, tel, mail in gemeente_personen:
        await _partij(PartijAard.persoon, naam, "personen", organisatie_id=partij_id[org],
                      telefoon=tel, email=mail)

    # ── 7. Leverancier-contactpersonen (2 per leverancier; rol → roltoewijzing hieronder) ──
    leverancier_personen = [
        ("L. Smeets", "GemSoft B.V.", "06-11223344", "l.smeets@gemsoft.test"),
        ("K. Peters", "GemSoft B.V.", "06-22334455", "k.peters@gemsoft.test"),
        ("T. van den Berg", "CivData Solutions", "06-33445566", "t.vandenberg@civdata.test"),
        ("F. Hendriks", "CivData Solutions", "06-44556677", "f.hendriks@civdata.test"),
        ("W. Jansen", "GeoWorks B.V.", "06-55667788", "w.jansen@geoworks.test"),
        ("C. Mulder", "GeoWorks B.V.", "06-66778899", "c.mulder@geoworks.test"),
        ("A. Dijkstra", "DataBridge B.V.", "06-77889900", "a.dijkstra@databridge.test"),
        ("I. van der Laan", "DataBridge B.V.", "06-88990011", "i.vanderlaan@databridge.test"),
        ("B. Vermeer", "FinSys N.V.", "06-99001122", "b.vermeer@finsys.test"),
        ("D. Koster", "FinSys N.V.", "06-00112233", "d.koster@finsys.test"),
        ("E. van Leeuwen", "SocioSuite GmbH", "06-11223355", "e.vanleeuwen@sociosuite.test"),
        ("G. Bosman", "SocioSuite GmbH", "06-22334466", "g.bosman@sociosuite.test"),
        ("H. de Wit", "BurgX B.V.", "06-33445577", "h.dewit@burgx.test"),
        ("N. Groothuis", "BurgX B.V.", "06-44556688", "n.groothuis@burgx.test"),
        ("O. Ploeg", "PermitPro B.V.", "06-55667799", "o.ploeg@permitpro.test"),
        ("V. Brouwer", "PermitPro B.V.", "06-66778800", "v.brouwer@permitpro.test"),
        ("Q. van Houten", "HRWorks B.V.", "06-77889911", "q.vanhouten@hrworks.test"),
        ("X. Pietersen", "HRWorks B.V.", "06-88990022", "x.pietersen@hrworks.test"),
        ("Y. Hendriksen", "OmgevingsSoft B.V.", "06-99001133", "y.hendriksen@omgevingssoft.test"),
        ("Z. van Beek", "OmgevingsSoft B.V.", "06-00112244", "z.vanbeek@omgevingssoft.test"),
    ]
    for naam, lev, tel, mail in leverancier_personen:
        await _partij(PartijAard.persoon, naam, "personen", organisatie_id=partij_id[lev],
                      telefoon=tel, email=mail)

    # ── 7b. Aanspreekpunt per leverancier (ADR-039) — de eerste contactpersoon van de leverancier
    #        wordt als aanspreekpunt (contactpersoon_id) gezet: een echte persoon, geen vrije tekst.
    #        Idempotent (alleen zetten als nog leeg). ──
    _eerste_contact: dict = {}
    for naam, lev, _tel, _mail in leverancier_personen:
        _eerste_contact.setdefault(lev, naam)
    for lev_naam, per_naam in _eerste_contact.items():
        lev_pid = partij_id[lev_naam]
        huidig = (await session.execute(
            select(Partij.contactpersoon_id).where(Partij.id == lev_pid, Partij.tenant_id == tid)
        )).scalar_one()
        if huidig is None:
            await partij_service.werk_bij(
                session, tid, lev_pid, PartijUpdate(contactpersoon_id=partij_id[per_naam])
            )

    # ── 8. Ketenpartner-contactpersonen (1 per ketenpartner) ──
    ketenpartner_personen = [
        ("F. de Jong", "Provincie Gelderland", "06-11223366", "f.dejong@gelderland.test"),
        ("G. Willems", "RVIG", "06-22334477", "g.willems@rvig.test"),
        ("H. van Dam", "RDW", "06-33445588", "h.vandam@rdw.test"),
        ("I. Fontijn", "Belastingdienst", "06-44556699", "i.fontijn@belastingdienst.test"),
    ]
    for naam, org, tel, mail in ketenpartner_personen:
        await _partij(PartijAard.persoon, naam, "personen", organisatie_id=partij_id[org],
                      telefoon=tel, email=mail)

    # ── 9. Applicaties (+ scoringsplan) ── (naam, omschrijving, host, gescoord, blokkerend, eigenaar)
    applicaties = [
        ("Zaaksysteem", "Centraal systeem voor zaakgericht werken — gedeeld alle gemeenten", "on_premise", 89, 1, "BvoWB"),
        ("Zaakafhandelcomponent", "Workflowcomponent voor zaakafhandeling — gedeeld alle gemeenten", "on_premise", 0, 0, "BvoWB"),
        ("DMS", "Documentmanagementsysteem — gedeeld alle gemeenten", "saas", 45, 0, "BvoWB"),
        ("Klantportaal", "Digitaal loket voor burgers — gedeeld alle gemeenten", "saas", 22, 0, "BvoWB"),
        ("BRP", "Basisregistratie Personen — gedeeld alle gemeenten", "saas", 89, 0, "BvoWB"),
        ("Gegevensmakelaar", "Koppelplatform voor gegevensuitwisseling — BvoWB infrastructuur", "on_premise", 0, 0, "BvoWB"),
        ("Financieel systeem", "Financiële administratie BvoWB en gemeenten", "private_cloud", 0, 0, "BvoWB"),
        ("Sociaal domein suite", "Casemanagement WMO/Jeugd/Participatie — gedeeld", "saas", 0, 0, "BvoWB"),
        ("Burgerzaken-suite", "Suite voor burgerzaken en persoonsdocumenten — gedeeld", "on_premise", 22, 0, "BvoWB"),
        ("Vergunningensysteem", "Vergunningverlening en -beheer Tiel", "saas", 0, 0, "Gemeente Tiel"),
        ("HR-systeem", "Personeels- en salarisadministratie Culemborg", "saas", 0, 0, "Gemeente Culemborg"),
        ("Omgevingsloket", "Omgevingsvergunningen en -plannen West Betuwe", "saas", 0, 0, "Gemeente West Betuwe"),
        # LI021 — bewust registratiegat: applicatie ZONDER eigenaar-organisatie ("nog niet toegewezen").
        # Kaal (gescoord=0, geen start_inventarisatie) → laat de scope-teller "zonder eigenaar" op 1 aanslaan.
        ("Archiefbeheer", "Archief- en bewaarbeheer — eigenaar nog niet toegewezen", "on_premise", 0, 0, None),
    ]
    for naam, oms, host, gescoord, blokkerend, eigenaar in applicaties:
        if naam in app_id:
            continue
        obj = await component_service.maak_aan(session, tid, ComponentCreate(
            componenttype="applicatie", naam=naam, beschrijving=oms, hostingmodel=host,
            eigenaar_organisatie_id=(partij_id[eigenaar] if eigenaar else None), **APP_DEFAULTS))
        app_id[naam] = obj["id"]
        telling["applicaties"] += 1
        if gescoord > 0:
            await component_service.start_beoordeling(session, tid, obj["id"])
            for i in range(gescoord):
                score = "nee" if i < blokkerend else "ja"
                await checklistscore_service.maak_aan(session, tid, ChecklistscoreCreate(
                    component_id=obj["id"], checklistvraag_id=_CODE_TO_ID[CODES[i]], score=score))
                telling["scores"] += 1

    # ── 10. Contracten (mantel vóór deelcontract) ── (naam, type, leverancier, van, tot, mantel, oms)
    contracten = [
        ("Raamovereenkomst ICT BvoWB 2023–2028", "mantelcontract", "GemSoft B.V.", "2023-01-01", "2028-12-31", None, "Raamcontract GemSoft voor Zaaksysteem en ZAC"),
        ("Deelcontract Zaaksysteem 2023–2026", "deelcontract", "GemSoft B.V.", "2023-01-01", "2026-12-31", "Raamovereenkomst ICT BvoWB 2023–2028", "Licentie en onderhoud Zaaksysteem"),
        ("Deelcontract ZAC 2023–2026", "deelcontract", "GemSoft B.V.", "2023-01-01", "2026-12-31", "Raamovereenkomst ICT BvoWB 2023–2028", "Licentie en onderhoud ZAC"),
        ("SaaS DMS & Klantportaal 2024–2027", "los_contract", "CivData Solutions", "2024-01-01", "2027-12-31", None, "SaaS-overeenkomst DMS en Klantportaal"),
        ("Licentiecontract BRP 2022–2026", "los_contract", "GeoWorks B.V.", "2022-01-01", "2026-12-31", None, "Licentie BRP-toegang en updates"),
        ("DataBridge koppelplatform 2024–2027", "los_contract", "DataBridge B.V.", "2024-01-01", "2027-12-31", None, "Beheer en doorontwikkeling Gegevensmakelaar"),
        ("FinSys onderhoudscontract 2024–2028", "los_contract", "FinSys N.V.", "2024-01-01", "2028-12-31", None, "Beheer en onderhoud Financieel systeem"),
        ("SocioSuite SaaS 2023–2026", "los_contract", "SocioSuite GmbH", "2023-03-01", "2026-02-28", None, "SaaS-licentie Sociaal domein suite"),
        ("Burgerzaken-suite licentie 2023–2026", "los_contract", "BurgX B.V.", "2023-06-01", "2026-05-31", None, "Licentie Burgerzaken-suite incl. support"),
        # DVO's — leverancier = BvoWB (interne dienstenprovider; organisatie is toegestaan)
        ("DVO BvoWB – Gemeente Tiel", "los_contract", "BvoWB", "2023-01-01", "2027-12-31", None, "Dienstverleningsovereenkomst gedeelde ICT-diensten Tiel"),
        ("DVO BvoWB – Gemeente Culemborg", "los_contract", "BvoWB", "2023-01-01", "2027-12-31", None, "Dienstverleningsovereenkomst gedeelde ICT-diensten Culemborg"),
        ("DVO BvoWB – Gemeente West Betuwe", "los_contract", "BvoWB", "2023-01-01", "2027-12-31", None, "Dienstverleningsovereenkomst gedeelde ICT-diensten West Betuwe"),
        # Gemeente-specifieke contracten
        ("Vergunningensysteem contract 2023–2026", "los_contract", "PermitPro B.V.", "2023-01-01", "2026-12-31", None, "Licentie vergunningensysteem Gemeente Tiel"),
        ("HR-systeem contract 2024–2027", "los_contract", "HRWorks B.V.", "2024-01-01", "2027-12-31", None, "HR-licentie Gemeente Culemborg"),
        ("Omgevingsloket contract 2023–2026", "los_contract", "OmgevingsSoft B.V.", "2023-01-01", "2026-12-31", None, "Licentie omgevingsloket Gemeente West Betuwe"),
    ]
    for naam, ctype, lev, van, tot, mantel, oms in contracten:
        if naam in contract_id:
            continue
        res = await contract_service.maak_aan(session, tid, ContractCreate(
            leverancier_id=partij_id[lev], contracttype=ctype, contractnaam=naam,
            mantelcontract_id=contract_id.get(mantel) if mantel else None,
            begindatum=date.fromisoformat(van), einddatum=date.fromisoformat(tot),
            omschrijving=oms, dekking=[], kostenmodel=[]))
        contract_id[naam] = res["id"]
        telling["contracten"] += 1

    # ── Component ↔ contract (association, relatie_rol=valt_onder) ──
    associaties = [
        ("Zaaksysteem", "Deelcontract Zaaksysteem 2023–2026"),
        ("Zaakafhandelcomponent", "Deelcontract ZAC 2023–2026"),
        ("DMS", "SaaS DMS & Klantportaal 2024–2027"),
        ("Klantportaal", "SaaS DMS & Klantportaal 2024–2027"),
        ("BRP", "Licentiecontract BRP 2022–2026"),
        ("Gegevensmakelaar", "DataBridge koppelplatform 2024–2027"),
        ("Financieel systeem", "FinSys onderhoudscontract 2024–2028"),
        ("Sociaal domein suite", "SocioSuite SaaS 2023–2026"),
        ("Burgerzaken-suite", "Burgerzaken-suite licentie 2023–2026"),
        ("Vergunningensysteem", "Vergunningensysteem contract 2023–2026"),
        ("HR-systeem", "HR-systeem contract 2024–2027"),
        ("Omgevingsloket", "Omgevingsloket contract 2023–2026"),
    ]
    for app_naam, c_naam in associaties:
        try:
            await component_contract_service.maak_aan(session, tid, ComponentContractCreate(
                component_id=app_id[app_naam], contract_id=contract_id[c_naam], relatie_rol="valt_onder"))
            telling["associaties"] += 1
        except RegistratieConflict:
            pass

    # ── 12. Flows (naam verplicht; meervoud per paar = kaartgroepering) ── (bron, doel, naam, richting, protocol, impact)
    _RICHTING = {"naar_doel": "eenrichting", "naar_bron": "eenrichting", "bidirectioneel": "tweerichting"}
    _PROTOCOL = {"REST": "api", "SOAP": "api", "StUF": "middleware", "api": "api", "middleware": "middleware"}
    flows = [
        ("Zaaksysteem", "Gegevensmakelaar", "Zaakinformatie push", "naar_doel", "REST", "hoog"),
        ("Zaaksysteem", "Gegevensmakelaar", "Documenten ophalen", "naar_bron", "REST", "midden"),
        ("Zaaksysteem", "Gegevensmakelaar", "Status terugkoppeling", "bidirectioneel", "REST", "midden"),
        ("Klantportaal", "Zaaksysteem", "Zaak aanmaken", "naar_doel", "REST", "hoog"),
        ("Klantportaal", "Zaaksysteem", "Zaakstatus opvragen", "naar_bron", "REST", "laag"),
        ("Burgerzaken-suite", "BRP", "BSN verificatie", "naar_doel", "StUF", "hoog"),
        ("Burgerzaken-suite", "BRP", "Adreswijziging verwerken", "bidirectioneel", "StUF", "midden"),
        ("Zaaksysteem", "DMS", "Documenten archiveren", "naar_doel", "REST", "hoog"),
        ("Zaaksysteem", "Burgerzaken-suite", "Burgerzaken-zaak aanmaken", "naar_doel", "StUF", "midden"),
        ("Zaaksysteem", "Financieel systeem", "Betaalopdracht doorzetten", "naar_doel", "REST", "midden"),
        ("Zaaksysteem", "Sociaal domein suite", "Sociaal dossier ophalen", "naar_bron", "REST", "midden"),
        ("Zaakafhandelcomponent", "Zaaksysteem", "Zaakstatus bijwerken", "naar_doel", "REST", "hoog"),
        ("Zaakafhandelcomponent", "DMS", "Besluit opslaan", "naar_doel", "REST", "midden"),
        ("Zaakafhandelcomponent", "Gegevensmakelaar", "Zaakdata verrijken", "naar_doel", "REST", "midden"),
        ("DMS", "Gegevensmakelaar", "Metadata exporteren", "naar_doel", "REST", "laag"),
        ("Klantportaal", "DMS", "Document uploaden", "naar_doel", "REST", "midden"),
        ("Klantportaal", "BRP", "Identiteit verifiëren", "naar_doel", "REST", "hoog"),
        ("Gegevensmakelaar", "BRP", "Persoonsgegevens opvragen", "naar_doel", "StUF", "hoog"),
        ("Gegevensmakelaar", "Financieel systeem", "Belastingdata synchroniseren", "naar_doel", "SOAP", "midden"),
        ("Gegevensmakelaar", "Burgerzaken-suite", "Adresgegevens doorzetten", "naar_doel", "StUF", "midden"),
        ("Gegevensmakelaar", "Sociaal domein suite", "Cliëntgegevens verrijken", "naar_doel", "REST", "midden"),
        ("Burgerzaken-suite", "DMS", "Reisdocumenten archiveren", "naar_doel", "REST", "laag"),
        ("Financieel systeem", "Klantportaal", "Betalingsstatus tonen", "naar_doel", "REST", "laag"),
        ("Sociaal domein suite", "Financieel systeem", "Uitbetalingen doorzetten", "naar_doel", "REST", "hoog"),
        ("Sociaal domein suite", "Klantportaal", "Aanvraagstatus tonen", "naar_doel", "REST", "laag"),
        ("BRP", "Burgerzaken-suite", "Basisregistratie updaten", "naar_doel", "StUF", "hoog"),
        # Ketenpartner-gerelateerde flows (app↔app; de Belastingdienst-flow is bewust weggelaten
        # — Belastingdienst is een ketenpartner-PARTIJ, geen component, dus geen flow-endpoint).
        ("Gegevensmakelaar", "BRP", "Persoonsgegevens RVIG ophalen", "naar_doel", "middleware", "hoog"),
        ("BRP", "Burgerzaken-suite", "BRP-mutaties verwerken", "naar_doel", "middleware", "hoog"),
        ("Klantportaal", "Gegevensmakelaar", "Burger-identificatie", "naar_doel", "api", "hoog"),
    ]
    bestaande_flows = {
        r.naam for r in (
            await session.execute(select(Relatie).where(Relatie.relatietype == "flow"))
        ).scalars().all()
    }
    for bron, doel, naam, richting, protocol, impact in flows:
        if naam in bestaande_flows:
            continue
        await relatie_service.maak_aan(session, tid, RelatieCreate(
            bron_id=app_id[bron], doel_id=app_id[doel], relatietype="flow", naam=naam,
            kenmerken={"richting": _RICHTING[richting], "protocol": _PROTOCOL[protocol],
                       "impact_bij_verbreking": impact}))
        telling["flows"] += 1

    # ── 11. Roltoewijzingen ──
    async def _rol(partij_naam, object_id, rol):
        try:
            await roltoewijzing_service.maak_aan(session, tid, partij_id[partij_naam], object_id, rol)
            telling["roltoewijzingen"] += 1
        except RegistratieConflict:
            pass

    rt_comp = [
        # BvoWB technisch beheer (P. van Dijk primair, T. Klaassen secundair)
        ("P. van Dijk", "Zaaksysteem", "technisch_beheer"),
        ("P. van Dijk", "Zaakafhandelcomponent", "technisch_beheer"),
        ("P. van Dijk", "DMS", "technisch_beheer"),
        ("P. van Dijk", "BRP", "technisch_beheer"),
        ("P. van Dijk", "Gegevensmakelaar", "technisch_beheer"),
        ("T. Klaassen", "Klantportaal", "technisch_beheer"),
        ("T. Klaassen", "Financieel systeem", "technisch_beheer"),
        ("T. Klaassen", "Sociaal domein suite", "technisch_beheer"),
        ("T. Klaassen", "Burgerzaken-suite", "technisch_beheer"),
        # BvoWB functioneel beheer + product owner
        ("J. de Vries", "Zaaksysteem", "functioneel_beheer"),
        ("J. de Vries", "Zaakafhandelcomponent", "functioneel_beheer"),
        ("J. de Vries", "Gegevensmakelaar", "functioneel_beheer"),
        ("J. de Vries", "Zaaksysteem", "product_owner"),
        ("S. de Boer", "DMS", "functioneel_beheer"),
        ("S. de Boer", "Klantportaal", "functioneel_beheer"),
        ("S. de Boer", "Burgerzaken-suite", "functioneel_beheer"),
        ("S. de Boer", "DMS", "product_owner"),
        # Gemeente product owners op gedeelde apps
        ("A. Janssen", "Zaaksysteem", "product_owner"),
        ("A. Janssen", "DMS", "product_owner"),
        ("A. Janssen", "Klantportaal", "product_owner"),
        ("A. Janssen", "Burgerzaken-suite", "product_owner"),
        ("B. van Essen", "Zaaksysteem", "product_owner"),
        ("B. van Essen", "DMS", "product_owner"),
        ("B. van Essen", "Klantportaal", "product_owner"),
        ("D. Lammers", "Zaaksysteem", "product_owner"),
        ("D. Lammers", "Klantportaal", "product_owner"),
        ("D. Lammers", "Burgerzaken-suite", "product_owner"),
        # Gemeente-specifieke apps
        ("A. Janssen", "Vergunningensysteem", "product_owner"),
        ("A. Janssen", "Vergunningensysteem", "functioneel_beheer"),
        ("P. van Dijk", "Vergunningensysteem", "technisch_beheer"),
        ("B. van Essen", "HR-systeem", "product_owner"),
        ("B. van Essen", "HR-systeem", "functioneel_beheer"),
        ("T. Klaassen", "HR-systeem", "technisch_beheer"),
        ("D. Lammers", "Omgevingsloket", "product_owner"),
        ("D. Lammers", "Omgevingsloket", "functioneel_beheer"),
        ("P. van Dijk", "Omgevingsloket", "technisch_beheer"),
    ]
    rt_contract = [
        ("R. Visser", "Raamovereenkomst ICT BvoWB 2023–2028", "contractbeheer"),
        ("R. Visser", "Deelcontract Zaaksysteem 2023–2026", "contractbeheer"),
        ("R. Visser", "Deelcontract ZAC 2023–2026", "contractbeheer"),
        ("R. Visser", "SaaS DMS & Klantportaal 2024–2027", "contractbeheer"),
        ("R. Visser", "DataBridge koppelplatform 2024–2027", "contractbeheer"),
        ("M. Bakker", "Licentiecontract BRP 2022–2026", "contractbeheer"),
        ("M. Bakker", "FinSys onderhoudscontract 2024–2028", "contractbeheer"),
        ("M. Bakker", "SocioSuite SaaS 2023–2026", "contractbeheer"),
        ("M. Bakker", "Burgerzaken-suite licentie 2023–2026", "contractbeheer"),
        ("R. Visser", "DVO BvoWB – Gemeente Tiel", "contractbeheer"),
        ("R. Visser", "DVO BvoWB – Gemeente Culemborg", "contractbeheer"),
        ("R. Visser", "DVO BvoWB – Gemeente West Betuwe", "contractbeheer"),
        ("A. Janssen", "Vergunningensysteem contract 2023–2026", "contractbeheer"),
        ("B. van Essen", "HR-systeem contract 2024–2027", "contractbeheer"),
        ("D. Lammers", "Omgevingsloket contract 2023–2026", "contractbeheer"),
    ]
    # Leverancier Account Managers + Service Delivery Managers op contracten
    rt_extern = [
        ("L. Smeets", "Raamovereenkomst ICT BvoWB 2023–2028", "account_manager"),
        ("L. Smeets", "Deelcontract Zaaksysteem 2023–2026", "account_manager"),
        ("L. Smeets", "Deelcontract ZAC 2023–2026", "account_manager"),
        ("K. Peters", "Raamovereenkomst ICT BvoWB 2023–2028", "service_delivery_manager"),
        ("K. Peters", "Deelcontract Zaaksysteem 2023–2026", "service_delivery_manager"),
        ("K. Peters", "Deelcontract ZAC 2023–2026", "service_delivery_manager"),
        ("T. van den Berg", "SaaS DMS & Klantportaal 2024–2027", "account_manager"),
        ("F. Hendriks", "SaaS DMS & Klantportaal 2024–2027", "service_delivery_manager"),
        ("W. Jansen", "Licentiecontract BRP 2022–2026", "account_manager"),
        ("C. Mulder", "Licentiecontract BRP 2022–2026", "service_delivery_manager"),
        ("A. Dijkstra", "DataBridge koppelplatform 2024–2027", "account_manager"),
        ("I. van der Laan", "DataBridge koppelplatform 2024–2027", "service_delivery_manager"),
        ("B. Vermeer", "FinSys onderhoudscontract 2024–2028", "account_manager"),
        ("D. Koster", "FinSys onderhoudscontract 2024–2028", "service_delivery_manager"),
        ("E. van Leeuwen", "SocioSuite SaaS 2023–2026", "account_manager"),
        ("G. Bosman", "SocioSuite SaaS 2023–2026", "service_delivery_manager"),
        ("H. de Wit", "Burgerzaken-suite licentie 2023–2026", "account_manager"),
        ("N. Groothuis", "Burgerzaken-suite licentie 2023–2026", "service_delivery_manager"),
        ("O. Ploeg", "Vergunningensysteem contract 2023–2026", "account_manager"),
        ("V. Brouwer", "Vergunningensysteem contract 2023–2026", "service_delivery_manager"),
        ("Q. van Houten", "HR-systeem contract 2024–2027", "account_manager"),
        ("X. Pietersen", "HR-systeem contract 2024–2027", "service_delivery_manager"),
        ("Y. Hendriksen", "Omgevingsloket contract 2023–2026", "account_manager"),
        ("Z. van Beek", "Omgevingsloket contract 2023–2026", "service_delivery_manager"),
    ]
    for p, a, r in rt_comp:
        await _rol(p, app_id[a], r)
    for p, c, r in rt_contract:
        await _rol(p, contract_id[c], r)
    for p, c, r in rt_extern:
        await _rol(p, contract_id[c], r)

    # ── 13. Organisatiegebruik (grof feit, ADR-036) + gebruikersgroep-verfijning ──
    # Grof feit = "organisatie X gebruikt applicatie Y", op zichzelf vastlegbaar zonder afdeling.
    # De meeste org×app-combinaties blijven GROF (geen afdeling eronder) → voedt de latere signaal-
    # demo "detaillering ontbreekt" (pass 2). Idempotent op (org, app).
    bestaande_feiten = {
        (r.organisatie_id, r.applicatie_id)
        for r in (await session.execute(
            select(Organisatiegebruik.organisatie_id, Organisatiegebruik.applicatie_id)
            .where(Organisatiegebruik.tenant_id == tid))).all()
    }

    async def _feit(app_naam, org_naam):
        key = (partij_id[org_naam], app_id[app_naam])
        if key in bestaande_feiten:
            return
        await organisatiegebruik_service.ensure(session, tid, partij_id[org_naam], app_id[app_naam])
        bestaande_feiten.add(key)
        telling["organisatiegebruik"] += 1

    gg_orgs = ["BvoWB", "Gemeente Tiel", "Gemeente Culemborg", "Gemeente West Betuwe"]
    # LI021 — Klantportaal bewust NIET hier: het wordt uitsluitend door de organisatieloze
    # "Burgers"-groep geserved → laat de scope-teller "alleen organisatieloos gebruikt" aanslaan.
    org_apps = ["Zaaksysteem", "Zaakafhandelcomponent", "DMS", "Burgerzaken-suite",
                "BRP", "Gegevensmakelaar", "Sociaal domein suite"]
    for app_naam in org_apps:
        for org_naam in gg_orgs:
            await _feit(app_naam, org_naam)
    await session.commit()  # grove feiten borgen vóór de verfijningen (idempotent-veilig)

    # ADR-036a — afdelingen zijn structurele organisatie_eenheid-partijen ónder de gemeente.
    # Maak ze aan (idempotent via _partij) zodat de verfijningen ernaar kunnen verwijzen via afdeling_id.
    await _partij(PartijAard.organisatie_eenheid, "Burgerzaken", "afdelingen", organisatie_id=partij_id["Gemeente Tiel"])
    await _partij(PartijAard.organisatie_eenheid, "Publiekszaken", "afdelingen", organisatie_id=partij_id["Gemeente Culemborg"])
    await _partij(PartijAard.organisatie_eenheid, "Documentbeheer", "afdelingen", organisatie_id=partij_id["Gemeente West Betuwe"])

    # Verfijning = een afdeling MÉT organisatie ónder het grove feit (hergebruikt het feit via
    # gebruikersgroep_service; geen dubbele org-invoer). ADR-036a: afdeling = een org-eenheid-partij.
    # Idempotent op (app, org, afdeling_id).
    verfijning_rows = (
        await session.execute(
            select(Relatie.bron_id, Organisatiegebruik.organisatie_id, Gebruikersgroep.afdeling_id)
            .join(Gebruikersgroep, Gebruikersgroep.id == Relatie.doel_id)
            .outerjoin(Organisatiegebruik, Organisatiegebruik.id == Gebruikersgroep.gebruik_id)
            .where(Relatie.relatietype == "serving", Relatie.tenant_id == tid)
        )
    ).all()
    bestaande_gg = {(r.bron_id, r.organisatie_id, r.afdeling_id) for r in verfijning_rows}

    async def _gg(app_naam, org_naam, afdeling_naam, aantal):
        org_id = partij_id[org_naam] if org_naam else None
        afdeling_id = partij_id[afdeling_naam] if afdeling_naam else None
        key = (app_id[app_naam], org_id, afdeling_id)
        if key in bestaande_gg:
            return
        await gebruikersgroep_service.maak_aan(session, tid, GebruikersgroepCreate(
            applicatie_id=app_id[app_naam], organisatie_id=org_id, afdeling_id=afdeling_id, aantal_gebruikers=aantal))
        bestaande_gg.add(key)
        telling["gebruikersgroepen"] += 1

    # Fijne verfijningen (afdeling-partij + organisatie) onder bestaande grove feiten.
    await _gg("Zaaksysteem", "Gemeente Tiel", "Burgerzaken", 40)
    await _gg("Zaaksysteem", "Gemeente Culemborg", "Publiekszaken", 25)
    await _gg("DMS", "Gemeente West Betuwe", "Documentbeheer", 15)

    # ── 13b. Burger-doelgroepen (ADR-038): externe organisaties met segment-afdelingen. ──
    # Per gemeente een burger-organisatie (aard=organisatie + scope=extern), met een paar
    # segment-afdelingen, gekoppeld aan de burgergerichte applicaties (voorheen "organisatieloos").
    burger_orgs = ["Burgers Tiel", "Burgers West Betuwe", "Burgers Culemborg"]
    for naam in burger_orgs:
        await _partij(PartijAard.organisatie, naam, "burgers", scope=PartijScope.extern,
                      omschrijving="Inwoners/doelgroep — externe organisatie (ADR-038)")
    burger_afdelingen = [
        ("Burgers Tiel", "Agrariërs"), ("Burgers Tiel", "Woningbezitters"),
        ("Burgers West Betuwe", "Agrariërs"), ("Burgers West Betuwe", "Ondernemers"),
        ("Burgers Culemborg", "Woningbezitters"), ("Burgers Culemborg", "Studenten"),
    ]
    for org_naam, seg in burger_afdelingen:
        await _partij(PartijAard.organisatie_eenheid, f"{org_naam} — {seg}", "afdelingen",
                      organisatie_id=partij_id[org_naam])
    # Koppel de burger-segmenten als gebruikersgroepen aan hun applicaties (grof feit via _gg/ensure).
    for app_naam, org_naam, seg, aantal in [
        ("Klantportaal", "Burgers Tiel", "Agrariërs", 12000),
        ("Klantportaal", "Burgers Tiel", "Woningbezitters", 23000),
        ("Burgerzaken-suite", "Burgers West Betuwe", "Agrariërs", 8000),
        ("Klantportaal", "Burgers Culemborg", "Woningbezitters", 15000),
        ("Zaaksysteem", "Burgers Culemborg", "Studenten", 4000),
    ]:
        await _gg(app_naam, org_naam, f"{org_naam} — {seg}", aantal)

    # ── 14. Infrastructuur (technology-laag) + component-samenstelling (LI021, context) ──
    # KALE componenten (Element + Component, géén subtype/scoring/profiel) → engine onaangeroerd.
    # Idempotent op naam resp. (bron, doel)-relatiepaar. Geen schema/migratie (bestaande typen/relaties).
    comp_naam_id = {c.naam: c.id for c in (await session.execute(select(Component))).scalars().all()}

    async def _infra(naam, type_, host, eigenaar):
        if naam in comp_naam_id:
            return comp_naam_id[naam]
        elem = Element(tenant_id=tid, element_type=ElementType.component); session.add(elem); await session.flush()
        session.add(Component(id=elem.id, tenant_id=tid, naam=naam, componenttype=type_,
                              hostingmodel=host, eigenaar_organisatie_id=eigenaar)); await session.flush()
        comp_naam_id[naam] = elem.id
        print(f"  + infra {naam} ({type_})")
        return elem.id

    bestaande_assignment = {
        (r.bron_id, r.doel_id) for r in (await session.execute(
            select(Relatie).where(Relatie.relatietype == "assignment", Relatie.tenant_id == tid)
        )).scalars().all()
    }

    async def _draait_op(host_id, app_naam):
        doel = app_id[app_naam]
        if (host_id, doel) in bestaande_assignment:
            return
        # ADR-023: draait_op → assignment, oriëntatie host→gehoste (bron=host, doel=app).
        await relatie_service.maak_aan(session, tid, RelatieCreate(
            bron_id=host_id, doel_id=doel, relatietype="assignment"))
        bestaande_assignment.add((host_id, doel))

    # Gedeelde database-server onder de zwaarste shared-apps: één onderlaag, meerdere gemeenten geraakt.
    db_id = await _infra("Shared DB-server", "database", HostingModel.on_premise, partij_id["BvoWB"])
    for app_naam in ("Zaaksysteem", "BRP", "DMS"):
        await _draait_op(db_id, app_naam)
    # Gedeelde fileshare onder de documentgerichte apps — BEWUST zonder eigenaar (gedeelde infra-omissie).
    fs_id = await _infra("Shared fileshare", "fileshare", HostingModel.on_premise, None)
    for app_naam in ("DMS", "Klantportaal"):
        await _draait_op(fs_id, app_naam)
    # Extern SaaS-platform onder een gemeente-specifieke app (andere impactsmaak: extern gehost).
    saas_id = await _infra("Extern SaaS-platform", "saas_dienst", HostingModel.saas, None)
    await _draait_op(saas_id, "Vergunningensysteem")

    # Samenstelling: Burgerzaken-suite = geheel; drie onderdelen "onderdeel van" (aggregation geheel→deel).
    # Onderdelen = applicatie MÉT eigenaar=BvoWB, kaal (geen start_inventarisatie) → geen gap-vervuiling.
    bestaande_aggr = {
        (r.bron_id, r.doel_id) for r in (await session.execute(
            select(Relatie).where(Relatie.relatietype == "aggregation", Relatie.tenant_id == tid)
        )).scalars().all()
    }
    for deel_naam in ("Aangiften", "Reisdocumenten", "Verkiezingen"):
        if deel_naam not in app_id:
            obj = await component_service.maak_aan(session, tid, ComponentCreate(
                componenttype="applicatie", naam=deel_naam, beschrijving=f"Onderdeel van de Burgerzaken-suite — {deel_naam}",
                hostingmodel="on_premise", eigenaar_organisatie_id=partij_id["BvoWB"], **APP_DEFAULTS))
            app_id[deel_naam] = obj["id"]
            telling["applicaties"] += 1
        paar = (app_id["Burgerzaken-suite"], app_id[deel_naam])
        if paar not in bestaande_aggr:
            await relatie_service.maak_aan(session, tid, RelatieCreate(
                bron_id=paar[0], doel_id=paar[1], relatietype="aggregation"))
            bestaande_aggr.add(paar)

    # ── ADR-037 — verantwoordelijke per checklistantwoord (afdeling-dan-persoon), demonstratief ──
    # Maakt de UX zichtbaar: één blokkerend antwoord mét PERSOON-verantwoordelijke (de bijbehorende
    # OPEN blokkade toont die afgeleid, "persoon — afdeling"), één niet-blokkerend antwoord met een
    # AFDELING, één met een PERSOON, en ALLE overige antwoorden BEWUST LEEG (voedt het Pass 2-signaal
    # `antwoord_zonder_verantwoordelijke`).
    # LI037-fix — doelrijen op VASTE IDENTITEIT (component + vraagcode) i.p.v. "de eerstvolgende
    # lege rij op created_at": dat criterium schoof elke run op en liet de bewust-lege rijen per
    # reseed met 2 dichtslibben. Zaaksysteem 1.1 is per scenario-constructie hét blokkerende
    # antwoord (blokkeer=1 → CODES[0]='1.1' scoort 'nee'); 1.2/1.3 zijn niet-blokkerend ('ja').
    # Vul-als-leeg op die identiteit: een al (handmatig) gezette waarde wordt nooit overschreven
    # en run 2 vindt de drie gevuld en doet niets → écht idempotent (run-stabiel op identiteit).
    # Registratief: `werk_bij` stuurt géén score mee → engine no-op.
    pers_id = partij_id.get("J. de Vries")           # persoon; draagt afdeling "Informatievoorziening"
    afd_id = partij_id.get("Informatievoorziening")  # afdeling (organisatie_eenheid)
    zaak_id = app_id.get("Zaaksysteem")
    if pers_id and afd_id and zaak_id:
        doelen = [
            ("1.1", pers_id),  # blokkerend antwoord → PERSOON (blokkade toont "persoon — afdeling")
            ("1.2", afd_id),   # niet-blokkerend → AFDELING
            ("1.3", pers_id),  # niet-blokkerend → PERSOON
        ]
        gevuld = 0
        for code, verantw_id in doelen:
            rij = (await session.execute(
                select(Checklistscore)
                .join(ChecklistVraag, ChecklistVraag.id == Checklistscore.checklistvraag_id)
                .where(
                    Checklistscore.tenant_id == tid,
                    Checklistscore.component_id == zaak_id,
                    ChecklistVraag.code == code,
                )
            )).scalars().first()
            if rij is None or rij.verantwoordelijke_id is not None:
                continue  # rij ontbreekt (afwijkende seed-stand) of al gezet → idempotent overslaan
            await checklistscore_service.werk_bij(
                session, tid, rij.id, ChecklistscoreUpdate(verantwoordelijke_id=verantw_id)
            )
            gevuld += 1
        await session.commit()
        telling["verantwoordelijken"] = gevuld  # run 1: 3 · run 2: 0 (het idempotentie-bewijs)

    # ── 15. Processen + procesvervullingen (ADR-042; verdiept LI037 fase 0) ──
    # Twee herkenbare procesboompjes (Vergunningverlening → Aanvraag behandelen;
    # Burgerzaken → Verhuizing verwerken) + koppelregels op bestaande componenten met de
    # GEMMA-startset-functies. Bewust: (a) één koppelregel op een NIET-applicatie
    # ("Shared DB-server", componenttype database — bewijst component-breed), (b) één
    # component met TWEE functies in hetzelfde proces (Zaaksysteem in "Aanvraag behandelen"
    # — bewijst losse, apart verwijderbare regels), (c) LI037: één boom van DRIE niveaus
    # (Vergunningverlening → Aanvraag behandelen → processtap "Besluit vastleggen") mét
    # vervulling op dat derde niveau (diepte = rijhoogte is browserverifieerbaar, ADR-034),
    # en (d) LI037: één deelproces BEWUST zonder ondersteunend systeem ("Bezwaar
    # behandelen" — de "geen ondersteunend systeem"-cue moet ergens te zien zijn).
    # Idempotent: skip-op-naam (proces) resp. skip-op-tripel (vervulling).
    from models.models import Proces as _Proces
    from schemas.proces import ProcesCreate

    proces_id_map = {r.naam: r.id for r in (await session.execute(select(_Proces))).scalars().all()}

    async def _proces(naam, ouder_naam=None, toelichting=None):
        if naam in proces_id_map:
            return proces_id_map[naam]
        obj = await proces_service.maak_aan(session, tid, ProcesCreate(
            naam=naam, toelichting=toelichting,
            ouder_id=proces_id_map[ouder_naam] if ouder_naam else None,
        ))
        proces_id_map[naam] = obj["id"]
        telling["processen"] += 1
        return obj["id"]

    await _proces("Vergunningverlening", toelichting="Bedrijfsproces: vergunningaanvragen van intake tot besluit.")
    await _proces("Aanvraag behandelen", "Vergunningverlening", "Werkproces: beoordelen en besluiten op een vergunningaanvraag.")
    # LI037 (c) — derde niveau: processtap onder het werkproces (de plek in de boom ís het niveau).
    await _proces("Besluit vastleggen", "Aanvraag behandelen", "Processtap: het besluit formeel vastleggen en bekendmaken.")
    # LI037 (d) — bewust ONDERSTEUNINGSLOOS deelproces (géén procesvervulling seeden; toont de
    # "geen ondersteunend systeem"-cue op de kaart).
    await _proces("Bezwaar behandelen", "Vergunningverlening", "Werkproces: behandelen van bezwaren tegen een vergunningbesluit.")
    await _proces("Burgerzaken", toelichting="Bedrijfsproces: burgerzaken-dienstverlening (BRP-gebonden).")
    await _proces("Verhuizing verwerken", "Burgerzaken", "Werkproces: verwerken van een binnengemeentelijke verhuizing.")

    # Component-lookup over ALLE typen (app_id bevat alleen applicaties; de DB-server niet).
    comp_id_map = {c.naam: c.id for c in (await session.execute(select(Component))).scalars().all()}
    vervullingen = [
        # (component-naam, proces-naam, applicatiefunctie, toelichting)
        ("Zaaksysteem", "Aanvraag behandelen", "registreren", "Zaakdossier van de aanvraag."),
        ("Zaaksysteem", "Aanvraag behandelen", "raadplegen", None),  # tweede functie, zelfde paar
        ("DMS", "Aanvraag behandelen", "archiveren", "Besluitdocumenten archiveren."),
        # LI037 (c) — vervulling op PROCESSTAP-niveau (niveau 3): het formele besluit wordt in
        # het DMS geregistreerd. ("Bezwaar behandelen" krijgt bewust géén regel — LI037 (d).)
        ("DMS", "Besluit vastleggen", "registreren", "Formele vastlegging van het besluit."),
        ("Vergunningensysteem", "Vergunningverlening", "ondersteunen", "Vakapplicatie vergunningproces (grof niveau)."),
        ("Burgerzaken-suite", "Verhuizing verwerken", "registreren", None),
        ("BRP", "Verhuizing verwerken", "gegevens_leveren", "Persoonsgegevens bij verhuizing."),
        # Component-breed: een niet-applicatie (database) vervult een rol in een proces.
        ("Shared DB-server", "Vergunningverlening", "ondersteunen", "Databaseplatform onder het zaak-/vergunningdomein."),
    ]
    for comp_naam, proces_naam, functie, toel in vervullingen:
        comp_id = comp_id_map.get(comp_naam)
        if comp_id is None:
            continue  # component niet in deze seed-stand — geen harde afhankelijkheid
        try:
            await procesvervulling_service.maak_aan(
                session, tid, comp_id, proces_id_map[proces_naam], functie, toel
            )
            telling["procesvervullingen"] += 1
        except RegistratieConflict:
            pass  # idempotent: het tripel bestaat al

    # ── 16. Bedrijfsfunctie-as (ADR-043 gate 1a) ──
    # Eén ingelezen referentiemodel-instantie (GEMMA) + een kleine GEMMA-achtige
    # functieboom: de drie topgroeperingen als gewone wortels (besluit LI039-4), per
    # wortel een paar functies en één niveau daaronder. Model-functies dragen een
    # bronsleutel (identiteit — idempotent get-or-create op sleutel, LI037-les: vaste
    # identiteit, nooit "de eerstvolgende rij"); één functie is bewust VERVALLEN
    # (markering zichtbaar, niet koppelbaar) en één functie is EIGEN (geen bronsleutel
    # → in de browser bewerkbaar, het verschil met read-only modelinhoud).
    from models.models import Bedrijfsfunctie as _Bfunc
    from models.models import Referentiemodel as _Refmodel
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate

    refmodel = (await session.execute(
        select(_Refmodel).where(_Refmodel.model_sleutel == "gemma_bedrijfsfuncties")
    )).scalar_one_or_none()
    if refmodel is None:
        refmodel = _Refmodel(
            tenant_id=tid, model_sleutel="gemma_bedrijfsfuncties",
            naam="GEMMA Bedrijfsfuncties", versie="GEMMA 2 (2025)",
        )
        session.add(refmodel)
        await session.commit()
        await session.refresh(refmodel)
        telling["referentiemodellen"] += 1

    bf_per_sleutel = {
        r.bron_sleutel: r
        for r in (await session.execute(
            select(_Bfunc).where(_Bfunc.bron_model_id == refmodel.id)
        )).scalars().all()
    }

    async def _modelfunctie(sleutel, naam, definitie, ouder_sleutel=None, vervallen=False):
        """Get-or-create op de bronsleutel (de identiteit — nooit op naam)."""
        bestaand = bf_per_sleutel.get(sleutel)
        if bestaand is not None:
            return bestaand.id
        ouder_id = bf_per_sleutel[ouder_sleutel].id if ouder_sleutel else None
        obj = await bedrijfsfunctie_service.maak_aan(
            session, tid, BedrijfsfunctieCreate(naam=naam, definitie=definitie, ouder_id=ouder_id),
            bron_model_id=refmodel.id, bron_sleutel=sleutel,
        )
        rij = await bedrijfsfunctie_service.haal_op(session, tid, obj["id"])
        if vervallen:
            # Het gate-1b-herinlees-pad markeert vervallen; de seed zet de vlag direct
            # (ORM-update → audit-gedekt) zodat de markering in de browser te zien is.
            rij.vervallen = True
            await session.commit()
            await session.refresh(rij)
        bf_per_sleutel[sleutel] = rij
        telling["bedrijfsfuncties"] += 1
        return rij.id

    # Wortels = de drie topgroeperingen (gewone wortelknopen, geen apart begrip).
    await _modelfunctie("besturend", "Besturend",
                        "Richting geven aan de organisatie: strategie, beleid en verantwoording.")
    await _modelfunctie("primair", "Primair",
                        "De kernactiviteiten waarvoor de gemeente bestaat: dienstverlening aan burgers en bedrijven.")
    await _modelfunctie("ondersteunend", "Ondersteunend",
                        "Alles wat de primaire functies mogelijk maakt: bedrijfsvoering en informatievoorziening.")
    # Besturend — twee functies + één verdieping.
    await _modelfunctie("strategie_beleid", "Strategie en beleid",
                        "Ontwikkelen en vaststellen van strategie en beleid.", "besturend")
    await _modelfunctie("sturing_verantwoording", "Sturing en verantwoording",
                        "Sturen op resultaat en verantwoorden over de uitvoering.", "besturend")
    await _modelfunctie("beleidsontwikkeling", "Beleidsontwikkeling",
                        "Vertalen van maatschappelijke opgaven naar concreet beleid.", "strategie_beleid")
    # Primair — twee functies + verdieping.
    await _modelfunctie("dienstverlening", "Dienstverlening",
                        "Leveren van producten en diensten aan burgers en bedrijven.", "primair")
    await _modelfunctie("vergunning_handhaving", "Vergunningverlening en handhaving",
                        "Beoordelen van aanvragen, verlenen van vergunningen en toezien op naleving.", "primair")
    await _modelfunctie("klantcontact", "Klantcontact",
                        "Afhandelen van vragen en contacten via alle kanalen.", "dienstverlening")
    await _modelfunctie("burgerzaken_f", "Burgerzaken",
                        "Registreren van en informeren over persoonsgegevens en levensgebeurtenissen.", "dienstverlening")
    # Ondersteunend — twee functies + verdieping.
    await _modelfunctie("informatievoorziening", "Informatievoorziening",
                        "Beschikbaar stellen en beheren van informatie en informatiesystemen.", "ondersteunend")
    await _modelfunctie("bedrijfsvoering", "Bedrijfsvoering",
                        "Ondersteunende processen: financiën, personeel, facilitair.", "ondersteunend")
    await _modelfunctie("financien", "Financiën",
                        "Begroten, betalen, innen en verantwoorden van geldstromen.", "bedrijfsvoering")
    await _modelfunctie("hrm", "HRM",
                        "Werven, ontwikkelen en beheren van personeel.", "bedrijfsvoering")
    # LI039-6-demo — vervallen model-functie: zichtbaar mét markering, niet koppelbaar.
    await _modelfunctie("regionale_samenwerking", "Regionale samenwerking",
                        "Vervallen in de nieuwe modelversie — bestaande registratie blijft zichtbaar.",
                        "besturend", vervallen=True)

    # EIGEN functie (geen bronsleutel — een herinlees raakt haar nooit aan); idempotent
    # skip-op-naam binnen de eigen (bronloze) functies.
    eigen_bestaat = (await session.execute(
        select(_Bfunc).where(
            _Bfunc.bron_sleutel.is_(None), _Bfunc.naam == "Datagedreven werken"
        )
    )).scalar_one_or_none()
    if eigen_bestaat is None:
        await bedrijfsfunctie_service.maak_aan(
            session, tid, BedrijfsfunctieCreate(
                naam="Datagedreven werken",
                definitie="Eigen functie van de gemeente (staat niet in het referentiemodel).",
                ouder_id=bf_per_sleutel["informatievoorziening"].id,
            ),
        )
        telling["bedrijfsfuncties"] += 1

    return telling


async def _seed_dev_gebruikers(session, tenant_id) -> dict:
    """ADR-029 — koppel 3 dev-loginaccounts (Keycloak) aan hun persoon in het register.
    De `keycloak_sub`'s zijn de VASTE Keycloak user-id's uit `likara-realm.json`
    (hardcoded — robuust, geen runtime-KC-afhankelijkheid in de seed). Idempotent op sub."""
    tid = tenant_id
    koppelingen = [
        ("aaaaaaaa-0001-0001-0001-000000000001", "J. de Vries"),
        ("aaaaaaaa-0001-0001-0001-000000000002", "P. van Dijk"),
        ("aaaaaaaa-0001-0001-0001-000000000003", "M. Bakker"),
    ]
    persoon_id = {
        r.naam: r.id
        for r in (
            await session.execute(select(Partij).where(Partij.aard == PartijAard.persoon))
        ).scalars().all()
    }
    bestaande = {
        r.keycloak_sub for r in (await session.execute(select(GebruikerPersoon))).scalars().all()
    }
    aangemaakt = 0
    for sub, naam in koppelingen:
        if sub in bestaande:
            continue
        pid = persoon_id.get(naam)
        if pid is None:
            print(f"  ! persoon '{naam}' niet gevonden — koppeling overgeslagen")
            continue
        session.add(GebruikerPersoon(tenant_id=tid, keycloak_sub=sub, persoon_id=pid))
        aangemaakt += 1
    await session.commit()
    return {"gebruiker_persoon": aangemaakt}


async def main() -> None:
    print(f"dev-seed: tenant {DEV_TENANT}")
    # ADR-006: vaste systeem-actor voor het audit-spoor van de dev-seed.
    async with get_worker_session(DEV_TENANT, actor_sub="system:dev_seed") as session:
        # ADR-022 W1: de vragenset is tenant-eigendom — kopieer de baseline (89 vragen
        # + antwoordconfig) in de dev-tenant als lk_app onder RLS, vóór applicaties/scores.
        await seed_checklist_vragen(session, DEV_TENANT)
        await seed_antwoordconfig(session, DEV_TENANT)
        print("  + baseline-vragenset (89) + antwoordconfig geseed voor de tenant")

        # code ↔ checklistvraag.id-map (applicatie-type) voor het scoringsplan.
        for code, vid in (
            await session.execute(
                select(ChecklistVraag.code, ChecklistVraag.id).where(
                    ChecklistVraag.componenttype == "applicatie"
                )
            )
        ).all():
            _CODE_TO_ID[code] = vid
            _ID_TO_CODE[vid] = code

        print("BvoWB shared-services ICT-landschap:")
        t = await _seed_bvowb_scenario(session, DEV_TENANT)
        print("  " + " · ".join(f"{k}={v}" for k, v in t.items()))

        # LI058 — de infra-seed (`_infra`) maakt database-componenten via directe ORM (geen
        # profiel). Geef beoordeelde niet-app-typen hun profiel + herberekening via de backfill
        # (zelfde mechaniek als de platform-toggle) zodat ze end-to-end scoren.
        from services import checklistconfig_service as _ccs
        n_bf = await _ccs.backfill_profielen(session, DEV_TENANT, "database")
        await session.commit()
        print(f"  + database-scoring-backfill: {n_bf} profiel(en)")

        print("Dev-gebruikers (gebruiker_persoon-koppelingen):")
        g = await _seed_dev_gebruikers(session, DEV_TENANT)
        print(f"  {g}")
    print("dev-seed: klaar")


if __name__ == "__main__":
    asyncio.run(main())
