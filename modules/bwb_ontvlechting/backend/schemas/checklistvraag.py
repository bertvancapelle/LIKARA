"""Pydantic v2-schema voor ChecklistVraag (read-only referentiedata).

Sinds ADR-019 verrijkt met `antwoordtype` + de optie-catalogus van de vraag.
De opties bevatten ook gedeactiveerde (`actief=false`) entries, zodat de frontend
een eerder opgeslagen — inmiddels inactieve — optiesleutel nog kan resolven naar
zijn label; de keuze-control toont alleen `actief`-opties (frontend-gating).
"""
import uuid

from pydantic import BaseModel, ConfigDict

from models.models import AntwoordType, ChecklistPrioriteit


class ChecklistVraagOptieRead(BaseModel):
    """Eén optie uit de catalogus (ADR-019)."""

    model_config = ConfigDict(from_attributes=True)

    optie_sleutel: str
    label: str
    volgorde: int
    actief: bool
    afgeleid_bron: str | None


class ChecklistVraagRead(BaseModel):
    """Volledige weergave — exact het model (geen tenant_id; referentiedata) +
    `antwoordtype` en de optie-catalogus (ADR-019)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    componenttype: str
    # LI050 (ADR-022 W3): de categorie is een verwijzing; naam + volgorde reizen mee
    # (transient gezet in de service — het eigenaar_organisatie_naam-patroon).
    categorie_id: uuid.UUID
    categorie_naam: str
    categorie_volgorde: int
    # LI050 (W5): de sleep-volgorde van de vraag binnen haar categorie.
    volgorde: int
    vraag: str
    prioriteit: ChecklistPrioriteit
    antwoordtype: AntwoordType
    opties: list[ChecklistVraagOptieRead] = []
