"""Pydantic v2-schemas — referentiemodel inlezen (tenant-zijde, gate 1b §2.2).

Drie leesvormen, geen invoer-schema's (het inlezen kent geen payload — het model komt
uit het gecureerde aanbod; POST zonder body):
- `ReferentiemodelAanbodItem`: één aangeboden model + wat déze tenant ervan heeft
  (ingelezen snapshot of None) — voedt het keuzescherm en de lege-staat-route.
- `ImportVoorbeeld`: de dry-run-telling (het voorbeeldscherm) — nieuw/bijgewerkt/
  vervallen (mét naam + in-gebruik: de werklijst), ongewijzigd, plaatsingen en de
  eerlijke overgeslagen-telling per elementtype.
- `ImportResultaat`: hetzelfde plan, ná uitvoering, plus het model-snapshot.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IngelezenModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    naam: str
    versie: str
    ingelezen_op: datetime
    # Gate 1b-afronding — False = de vorige inlees is niet afgerond (afgebroken): het
    # model staat er mogelijk half; het scherm meldt dat eerlijk met een herstart-route.
    inlees_voltooid: bool


class ReferentiemodelAanbodItem(BaseModel):
    model_sleutel: str
    label: str
    herkomst: str
    versie: str
    beschikbaar: bool                 # het modelbestand reist mee in de release
    ingelezen: IngelezenModel | None  # None = deze tenant heeft dit model (nog) niet
    aantal_functies: int              # functies van dít model bij deze tenant
    aantal_vervallen: int


class VervallenFunctie(BaseModel):
    naam: str
    in_gebruik: bool


class ImportVoorbeeld(BaseModel):
    nieuw: list[str]
    bijgewerkt: list[str]
    vervallen: list[VervallenFunctie]
    ongewijzigd: int
    plaatsingen_totaal: int
    plaatsingen_nieuw: int
    plaatsingen_vervallen: int
    overgeslagen: dict[str, int]
    overgeslagen_totaal: int


class ImportModelSnapshot(BaseModel):
    model_sleutel: str
    naam: str
    versie: str


class ImportResultaat(ImportVoorbeeld):
    model: ImportModelSnapshot
