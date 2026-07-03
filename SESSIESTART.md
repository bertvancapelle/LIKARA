# SESSIESTART — LIKARA V031

**Datum**: 2026-07-03
**Platform**: LIKARA — een product van G. van Capelle Beheer B.V.

---

## Instructie voor CC bij sessiestart

1. Lees dit document volledig
2. Voer de sessiestart uit conform CLAUDE.md:
   - Controleer of .claude/skills/likara/ bestaat
   - Zo ja: normale modus — lees alle likara-skills + engineering/security
   - Zo nee: bootstrap-modus — lees alleen engineering/security
3. Lees SESSIE_BRIEFING.md voor de actuele projectstatus
4. Bevestig: "Sessiestart compleet — LIKARA V031 — [N] skills geladen"
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

# SESSIE_BRIEFING.md — LIKARA V031

**Gegenereerd**: 2026-07-03

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V031 |
| Datum | July 2026 |
| Commit | 4c8d113 |
| Tests | backend 841 (module) + 80 (platform) / frontend 772 groen (2 skipped) |
| TST-rapport | TST-V031-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
4c8d113 [adr037] verantwoordelijke-picker + aandacht-signaal + velduitleg — Pass 2 — ADR-037
e21a28e [adr037] verantwoordelijke per checklistantwoord — schema-gate Pass 1 — ADR-037
e177bd7 chore(release): sessie-afsluiting V030 — ADR-036 + Velduitleg + ADR-036a
0e439d3 [frontend] contract-leverancier-picker naar geldige aarden — ADR-024
929435e [frontend] gebruikersgroep bewerken — organisatie correct voorvullen — ADR-036
```

---

## Prioriteiten volgende sessie

# LIKARA — Next Session (V031)

> **Sessie LI030 — ADR-037 (verantwoordelijke per checklistantwoord), volledig geland (V031):**
> het vrije-tekstveld "Eigenaar" op een checklistantwoord vervangen door een gestructureerde
> **verantwoordelijke** (afdeling óf persoon uit het register), met de blokkade-eigenaar afgeleid.
> - **Pass 1 — schema-gate (`e21a28e`, migratie `0051`):** `checklistscore.verantwoordelijke_id`
>   (composiet-FK → `element`, ON DELETE SET NULL) vervangt `checklistscore.eigenaar`;
>   `blokkade.eigenaar` gedropt (afgeleid in de leeslaag via `checklistscore.verantwoordelijke_id`).
>   Aard-validatie (422 `ONGELDIGE_VERANTWOORDELIJKE`); dubbele engine-borging (score blijft enige
>   lifecycle-driver); seed-scenario (persoon/afdeling/leeg + blokkerend antwoord).
> - **Pass 2 — invoer + signaal (`4c8d113`):** verantwoordelijke-picker in `ChecklistscoreSectie`
>   (afdeling/persoon in één `ZoekSelect`, `aard_in`), PATCH `verantwoordelijke_id` zonder score;
>   aandacht-signaal `antwoord_zonder_verantwoordelijke` (registratiegaten via `table()`-handle,
>   engine-veilig) + `SIGNAAL_LABEL` + velduitleg; Opslaan-knop leesbaar (primaire kleur);
>   identiteit **"afdeling — organisatie" / "persoon — afdeling — organisatie"** in lijst, veld én
>   weergave na selectie (read-uitbreiding: `verantwoordelijke_organisatie` + partij-lijst
>   `organisatie_naam`/`afdeling_naam`).
>
> Twee incident-lessen (groene tests dekten een kapotte UX niet — pas in de browser zichtbaar):
> onleesbare Opslaan-knop (wit-op-bijna-wit) en veld-vs-lijst-identiteit. Vuistregels geborgd in
> `likara-frontend`/`likara-tests`/`likara-ux`. Separaat gezien maar buiten scope gehouden:
> `NIET_GEAUTHENTICEERD` bij opslaan = sessie-/tokenverval + gefaalde refresh (niet de PATCH).
>
> Laatste commit: `4c8d113`. Tests: backend **841** (module) + **80** (platform), 2 skipped ·
> frontend **772**. Migratie-head **0051**.

## Top-5 prioriteiten (volgende sessie)

1. **Detailpagina's — GebruikersgroepDetail + BlokkadeDetail.** GebruikersgroepDetail is het verst
   (feitenonderzoek gedaan: read + formulier bestaan al; ontbreken: het scherm zelf, identiteit-/
   applicatie-weergave, signalen-ter-plekke, en objecthistorie-ontsluiting `objecthistorie._TYPES` +
   `haal_op`-resolutie). **BlokkadeDetail heeft eerst een conceptuele keuze met Bert:** eigen pagina
   vs. doorklik naar de component-checklisttab — uitdenken vóór bouw. BlokkadeDetail-restpunt: detail-
   read (`BlokkadeRead`) verrijken met **herkomst** (checklistvraag `vraag_code`/`vraag`/score).

2. **Breder org-context-patroon** — dezelfde "afdeling — organisatie"-ontdubbeling (ADR-036a/037,
   via `gebruikersgroepIdentiteit`) ook toepassen op de **ContractFormulier-leverancier-picker** en
   **PartijLijst** — de enige resterende niet-org-gescoopte afdeling/persoon-lijsten.

3. **Auth/sessie-cluster** (uit LI030-onderzoek): (a) **dev-sessie-robuustheid bij reseed** — een
   stack-herstart (Redis/Keycloak) doodt levende sessies stil; persistentie of gedocumenteerde
   re-login; (b) **UX-vangrail** — 401 na gefaalde refresh → gebruiker naar opnieuw inloggen leiden
   i.p.v. een kale rode `NIET_GEAUTHENTICEERD`-toast; (c) **auth/refresh-testgat** — nu overal gemockt;
   geen echte 401→refresh→retry-dekking.

4. **Impact-verkenner render-herbouw** — één deterministische render-eigenaar; edges-onzichtbaar-bug
   zit in de echte cytoscape-render (logica bewezen correct). Zwaarste item, verse sessie; met échte
   render-verificatie i.p.v. mocks + de Cytoscape-mock-consoleruis opruimen.

5. **ADR-036 "begin grof"-invoerroute** — frontend-formulier om een grof organisatiegebruik-feit los
   vast te leggen (organisatie zonder afdeling). Backend bestaat al; zonder dit vuurt "detaillering
   ontbreekt" alleen op seed-data.

**Klein onderhoud (kan meeliften, geen top-5-plek):** ADR-035 slice 3 (configureerbare score-drempel);
verantwoordelijkheid-/roltoewijzing-partij-picker-scope (eerst de domeinvraag); RelatieKenmerk-dimensie-
velduitleg (content klaar, wacht op invoerveld); dode-code-opschoning; de cytoscape-test-ruis (bij #4).

---

## Openstaande punten (volledig)

### ADR-037 / verantwoordelijke per checklistantwoord — ✅ GELAND (V031, migratie 0051)
- Pass 1 (`e21a28e`) schema-gate + Pass 2 (`4c8d113`) picker/signaal/velduitleg/identiteit.
- **Open vervolg (top-5 #2):** org-context-patroon uitrollen naar leverancier-picker + PartijLijst.

### Detailpagina's (gebruikersgroep + blokkade) — top-5 #1
- Standalone pagina's ontbreken nog. GebruikersgroepDetail-grounding gedaan; BlokkadeDetail vraagt
  eerst de conceptuele keuze (eigen pagina vs. doorklik) met Bert. Objecthistorie `_TYPES` uitbreiden
  met `gebruikersgroep` + `blokkade` voor het 'i'-paneel (bouwstenen `haal_op` + `Entiteit`-enum
  bestaan al).

### Auth/sessie-cluster — top-5 #3 (nieuw, uit LI030)
- (a) reseed doodt levende sessies stil (Redis/Keycloak); (b) 401→re-login-UX-vangrail;
  (c) auth/refresh-testgat (echte 401→refresh→retry-dekking ontbreekt).

### ADR-036 / organisatiegebruik — ✅ GELAND (V030)
- **Open vervolg (top-5 #5):** frontend-invoerroute om een grof feit los vast te leggen.

### ADR-036a / afdeling structureel — ✅ GELAND (V030, migratie 0050)

### Velduitleg — ✅ GELAND (V030)
- **Parked:** RelatieKenmerk-dimensie-velduitleg (content klaar; wacht op een invoerveld).

### Component-focus-herfundering — ✅ AFGEROND (LI057–LI059, migraties 0045–0047)

### Impact-verkenner — top-5 #4
- **Render-bug** (edges onzichtbaar op preset-pad; `nodes:visible` inzakking) — onopgelost. Logica/model
  bewezen correct; zit in de echte cytoscape-render.
- Modus ego→impact ontkoppelen van set-grootte (ADR-033-revisie); Swimlane (ADR-034, geparkeerd);
  Saved views als permanente hoofdingang (Fase D).
- **Test-hygiëne (pre-existing):** ~29–33 unhandled-rejection-consoleruis uit de Cytoscape-mock
  (`cy.nodes`) + theme-CSS-fetch-abort in `LandschapskaartView.test.js`/`LandschapskaartPopups.test.js`
  — **geen falende test** (frontend 772/772). Bij render-herbouw meenemen.

### ADR-035 Signalering
- Slice 3: "Registratie onvolledig" (configureerbare score-drempelwaarde) — uitgesteld (klein onderhoud).
- badges op GebruikersgroepDetail/BlokkadeDetail — bij die detail-pagina's (top-5 #1).

### Partij-pickers
- **Verantwoordelijkheid-/roltoewijzing-partij-picker** ongefilterd → eerst domeinvraag, dán scoping
  (klein onderhoud). Contract-leverancier-picker is versmald (`aard_in`); org-context nog toe te voegen
  (top-5 #2).

### Cosmetic/klein
- Zoekbalk-contextlabel "Component toevoegen aan beeld" in kaart-modus. Dode-code-opschoning.

### Strategisch (parked)
- Export/import/rapportage — scope apart te bepalen.
- **DC013** — GitHub-repo/remote-rename + lokale `~/complidata/`-map opruimen (Berts actie).
- Deploy-side `.env`/secrets bijwerken op andere omgevingen; `~/likara/secrets/` daadwerkelijk vullen.


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — LIKARA V031"
4. Wacht op START: [naam] van Bert

