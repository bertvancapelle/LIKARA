# SESSIE_BRIEFING.md — LIKARA V030

**Gegenereerd**: 2026-07-03

---

## Bouwstatus

## Actuele bouwstatus

| Veld | Waarde |
|------|--------|
| Build | V030 |
| Datum | July 2026 |
| Commit | 0e439d3 |
| Tests | backend 914/2/0 · frontend 763 groen |
| TST-rapport | TST-V030-Validatierapport.md |
| Kritieke bevindingen | 0 |

---

## Recente commits

```
0e439d3 [frontend] contract-leverancier-picker naar geldige aarden — ADR-024
929435e [frontend] gebruikersgroep bewerken — organisatie correct voorvullen — ADR-036
a09a8cb [frontend] afdeling-aanmaak search-first — geen voortijdige duplicaten — ADR-036a
480fa84 feat(datamodel): ADR-036a — gebruikersgroep-afdeling structureel (afdeling_id FK)
8ea87be feat(frontend): velduitleg slice 2 — uitrol over alle formulieren (popover-'i')
```

---

## Prioriteiten volgende sessie

# LIKARA — Next Session (V030)

> **Sessie ADR-036 + Velduitleg + ADR-036a (V030):** organisatiegebruik van applicaties
> **end-to-end** gebouwd (grof feit + gebruikersgroep-verfijning + afleiding/signaal/identiteit),
> veld-uitleg op alle formulieren, de afdeling structureel gemaakt, plus drie gerichte UI-fixes.
> - **ADR-036 (`8e7e419`, `bff1254`, `889fc4d`):** grof organisatiegebruik-feit + gebruikersgroep
>   als fijne verfijning (`gebruik_id`); kaart-afleiding "gebruikt door", signaal "detaillering
>   ontbreekt", identiteit "afdeling — organisatie"; invariant-test "afdeling-met-org ⟹ grof feit".
> - **Velduitleg (`7cc6e24`, `8ea87be`):** `VeldUitleg`-component + centrale `velduitleg.js`;
>   content-uitrol (popover-'i') over alle formulieren.
> - **ADR-036a (`480fa84`, `a09a8cb`):** afdeling structureel — `afdeling_id` → organisatie_eenheid-
>   partij (migratie **0050**); search-first afdeling-picker (aanmaken in de lege zoekstaat).
> - **UI-fixes (`929435e`, `0e439d3`):** bewerken-voorvulling gebruikersgroep (organisatie uit grof
>   feit voorvullen); contract-leverancier-picker versmald naar geldige aarden (`aard_in`).
>
> Eigenaar-organisatie-picker: onderzocht, **geen defect** (stale seed-data; reseed toont alle 4 orgs).
>
> Laatste commit: `0e439d3`. Tests: backend **914/0** (2 skipped) · frontend **763**. Migratie-head **0050**.

## Top-5 prioriteiten (volgende sessie)

1. **GebruikersgroepDetail + BlokkadeDetail** — nu ontgrendeld (ADR-036/036a leverden de betekenislaag;
   grounding gedaan). BlokkadeDetail-restpunten: detail-read (`BlokkadeRead`) verrijken met **herkomst**
   (checklistvraag `vraag_code`/`vraag`/score); eigenaar blijft **vrij tekstveld**; `objecthistorie._TYPES`
   uitbreiden met `gebruikersgroep` + `blokkade` voor het 'i'-paneel.

2. **ADR-036 "begin grof"-invoerroute** — frontend-formulier om een grof organisatiegebruik-feit los vast
   te leggen (organisatie zonder afdeling). Backend bestaat al (`organisatiegebruik*` routes/schemas/
   services); zonder dit vuurt "detaillering ontbreekt" alleen op seed-data. Maakt ADR-036 end-to-end
   bruikbaar.

3. **Impact-verkenner render-herbouw** — één deterministische render-eigenaar; edges-onzichtbaar-bug zit
   in de echte cytoscape-render (logica bewezen correct). Zwaarste item, verse sessie; met échte
   render-verificatie i.p.v. mocks + de ~30 Cytoscape-mock-consoleruis opruimen.

4. **ADR-035 slice 3** — configureerbare score-drempel voor "Registratie onvolledig".

5. **Verantwoordelijkheid-/roltoewijzing-partij-picker scope** — eerst de **domeinvraag** (welke
   partij-aarden mogen een beheerrol dragen?), dán de picker-scoping. Niet blind versmallen.

**Klein onderhoud (kan meeliften, geen top-5-plek):** RelatieKenmerk-dimensie-velduitleg (content staat
klaar in `velduitleg.js`; wacht op een invoerveld — nu sectie-gedreven); dode-code-opschoning; de
cytoscape-test-ruis (bij #3).

---

## Openstaande punten (volledig)

### ADR-036 / organisatiegebruik — ✅ GELAND (V030)
- Grof feit `organisatiegebruik` + gebruikersgroep-verfijning (`gebruik_id`); kaart-afleiding "gebruikt
  door"; signaal "gebruik bekend, detaillering ontbreekt"; identiteit "afdeling — organisatie".
- **Open vervolg (top-5 #2):** frontend-invoerroute om een grof feit los vast te leggen.

### ADR-036a / afdeling structureel — ✅ GELAND (V030, migratie 0050)
- `gebruikersgroep.afdeling` (vrije tekst) → `afdeling_id` → organisatie_eenheid-partij binnen de
  grove-feit-organisatie (spiegel persoon→afdeling). Search-first afdeling-picker.

### Velduitleg — ✅ GELAND (V030)
- `VeldUitleg`-component + centrale `velduitleg.js`; popover-'i' op alle formulieren.
- **Parked:** RelatieKenmerk-dimensie-velduitleg (content klaar; wacht op een invoerveld).

### Component-focus-herfundering — ✅ AFGEROND (LI057–LI059, migraties 0045–0047)
- Q1 per-type configureerbaar (`checklist_dragend`), Q2 velden component-breed NOT NULL + defaults,
  Q3 subtabel gedropt (0047), Q4 type vrij wijzigbaar met data-safety, Q5 enum-rename gedaan.

### Detailpagina's (gebruikersgroep + blokkade) — ontgrendeld (top-5 #1)
- Standalone pagina's ontbreken nog; betekenislaag is er nu (ADR-036/036a). BlokkadeDetail-restpunten
  zoals in top-5 #1.

### Impact-verkenner
- **Render-bug** (edges onzichtbaar op preset-pad; `nodes:visible` inzakking) — onopgelost, geagendeerd
  voor de render-herbouw (top-5 #3). Logica/model bewezen correct; zit in de echte cytoscape-render.
- Modus ego→impact ontkoppelen van set-grootte (ADR-033-revisie) — nog niet opgepakt.
- Swimlane (ADR-034, geparkeerd); Saved views als permanente hoofdingang (Fase D).
- **Test-hygiëne (pre-existing):** ~30–33 unhandled-rejection-consoleruis uit de Cytoscape-mock in
  `LandschapskaartView.test.js` — **geen falende test** (frontend 763/763). Bij render-herbouw meenemen.

### ADR-035 Signalering
- Slice 3: "Registratie onvolledig" (configureerbare score-drempelwaarde) — uitgesteld (top-5 #4).
- blokkade_zonder_eigenaar — structureel onmogelijk zonder schema-/semantiekherziening.
- badges op GebruikersgroepDetail/BlokkadeDetail — bij die detail-pagina's (top-5 #1).

### Partij-pickers
- **Verantwoordelijkheid-/roltoewijzing-partij-picker** ongefilterd → eerst domeinvraag, dán scoping
  (top-5 #5). Contract-leverancier-picker is deze sessie al versmald (`aard_in`).

### Cosmetic/klein
- Zoekbalk-contextlabel "Component toevoegen aan beeld" in kaart-modus.
- Dode-code-opschoning.

### Strategisch (parked)
- Export/import/rapportage — scope apart te bepalen.
- **DC013** — GitHub-repo/remote-rename + lokale `~/complidata/`-map opruimen (Berts actie).
- Deploy-side `.env`/secrets bijwerken op andere omgevingen; `~/likara/secrets/` daadwerkelijk vullen.


---

## Instructie voor CC

1. Lees deze briefing volledig
2. Lees CLAUDE.md (sessiestart-protocol)
3. Bevestig: "Sessie-briefing geladen — LIKARA V030"
4. Wacht op START: [naam] van Bert
