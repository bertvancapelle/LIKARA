# SESSIESTART — LIKARA V024

**Datum**: 2026-06-29
**Platform**: LIKARA — een product van G. van Capelle Beheer B.V.

---

## Instructie voor CC bij sessiestart

1. Lees dit document volledig
2. Voer de sessiestart uit conform CLAUDE.md:
   - Controleer of .claude/skills/likara/ bestaat
   - Zo ja: normale modus — lees alle likara-skills + engineering/security
   - Zo nee: bootstrap-modus — lees alleen engineering/security
3. Lees SESSIE_BRIEFING.md voor de actuele projectstatus
4. Bevestig: "Sessiestart compleet — LIKARA V024 — [N] skills geladen"
5. Wacht op START: [naam] van Bert

---

## Interactieregel (VERPLICHT — niet-onderhandelbaar)

Geldt voor zowel CC als claude.ai, in elke sessie:

- Stel vragen ALTIJD één voor één. Stel nooit meerdere vragen tegelijk.
  Wacht op het antwoord van Bert voordat je een volgende vraag stelt.
- Geef adviezen ALTIJD één voor één. Geef nooit meerdere adviezen tegelijk.
  Wacht op de reactie van Bert voordat je een volgend advies geeft.

Deze regel is niet-onderhandelbaar en overschrijft elke neiging om
meerdere vragen of adviezen te bundelen.

---

## Opdrachtformaat CC-opdrachten (VERPLICHT — standaardwerkwijze)

claude.ai levert elke CC-opdracht ALTIJD aan als een .md-bestand
(downloadbaar), nooit als een los codeblok in de chat. Bert gebruikt dat
.md-bestand in CC. Deze afspraak geldt in elke sessie.

---

# SESSIE_BRIEFING.md — LIKARA V024

**Gegenereerd**: 2026-06-29

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V024 |
| Datum | June 2026 |
| Commit | 0e16999 |
| Tests | 698 frontend + 910 backend groen (2 skipped) |
| TST-rapport | TST-V024-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
0e16999 chore: verouderd root-OPVOLGPUNTEN.md verwijderd — docs/OPVOLGPUNTEN.md is de enige bron (LI023)
ac4afb7 docs(adr): ADR-025/026 nadere besluiten + ADR-030 besloten + ADR-035 Signalering aangemaakt + OPVOLGPUNTEN bijgewerkt (LI023)
3fc3414 docs: PRODUCTVISIE.md toegevoegd aan projectroot (LI023)
a4979fa fix(landschapskaart): zoekterm en dropdown resetten na aanvinken component (LI023)
1019d8f feat(landschapskaart): generieke re-layout bij elke node-samenstelling-wijziging (LI023)
```

---

## Prioriteiten volgende sessie

# NEXT_SESSION.md — LIKARA V023

**Gegenereerd**: 2026-06-27 (sessie-afsluiting LI022)
**Build**: V022 → **V023**
**Migratie head**: `0042` (`0042_adr033_opgeslagen_view`) — LI022 had geen schema-/migratiewijziging
(Fase B = frontend + read-side; slice 2a = nieuwe read-queries over bestaande relaties).
**Tests**: frontend **663 groen** + `vite build` + `test:css-build` ok; backend **910 passed / 2 skipped**
(de 8 LI021-failers zijn herijkt — 0 failers).

---

## Stand van zaken (V023) — Landschapskaart Fase B (set-gestuurd) + hygiëne/rename

Deze sessie (LI022):
- **Reset + seed-herijking** (`d6cd59f`) — de 8 pre-existing live-DB-failers herijkt op de verrijkte
  `_seed_bvowb_scenario` (seed onaangeroerd; tests bewogen mee).
- **Skill-laag hernoemd** `complidata-* → likara-*` + nieuwe **`likara-werkprotocol`**-skill (`8b8a8b2`);
  **Laag-2 identifier-rename** als opvolgpunt geborgd (`6043094`).
- **Fase B slice 0+1** (`10bb35e`) — set-gestuurd laadpad + `subgraaf` api-client.
- **Fase B slice 2a** (`509e9ca`) — contract- + gebruiker-context-routes naar componenten (databron voor
  de "Via context"-ingangen).
- **Sessie-afsluiting** — generators (gen_build/gen_sessiestart) meegerenamed naar `.claude/skills/likara/`.

---

## Vertrekpunt volgende sessie — Slice 2b (BESLOTEN ONTWERP, niet opnieuw ontwerpen)

**Slice 2b — leeg-openend 4-ingangen-beginscherm (frontend).** Vervangt de placeholder uit slice 1 door
het echte scherm. **Databron staat volledig klaar** (slice 2a + bestaande routes); geen backend nodig.

- **Hoofdroute (zoekzone):** type-scope-keuze (standaard `applicatie`; "applicatie" is gewoon een waarde
  van het componenttype-filter, **géén aparte ingang**; aanpasbaar) + vrije zoekterm → `api.componenten.lijst`
  (server-side, AND-gecombineerd) → treffers als **aanvinkbare multi-select-dropdown** → aangevinkte
  componenten verschijnen als **"In beeld"-chips** onder de balk.
- **"In beeld"-chips = tweede bewerk-plek op één selectie:** uitvinken/`×` = uit de graaf; één bron van
  waarheid met de knopen.
- **Filters** (laag · hosting · eigenaar) weggevouwen onder "+ Filters", verfijnen dezelfde treffers.
- **Via context (drie symmetrische routes — doorzoekbare multi-selects → onderliggende componenten in de set):**
  - leverancier → `api.partijen.lijst({aard:'externe_partij', zoek})` + `GET /partijen/{id}/componenten`
  - contract → `api.contracten.lijst({zoek})` + `GET /contracten/{id}/componenten` (nieuw, slice 2a)
  - gebruiker-context → `GET /gebruikersgroepen/contexten?zoek=` (distinct org+afdeling, met telling) +
    `GET /gebruikersgroepen/contexten/componenten?organisatie_id=&afdeling=`
- **Hergebruiken:** bestaande opgeslagen-views-lijst, als gelijkwaardige ingang op het scherm.
- **Toon het hele landschap:** bestaande actie (slice 1), bescheiden apart onderaan.
- **Granulariteit:** component-zoek = individuen kiezen; context-routes = context kiezen → alle
  onderliggende componenten. Alles **accumuleert**; subgraaf-herfetch op de hele set bij elke mutatie.
- **Engine:** read-only/frontend; geen backend nodig.

---

## Herziene slice-planning (het ontwerp heeft de oude nummering verschoven)

- **Slice 2b absorbeert** de oude "Typen server-side" (oud slice 3) en "Bladeren" (oud slice 4) — die
  worden **niet apart** gebouwd.
- **Slice 5 (design-heavy, CHECKPOINT-EERST):** het interactiemodel op de graaf — klik = toevoegen,
  `×` = weghalen, doorklik haalt buren erbij (+voegt de buur toe), verzamel-doorklik op context-knopen
  (alle onderliggende componenten), "N in beeld"-teller op de graaf, "Begin opnieuw" als harde reset —
  **plus** de geparkeerde **subgraaf-semantiek-beslissing** (welke van filter/scope/impact/swimlane
  zinvol zijn op een set). Bert wil het interactiegedrag kunnen **testen** zodra deze slice landt.
- **Slice 6:** opschonen (dode full-graph-op-mount-paden, `cytoscape-dagre`-cleanup).

---

## Bekende risico's en aandachtspunten

- **8 LI021-failers zijn opgelost** (herijkt op de verrijkte seed) — niet als open beschouwen.
- **`GET /gebruikersgroepen/contexten` is bewust ongepagineerd** (begrensde afgeleide lijst). Alleen bij
  extreem veel distinct (org, afdeling)-contexten een keyset-slice nodig (zie OPVOLGPUNTEN).
- **Laag-2 identifier-rename** (`complidata-api`-clientId, `cd_`-familie, `COMPLIDATA_TEST_MODE`) staat nog
  open als aparte, gecoördineerde slag (OPVOLGPUNTEN) — raakt Keycloak/realm + evt. schema (tabelprefix).
- Werktree is **schoon** na de afsluit-commit(s).

---

## Geleerde patronen deze sessie (verwerkt in de likara-skills)

- **likara-frontend** — set-gestuurd kaart-laadpad: leeg openen, subgraaf-per-set (hele set herfetch),
  hele-landschap als bewuste actie met "X van N"-teller op verwerkte data, begin-opnieuw = harde reset,
  entry-point = verse history-wortel.
- **likara-backend** — context→componenten read-endpoint: deel de WHERE, splits de projectie; geen
  ComponentProfiel-join (engine-ontkoppeld, kale componenten mee); nullable composiet-sleutel via
  `IS NOT DISTINCT FROM`; begrensde distinct-picker mag ongepagineerd.
- **likara-tests** — strategie A bij een laadpad-omslag: mountView laadt de "volledige" modus, één setter
  voedt beide laadpaden, nieuwe bedrading-tests apart; nagel onbesliste semantiek niet vast; function-
  bronscan met `ast`-docstring-strip voor engine-borging.


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — LIKARA V024"
4. Wacht op START: [naam] van Bert

