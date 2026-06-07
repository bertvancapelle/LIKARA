"""Pydantic v2-schemas voor het tenant-brede dashboard (CD014, #9).

Read-only aggregatie — geen Create/Update, geen request-body of query-params
(en dus geen `extra='forbid'`-invoeroppervlak). De lifecycle-telling toont de
vier reële statussen; `checklist_compleet` is transient (ADR-013 B4) en valt
hier bewust buiten.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.models import LifecycleStatus


class DashboardRecentItem(BaseModel):
    """Eén recent gewijzigde applicatie (compacte weergave voor het dashboard)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    naam: str
    lifecycle_status: LifecycleStatus
    gewijzigd_op: datetime


class DashboardRead(BaseModel):
    """Tenant-breed dashboard-overzicht (één respons).

    - `lifecycle_telling`: aantal applicaties per reële lifecycle-status
      (vaste sleutels, 0-default; `checklist_compleet` transient → niet getoond).
    - `open_blokkades`: aantal nog niet opgeloste blokkades (ADR-013-definitie).
    - `recent_gewijzigd`: de meest recent gewijzigde applicaties (vast limiet).
    """

    lifecycle_telling: dict[str, int]
    open_blokkades: int
    recent_gewijzigd: list[DashboardRecentItem]
