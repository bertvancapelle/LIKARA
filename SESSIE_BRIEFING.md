# SESSIE_BRIEFING.md — LIKARA V033

**Gegenereerd**: 2026-07-05

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V033 |
| Datum | July 2026 |
| Commit | ca8c999 |
| Tests | backend 866 (module) + 80 (platform) / frontend 825 groen (2 skipped) |
| TST-rapport | TST-V033-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
ca8c999 [gebruiker-bewerken] org/afdeling wijzigen + picker- en accountsysteem-fixes — LI032
4534533 [frontend] gebruikersgroep afdeling-inline-aanmaak → gedeelde AfdelingSelect — LI032
b1fde48 [frontend+backend] gebruiker aanmaken: organisatie-keuze + gescopte afdeling — LI032
bebf658 [frontend] afdeling ter plekke aanmaken (gedeelde AfdelingSelect) — LI032
5d007b4 [frontend] centrale verlopen-sessie-vangrail + zoek-norm
```

---

## Prioriteiten volgende sessie

# LIKARA — Next Session (V033)

> **Sessie LI032 — gebruiker-cluster: contactpersoon uit register (ADR-039), sessie-vangrail,
> ter-plekke-aanmaken (afdeling), gebruiker aanmaken + bewerken (organisatie/afdeling), en
> account-/picker-reparaties. Volledig geland (V033).**
>
> Afgerond in LI032:
> - **Contactpersoon = verwijzing naar een persoon (ADR-039, migratie `0054`, commit `0b91493`).**
>   `partij.contactpersoon_id` FK (SET NULL kolom-specifiek) vervangt het vrije-tekstveld; alleen op
>   organisatie-achtige aarden; persoon-binnen-partij-validatie; read-verrijking `contactpersoon_naam`.
> - **Centrale verlopen-sessie-vangrail + zoek-fout-norm (commit `5d007b4`).** Eén afhandelpunt in
>   `api.js` op het bewezen-gefaalde-refresh-punt → redirect `login?sessie_verlopen=1&next=<pad>`;
>   framework-loze callback-bedrading; nooit rauwe `NIET_GEAUTHENTICEERD` in beeld.
> - **Ter-plekke-aanmaken (afdeling) via gedeelde `AfdelingSelect`** op 4 plekken (PartijFormulier,
>   ContactpersoonSelect, GebruikersbeheerView, GebruikersgroepSectie) — commits `bebf658`, `4534533`.
> - **Gebruiker aanmaken** met organisatie (intern-only) + gescoopte afdeling (in `b1fde48`), en
>   **gebruiker bewerken** org/afdeling + picker-voorvul-fix + accountsysteem-fix + 2e interne
>   testorganisatie + stale-label-`:key` + picker-integratie-testpatroon (commit `ca8c999`).
> - **Skills: 18 LI032-patronen vastgelegd** (deze afsluit-commit) over domeinmodel/ux/frontend/
>   security/resilience/tests/werkprotocol.
>
> Tests: backend **866** (module, 2 skipped) + **80** (platform) · frontend **825** (69 files).
> Migratie-head **0054**. Bekende niet-blokkerende ruis: `LandschapskaartView.test.js` /
> `LandschapskaartPopups` cytoscape-teardown-flake (unhandled-rejections, geen testfalen).

## ⚙️ Eerste runtime-stap (dev-DB)
De dev-DB is deze sessie gemigreerd (0054) en gereseed (incl. de tweede interne organisatie
**RID Rivierenland** + afdelingen). Bij twijfel over verse data: gedocumenteerde stack-reset —
`docker compose down` → `docker volume rm likara_lk_postgres_data` → `docker compose up -d` →
`docker exec -w /app lk-api python3 dev_seed_testdata.py`. (`down -v` staat op **deny**.)

## Top-5 prioriteiten (volgende sessie)

1. **GebruikersgroepDetail** op het schone model (feitenonderzoek + opzet stonden al; verst
   gevorderd). Eén invalshoek-neutrale detailpagina op `gebruikersgroepen/:id`; applicatie-kant-ingang
   eerst; alleen groep-eigen signalen. Bekende kleine gaten: objecthistorie-allowlist
   `objecthistorie._TYPES` mist `gebruikersgroep` (`haal_op` bestaat al); applicatie-naam vs -id in de read.
2. **BlokkadeDetail** — eerst **ontwerpkeuze met Bert**: eigen pagina vs. doorklik naar de
   component-checklisttab. Beslissen vóór bouw. Restpunt: `BlokkadeRead` verrijken met herkomst
   (checklistvraag `vraag_code`/`vraag`/score).
3. **"afdeling — organisatie" breder doortrekken** — de org-context-ontdubbeling ook toepassen op de
   **ContractFormulier-leverancier-picker** en **PartijLijst** (de resterende niet-org-gescoopte
   afdeling/persoon-lijsten; PartijLijst intern/extern-kolom/badge hoort hier ook).

**Zwaarste los item (verse sessie):** **Impact-verkenner render-herbouw** — één deterministische
render-eigenaar; edges-onzichtbaar-bug in de echte cytoscape-render (logica bewezen correct); met
échte render-verificatie + de Cytoscape-mock-consoleruis (incl. de parallel-flake) opruimen.

**Bestaande backlog (ongewijzigd meenemen):** ADR-035 slice 3 (configureerbare score-drempel);
roltoewijzing-/verantwoordelijkheid-partij-picker-scope (domeinvraag: welke aarden mogen een rol
dragen); ADR-036-vervolg (coarse organisatiegebruik-UI); RelatieKenmerk-velduitleg (wacht op
invoerveld); dode-code-opschoning.

---

## Geparkeerde vervolgpunten uit LI032 (expliciet, niet stil — zie OPVOLGPUNTEN.md)
1. **Gebruikersnaam≠e-mail provisioning** — de update-PUT stuurt geen username meer (opgelost);
   controleer of elders in provisioning nog aannames op `username==email` zitten. (Laag, auth.)
2. **404 op een verdwenen bewerk-/detailitem** vriendelijker tonen (inline "bestaat niet (meer)"
   i.p.v. toast op een leeg formulier). Laag, UX (kwam op bij de reseed-stale-id-casus).
3. **Echte auth-keten-test** — end-to-end: korte token-TTL → echte `/auth/refresh` → echte
   Keycloak-grant → Redis-rotatie → geslaagde retry; plus een écht-verlopen refresh → login. Nu
   alleen offline-gemockt geborgd.
4. **Reseed-ergonomie / sessie stil dood bij stack-herstart** (Redis/Keycloak-persistentie) — de
   vangrail vangt het symptoom al af; dit is de dev-ergonomie-kant.
5. **`LandschapskaartView.test.js` parallel-flake** (cytoscape unhandled-rejections) — mee te nemen
   bij de impact-verkenner-render-herbouw.

---

## Openstaande punten (volledig)

### LI032 gebruiker-cluster — ✅ GELAND (V033, migratie 0054)
- Contactpersoon uit register (`0b91493`) · sessie-vangrail + zoek-norm (`5d007b4`) · afdeling
  ter-plekke-aanmaken (`bebf658`, `4534533`) · gebruiker aanmaken (`b1fde48`) · gebruiker bewerken
  org/afdeling + picker-/accountsysteem-fixes + 2e interne org + stale-label + testpatroon (`ca8c999`)
  · skills 18 patronen (afsluit-commit).

### Detailpagina's (gebruikersgroep + blokkade) — top-5 #1/#2
- Standalone pagina's ontbreken nog. GebruikersgroepDetail-grounding gedaan; BlokkadeDetail vraagt
  eerst de conceptuele keuze. Objecthistorie `_TYPES` uitbreiden met `gebruikersgroep` (+ `blokkade`).

### ADR-038 / gebruikersgroep-consolidatie + intern/extern — ✅ GELAND (V032, migraties 0052–0053)
- **Open vervolg (top-5 #3):** intern/extern in PartijLijst (kolom/badge) — bewust uitgesteld.

### ADR-037 / verantwoordelijke per checklistantwoord — ✅ GELAND (V031, migratie 0051)
### ADR-036 / organisatiegebruik — ✅ GELAND (V030) · vervolg: coarse organisatiegebruik-UI (klein onderhoud)
### ADR-036a / afdeling structureel — ✅ GELAND (V030, migratie 0050)

### Auth/sessie-cluster — deels geland in LI032
- Vangrail (b) geland. Rest geparkeerd: (a) reseed doodt levende sessies stil; (c) echte
  auth/refresh-keten-test (nu gemockt) — zie geparkeerde vervolgpunten 3/4.

### Impact-verkenner — zwaarste los item
- Render-bug (edges onzichtbaar op preset-pad) onopgelost; logica/model bewezen correct.
- Test-hygiëne: cytoscape unhandled-rejection-consoleruis + parallel-flake — geen falende test;
  bij render-herbouw meenemen (geparkeerd vervolgpunt 5).

### ADR-035 Signalering
- Slice 3 (configureerbare score-drempel) — uitgesteld. Badges op detail-pagina's — bij top-5 #1/#2.

### Partij-pickers
- Verantwoordelijkheid-/roltoewijzing-partij-picker ongefilterd → eerst domeinvraag, dán scoping.
  Contract-leverancier-picker versmald (`aard_in`); org-context nog toe te voegen (top-5 #3).

### Velduitleg
- **Parked:** RelatieKenmerk-dimensie-velduitleg (content klaar; wacht op een invoerveld).

### Cosmetic/klein
- Zoekbalk-contextlabel "Component toevoegen aan beeld" in kaart-modus. Dode-code-opschoning.

### Strategisch (parked)
- Export/import/rapportage — scope apart te bepalen.
- **DC013** — GitHub-repo/remote-rename + lokale map-opruiming (Berts actie).
- Deploy-side `.env`/secrets bijwerken op andere omgevingen; `~/likara/secrets/` daadwerkelijk vullen.


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — LIKARA V033"
4. Wacht op START: [naam] van Bert
