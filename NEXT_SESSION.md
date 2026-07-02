# LIKARA — Next Session (V029)

> **Sessie LI060 + ADR-028 (V029):** componenttype-catalogus uitgebreid (8 typen, 3 extra
> beoordeelbaar) én **componentclassificatie (ADR-028) end-to-end** — rol + BIV door data/API/
> beheer/formulier/detail/lijst/kaart/signalering.
> - **LI060 (`7c36b33`):** 8 componenttypen; `applicatieserver`→`server_compute`,
>   `middleware`→`integratievoorziening` (system_software/technology), nieuw `landelijke_voorziening`.
> - **ADR-028 slices 1–4** (`d61bddf`, `939dbf2`, `131b674`, `b351b59`): 2 platform-catalogi
>   (`componentrol_optie`, `biv_schaal_optie`) + 4 component-kolommen (migratie 0048); beheerschermen;
>   rol/BIV in formulier/detail/lijst/kaart (drempel op `volgorde`, filter-exemptie, rand voor
>   externe dataprovider); kritiek signaal "BIV-classificatie onvolledig" (signalering nu 11 typen).
> - **ADR-036 (nieuw, functioneel besloten — bouw uitgesteld):** organisatiegebruik van applicaties.
>
> Laatste commit: `b351b59`. Tests: backend **898/0** (2 skipped) · frontend **742**. Migratie-head **0048**.

## Top-5 prioriteiten (volgende sessie)

1. **ADR-036 bouwen** — organisatiegebruik (grof "organisatie gebruikt applicatie"-feit +
   gebruikersgroep als fijne verfijning + read-only signaal "detaillering ontbreekt"). Schema-rakend,
   meerdere gate-slices; **design-checkpoint first** (open bouwknopen in `docs/adr/ADR-036`).

2. **GebruikersgroepDetail + BlokkadeDetail** — **ná** ADR-036 (de groep-pagina hangt aan de nieuwe
   betekenislaag); grounding is gedaan. BlokkadeDetail-restpunten: detail-read verrijken met herkomst;
   eigenaar = vrij tekstveld (geen structurele verantwoordelijke); `objecthistorie._TYPES` uitbreiden
   met gebruikersgroep + blokkade voor het 'i'-paneel.

3. **Render-/orkestratielaag Impact-verkenner herbouwen** — één deterministische render-eigenaar, géén
   cascade, met **echte** render-verificatie (headless-cytoscape/e2e) i.p.v. mocks. Zwaarste item; verse
   sessie. (Los test-hygiëne: ~30 Cytoscape-mock-consoleruis meenemen.)

4. **ADR-035 slice 3** — configureerbare score-drempel voor "Registratie onvolledig".

5. **Componenttype-vervolg / dode-code-opschoning.**

## Openstaande punten (volledig)

### Component-focus-herfundering — ✅ AFGEROND (LI057–LI059, migraties 0045–0047)
- Q1 per-type configureerbaar (`checklist_dragend`), Q2 velden component-breed NOT NULL + defaults,
  Q3 subtabel gedropt (0047), Q4 type vrij wijzigbaar met data-safety, Q5 enum-rename gedaan.
- Checklist-beheer is **tenant-scoped** (ADR-022 W1) — geen platform-brede checklist-baseline (bewust);
  platformbeheerder togglet `checklist_dragend` + baseline-inhoud in de seed.

### Impact-verkenner
- **Render-bug** (edges onzichtbaar op preset-pad; `nodes:visible` inzakking) — onopgelost, geagendeerd
  voor de render-herbouw (top-5 #2). Logica/model bewezen correct; zit in de echte cytoscape-render.
- Modus ego→impact ontkoppelen van set-grootte (ADR-033-revisie) — nog niet opgepakt.
- Swimlane (ADR-034, geparkeerd); Saved views als permanente hoofdingang (Fase D).
- **Los test-hygiëne-punt (pre-existing):** `LandschapskaartView.test.js` meldt ~29 unhandled-rejection-
  console­ruis uit de Cytoscape-mock (async teardown) — **geen falende test** (frontend 717/717). Bij de
  render-herbouw meenemen (schonere mock/teardown).

### ADR-035 Signalering
- Slice 3: "Registratie onvolledig" (configureerbare score-drempelwaarde) — uitgesteld.
- blokkade_zonder_eigenaar — structureel onmogelijk zonder schema-/semantiekherziening.
- badges op GebruikersgroepDetail/BlokkadeDetail — uitgesteld tot die detail-pagina's bestaan.

### Platform / detail-pagina's
- GebruikersgroepDetail + BlokkadeDetail standalone pagina's ontbreken.

### Cosmetic/klein
- Zoekbalk-contextlabel "Component toevoegen aan beeld" in kaart-modus.

### Strategisch (parked)
- Export/import/rapportage — scope apart te bepalen.
- **DC013** — GitHub-repo/remote-rename + lokale `~/complidata/`-map opruimen (Berts actie).
- Deploy-side `.env`/secrets bijwerken op andere omgevingen; `~/likara/secrets/` daadwerkelijk vullen.
