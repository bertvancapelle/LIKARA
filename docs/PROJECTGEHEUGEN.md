# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V029 · 2026-07-02
- **Commit:** b351b59 (ADR-028 slice 4) — sessie-afsluiting V029 volgt
- **Tests:** backend 898 / 2 skipped / 0 failed · frontend 742 groen (65 files) · 0 kritieken
- **Migratie-head:** `0048_adr028_classificatie`
- **TST-rapport:** `docs/TST-V029-Validatierapport.md`

## Deze sessie (LI060 + ADR-028) — componenttype-catalogus + componentclassificatie AFGEROND
**Kader:** componenttype-catalogus verrijkt (8 typen) én twee registratieve instance-labels op elk
component (rol + BIV), los van het type. Puur registratief; score = enige lifecycle-driver.
- **LI060 (`7c36b33`):** 8 componenttypen — `applicatieserver`→`server_compute`,
  `middleware`→`integratievoorziening` (system_software/technology — eigen bindweefsel), nieuw
  `landelijke_voorziening` (application_service/application); drie extra beoordeelbaar (1 startvraag elk).
  Geen migratie (seed = single source; reseed).
- **ADR-028 slice 1 (0048, `d61bddf`):** schema-fundament — 2 platform-catalogi (`componentrol_optie`,
  `biv_schaal_optie`; single-purpose, ordinale BIV via `volgorde`) + 4 component-kolommen (rol NOT NULL
  default `interne_applicatie`; 3× BIV nullable) + RBAC (2 `PlatformEntiteit`) + audit.
- **ADR-028 slice 2 (`939dbf2`):** formulier + detail (rol + BIV) + `RolConfigBeheer`/`BivConfigBeheer` +
  additief `/componenten/opties` (rol-opties + ordinale BIV-niveaus).
- **ADR-028 slice 3 (`131b674`):** rol/BIV-filter in lijst (server-side, drempel op `volgorde`) + kaart
  (client-side, filter-exemptie context-nodes) + gestippelde rand voor `externe_dataprovider`.
- **ADR-028 slice 4 (`b351b59`):** kritiek signaal "BIV-classificatie onvolledig" (≥1 BIV-veld leeg) —
  signalering nu **11 signaaltypen** (6 kritiek / 5 aandacht).
- **Engine-invariant dubbel geborgd** (import-afwezigheid + function-bronscan + live geen-profiel).
- **ADR-036 (nieuw, functioneel besloten — bouw uitgesteld):** organisatiegebruik van applicaties (grof
  feit + gebruikersgroep als fijne verfijning + read-only signaal). Grounding GebruikersgroepDetail +
  BlokkadeDetail gedaan; geparkeerd tot ADR-036 beslist.

## Top-5 prioriteiten volgende sessie
1. **ADR-036 bouwen** — organisatiegebruik (grof feit + verfijning + signaal); schema-rakend,
   design-checkpoint first (open bouwknopen in `docs/adr/ADR-036`)
2. **GebruikersgroepDetail + BlokkadeDetail** — ná ADR-036 (hangen eraan); grounding gedaan
3. **Impact-verkenner render-herbouw** — deterministische render-eigenaar + echte render-verificatie
   (incl. het losse Cytoscape-mock-consoleruispunt in `LandschapskaartView.test.js`)
4. **ADR-035 Slice 3** — "Registratie onvolledig" (configureerbare score-drempelwaarde)
5. **Componenttype-vervolg / dode-code-opschoning**

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL; lokale
  map `~/complidata/` opruimen (stack draait op `~/likara/`). Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken (`RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-/env-namen) + re-provision.
- **OP-30** — env-test-robuustheid: `test_callback_succes_zet_lk_session_cookie` laat
  `cookie_secure` van de omgeving afhangen; expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar feitelijk nooit gevuld → verzoenen.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
