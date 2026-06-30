"""Pytest-padconfiguratie voor de bwb_ontvlechting-moduletests.

Voegt de platform-backend (voor `app.models.base`) en de module-backend
(voor `models`, `services`, `schemas`, `routes`) toe aan sys.path, en zet de
verplichte env-vars VÓÓR enig `app.*`-import (de route-integratietests
importeren de app-laag, die `Settings()` bij import instantieert). De waarden
zijn dummy's; geen test maakt een echte verbinding (alles gemockt/overschreven).
"""
import os
import pathlib
import sys

# .../modules/bwb_ontvlechting/backend/tests/conftest.py → repo-root = parents[4]
ROOT = pathlib.Path(__file__).resolve().parents[4]

for _p in (ROOT / "backend", ROOT / "modules" / "bwb_ontvlechting" / "backend"):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

_ENV_DEFAULTS = {
    "DATABASE_URL": "postgresql+asyncpg://lk_app:x@localhost/likara",
    "DATABASE_URL_SYNC": "postgresql://lk_app:x@localhost/likara",
    "PLATFORM_DATABASE_URL": "postgresql+asyncpg://lk_platform:x@localhost/likara",
    "KEYCLOAK_URL": "http://localhost:8080",
    "KEYCLOAK_REALM": "likara",
    "KEYCLOAK_CLIENT_ID": "likara-api",
    "KEYCLOAK_CLIENT_SECRET": "test-secret",
    "RABBITMQ_URL": "amqp://localhost",
    "LIKARA_TEST_MODE": "true",
}
for _k, _v in _ENV_DEFAULTS.items():
    os.environ.setdefault(_k, _v)
