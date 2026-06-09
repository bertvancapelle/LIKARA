"""Module-domeinexcepties + HTTP-handlers (P5).

Worden in de service-laag gegooid en in `backend/app/main.py` op handlers
gemapt naar het canonieke foutformaat `{"fout":{"code","http_status","bericht"}}`
— exact analoog aan `OnvoldoendeRechten` (middleware/authz): exceptie én handler
in één bestand, registratie in `main.py`.

Pinning (besluit Bert):
- `NietGevonden`            → HTTP 404, code `NIET_GEVONDEN`
- `OngeldigeStatusovergang` → HTTP 409, code `ONGELDIGE_STATUSOVERGANG`
- `KoppelingConflict`       → HTTP 409, code `KOPPELING_CONFLICT`
- `ChecklistscoreConflict`  → HTTP 409, code `CHECKLISTSCORE_BESTAAT_AL`
"""
from starlette.requests import Request
from starlette.responses import JSONResponse


class NietGevonden(Exception):
    """Record bestaat niet binnen de tenant-scope (OP-6: ander-tenant ⇒ 404).

    Maakt bewust GEEN onderscheid tussen 'bestaat niet' en 'andere tenant':
    beide leveren 404, zodat het bestaan van vreemde records niet lekt.
    """

    def __init__(self, entiteit: str, identifier=None):
        self.entiteit = entiteit
        self.identifier = identifier
        super().__init__(f"{entiteit} niet gevonden")


class OngeldigeStatusovergang(Exception):
    """Een lifecycle-overgang die vanuit de huidige status niet is toegestaan."""

    def __init__(self, van, naar):
        self.van = van
        self.naar = naar
        super().__init__(f"ongeldige statusovergang: {van} -> {naar}")


class KoppelingConflict(Exception):
    """DB-integriteitsbackstop voor Koppeling (CHECK `bron <> doel`).

    De primaire `bron == doel`-validatie zit op schema-niveau (FastAPI-422);
    deze exceptie vangt het onwaarschijnlijke geval dat een integriteitsregel
    pas in de DB afketst, zodat er nooit een rauwe DB-melding lekt.
    """


class ChecklistscoreConflict(Exception):
    """Dubbele Checklistscore voor (tenant, applicatie, vraag_code).

    Up-front gedetecteerd; de unieke index `uq_checklistscore_app_vraag` is de
    backstop (`IntegrityError` → rollback → deze exceptie).
    """


class OngeldigAntwoord(Exception):
    """Semantisch ongeldig `antwoord_waarde` (ADR-019): het type past niet bij de
    vraag, of de optiesleutel bestaat niet / is niet actief.

    HTTP **422** (validatie), maar via het canonieke envelope i.p.v. native
    FastAPI: deze check vereist de optie-catalogus uit de DB en kan dus niet in
    een Pydantic-validator (die structureel/DB-vrij blijft, ADR-014). Raakt de
    score-/lifecycle-/blokkade-engine niet.
    """

    def __init__(self, bericht: str = "Het opgegeven antwoord is ongeldig."):
        self.bericht = bericht
        super().__init__(bericht)


# ── HTTP-handlers (canoniek foutformaat; geen architectuurdetails) ──────────

async def niet_gevonden_handler(request: Request, exc: NietGevonden) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "fout": {
                "code": "NIET_GEVONDEN",
                "http_status": 404,
                "bericht": "De gevraagde resource is niet gevonden.",
            }
        },
    )


async def ongeldige_statusovergang_handler(
    request: Request, exc: OngeldigeStatusovergang
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "fout": {
                "code": "ONGELDIGE_STATUSOVERGANG",
                "http_status": 409,
                "bericht": "De gevraagde statusovergang is niet toegestaan.",
            }
        },
    )


async def koppeling_conflict_handler(
    request: Request, exc: KoppelingConflict
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "fout": {
                "code": "KOPPELING_CONFLICT",
                "http_status": 409,
                "bericht": "De koppeling kon niet worden opgeslagen wegens een conflict.",
            }
        },
    )


async def checklistscore_conflict_handler(
    request: Request, exc: ChecklistscoreConflict
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "fout": {
                "code": "CHECKLISTSCORE_BESTAAT_AL",
                "http_status": 409,
                "bericht": "Voor deze vraag bestaat al een score voor deze applicatie.",
            }
        },
    )


async def ongeldig_antwoord_handler(
    request: Request, exc: OngeldigAntwoord
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "fout": {
                "code": "ONGELDIG_ANTWOORD",
                "http_status": 422,
                "bericht": exc.bericht,
            }
        },
    )
