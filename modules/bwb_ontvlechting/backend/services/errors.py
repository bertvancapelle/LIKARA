"""Module-domeinexcepties + HTTP-handlers (P5).

Worden in de service-laag gegooid en in `backend/app/main.py` op handlers
gemapt naar het canonieke foutformaat `{"fout":{"code","http_status","bericht"}}`
— exact analoog aan `OnvoldoendeRechten` (middleware/authz): exceptie én handler
in één bestand, registratie in `main.py`.

Pinning (besluit Bert, Blok 0):
- `NietGevonden`            → HTTP 404, code `NIET_GEVONDEN`
- `OngeldigeStatusovergang` → HTTP 409, code `ONGELDIGE_STATUSOVERGANG`
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
