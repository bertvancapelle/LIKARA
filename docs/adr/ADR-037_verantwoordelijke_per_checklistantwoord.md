# ADR-037 — Verantwoordelijke per checklistantwoord

**Status:** Besloten (knopen 1–5 vastgelegd LI030) — gerealiseerd in Pass 1 (schema-gate)
**Datum:** 2026-07-03
**Relatie:** Bouwt op ADR-024 (partijenregister, 4 aarden) en ADR-036a (afdeling structureel:
`afdeling_id` → organisatie_eenheid-partij; persoon draagt zijn afdeling zelf). Vervangt het vrije
tekstveld `Checklistscore.eigenaar` en laat `Blokkade.eigenaar` (vrije tekst) vervallen.
**Invariant (ongewijzigd):** score blijft de enige lifecycle-driver — de engine wordt niet geraakt.
De verantwoordelijke is een registratie-feit náást de engine (read/registratie), geen engine-invoer.

---

## Context / aanleiding (functioneel)

Bij het invullen van een checklistantwoord weet de gebruiker vaak al wíé ervoor instaat: de
**afdeling** die het antwoord aanlevert, en waar bekend de **persoon** binnen die afdeling. Vandaag
legt hij dat vast in een vrij tekstveld "Eigenaar" op het antwoord. Vrije tekst betekent dat
dezelfde persoon de ene keer "Jan", de andere keer "J. de Vries" heet — het systeem kan daardoor
nooit betrouwbaar de vraag beantwoorden *"welke antwoorden liggen bij wie?"*. Het register weet al
wie de afdelingen en personen zijn; de verantwoordelijkheid hoort daaraan gekoppeld, niet los getypt.

Wanneer een onvoldoende antwoord een blokkade veroorzaakt, is de verantwoordelijke van dat antwoord
de natuurlijke eigenaar van de blokkade. De gebruiker wil dat niet nog eens apart invullen — het
staat er al.

**Kern (feitenonderzoek LI030):** er is geen aparte antwoord-tabel — het antwoord ís de
`Checklistscore`-rij (1-op-1 per component+vraag). Het veld "Eigenaar" op het formulier is
`Checklistscore.eigenaar` (het antwoord-veld), níét `Blokkade.eigenaar`. De verantwoordelijke is dus
de **opwaardering van dit bestaande antwoord-veld** van vrije tekst → partij-koppeling.

---

## Besluit (kern)

1. **Verantwoordelijke per antwoord — vervangt de vrije tekst.** `Checklistscore` krijgt één
   `verantwoordelijke_id` (koppeling naar het partijenregister) die het bestaande vrije-tekstveld
   `eigenaar` **vervangt**. Geen twee "wie"-velden naast elkaar — dat zou de gebruiker laten raden
   welk veld leidend is.
2. **Eén veld, afdeling óf persoon.** De verantwoordelijke is één partij met aard
   ∈ {`organisatie_eenheid` (afdeling), `persoon`}. Kiest de gebruiker een **persoon**, dan draagt
   die zijn **afdeling** zelf al (ADR-036a) — de afdeling wordt afgeleid getoond
   ("Jan de Vries — Burgerzaken"), niet apart ingevuld. Eén FK volstaat; twee losse velden
   (afdeling + persoon) zouden de gebruiker dwingen ze consistent te houden — onnodig en foutgevoelig.
3. **v1 laat beide detailniveaus toe.** Afdeling én persoon zijn vanaf v1 kiesbaar. Alleen afdeling
   toestaan zou de gebruiker dwingen het detail (de persoon) weg te gooien dat hij juist wil kunnen
   vastleggen.
4. **Leeg mag — wordt een aandacht-signaal.** De verantwoordelijke is **optioneel**. Leeg blijven is
   een geldige, bedoelde toestand ("je registreert om zichtbaar te maken wat je nog niet weet") en
   levert het aandacht-signaal `antwoord_zonder_verantwoordelijke` op — géén blokkade, geen blokkering.
5. **Blokkade-eigenaar wordt afgeleid — geen eigen veld meer.** `Blokkade.eigenaar` (vrije tekst)
   **vervalt**. Een blokkade **toont** de verantwoordelijke van het onderliggende antwoord, puur
   afgeleid in de **leeslaag**. Corrigeert de gebruiker de verantwoordelijke op het antwoord, dan
   beweegt de blokkade vanzelf mee. **Geen overschrijven in v1** — dat introduceert weer een tweede
   "wie" die kan afwijken van de bron; wordt bewust toegevoegd zodra een concreet geval het vraagt.
6. **Geen overdrachtsgeschiedenis.** De verantwoordelijke is een eigenschap van het huidige antwoord;
   overschrijven vervangt de waarde, de vorige wordt niet bewaard.

---

## Randvoorwaarden (besloten)

- **Signaal:** sleutel `antwoord_zonder_verantwoordelijke`, label "Antwoord zonder verantwoordelijke",
  niveau **aandacht** (blokkeert niets; stimuleert volledigheid). Bewust onderscheiden van het
  bestaande `component_zonder_verantwoordelijke` (dat gaat over een component zonder beheerrol).
  *(Pass 2.)*
- **Afleiding blokkade-eigenaar leeft in de leeslaag** (join `Blokkade.checklistscore_id` →
  `Checklistscore.verantwoordelijke_id` → partij-naam + afdeling). De engine (`_synchroniseer_blokkade`)
  raakt het veld niet — dat houdt de score/lifecycle-scheiding zuiver.
- **Testbaarheid is een eis, geen bijzaak.** De seed levert een scenario waarin de gebruiker dit in
  de praktijk ziet: antwoorden met een persoon-verantwoordelijke, antwoorden met alleen een afdeling,
  antwoorden bewust zónder (voor het signaal), en ≥1 onvoldoende antwoord zodat er een echte blokkade
  met afgeleide eigenaar ontstaat. **Seed volgt het gebruikersverhaal; test volgt de seed.**

---

## Model / aanpak

- **Landingsplek:** `Checklistscore.verantwoordelijke_id`, composiet-FK
  `(tenant_id, verantwoordelijke_id) → element(tenant_id, id)`, **ON DELETE SET NULL** (spiegelt
  `component.eigenaar_organisatie_id`: verdwijnt de partij, dan re-opent het gat — het blokkeert de
  verwijdering niet, consistent met "leeg mag → signaal").
- **Aard-borging:** app-side `_valideer_verantwoordelijke` (`partij_service.valideer_verantwoordelijke`,
  spiegel van `_valideer_lidmaatschap`): aard ∈ {`organisatie_eenheid`, `persoon`} → anders 422
  (`ONGELDIGE_VERANTWOORDELIJKE`). De aard leeft op de partij-tabel, dus een pure kolom-`CHECK` kan dit
  niet afdwingen; de FK borgt een geldig element, de service borgt de aard (structurele borging op de
  plek waar ze kán leven).
- **`Checklistscore.eigenaar` (vrije tekst) wordt gedropt** en vervangen door `verantwoordelijke_id`.
  Read levert `verantwoordelijke_id` + afgeleide `verantwoordelijke_naam` (+ `verantwoordelijke_afdeling`
  bij persoon).
- **`Blokkade.eigenaar` (vrije tekst) wordt gedropt.** `BlokkadeRead`/lijst/overzicht tonen de
  afgeleide `verantwoordelijke_naam` (+ afdeling) van de gekoppelde score (sorteer-/leesvelden
  verschuiven mee: `eigenaar` → `verantwoordelijke_naam`).
- **Seed:** `dev_seed_testdata.py` zet de antwoord-verantwoordelijke met echte afdelingen/personen
  (persoon "J. de Vries — Informatievoorziening", afdeling "Informatievoorziening", en een blokkerend
  antwoord met verantwoordelijke; de rest bewust leeg).
- **Ontwikkelmodus:** alleen testdata — de kolom-drops vragen géén datamigratie, reseed volstaat.
  "Migratie" = alembic-schemastap (`0051_adr037_verantw`).

---

## Invarianten

- **Engine onaangeroerd / score blijft enige lifecycle-driver.** `verantwoordelijke_id` valt buiten
  elk engine-leespad (`bepaal_lifecycle` leest het niet); de blokkade-afleiding leeft in de leeslaag.
  Dubbele borging: (1) afwezigheidstest — de verantwoordelijke read-/validatie-paden
  (`checklistscore_service._verrijk`, `partij_service.valideer_verantwoordelijke`/
  `resolve_verantwoordelijken`) importeren/refereren geen engine-(her)afleidingssymbool; (2) live-test
  — een verantwoordelijke zetten/wijzigen/leegmaken muteert geen `component_profiel`/`lifecycle_status`/
  `checklistscore.score`/`blokkade` (`test_engine_borging_adr037`).
- **Structureel boven conventioneel** — FK + service-aard-borging, geen vrije-tekst-conventie.
- **Geen afgeleide relaties** — de verantwoordelijke wordt expliciet door de gebruiker gezet.

---

## Gevolgen

- Het antwoordformulier houdt **één** "Verantwoordelijke"-veld (partij-picker in Pass 2), geen vrij
  tekstvak.
- "Wat ligt er bij wie" wordt een echte, opvraagbare vraag (afdeling of persoon uit het register).
- Blokkades tonen automatisch de juiste eigenaar zonder dubbele invoer, altijd kloppend.
- Blast-radius `eigenaar`-drops: ≈6 backend-vindplaatsen op blokkade + het antwoord-formulier + seed.
  Alles binnen dev-testdata; reseed dekt het.
- Geen nieuwe RBAC-entiteit/audit-entiteit: het veld leeft op bestaande entiteiten
  (`checklistscore`) via bestaande routes/permissies.

---

## Bouw-fasering

**Pass 1 — schema-gate (gerealiseerd):** migratie `0051_adr037_verantw` (voeg `verantwoordelijke_id`
toe; drop `checklistscore.eigenaar`; drop `blokkade.eigenaar`) + model + `_valideer_verantwoordelijke`
+ `ChecklistscoreRead/Update` (verantwoordelijke + afgeleide naam/afdeling) + `BlokkadeRead`/lijst/
overzicht afgeleide verantwoordelijke (leeslaag) + seed-scenario + dubbele engine-borging + minimale
frontend-ontkoppeling (eigenaar-veld eruit; blokkade read-only verantwoordelijke).

**Pass 2 — read-side + frontend:** aandacht-signaal `antwoord_zonder_verantwoordelijke`
(`registratiegaten()` + `SIGNAAL_LABEL`) + volwaardige verantwoordelijke-picker in
`ChecklistscoreSectie.vue` (afdeling/persoon via `ZoekSelect` + partij-scope, voorvullen bij bewerken,
afdeling afgeleid tonen bij persoon) + velduitleg-content. Puur additief.

---

## Open subknopen

Geen — knopen 1–5 zijn met Bert besloten (LI030).
