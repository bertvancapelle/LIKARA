# ADR-035 — Signalering registratiegaten

**Status:** Besloten
**Datum:** 2026-06-29
**Nummering:** ADR-031 was reeds vergeven (Landschapskaart ring-uitbreiding); dit Signalering-ADR
draagt daarom nummer **ADR-035** (eerstvolgende vrije nummer; hoogste bestaande was ADR-034).
**Relatie:** Read-only inzichtlaag; raakt geen engine, geen lifecycle-driver.
Absorbeert en vervangt de losse signalerings-cases uit OPVOLGPUNTEN.
Plaatsingssignalen (bestaand scherm) wordt onderdeel van het bredere
Signalering-scherm.

**Invariant:** Signalering is puur read-only — geen engine-poort, geen
score-mutatie, geen lifecycle-driver.

---

## Context

Registratiegaten (ontbrekende eigenaren, contracten zonder leverancier,
geïsoleerde componenten) zijn nu niet zichtbaar in de applicatie. De productvisie
stelt: "LIKARA stimuleert volledigheid actief." Dit ADR vult die belofte in.

---

## Besluit (kern)

1. **Coherente signaleringslocatie.** Het bestaande "Plaatsingssignalen"-scherm
   wordt uitgebreid tot een breed "Signalering"-scherm met twee tabs:
   - **Registratiegaten** — dit ADR
   - **Plaatsing** — bestaande plaatsingssignalen (ongewijzigd)

2. **Twee presentatielagen:**
   - **Badges op entiteiten** — directe contextuele signalering op de entiteit
     waar het gat zit (component, contract, gebruikersgroep, blokkade)
   - **Centraal overzicht** — alle openstaande gaten op één plek, prioriteerbaar

3. **Elf signaaltypen in twee niveaus** (6 kritiek / 5 aandacht):

   🔴 **Kritiek** (governance direct geraakt):
   - Component zonder eigenaar (organisatie)
   - Component zonder verantwoordelijke persoon (rol)
   - BIV-classificatie onvolledig (≥1 van beschikbaarheid/integriteit/vertrouwelijkheid leeg) — ADR-028 slice 4
   - Registratie onvolledig (score onder drempelwaarde)
   - Contract zonder leverancier
   - Blokkade zonder eigenaar

   🟡 **Aandacht** (volledigheid geraakt, niet direct blokkerend):
   - Component zonder gebruikersgroep
   - Component zonder koppeling (geïsoleerd)
   - Contract zonder gekoppeld component
   - Gebruikersgroep zonder organisatie
   - Object zonder enige roltoewijzing

4. **Score-drempelwaarde:** configureerbaar per tenant (platformbeheerder),
   standaard 80%. Onder de drempel = signaal "registratie onvolledig".

5. **Actiegerichtheid:** elk signaal in het centrale overzicht heeft een
   directe doorkliklink naar de entiteit. Geen in-line bewerking in het
   signaleringsscherm — de gebruiker navigeert naar de juiste plek.

---

## Invarianten

- Read-only; geen engine-poort, geen score-mutatie.
- Generalisatie-discipline n≥2: bouw het tweede concrete signaaltype naast
  het eerste vóór abstractie.
- Signalering is een afgeleide inzichtlaag — geen opgeslagen state,
  altijd live berekend.

---

## Gevolgen

- Navigatiemenu: "Plaatsingssignalen" → "Signalering" (met tabs).
- Badges op: ComponentDetail, ContractDetail, GebruikersgroepDetail,
  BlokkadeDetail.
- Drempelwaarde-configuratie: platformbeheer-instellingen.
- RBAC: hergebruik bestaande leespermissies per entiteitstype.

---

## Bouw-fasering (indicatief)

1. **Eerste twee signaaltypen** (n≥2-discipline): component zonder eigenaar +
   contract zonder leverancier — badges + centraal overzicht.
2. **Overige kritieke signalen** toevoegen.
3. **Aandacht-signalen** toevoegen.
4. **Score-drempelwaarde** configureerbaar maken.
5. **Plaatsingssignalen** integreren als tweede tab.

---

## Uitvoeringsnotities

- **`blokkade_zonder_eigenaar` vereist schema-/semantiekherziening — uitgesteld.** Een blokkade is
  geen element-subtype (eigen PK; FK's naar `checklistscore`/`component_profiel`, géén composiet-FK
  naar `element`), en `roltoewijzing.object_id` verwijst naar `element`. Een roltoewijzing kan een
  blokkade dus structureel niet refereren → "geen roltoewijzing op de blokkade" is voor élke blokkade
  waar. Het signaal is daarom (nog) niet zinvol te berekenen; herziening nodig (bv. blokkade-eigenaar
  afleiden van de eigenaar/verantwoordelijke van het component).
- **`contract_zonder_leverancier` vervalt blijvend:** `contract.leverancier_id` is `NOT NULL` — een
  contract heeft altijd een leverancier (zie ook Slice 1).
- **Badges alleen waar een detail-pagina bestaat.** ComponentDetail draagt de badge; voor
  gebruikersgroep en blokkade bestaan geen standalone detail-pagina's, dus die signalen zijn (Slice 2)
  uitsluitend zichtbaar in het centrale Registratiegaten-overzicht.
