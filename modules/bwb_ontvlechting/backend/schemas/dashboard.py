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


class DashboardReadinessType(BaseModel):
    """ADR-022 Fase F — readiness van één checklist-dragend componenttype (Besluit 3:
    per type, geen gefuseerd mengcijfer). `telling` = aantal per reële lifecycle-status
    (vaste sleutels, 0-default); `migratieklaar` van `totaal` = de "n van m gereed"-rollup."""

    componenttype: str
    componenttype_label: str
    telling: dict[str, int]
    totaal: int
    migratieklaar: int


class DashboardRead(BaseModel):
    """Tenant-breed dashboard-overzicht (één respons).

    - `readiness_per_type`: per checklist-dragend type de statusverdeling + rollup
      (ADR-022 Fase F, Besluit 3). Kale typen (zonder profiel) verschijnen niet.
    - `open_blokkades`: aantal nog niet opgeloste blokkades (ADR-013-definitie).
    - `recent_gewijzigd`: de meest recent gewijzigde profiel-dragende componenten.
    - `klaar_verklaard`: componenten met een levende klaar-verklaring (ADR-027 slice 3).
    - `klaar_met_afwijking`: daarvan de gevallen met een nog niet complete checklist
      (klaar verklaard terwijl de vragen-stand onvolledig is — read-only afgeleid).
    """

    readiness_per_type: list[DashboardReadinessType]
    open_blokkades: int
    recent_gewijzigd: list[DashboardRecentItem]
    klaar_verklaard: int = 0
    klaar_met_afwijking: int = 0
