"""DEV-ONLY testdata-seed — BWB-ontvlechting (V005, CD-Testdata-seed).

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

Draaien (binnen de draaiende stack, als cd_app onder RLS):

    docker compose exec cd-api python3 dev_seed_testdata.py

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

from app.core.database import get_worker_session  # noqa: E402
from models.models import (  # noqa: E402
    AntwoordType,
    Applicatie,
    Blokkade,
    BlokkadeStatus,
    ChecklistScore,
    ChecklistVraag,
    ChecklistVraagOptie,
    Checklistscore,
    Component,
    ComponentContract,
    ComponentStructuur,
    Contract,
    HostingModel,
    Koppeling,
    Leverancier,
)
from schemas.applicatie import ApplicatieCreate  # noqa: E402
from schemas.applicatie_contract import ApplicatieContractCreate  # noqa: E402
from schemas.blokkade import BlokkadeUpdate  # noqa: E402
from schemas.checklistscore import ChecklistscoreCreate, ChecklistscoreUpdate  # noqa: E402
from schemas.contract import ContractCreate  # noqa: E402
from schemas.koppeling import KoppelingCreate  # noqa: E402
from schemas.leverancier import LeverancierCreate  # noqa: E402
from services import (  # noqa: E402
    applicatie_contract_service,
    applicatie_service,
    blokkade_service,
    checklistscore_service,
    contract_service,
    koppeling_service,
    leverancier_service,
)
from services.seed import CHECKLIST_VRAGEN  # noqa: E402

# Bestaande dev-tenant (hoofdopdracht §2) — geen nieuwe tenant.
DEV_TENANT = "11111111-1111-1111-1111-111111111111"

# Vaste code-volgorde van de 89 vragen (deterministisch scoren).
CODES = [v["code"] for v in CHECKLIST_VRAGEN]

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
LEVERANCIERS_D = [
    {"naam": "GemSoft B.V.", "straat_huisnummer": "Softwareplein 12", "postcode": "3811 AB",
     "plaats": "Amersfoort", "contactpersoon": "Account Management",
     "telefoon": "033-1234567", "mobiel": "06-12345678", "email": "contact@gemsoft.example"},
    {"naam": "CivData Solutions", "straat_huisnummer": "Dataweg 8", "postcode": "3542 AD",
     "plaats": "Utrecht", "contactpersoon": "Servicedesk",
     "telefoon": "030-7654321", "mobiel": "06-87654321", "email": "info@civdata.example"},
    # Minimaal: alleen plaats + email.
    {"naam": "InfraHost Nederland", "plaats": "Rotterdam", "email": "support@infrahost.example"},
    # Minimaal: alleen contactpersoon + telefoon.
    {"naam": "GeoWorks B.V.", "contactpersoon": "Verkoop binnendienst", "telefoon": "020-5556677"},
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

    obj = await applicatie_service.maak_aan(
        session, DEV_TENANT,
        ApplicatieCreate(
            naam=naam, beschrijving=app["beschrijving"], hostingmodel=app["host"],
            eigenaar_organisatie=app["org"], eigenaar_naam=None, leverancier=None,
            **APP_DEFAULTS,
        ),
    )
    app_id = obj.id

    # e-Depot blijft `concept`: niet starten, niet scoren.
    if app["scored"] == 0 and not app["post"]:
        print(f"  + {naam}: aangemaakt (concept, 0/89)")
        return app_id

    # Verlaat de `concept`-vloer via de legitieme handmatige start (ADR-013):
    # herbereken vanuit `concept` blijft anders `concept`.
    await applicatie_service.start_inventarisatie(session, DEV_TENANT, app_id)

    for i in range(app["scored"]):
        await checklistscore_service.maak_aan(
            session, DEV_TENANT,
            ChecklistscoreCreate(
                applicatie_id=app_id, vraag_code=CODES[i],
                score=_score_voor(i, app["blokkeer"]),
            ),
        )

    # Nabewerkingen — uitsluitend via de legitieme paden.
    for stap in app["post"]:
        code = CODES[stap["pos"]]
        score_obj = (
            await session.execute(
                select(Checklistscore).where(
                    Checklistscore.applicatie_id == app_id,
                    Checklistscore.vraag_code == code,
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
    """Maak de 10 koppelingen. Idempotent op (bron, doel)."""
    bestaande = {
        (r.bron_applicatie_id, r.doel_applicatie_id)
        for r in (await session.execute(select(Koppeling))).scalars().all()
    }
    for bron_idx, doel_idx, omschrijving, protocol in KOPPELINGEN:
        bron_id = app_ids[bron_idx]
        doel_id = app_ids[doel_idx]
        if (bron_id, doel_id) in bestaande:
            print(f"  = koppeling {bron_idx}→{doel_idx}: bestaat al — overgeslagen")
            continue
        await koppeling_service.maak_aan(
            session, DEV_TENANT,
            KoppelingCreate(
                bron_applicatie_id=bron_id, doel_applicatie_id=doel_id,
                protocol=protocol, omschrijving=omschrijving, **KOP_DEFAULTS,
            ),
        )
        print(f"  + koppeling {bron_idx}→{doel_idx}: {omschrijving}")


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
    code = score_obj.vraag_code
    velden = {
        "bevinding": BEVINDING_PER_CODE.get(
            code, f"De bevinding voor checklistvraag {code} is vastgelegd."
        ),
        "eigenaar": eigenaar,
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
            select(Checklistscore).where(Checklistscore.applicatie_id == app_id)
        )
    ).scalars().all()
    if not scores:
        return 0

    blok_score_ids = {
        sid for (sid,) in (
            await session.execute(
                select(Blokkade.checklistscore_id).where(Blokkade.applicatie_id == app_id)
            )
        ).all()
    }
    op_code = sorted(scores, key=lambda s: _code_key(s.vraag_code))
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
    for code, sleutel in (
        await session.execute(
            select(ChecklistVraagOptie.vraag_code, ChecklistVraagOptie.optie_sleutel)
            .where(ChecklistVraagOptie.actief.is_(True))
            .order_by(ChecklistVraagOptie.vraag_code, ChecklistVraagOptie.volgorde)
        )
    ).all():
        opties_per_code.setdefault(code, []).append(sleutel)
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
            select(Checklistscore).where(Checklistscore.applicatie_id == app_id)
        )
    ).scalars().all()

    gevuld = 0
    for s in scores:
        if s.vraag_code not in typed or s.antwoord_waarde:
            continue
        waarde = _kies_antwoord(
            typed[s.vraag_code], s.vraag_code, app_nr, host, opties_per_code.get(s.vraag_code, [])
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
    # --- Leveranciers (idempotent op naam) ---
    lev_ids = {
        r.naam: r.id for r in (await session.execute(select(Leverancier))).scalars().all()
    }
    for lev in LEVERANCIERS_D:
        if lev["naam"] in lev_ids:
            print(f"  = leverancier {lev['naam']}: bestaat al — overgeslagen")
            continue
        obj = await leverancier_service.maak_aan(session, DEV_TENANT, LeverancierCreate(**lev))
        lev_ids[lev["naam"]] = obj.id
        print(f"  + leverancier {lev['naam']}")

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
        (r.component_id, r.contract_id)  # shared-PK: component_id == applicatie_id
        for r in (await session.execute(select(ComponentContract))).scalars().all()
    }
    for app_idx, contractnaam, rol in KOPPELINGEN_D:
        app_id = app_ids[app_idx]
        contract_id = con_ids[contractnaam]
        if (app_id, contract_id) in bestaande_kop:
            print(f"  = koppeling app{app_idx}→{contractnaam}: bestaat al — overgeslagen")
            continue
        await applicatie_contract_service.maak_aan(
            session, DEV_TENANT,
            ApplicatieContractCreate(applicatie_id=app_id, contract_id=contract_id, relatie_rol=rol),
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
        c = Component(tenant_id=tid, naam=naam, componenttype=type_, hostingmodel=host,
                      eigenaar_organisatie=org)
        session.add(c)
        await session.flush()
        comps[naam] = c.id
        print(f"  + component {naam} ({type_})")
        return c.id

    db_id = await _ensure("Oracle FIN-DB", "database", HostingModel.on_premise, "Financiën")
    fs_id = await _ensure("Geo-fileshare", "fileshare", HostingModel.on_premise, "Ruimte")

    bestaand = {
        (r.component_id, r.op_component_id, r.relatietype)
        for r in (await session.execute(select(ComponentStructuur))).scalars().all()
    }
    relaties = [
        (app_ids[6], db_id, "draait_op"),   # Belastingsysteem → Oracle FIN-DB (gedeeld)
        (app_ids[7], db_id, "draait_op"),   # Financieel → Oracle FIN-DB (gedeeld)
        (app_ids[9], fs_id, "draait_op"),   # GIS-viewer → Geo-fileshare
    ]
    for comp_id, op_id, rel in relaties:
        if (comp_id, op_id, rel) in bestaand:
            continue
        session.add(ComponentStructuur(
            tenant_id=tid, component_id=comp_id, op_component_id=op_id, relatietype=rel
        ))
        print(f"  + structuur: {rel} op {op_id}")
    await session.commit()
    return {"componenten_extra": 2, "structuurrelaties": len(relaties)}


async def main() -> None:
    print(f"dev-seed: tenant {DEV_TENANT}")
    async with get_worker_session(DEV_TENANT) as session:
        # Bestaande applicaties (idempotentie): naam → id binnen de tenant.
        bestaande = {
            r.naam: r.id
            for r in (await session.execute(select(Applicatie))).scalars().all()
        }
        app_ids: dict[int, object] = {}
        print("applicaties:")
        for nr, app in enumerate(APPS, start=1):
            app_ids[nr] = await _seed_applicatie(session, app, bestaande)

        print("koppelingen:")
        await _seed_koppelingen(session, app_ids)

        print("checklist-velden (bevinding/eigenaar/actie):")
        totaal = 0
        for nr in sorted(app_ids):
            totaal += await _seed_velden(session, nr, app_ids[nr])
        print(f"  velden gevuld op {totaal} rij(en)")

        print("antwoord_waarde (ADR-019):")
        typed, opties_per_code = await _laad_catalogus(session)
        totaal = 0
        for nr in sorted(app_ids):
            host = APPS[nr - 1]["host"]
            totaal += await _seed_antwoord_waarden(
                session, nr, host, app_ids[nr], typed, opties_per_code
            )
        print(f"  antwoord_waarde gevuld op {totaal} rij(en)")

        print("Aanvulling D — contractlandschap (leveranciers/contracten/koppelingen):")
        telling = await _seed_aanvulling_d(session, app_ids)
        print(f"  leveranciers={telling['leveranciers']} contracten={telling['contracten']}")

        print("Aanvulling E — technische laag (componenten + structuurrelaties):")
        tl = await _seed_technische_laag(session, app_ids)
        print(f"  extra componenten={tl['componenten_extra']} structuurrelaties={tl['structuurrelaties']}")
    print("dev-seed: klaar")


if __name__ == "__main__":
    asyncio.run(main())
