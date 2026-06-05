"""Pytest-padconfiguratie voor de bwb_ontvlechting-moduletests.

Voegt de platform-backend (voor `app.models.base`) en de module-backend
(voor `models`, `services`) toe aan sys.path.
"""
import pathlib
import sys

# .../modules/bwb_ontvlechting/backend/tests/conftest.py → repo-root = parents[4]
ROOT = pathlib.Path(__file__).resolve().parents[4]

for _p in (ROOT / "backend", ROOT / "modules" / "bwb_ontvlechting" / "backend"):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)
