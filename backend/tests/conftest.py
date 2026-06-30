"""Pytest-config voor de backend-tests.

Zet verplichte env-vars VÓÓR import van `app.*` — `app.core.config`
instantieert `Settings()` bij import en faalt zonder deze waarden. De waarden
zijn dummy's; geen enkele test maakt een echte verbinding (Keycloak/Redis/DB
worden gemockt).
"""
import os
import pathlib
import sys

_DEFAULTS = {
    "DATABASE_URL": "postgresql+asyncpg://lk_app:x@localhost/likara",
    "DATABASE_URL_SYNC": "postgresql://lk_app:x@localhost/likara",
    "PLATFORM_DATABASE_URL": "postgresql+asyncpg://lk_platform:x@localhost/likara",
    "KEYCLOAK_URL": "http://localhost:8080",
    "KEYCLOAK_REALM": "likara",
    "KEYCLOAK_CLIENT_ID": "likara-app",
    "KEYCLOAK_CLIENT_SECRET": "test-secret",
    "RABBITMQ_URL": "amqp://localhost",
    "LIKARA_TEST_MODE": "true",
}
for _k, _v in _DEFAULTS.items():
    os.environ.setdefault(_k, _v)

_BACKEND = pathlib.Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
