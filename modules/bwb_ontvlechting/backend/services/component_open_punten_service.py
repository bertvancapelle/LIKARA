"""Service — "wat heeft dit component nog nodig?" (LI047, ADR-052 besluiten 1-22).

De consultant die één component openslaat kon nergens zien wat er nog ontbreekt: dat stond verspreid
over zes tot acht plekken (velden op het Overzicht, de contracten, de verantwoordelijkheden, de
koppelingen, de checklist). Dus liep hij ze niet allemaal langs, of hij miste iets.

Drie blokken, ÉÉN afleiding:
- **"Dit moet nog"** — verplichte norm-feiten die op dit component niet zijn vastgesteld;
- **"Dit zou netjes zijn"** — dezelfde bepaling, andere lat: de NIET-verplichte feiten;
- **"Dit valt op"** — wat géén ontbrekend feit is: checklistantwoorden op nee/deels (GEBUNDELD tot
  één regel met het aantal, nooit los) en "staat los in het landschap".

Besluit 13 — blok 1 en 2 komen uit `component_norm_service.status_van_feiten`: hetzelfde oordeel,
alleen een andere lat. Er wordt hier GEEN tweede bepaling gebouwd; deze module filtert en presenteert.

Besluit 14 — teller en lijst komen uit dezelfde lijst (`aantal` = `len(punten)`), zodat een tabnaam
die "4" zegt nooit drie regels kan tonen.

Besluit 10 — een bewuste vaststelling dempt óók blok 3: "staat los in het landschap" verschijnt
alleen als er over koppelingen nog NIETS is vastgelegd. Minimaal: het gedeelde tenant-brede signaal
blijft ongemoeid; de demping leeft hier, in deze afleiding.

Engine-onaangeroerd (ADR-052): puur SELECT, geen import van/schrijf naar de lifecycle-engine.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import (
    ChecklistVraag,
    Checklistscore,
    Component,
    ComponentKlaarverklaring,
    KlaarverklaringStatus,
)
from services import actieve_vraag
from services import actor_resolutie
from services import component_norm_service as norm
from services import registratiegaten_service

# ── Waar landt het antwoord? (besluit 8: elk punt heeft een route) ─────────────────────────────
# Twee soorten landing: een VELD-ANKER op het Overzicht (het veld wordt gemarkeerd) of een TABBLAD.
# De sleutels spiegelen `detailIngang.js` (VELD_ANKERS + AANLEIDING_SLEUTELS) — de frontend bouwt er
# `detailRoute()` mee. ADR-054: nooit een route beloven waar niets te landen valt; feiten zonder
# landing krijgen daarom `None` (zie `_route`), en de UI toont die regel zonder doorklik.
_ROUTE_VELD = {
    norm.FEIT_EIGENAAR: "eigenaar",
    norm.FEIT_BIV: "biv",
    norm.FEIT_LEVENSFASE: "levensfase",
    norm.FEIT_BEDOELING: "bedoeling",
}
_ROUTE_TAB = {
    norm.FEIT_VERANTWOORDELIJKE: "verantwoordelijkheden",
    norm.FEIT_BEDRIJFSFUNCTIE: "bedrijfsfunctie",
    norm.FEIT_GEBRUIKERSGROEP: "gebruikersgroepen",
    norm.FEIT_KOPPELINGEN: "koppelingen",
    norm.FEIT_CONTRACT: "contracten",
}
# Tabbladen die NIET voor elk componenttype bestaan (ComponentDetail.vue).
# LEEG sinds LI047: `gebruikersgroepen` volgt `ondersteunt_werk` (ADR-055) en juist voor de typen
# zonder die vlag ontstaat het punt niet; `koppelingen` is component-breed gemaakt omdat een punt
# zonder invoerplek de belofte van dit overzicht breekt — alles wat erin staat is af te werken.
# De vangrail hieronder BLIJFT staan: ontstaat er ooit weer een tabblad dat niet overal bestaat,
# dan levert de afleiding géén route in plaats van een dode link (ADR-054).
_TAB_ALLEEN_APPLICATIE: set[str] = set()
_APPLICATIE_TYPE = "applicatie"

# Blok 3 draagt wat géén ontbrekend feit is (besluit 3).
PUNT_CHECKLIST = "checklist_nee_deels"
PUNT_ISOLATIE = "staat_los"
# ADR-056 besluit 10 — antwoorden waarvan de vraag als echte wijziging is aangepast:
# opnieuw beantwoorden is werk, maar er is niets fout (niet-blokkerend blok).
PUNT_VRAAG_GEWIJZIGD = "vraag_gewijzigd"

MOET_NOG = "moet_nog"
NETJES = "netjes"
VALT_OP = "valt_op"


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _route(feit: str, componenttype: str) -> dict | None:
    """De aanleiding waarmee de frontend `detailRoute()` bouwt, of None als er voor dít
    componenttype geen plek bestaat om het antwoord vast te leggen."""
    if feit in _ROUTE_VELD:
        return {"soort": "veld", "veld": _ROUTE_VELD[feit]}
    tab = _ROUTE_TAB.get(feit)
    if tab is None:
        return None  # geen bekende landing (bv. `hosting`: wél een Overzicht-veld, geen anker)
    if tab in _TAB_ALLEEN_APPLICATIE and componenttype != _APPLICATIE_TYPE:
        return None
    return {"soort": "tab", "tab": tab}


def _blok(punten: list[dict]) -> dict:
    """Besluit 14 — teller en lijst uit ÉÉN bron: het getal is de lengte van de lijst, niet een
    aparte telling ernaast die stilletjes uit de pas kan lopen."""
    return {"aantal": len(punten), "punten": punten}


async def _checklist_nee_deels(session: AsyncSession, tid: uuid.UUID, component_id) -> int:
    """Aantal checklistantwoorden op nee/deels. Puur tellen — de checklist zelf is engine-domein en
    wordt hier niet gelezen of aangeraakt."""
    return int(
        (
            await session.execute(
                select(func.count(Checklistscore.id)).where(
                    Checklistscore.tenant_id == tid,
                    Checklistscore.component_id == component_id,
                    Checklistscore.score.in_(("nee", "deels")),
                    # LI050: een uitgezette vraag bestaat voor de beoordeling niet — anders
                    # toont dit blok een punt dat de consultant niet kan wegwerken.
                    actieve_vraag.score_telt_mee(Checklistscore.checklistvraag_id),
                )
            )
        ).scalar_one()
        or 0
    )


async def _vraag_gewijzigd(session: AsyncSession, tid: uuid.UUID, component_id) -> int:
    """ADR-056 besluit 4/10 — het aantal antwoorden van dit component waarvan de vraag
    ná het antwoord als ECHTE wijziging is aangepast: de bevroren formulering wijkt af
    van de huidige (de vergelijking ís het sein; geen opgeslagen markering). Alleen
    actieve vragen — een uitgezette vraag bestaat voor de beoordeling niet (LI050).
    Puur tellen; raakt score/lifecycle niet."""
    return int(
        (
            await session.execute(
                select(func.count(Checklistscore.id))
                .join(ChecklistVraag, ChecklistVraag.id == Checklistscore.checklistvraag_id)
                .where(
                    Checklistscore.tenant_id == tid,
                    Checklistscore.component_id == component_id,
                    ChecklistVraag.actief.is_(True),
                    Checklistscore.vraag_bevroren != ChecklistVraag.vraag,
                )
            )
        ).scalar_one()
        or 0
    )


async def _klaarverklaring(session: AsyncSession, tid: uuid.UUID, component_id) -> dict | None:
    """De levende klaarverklaring (status=klaar) met wie/wanneer, of None. Besluit 16: de TOON van
    het overzicht verandert erdoor — vóór klaarverklaring neutraal, erna verantwoording."""
    rij = (
        await session.execute(
            select(
                ComponentKlaarverklaring.status,
                ComponentKlaarverklaring.verklaard_door_sub,
                ComponentKlaarverklaring.verklaard_door,
                ComponentKlaarverklaring.verklaard_op,
            ).where(
                ComponentKlaarverklaring.tenant_id == tid,
                ComponentKlaarverklaring.component_id == component_id,
            )
        )
    ).first()
    if rij is None or rij.status != KlaarverklaringStatus.klaar:
        return None
    # ADR-029 — sub → persoon.naam, met de e-mail als leesbare terugval. Dezelfde resolutie als het
    # migratiegereedheid-blok; zonder deze stap zou dit scherm een e-mailadres tonen waar het andere
    # een naam toont, over dezelfde gebeurtenis. `None` = niet vastgelegd (de kolom is nullable) —
    # de UI zegt dat dan met zoveel woorden i.p.v. een gat te laten vallen.
    naam = await actor_resolutie.resolveer_naam(
        session, tid, sub=rij.verklaard_door_sub, email=rij.verklaard_door
    )
    return {"verklaard_door": naam, "verklaard_op": rij.verklaard_op}


async def open_punten(session: AsyncSession, tenant_id, component_id) -> dict | None:
    """Alles wat dit component nog nodig heeft, in drie blokken. ``None`` als het component niet
    bestaat of buiten de tenant valt (geen lek). Read-only."""
    tid = _tenant_uuid(tenant_id)
    componenttype = (
        await session.execute(
            select(Component.componenttype).where(
                Component.tenant_id == tid, Component.id == component_id
            )
        )
    ).scalar_one_or_none()
    if componenttype is None:
        return None

    # ── Blok 1 + 2: ÉÉN bepaling over ALLE harde feiten, daarna twee filters (besluit 13) ──
    status = await norm.status_van_feiten(session, tid, component_id, norm.HARDE_FEITEN)
    if status is None:  # pragma: no cover — componenttype gevonden ⇒ component bestaat
        return None
    verplicht = {feit for feit, v in (await norm.haal_norm(session, tid)).items() if v}

    def _punt(feit: str) -> dict:
        return {"feit": feit, "route": _route(feit, componenttype)}

    open_feiten = [f for f, s in status.items() if s == norm.NIET_VASTGESTELD]
    moet_nog = [_punt(f) for f in open_feiten if f in verplicht]
    netjes = [_punt(f) for f in open_feiten if f not in verplicht]

    # ── Blok 3: wat géén ontbrekend feit is (besluit 3) ──
    valt_op: list[dict] = []
    aantal_nee_deels = await _checklist_nee_deels(session, tid, component_id)
    if aantal_nee_deels:
        # GEBUNDELD tot één regel met het aantal — nooit als losse regels (besluit 3): twintig
        # rode regels verdrinken de vier feiten die er echt toe doen.
        valt_op.append(
            {"soort": PUNT_CHECKLIST, "aantal": aantal_nee_deels,
             "route": {"soort": "tab", "tab": "checklist"}}
        )
    # ADR-056 besluit 10 — verouderde antwoorden: gebundeld, niet-blokkerend, met de
    # route naar de checklist waar het opnieuw antwoorden gebeurt.
    aantal_vraag_gewijzigd = await _vraag_gewijzigd(session, tid, component_id)
    if aantal_vraag_gewijzigd:
        valt_op.append(
            {"soort": PUNT_VRAAG_GEWIJZIGD, "aantal": aantal_vraag_gewijzigd,
             "route": {"soort": "tab", "tab": "checklist"}}
        )

    # Besluit 10 — een bewuste vaststelling dempt óók dit punt. Zonder die demping zegt blok 1
    # "vastgesteld (bewust geen koppelingen)" terwijl blok 3 op hetzelfde scherm "staat los in het
    # landschap" roept: een tegenspraak over één feit, en precies op het schone geval (HR-systeem).
    # Minimaal gebouwd: het tenant-brede signaal blijft ongemoeid, de demping leeft hier.
    if status.get(norm.FEIT_KOPPELINGEN) == norm.NIET_VASTGESTELD:
        badge = await registratiegaten_service.badge_voor_component(session, tid, component_id)
        if registratiegaten_service._SIG_ISOLATIE in set(badge.get("signalen", [])):
            valt_op.append(
                {"soort": PUNT_ISOLATIE, "aantal": None,
                 "route": _route(norm.FEIT_KOPPELINGEN, componenttype)}
            )

    # ── Klaarverklaring: besluiten 15-18 ──
    kv = await _klaarverklaring(session, tid, component_id)
    if kv is not None:
        # De punten VERDWIJNEN NIET (besluit 15) — ze zijn nog steeds niet vastgesteld; er is alleen
        # besloten er niet op te wachten. Wat verandert is de toon (16) en de splitsing (17):
        # bewust afgewogen bij het verklaren vs. de lat verschoof daarna. Dezelfde gedeelde
        # afleiding als het werkvoorraadvenster — nooit een tweede berekening.
        afwijking = await norm.afwijking_voor_component(session, tid, component_id)
        kv = {**kv, norm.BEWUST: afwijking[norm.BEWUST], norm.VERSCHOVEN: afwijking[norm.VERSCHOVEN]}

    return {
        "component_id": component_id,
        MOET_NOG: _blok(moet_nog),
        NETJES: _blok(netjes),
        VALT_OP: _blok(valt_op),
        # ADR-056 besluit 10 (LI051) — het getal op het tabblad telt BEIDE soorten
        # werk: wat nooit is vastgesteld (blok 1) én wat opnieuw beantwoord moet
        # worden (verouderde antwoorden). Zelfde afleiding als de blokken hierboven —
        # één bron, geen tweede telling. Geen poort: klaar verklaren kan gewoon.
        "tabblad_aantal": len(moet_nog) + aantal_vraag_gewijzigd,
        # Besluit 18 — zonder klaarverklaring is het één neutrale lijst: geen bevroren
        # momentopname, dus geen bewust/verschoven-onderscheid om te tonen.
        "klaarverklaring": kv,
    }
