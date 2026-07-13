"""Referentiemodel-import — droog draaien + uitvoeren op ÉÉN codepad (gate 1b).

De beheerder kiest een model uit het gecureerde aanbod (`referentiemodel_optie`,
platform-catalogus), ziet eerst het VOORBEELD (de dry-run-telling: nieuw · bijgewerkt ·
vervallen — mét namen en in-gebruik — · overgeslagen) en bevestigt; pas dan landt het.
Niets landt stil (ADR-043: geen synchronisatiemachine — inlezen is een zeldzame,
bewuste handeling).

Architectuur:
- **Eén vergelijking voor voorbeeld én uitvoering**: `_bepaal_plan` is puur (DB-vrij
  testbaar); `dry_run` en `voer_uit` lezen dezelfde bron via dezelfde parser
  (`ameff.lees_ameff`) en berekenen hetzelfde plan — de uitvoering is "plan + schrijven",
  nooit een tweede vergelijking die uit de pas kan lopen.
- **Bronsleutel = identiteit** (ADR-043): matchen op `(bron_model, bron_sleutel)` —
  nooit op naam. Naam, definitie en plaatsingen worden bijgewerkt naar de bron.
- **Schrijven ORM-matig via de bestaande facade** (`bedrijfsfunctie_service.maak_aan` /
  `plaats` / `verwijder_plaatsing` met `via_import=True` — het legitieme pad langs
  `MODELINHOUD_BESCHERMD`; het slot zelf blijft intact). Een SQL-upsert zou de audit
  omzeilen (die hangt aan de ORM-flush-hooks).
- **Vervallen = set-verschil op bronsleutel**, markeren — nooit hard verwijderen
  (CASCADE zou eigen registratie meeslepen). Een functie die terugkeert in de bron
  "herleeft" (vlag weer af). Plaatsingen van een vervallen functie worden BEVROREN
  (niet gewist): de functie blijft zichtbaar op haar historische plek in de boom.
- **Eigen functies** (zonder bronsleutel) worden nooit geraakt; plaatsingen waar een
  eigen functie bij betrokken is, vallen buiten de synchronisatie.
- **Aanbod gesloten**: welke bestanden LIKARA levert staat in `_AANBOD_BESTANDEN`
  (repo-route, zie `referentiemodellen/HERKOMST.md`); de motor (parser + dit plan)
  is modelonafhankelijk.

Engine-invariant: dit pad importeert géén lifecycle-/score-/blokkade-symbolen en
muteert geen `component_profiel` — score blijft de enige lifecycle-driver (dubbel
geborgd in `test_referentiemodel_import_gate1b.py`).
"""
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import Bedrijfsfunctie, Referentiemodel, ReferentiemodelOptie
from services import bedrijfsfunctie_service
from services.ameff import AmeffFout, AmeffInhoud, lees_ameff
from services.errors import OngeldigeRegistratie

# Gecureerd aanbod → bestand in de release (repo-route, besloten LI039). Eén regel per
# aangeboden model; herkomst/licentie/SHA-256 staan in referentiemodellen/HERKOMST.md.
_REFERENTIEMODELLEN_DIR = Path(__file__).resolve().parents[1] / "referentiemodellen"
_AANBOD_BESTANDEN: dict = {
    "gemma_bedrijfsfuncties": _REFERENTIEMODELLEN_DIR / "GEMMA_release_2026-07-01.xml",
}


@dataclass(frozen=True)
class FunctieStand:
    """DB-vrij snapshot van één bestaande model-functie (voor het pure plan)."""

    sleutel: str
    naam: str
    definitie: str | None
    vervallen: bool


@dataclass
class ImportPlan:
    """De uitkomst van de vergelijking — voedt het voorbeeldscherm ÉN de uitvoering."""

    nieuw: list = field(default_factory=list)         # namen (uit de bron)
    bijgewerkt: list = field(default_factory=list)    # namen — naam/definitie/plaatsing/herleefd
    vervallen: list = field(default_factory=list)     # [{"naam": …, "in_gebruik": bool}]
    ongewijzigd: int = 0
    plaatsingen_totaal: int = 0                       # plaatsingen in de bron
    plaatsingen_nieuw: int = 0
    plaatsingen_vervallen: int = 0                    # verhangen: bestond, niet meer in de bron
    overgeslagen: dict = field(default_factory=dict)  # elementtype → aantal (eerlijk)
    overgeslagen_totaal: int = 0

    def als_dict(self) -> dict:
        return {
            "nieuw": list(self.nieuw),
            "bijgewerkt": list(self.bijgewerkt),
            "vervallen": [dict(v) for v in self.vervallen],
            "ongewijzigd": self.ongewijzigd,
            "plaatsingen_totaal": self.plaatsingen_totaal,
            "plaatsingen_nieuw": self.plaatsingen_nieuw,
            "plaatsingen_vervallen": self.plaatsingen_vervallen,
            "overgeslagen": dict(self.overgeslagen),
            "overgeslagen_totaal": self.overgeslagen_totaal,
        }


def _bepaal_plan(
    bron: AmeffInhoud,
    bestaand: list,          # list[FunctieStand] — de huidige model-functies
    bestaande_plaatsingen: set,  # {(ouder_sleutel, kind_sleutel)} tussen model-functies
    in_gebruik: set,         # sleutels van functies met registratie eraan (gate 2: leeg)
) -> ImportPlan:
    """Puur (DB-vrij): vergelijk de bron met de bestaande stand. Dry-run en uitvoering
    gebruiken exact dit ene plan.

    - nieuw: in de bron, nog niet aanwezig.
    - bijgewerkt: naam/definitie gewijzigd, herleefd (was vervallen, is terug), of
      verhangen (de eigen plaatsingen — als kínd — wijken af van de bron).
    - vervallen: aanwezig (nog niet vervallen), niet meer in de bron — mét naam en
      in-gebruik-vlag (de werklijst). Al-vervallen en nog steeds afwezig = geen
      wijziging (idempotente herinlees telt 0).
    - Plaatsings-diff alleen tussen bron-functies; paren met een vertrekkend/vervallen
      endpoint worden bevroren (blijven staan), paren met een eigen functie vallen
      buiten scope van de aanroeper.
    """
    bron_per_sleutel = {f.sleutel: f for f in bron.functies}
    bestaand_per_sleutel = {f.sleutel: f for f in bestaand}

    plan = ImportPlan(
        plaatsingen_totaal=len(bron.plaatsingen),
        overgeslagen=dict(bron.overgeslagen),
        overgeslagen_totaal=bron.overgeslagen_totaal,
    )

    # Plaatsings-diff (op sleutel-paren). Weghalen alléén als beide endpoints nog in de
    # bron staan — anders is het geen "verhangen" maar een vertrekkende functie, en die
    # houdt haar historische plek (vervallen = zichtbaar mét markering, niet zwevend).
    plan_plaatsing_nieuw = bron.plaatsingen - bestaande_plaatsingen
    plan_plaatsing_weg = {
        (o, k) for (o, k) in bestaande_plaatsingen - bron.plaatsingen
        if o in bron_per_sleutel and k in bron_per_sleutel
    }
    plan.plaatsingen_nieuw = len(plan_plaatsing_nieuw)
    plan.plaatsingen_vervallen = len(plan_plaatsing_weg)
    # Verhangen raakt het KIND (diens plek wijzigt).
    verhangen_kinderen = {k for _, k in plan_plaatsing_nieuw if k in bestaand_per_sleutel} | {
        k for _, k in plan_plaatsing_weg
    }

    for sleutel, bron_f in bron_per_sleutel.items():
        huidig = bestaand_per_sleutel.get(sleutel)
        if huidig is None:
            plan.nieuw.append(bron_f.naam)
            continue
        gewijzigd = (
            huidig.naam != bron_f.naam
            or huidig.definitie != bron_f.definitie
            or huidig.vervallen                    # herleefd
            or sleutel in verhangen_kinderen       # verhangen
        )
        if gewijzigd:
            plan.bijgewerkt.append(bron_f.naam)
        else:
            plan.ongewijzigd += 1

    for sleutel, huidig in bestaand_per_sleutel.items():
        if sleutel not in bron_per_sleutel and not huidig.vervallen:
            plan.vervallen.append({"naam": huidig.naam, "in_gebruik": sleutel in in_gebruik})

    plan.nieuw.sort()
    plan.bijgewerkt.sort()
    plan.vervallen.sort(key=lambda v: v["naam"])
    return plan


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


async def _aanbod_rij(session: AsyncSession, model_sleutel: str) -> ReferentiemodelOptie:
    rij = (
        await session.execute(
            select(ReferentiemodelOptie).where(
                ReferentiemodelOptie.optie_sleutel == model_sleutel
            )
        )
    ).scalar_one_or_none()
    if rij is None or not rij.actief:
        raise OngeldigeRegistratie(
            "ONBEKEND_MODEL", "Dit referentiemodel wordt niet (meer) aangeboden."
        )
    return rij


def _lees_bron(model_sleutel: str) -> AmeffInhoud:
    pad = _AANBOD_BESTANDEN.get(model_sleutel)
    if pad is None:
        raise OngeldigeRegistratie(
            "ONBEKEND_MODEL", "Voor dit referentiemodel is geen modelbestand beschikbaar."
        )
    try:
        return lees_ameff(pad)
    except AmeffFout as fout:
        raise OngeldigeRegistratie("MODELBESTAND_ONGELDIG", str(fout)) from None


async def _bestaande_stand(
    session: AsyncSession, tid: uuid.UUID, refmodel_id
) -> tuple[list, set, dict]:
    """Huidige model-functies + de plaatsingen dáártussen (paren met een eigen functie
    als endpoint vallen buiten de synchronisatie — die raakt de import nooit aan)."""
    if refmodel_id is None:
        return [], set(), {}
    functies = (
        await session.execute(
            select(Bedrijfsfunctie).where(
                Bedrijfsfunctie.tenant_id == tid,
                Bedrijfsfunctie.bron_model_id == refmodel_id,
            )
        )
    ).scalars().all()
    sleutel_per_id = {f.id: f.bron_sleutel for f in functies}
    paren = await bedrijfsfunctie_service._plaatsings_paren(session, tid)
    plaatsingen = {
        (sleutel_per_id[o], sleutel_per_id[k])
        for (o, k) in paren
        if o in sleutel_per_id and k in sleutel_per_id
    }
    stand = [
        FunctieStand(
            sleutel=f.bron_sleutel, naam=f.naam, definitie=f.definitie, vervallen=f.vervallen
        )
        for f in functies
    ]
    return stand, plaatsingen, {f.bron_sleutel: f for f in functies}


async def _in_gebruik_sleutels(session: AsyncSession, tid: uuid.UUID, per_sleutel: dict) -> set:
    """Bronsleutels van functies waar tenant-registratie aan hangt. Het koppelen van
    componenten aan functies is gate 2 — er kán nu nog niets aan een functie hangen,
    dus dit is per definitie de lege set (geen verzonnen getal). Gate 2 vult deze
    functie met de echte koppel-telling; de voorbeeld-vorm ("waarvan N nog in gebruik")
    staat er al."""
    return set()


async def overzicht(session: AsyncSession, tenant_id) -> list:
    """Het aanbod voor de tenant (read-only): per actief aangeboden model wat déze
    tenant ervan heeft — ingelezen snapshot (of None) + functie-tellingen. Voedt het
    keuzescherm en de lege-staat-route in de functieboom."""
    from sqlalchemy import func

    tid = _tenant_uuid(tenant_id)
    opties = (
        await session.execute(
            select(ReferentiemodelOptie)
            .where(ReferentiemodelOptie.actief.is_(True))
            .order_by(ReferentiemodelOptie.volgorde, ReferentiemodelOptie.id)
        )
    ).scalars().all()
    modellen = {
        r.model_sleutel: r
        for r in (
            await session.execute(
                select(Referentiemodel).where(Referentiemodel.tenant_id == tid)
            )
        ).scalars().all()
    }
    tellingen = {
        rij.bron_model_id: (rij.totaal, rij.vervallen)
        for rij in (
            await session.execute(
                select(
                    Bedrijfsfunctie.bron_model_id,
                    func.count().label("totaal"),
                    func.count().filter(Bedrijfsfunctie.vervallen).label("vervallen"),
                )
                .where(
                    Bedrijfsfunctie.tenant_id == tid,
                    Bedrijfsfunctie.bron_model_id.is_not(None),
                )
                .group_by(Bedrijfsfunctie.bron_model_id)
            )
        ).all()
    }
    resultaat = []
    for optie in opties:
        ingelezen = modellen.get(optie.optie_sleutel)
        totaal, vervallen = tellingen.get(ingelezen.id if ingelezen else None, (0, 0))
        resultaat.append({
            "model_sleutel": optie.optie_sleutel,
            "label": optie.label,
            "herkomst": optie.herkomst,
            "versie": optie.versie,
            "beschikbaar": optie.optie_sleutel in _AANBOD_BESTANDEN,
            "ingelezen": ingelezen,
            "aantal_functies": totaal,
            "aantal_vervallen": vervallen,
        })
    return resultaat


async def dry_run(
    session: AsyncSession, tenant_id, model_sleutel: str, *, bron: AmeffInhoud | None = None,
) -> dict:
    """Droog draaien: parsen + vergelijken ZONDER te schrijven — het voorbeeldscherm.
    `bron` is injecteerbaar voor tests; standaard het gecureerde bestand."""
    tid = _tenant_uuid(tenant_id)
    await _aanbod_rij(session, model_sleutel)
    inhoud = bron if bron is not None else _lees_bron(model_sleutel)
    refmodel = (
        await session.execute(
            select(Referentiemodel).where(
                Referentiemodel.tenant_id == tid,
                Referentiemodel.model_sleutel == model_sleutel,
            )
        )
    ).scalar_one_or_none()
    stand, plaatsingen, per_sleutel = await _bestaande_stand(
        session, tid, refmodel.id if refmodel else None
    )
    in_gebruik = await _in_gebruik_sleutels(session, tid, per_sleutel)
    return _bepaal_plan(inhoud, stand, plaatsingen, in_gebruik).als_dict()


async def voer_uit(
    session: AsyncSession, tenant_id, model_sleutel: str, *, bron: AmeffInhoud | None = None,
) -> dict:
    """Voer de import uit — exact het plan dat de dry-run toonde (zelfde parser, zelfde
    vergelijking), nu mét schrijven. Idempotent: een tweede run levert 0 wijzigingen.

    Schrijfvolgorde: aanbod-snapshot → nieuw/bijgewerkt/herleefd → plaatsingen erbij →
    plaatsingen weg (verhangen) → vervallen markeren. ORM-matig via de facade
    (audit-gedekt); per facade-aanroep één commit (het seed-precedent) — een afgebroken
    import laat dus een deelstand achter die een herstart idempotent afmaakt.
    """
    tid = _tenant_uuid(tenant_id)
    aanbod = await _aanbod_rij(session, model_sleutel)
    inhoud = bron if bron is not None else _lees_bron(model_sleutel)

    # Het ingelezen-model-snapshot van de tenant (get-or-create; herinlees werkt bij).
    refmodel = (
        await session.execute(
            select(Referentiemodel).where(
                Referentiemodel.tenant_id == tid,
                Referentiemodel.model_sleutel == model_sleutel,
            )
        )
    ).scalar_one_or_none()
    if refmodel is None:
        refmodel = Referentiemodel(
            tenant_id=tid, model_sleutel=model_sleutel,
            naam=aanbod.label, versie=aanbod.versie,
            inlees_voltooid=False,  # begin-markering: er gáát geschreven worden
        )
        session.add(refmodel)
        await session.commit()
        await session.refresh(refmodel)

    stand, plaatsingen, per_sleutel = await _bestaande_stand(session, tid, refmodel.id)
    in_gebruik = await _in_gebruik_sleutels(session, tid, per_sleutel)
    plan = _bepaal_plan(inhoud, stand, plaatsingen, in_gebruik)

    # BEGIN-markering (gate 1b-afronding): de inlees is pas "geland" als de vlag aan
    # het eind weer op True staat. Breekt de import af (browser dicht, container weg),
    # dan blijft False staan en meldt het scherm eerlijk "de vorige inlees is niet
    # afgerond" — nooit een halve boom die zich voordoet als het hele model, en nooit
    # een nog-niet-gemarkeerde vervallen functie die zich voordoet als geldig.
    refmodel.inlees_voltooid = False
    await session.commit()

    bron_per_sleutel = {f.sleutel: f for f in inhoud.functies}

    # 1. Nieuw + bijgewerkt + herleefd — matchen op bronsleutel, nooit op naam.
    from schemas.bedrijfsfunctie import BedrijfsfunctieCreate

    for sleutel, bron_f in bron_per_sleutel.items():
        huidig = per_sleutel.get(sleutel)
        if huidig is None:
            aangemaakt = await bedrijfsfunctie_service.maak_aan(
                session, tid,
                BedrijfsfunctieCreate(naam=bron_f.naam, definitie=bron_f.definitie),
                bron_model_id=refmodel.id, bron_sleutel=sleutel,
            )
            per_sleutel[sleutel] = await bedrijfsfunctie_service.haal_op(
                session, tid, aangemaakt["id"]
            )
        elif (
            huidig.naam != bron_f.naam
            or huidig.definitie != bron_f.definitie
            or huidig.vervallen
        ):
            huidig.naam = bron_f.naam
            huidig.definitie = bron_f.definitie
            huidig.vervallen = False  # herleefd: terug in de bron = terug in het model
            await session.commit()

    # 2. Plaatsingen bijwerken (1-op-1 uit de bron, incl. de meervoudige gevallen).
    id_per_sleutel = {s: f.id for s, f in per_sleutel.items()}
    for ouder_s, kind_s in sorted(inhoud.plaatsingen - plaatsingen):
        await bedrijfsfunctie_service.plaats(
            session, tid, id_per_sleutel[kind_s], id_per_sleutel[ouder_s], via_import=True,
        )
    for ouder_s, kind_s in sorted(plaatsingen - inhoud.plaatsingen):
        # Alleen verhangen-paren (beide endpoints nog in de bron); een plaatsing van een
        # vertrekkende functie wordt bevroren — zichtbaar op haar historische plek.
        if ouder_s in bron_per_sleutel and kind_s in bron_per_sleutel:
            await bedrijfsfunctie_service.verwijder_plaatsing(
                session, tid, id_per_sleutel[kind_s], id_per_sleutel[ouder_s], via_import=True,
            )

    # 3. Vervallen markeren (set-verschil) — nooit hard verwijderen.
    for sleutel, huidig in per_sleutel.items():
        if sleutel not in bron_per_sleutel and not huidig.vervallen:
            huidig.vervallen = True
            await session.commit()

    # Snapshot bijwerken (label/versie uit het actuele aanbod + inleesmoment) én de
    # EIND-markering: pas hier — ná de laatste schrijfstap, incl. vervallen — is de
    # inlees echt geland. Eén commit: snapshot en voltooid-vlag landen samen.
    from sqlalchemy import text as _text

    refmodel.naam = aanbod.label
    refmodel.versie = aanbod.versie
    refmodel.ingelezen_op = (
        await session.execute(_text("SELECT now()"))
    ).scalar_one()
    refmodel.inlees_voltooid = True
    await session.commit()

    resultaat = plan.als_dict()
    resultaat["model"] = {
        "model_sleutel": model_sleutel, "naam": aanbod.label, "versie": aanbod.versie,
    }
    return resultaat
