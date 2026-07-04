# LIKARA — Next Session (V032)

> **Sessie LI031 — ADR-038 (gebruikersgroep-consolidatie + intern/extern-kenmerk), volledig geland (V032).**
> Eén consistent model: een gebruikersgroep hoort **altijd** bij een organisatie; burger-doelgroepen
> zijn gewone **externe organisaties met afdelingen**. Intern/extern is een expliciet kenmerk op
> partijen. Geland in vijf slices + het ADR:
> - **ADR-038 geschreven** (`1d9ab3a`).
> - **Slice 1a — `partij.scope`, additief (`2f1c816`, migratie `0052`):** `partij_scope_enum`
>   (intern/extern), nullable + twee CHECKs (gezet iff organisatie/externe_partij; externe_partij vast
>   extern; afdeling/persoon leiden af). Default extern op organisatie; seed BvoWB=intern.
> - **Slice 1b — consolidatie (`195c489`, migratie `0053`):** `gebruikersgroep.gebruik_id` **NOT NULL**
>   (FK → RESTRICT); `burger`-aard uit `partij_aard_enum` verwijderd (type-recreate). Organisatie
>   verplicht in Create + service-422; werk_bij weigert org=null. Dode resten weg: kaart-veld
>   `gebruikt_door_organisatieloos` + signaal `gebruikersgroep_zonder_organisatie`. Seed: burger-
>   doelgroepen als 3 externe organisaties + 6 segment-afdelingen + 5 groepen.
> - **Slice 2a — groep-dialoog org verplicht (`edb4eb8`):** client-side inline-melding + `*`-markering.
> - **Slice 2b — intern/extern-UI (`3ec3320`):** kiesbaar in `PartijFormulier` (radio-kaartjes, default
>   Extern; vast "Extern" bij externe partij; niet bij afdeling/persoon), leesbaar in `PartijDetail`.
> - **Slice 2c — kaart-opruiming (`6702bd2`):** dood burger-silhouet/label/legenda/predicate weg.
>
> Laatste commit: `6702bd2`. Tests: backend **851** (module) + **80** (platform), 2 skipped ·
> frontend **780**. Migratie-head **0053**.

## ⚙️ Eerste runtime-stap (vóór browserverificatie in LI032)
De dev-DB is deze sessie gemigreerd (0053) en gereseed voor de tests, maar een **verse reseed** is
nodig om de nieuwe seed + scope-waarden (BvoWB=intern, burger-doelgroepen als externe organisaties met
afdelingen) volledig in de UI te zien. Gedocumenteerde stack-reset:
`docker compose down` → `docker volume rm likara_lk_postgres_data` → `docker compose up -d` →
`docker exec -w /app lk-api python3 dev_seed_testdata.py`. (`down -v` staat op **deny**.)

## Top-5 prioriteiten (volgende sessie)

1. **Contactpersoon als keuze uit personen van de eigen organisatie — SCHEMA-GATE (ADR-waardig).**
   **Expliciet vóór GebruikersgroepDetail (besluit Bert LI031).** Contactpersoon op een partij is nu
   vrije tekst; wordt een verwijzing naar een **persoon-partij van de organisatie zelf**. Sjabloon =
   ADR-036a/037: FK-kolom `partij.contactpersoon_id` + validator "persoon binnen deze organisatie"
   (spiegel `valideer_verantwoordelijke`) + read-verrijking `contactpersoon_naam` + migratie +
   dev-reseed. **Bouwstenen liggen klaar:** read `api.partijen.lijst({aard:'persoon', organisatie_id})`,
   `ZoekSelect`, identiteit "persoon — afdeling — organisatie" (`_verrijk_context`). **Beslist:**
   optioneel; keuze uitsluitend uit personen met `organisatie_id = deze partij`; geen vrije tekst meer.
   **Open ontwerpvragen vóór bouw (uit het LI031-feitenonderzoek):**
   - (a) **VOORAAN:** mag je een contactpersoon **ter plekke aanmaken** als er nog geen personen onder de
     organisatie staan (zoals de afdeling-picker in `GebruikersgroepSectie`), of alleen kiezen uit bestaande?
   - (b) op welke aarden krijgt de partij een contactpersoon-veld — alleen **organisatie-achtig**
     (organisatie + externe_partij) i.p.v. alle?
   - (c) **vervangen vs. additief** (aanbeveling: vervangen, met reseed).
   - (d) `telefoon`/`mobiel`/`email`-vrijvelden bewust **buiten scope** (enkel signaleren).
   - (e) migratie-landing **defensief/reseed** zoals `0053`.

2. **GebruikersgroepDetail** op het schone model. Opzet beslist (LI031): één invalshoek-neutrale
   detailpagina op `gebruikersgroepen/:id`; **applicatie-kant-ingang eerst** (rij-klik vanuit
   `GebruikersgroepSectie`), partij-kant-ingang als eigen slice erna (ná een korte PartijDetail-
   grounding). **Signaal-scope beslist:** op het detail alleen de **groep-eigen** signalen; het
   grove-feit-signaal hoort er niet. Bekende kleine gaten (eerder feitenonderzoek): objecthistorie-
   allowlist `objecthistorie._TYPES` mist `gebruikersgroep` (`haal_op` bestaat al); applicatie-**naam**
   vs. -id in de read; per-groep signaal-weergave (client-filter op registratiegaten kan).

3. **BlokkadeDetail** — nog te maken **conceptuele keuze met Bert**: eigen pagina óf doorklik naar de
   component-checklisttab. Beslissen vóór bouw. Restpunt: detail-read (`BlokkadeRead`) verrijken met
   **herkomst** (checklistvraag `vraag_code`/`vraag`/score).

4. **Breder org-context-patroon** — de "afdeling — organisatie"-ontdubbeling (ADR-036a/037/038, via
   `gebruikersgroepIdentiteit`) ook toepassen op de **ContractFormulier-leverancier-picker** en
   **PartijLijst** — de enige resterende niet-org-gescoopte afdeling/persoon-lijsten. (PartijLijst-
   intern/extern-kolom/badge hoort hier ook — bewust uitgesteld in Slice 2b.)

5. **Auth/sessie-cluster** (uit LI030-onderzoek): (a) **dev-sessie-robuustheid bij reseed** — een
   stack-herstart (Redis/Keycloak) doodt levende sessies stil; persistentie of gedocumenteerde
   re-login; (b) **UX-vangrail** — 401 na gefaalde refresh → naar opnieuw inloggen leiden i.p.v. een
   kale rode `NIET_GEAUTHENTICEERD`-toast; (c) **auth/refresh-testgat** — nu overal gemockt.

**Zwaarste los item (verse sessie):** **Impact-verkenner render-herbouw** — één deterministische
render-eigenaar; edges-onzichtbaar-bug in de echte cytoscape-render (logica bewezen correct); met
échte render-verificatie + de Cytoscape-mock-consoleruis opruimen.

**Klein onderhoud (kan meeliften):** ADR-036 "begin grof"-invoerroute (frontend-formulier voor een los
grof feit); ADR-035 slice 3 (configureerbare score-drempel); verantwoordelijkheid-/roltoewijzing-
partij-picker-scope (eerst de domeinvraag); RelatieKenmerk-dimensie-velduitleg (content klaar, wacht op
invoerveld); dode-code-opschoning.

---

## Openstaande punten (volledig)

### ADR-038 / gebruikersgroep-consolidatie + intern/extern — ✅ GELAND (V032, migraties 0052–0053)
- Slice 1a (`2f1c816`) `partij.scope` · 1b (`195c489`) consolidatie + burger-aard weg · 2a (`edb4eb8`)
  org verplicht · 2b (`3ec3320`) intern/extern-UI · 2c (`6702bd2`) kaart-opruiming.
- **Runtime-restpunt:** verse reseed vóór browserverificatie (zie boven).
- **Open vervolg (top-5 #4):** intern/extern in PartijLijst (kolom/badge) — bewust uitgesteld.

### Contactpersoon uit register — top-5 #1 (schema-gate, ADR-waardig)
- Feitenonderzoek gedaan (LI031). Vrije tekst → persoon-verwijzing; 5 open ontwerpvragen (zie top-5 #1).

### Detailpagina's (gebruikersgroep + blokkade) — top-5 #2/#3
- Standalone pagina's ontbreken nog. GebruikersgroepDetail-grounding gedaan (opzet + signaal-scope
  beslist); BlokkadeDetail vraagt eerst de conceptuele keuze. Objecthistorie `_TYPES` uitbreiden met
  `gebruikersgroep` (+ `blokkade`) voor het 'i'-paneel — `haal_op` bestaat al.

### ADR-037 / verantwoordelijke per checklistantwoord — ✅ GELAND (V031, migratie 0051)

### ADR-036 / organisatiegebruik — ✅ GELAND (V030)
- **Open vervolg (klein onderhoud):** frontend-invoerroute om een grof feit los vast te leggen.

### ADR-036a / afdeling structureel — ✅ GELAND (V030, migratie 0050)

### Auth/sessie-cluster — top-5 #5 (uit LI030)
- (a) reseed doodt levende sessies stil (Redis/Keycloak); (b) 401→re-login-UX-vangrail;
  (c) auth/refresh-testgat (echte 401→refresh→retry-dekking ontbreekt).

### Impact-verkenner — zwaarste los item
- **Render-bug** (edges onzichtbaar op preset-pad; `nodes:visible` inzakking) — onopgelost. Logica/model
  bewezen correct; zit in de echte cytoscape-render.
- Modus ego→impact ontkoppelen van set-grootte (ADR-033-revisie); Swimlane (ADR-034, geparkeerd);
  Saved views als permanente hoofdingang (Fase D).
- **Test-hygiëne (pre-existing):** ~31 unhandled-rejection-consoleruis uit de Cytoscape-mock + theme-
  CSS-fetch-abort in `LandschapskaartView.test.js` — **geen falende test** (frontend 780/780). Bij
  render-herbouw meenemen.

### ADR-035 Signalering
- Slice 3: "Registratie onvolledig" (configureerbare score-drempelwaarde) — uitgesteld (klein onderhoud).
- badges op GebruikersgroepDetail/BlokkadeDetail — bij die detail-pagina's (top-5 #2/#3).

### Partij-pickers
- **Verantwoordelijkheid-/roltoewijzing-partij-picker** ongefilterd → eerst domeinvraag, dán scoping
  (klein onderhoud). Contract-leverancier-picker versmald (`aard_in`); org-context nog toe te voegen
  (top-5 #4).

### Velduitleg
- **Parked:** RelatieKenmerk-dimensie-velduitleg (content klaar; wacht op een invoerveld).

### Component-focus-herfundering — ✅ AFGEROND (LI057–LI059, migraties 0045–0047)

### Cosmetic/klein
- Zoekbalk-contextlabel "Component toevoegen aan beeld" in kaart-modus. Dode-code-opschoning.

### Strategisch (parked)
- Export/import/rapportage — scope apart te bepalen.
- **DC013** — GitHub-repo/remote-rename + lokale `~/complidata/`-map opruimen (Berts actie).
- Deploy-side `.env`/secrets bijwerken op andere omgevingen; `~/likara/secrets/` daadwerkelijk vullen.
