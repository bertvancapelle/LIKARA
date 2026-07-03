# LIKARA — Projectgeheugen

> Repo-gebundeld projectgeheugen. Bijwerken bij **elke** sessie-afsluiting **vóór**
> `gen_build.py`, zodat het automatisch in de sessie-ZIP wordt meegenomen
> (`gen_sessiestart.py` globt `docs/*.md`). Spiegel hierna de claude.ai-memory.

## Bouwstand
- **Build:** V030 · 2026-07-03
- **Commit:** 0e439d3 (contract-leverancier picker) — sessie-afsluiting V030 volgt
- **Tests:** backend 914 / 2 skipped / 0 failed · frontend 763 groen (66 files) · 0 kritieken
- **Migratie-head:** `0050_adr036a_gg_afdeling`
- **TST-rapport:** `docs/TST-V030-Validatierapport.md`

## Deze sessie (ADR-036 + Velduitleg + ADR-036a) — organisatiegebruik end-to-end AFGEROND
**Kader:** organisatiegebruik van applicaties end-to-end gebouwd, veld-uitleg op alle formulieren, de
afdeling structureel gemaakt, plus drie gerichte UI-fixes. Puur registratief; score = enige lifecycle-driver.
- **ADR-036 (`8e7e419`, `bff1254`, `889fc4d`):** grof "organisatie gebruikt applicatie"-feit
  (`organisatiegebruik`) + gebruikersgroep als fijne verfijning (`gebruik_id`); kaart-afleiding "gebruikt
  door", read-only signaal "gebruik bekend, detaillering ontbreekt", identiteit "afdeling — organisatie";
  invariant-test "afdeling-met-org ⟹ grof feit".
- **Velduitleg (`7cc6e24`, `8ea87be`):** `VeldUitleg`-component + centrale `velduitleg.js`; popover-'i'
  uitgerold over alle formulieren.
- **ADR-036a (`480fa84`, `a09a8cb`, migratie 0050):** afdeling structureel — `afdeling_id` →
  organisatie_eenheid-partij binnen de grove-feit-organisatie; search-first afdeling-picker (aanmaken in
  de lege zoekstaat).
- **UI-fixes (`929435e`, `0e439d3`):** bewerken-voorvulling gebruikersgroep (organisatie voorvullen uit
  grof feit + `initieel-weergave`); contract-leverancier-picker versmald naar `aard_in`
  (organisatie/organisatie_eenheid/externe_partij); seed geverifieerd geldig.
- **Eigenaar-organisatie-picker:** onderzocht, **geen defect** (filter correct, 4 orgs geseed, query levert
  alle 4) — "alleen BvoWB" was stale seed-data; reseed lost het op.
- **Signaaltelling gecorrigeerd:** feitelijk **9 signaaltypen (3 kritiek / 6 aandacht)** — skill bijgetrokken.

## Top-5 prioriteiten volgende sessie
1. **GebruikersgroepDetail + BlokkadeDetail** — ontgrendeld (betekenislaag is er); BlokkadeDetail-
   restpunten: herkomst in `BlokkadeRead`, eigenaar = vrij tekstveld, `objecthistorie._TYPES` uitbreiden
2. **ADR-036 "begin grof"-invoerroute** — frontend-formulier om een grof feit los vast te leggen
   (backend bestaat al); zonder dit vuurt "detaillering ontbreekt" alleen op seed-data
3. **Impact-verkenner render-herbouw** — deterministische render-eigenaar + echte render-verificatie
   (incl. het losse Cytoscape-mock-consoleruispunt in `LandschapskaartView.test.js`)
4. **ADR-035 Slice 3** — "Registratie onvolledig" (configureerbare score-drempelwaarde)
5. **Verantwoordelijkheid-/roltoewijzing-partij-picker scope** — eerst domeinvraag, dán scoping

## Resterend uit de rebrand (geen code)
- **DC013** — GitHub-repo/remote `bertvancapelle/CompliData` → LIKARA + remote-URL; lokale
  map `~/complidata/` opruimen (stack draait op `~/likara/`). Berts GitHub-actie.
- **Deploy-side** — andere omgevingen: `.env`/secrets bijwerken (`RABBITMQ_URL`→`lk_rabbit`,
  `MINIO_ROOT_USER`→`likara_admin`, cookie-/env-namen) + re-provision.
- **OP-30** — env-test-robuustheid: `test_callback_succes_zet_lk_session_cookie` laat
  `cookie_secure` van de omgeving afhangen; expliciet zetten.
- **Procesgat secrets-backup** — `~/likara/secrets/` gedocumenteerd maar feitelijk nooit gevuld → verzoenen.

> Volledige backlog: `docs/OPVOLGPUNTEN.md` (enige bron).
